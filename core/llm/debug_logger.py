"""
Agent调试日志系统

记录所有Agent的活动信息，包括：
- LLM请求/响应
- 工具调用/结果
- 专家分析过程
- 耗时统计

使用方式：
    logger = AgentDebugLogger()
    session_id = logger.start_session(fen, question)
    logger.log_input("tactics", {"messages": [...]})
    logger.log_output("tactics", {"content": "...", "tool_calls": [...]}, duration_ms=1500)
    logger.end_session()
"""

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Any, Optional
import uuid


@dataclass
class AgentLogEntry:
    """单条日志记录"""
    timestamp: str           # ISO格式时间
    session_id: str          # 会话ID
    agent_type: str          # orchestrator | tactics | strategy | engine | synthesizer
    event_type: str          # input | output | tool_call | tool_result | thinking | error | start | end
    data: Dict[str, Any]     # 具体内容
    duration_ms: int = 0     # 耗时（毫秒）

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class AnalysisSessionLog:
    """一次完整分析的日志"""
    session_id: str
    fen: str
    question: str
    start_time: str
    end_time: str = None
    entries: List[Dict] = field(default_factory=list)

    # 汇总信息
    total_duration_ms: int = 0
    total_tool_calls: int = 0
    expert_results: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return asdict(self)


class AgentDebugLogger:
    """Agent调试日志记录器"""

    def __init__(self, log_dir: str = "logs/agent_debug", enabled: bool = True):
        self.log_dir = log_dir
        self.enabled = enabled
        self.current_session: Optional[AnalysisSessionLog] = None
        self._start_time: Optional[datetime] = None
        self._event_times: Dict[str, datetime] = {}  # 用于计算耗时

    def start_session(self, fen: str, question: str) -> str:
        """开始新会话，返回session_id"""
        if not self.enabled:
            return ""

        session_id = f"sess_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        self._start_time = datetime.now()

        self.current_session = AnalysisSessionLog(
            session_id=session_id,
            fen=fen,
            question=question,
            start_time=self._start_time.isoformat(),
        )

        self._log_event(
            agent_type="orchestrator",
            event_type="start",
            data={"action": "开始分析", "fen": fen, "question": question}
        )

        return session_id

    def log_input(self, agent_type: str, data: Dict, event_id: str = None):
        """记录输入（如LLM请求的messages）"""
        if not self.enabled or not self.current_session:
            return

        event_id = event_id or f"{agent_type}_{datetime.now().strftime('%H%M%S_%f')}"
        self._event_times[event_id] = datetime.now()

        # 简化messages记录（避免过长）
        simplified_data = self._simplify_data(data)

        self._log_event(
            agent_type=agent_type,
            event_type="input",
            data=simplified_data,
        )

    def log_output(self, agent_type: str, data: Dict, duration_ms: int = 0, event_id: str = None):
        """记录输出（如LLM响应）"""
        if not self.enabled or not self.current_session:
            return

        # 计算实际耗时
        if event_id and event_id in self._event_times:
            start = self._event_times.pop(event_id)
            duration_ms = int((datetime.now() - start).total_seconds() * 1000)

        self._log_event(
            agent_type=agent_type,
            event_type="output",
            data=self._simplify_data(data),
            duration_ms=duration_ms,
        )

    def log_tool_call(self, agent_type: str, tool_name: str, arguments: Dict):
        """记录工具调用"""
        if not self.enabled or not self.current_session:
            return

        self.current_session.total_tool_calls += 1

        self._log_event(
            agent_type=agent_type,
            event_type="tool_call",
            data={
                "tool_name": tool_name,
                "arguments": arguments,
            }
        )

    def log_tool_result(self, agent_type: str, tool_name: str, result: Dict, duration_ms: int = 0):
        """记录工具返回"""
        if not self.enabled or not self.current_session:
            return

        self._log_event(
            agent_type=agent_type,
            event_type="tool_result",
            data={
                "tool_name": tool_name,
                "result": self._simplify_data(result),
            },
            duration_ms=duration_ms,
        )

    def log_expert_start(self, agent_type: str):
        """记录专家开始分析"""
        if not self.enabled or not self.current_session:
            return

        self._log_event(
            agent_type=agent_type,
            event_type="expert_start",
            data={"action": f"开始{agent_type}专家分析"}
        )

    def log_expert_result(self, agent_type: str, finding: str, details: str = None, success: bool = True):
        """记录专家分析结果"""
        if not self.enabled or not self.current_session:
            return

        self.current_session.expert_results[agent_type] = finding[:100] + "..." if len(finding) > 100 else finding

        self._log_event(
            agent_type=agent_type,
            event_type="expert_result",
            data={
                "finding": finding,
                "details": details[:500] if details else None,
                "success": success,
            }
        )

    def log_thinking(self, agent_type: str, message: str):
        """记录思考过程"""
        if not self.enabled or not self.current_session:
            return

        self._log_event(
            agent_type=agent_type,
            event_type="thinking",
            data={"message": message}
        )

    def log_error(self, agent_type: str, error: str):
        """记录错误"""
        if not self.enabled or not self.current_session:
            return

        self._log_event(
            agent_type=agent_type,
            event_type="error",
            data={"error": error}
        )

    def end_session(self) -> Optional[AnalysisSessionLog]:
        """结束会话，保存日志文件"""
        if not self.enabled or not self.current_session:
            return None

        end_time = datetime.now()
        self.current_session.end_time = end_time.isoformat()

        if self._start_time:
            self.current_session.total_duration_ms = int((end_time - self._start_time).total_seconds() * 1000)

        self._log_event(
            agent_type="orchestrator",
            event_type="end",
            data={
                "action": "分析完成",
                "total_tool_calls": self.current_session.total_tool_calls,
                "total_duration_ms": self.current_session.total_duration_ms,
            }
        )

        # 保存到文件
        self._save_to_file()

        return self.current_session

    def _log_event(self, agent_type: str, event_type: str, data: Dict, duration_ms: int = 0):
        """记录一条事件"""
        if not self.current_session:
            return

        entry = AgentLogEntry(
            timestamp=datetime.now().isoformat(),
            session_id=self.current_session.session_id,
            agent_type=agent_type,
            event_type=event_type,
            data=data,
            duration_ms=duration_ms,
        )

        self.current_session.entries.append(entry.to_dict())

    def _simplify_data(self, data: Dict, max_length: int = 1000) -> Dict:
        """简化数据，避免日志过长"""
        result = {}
        for key, value in data.items():
            if isinstance(value, str) and len(value) > max_length:
                result[key] = value[:max_length] + f"... (截断，原长{len(value)})"
            elif isinstance(value, dict):
                result[key] = self._simplify_data(value, max_length)
            elif isinstance(value, list):
                if len(value) > 10:
                    result[key] = value[:10] + [f"... (共{len(value)}项)"]
                else:
                    result[key] = [self._simplify_data(v, max_length) if isinstance(v, dict) else v for v in value]
            else:
                result[key] = value
        return result

    def _save_to_file(self):
        """保存日志到文件"""
        if not self.current_session:
            return

        try:
            os.makedirs(self.log_dir, exist_ok=True)

            # JSON格式
            json_path = os.path.join(self.log_dir, f"{self.current_session.session_id}.json")
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(self.current_session.to_dict(), f, ensure_ascii=False, indent=2)

            # 可读文本格式
            txt_path = os.path.join(self.log_dir, f"{self.current_session.session_id}.txt")
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(self.export_readable())

        except Exception as e:
            import traceback
            print(f"[DebugLogger] 保存日志失败: {e}")
            traceback.print_exc()

    def export_json(self) -> str:
        """导出为JSON格式"""
        if not self.current_session:
            return "{}"
        return json.dumps(self.current_session.to_dict(), ensure_ascii=False, indent=2)

    def export_readable(self) -> str:
        """导出为可读的文本日志"""
        if not self.current_session:
            return ""

        lines = []
        session = self.current_session

        # 头部
        lines.append("=" * 80)
        lines.append(f"会话ID: {session.session_id}")
        lines.append(f"开始时间: {session.start_time}")
        lines.append(f"FEN: {session.fen}")
        lines.append(f"问题: {session.question}")
        lines.append("=" * 80)
        lines.append("")

        # 事件记录
        for entry in session.entries:
            ts = entry['timestamp'].split('T')[1].split('.')[0] if 'T' in entry['timestamp'] else entry['timestamp']
            agent = entry['agent_type'].upper()
            event = entry['event_type']
            data = entry['data']
            duration = entry.get('duration_ms', 0)

            # 事件类型格式化
            if event == "start":
                lines.append(f"[{ts}] {agent} > 开始分析")
            elif event == "end":
                lines.append("")
                lines.append("=" * 80)
                lines.append("会话汇总")
                lines.append(f"  总耗时: {session.total_duration_ms / 1000:.1f}秒")
                lines.append(f"  工具调用: {session.total_tool_calls}次")
                if session.expert_results:
                    lines.append("  专家结果:")
                    for expert, finding in session.expert_results.items():
                        lines.append(f"    - {expert}: {finding}")
                lines.append("=" * 80)
            elif event == "expert_start":
                lines.append("")
                lines.append("-" * 80)
                lines.append(f"[{ts}] {agent} > 开始分析")
            elif event == "expert_result":
                lines.append(f"[{ts}] {agent} > 分析完成")
                finding = data.get('finding', '')
                if finding:
                    lines.append(f"  发现: {finding[:200]}")
            elif event == "input":
                lines.append(f"[{ts}] {agent} > INPUT")
                if 'messages' in data:
                    for msg in data.get('messages', [])[:4]:  # 只显示前4条
                        role = msg.get('role', 'unknown')
                        content = str(msg.get('content', ''))[:100]
                        lines.append(f"    [{role.upper()}] {content}...")
            elif event == "output":
                dur_str = f" (耗时 {duration}ms)" if duration else ""
                lines.append(f"[{ts}] {agent} > OUTPUT{dur_str}")
                content = data.get('content', '')
                if content:
                    lines.append(f"  {content[:200]}")
                tool_calls = data.get('tool_calls', [])
                if tool_calls:
                    # 处理tool_calls可能是字符串或字典的情况
                    tool_names = []
                    for tc in tool_calls:
                        if isinstance(tc, dict):
                            func = tc.get('function')
                            if isinstance(func, dict):
                                tool_names.append(func.get('name', 'unknown'))
                            elif isinstance(func, str):
                                tool_names.append(func)
                            else:
                                tool_names.append('unknown')
                        else:
                            tool_names.append(str(tc)[:50])
                    lines.append(f"  工具调用: {tool_names}")
            elif event == "tool_call":
                tool_name = data.get('tool_name', 'unknown')
                args = data.get('arguments', {})
                lines.append(f"[{ts}] {agent} > TOOL_CALL: {tool_name}")
                lines.append(f"  参数: {json.dumps(args, ensure_ascii=False)[:150]}")
            elif event == "tool_result":
                tool_name = data.get('tool_name', 'unknown')
                result = data.get('result', {})
                dur_str = f" (耗时 {duration}ms)" if duration else ""
                lines.append(f"[{ts}] {agent} > TOOL_RESULT{dur_str}")
                result_str = json.dumps(result, ensure_ascii=False)
                lines.append(f"  {result_str[:200]}")
            elif event == "thinking":
                lines.append(f"[{ts}] {agent} > THINKING: {data.get('message', '')}")
            elif event == "error":
                lines.append(f"[{ts}] {agent} > ERROR: {data.get('error', '')}")
            else:
                lines.append(f"[{ts}] {agent} > {event.upper()}: {str(data)[:100]}")

        return "\n".join(lines)


# 全局实例（可选）
_global_logger: Optional[AgentDebugLogger] = None

def get_debug_logger() -> AgentDebugLogger:
    """获取全局调试日志记录器"""
    global _global_logger
    if _global_logger is None:
        _global_logger = AgentDebugLogger()
    return _global_logger

def set_debug_logger(logger: AgentDebugLogger):
    """设置全局调试日志记录器"""
    global _global_logger
    _global_logger = logger
