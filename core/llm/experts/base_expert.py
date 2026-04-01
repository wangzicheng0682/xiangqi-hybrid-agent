"""
专家Agent基类 - 共享逻辑

提供三个专家共用的基础设施：
- LLM API调用（含流式）
- 棋盘布局生成
- 工具执行
- 共享上下文构建
"""

import json
import os
import re
import time
import requests
from typing import Dict, List, Any, Callable, Optional, TYPE_CHECKING
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from core.llm.agent_tools import AgentTools, ToolResult
    from core.llm.debug_logger import AgentDebugLogger

from core.llm.agent_tools import AgentTools, ToolResult
from core.llm.tracing import get_tracer, SpanNames, SpanAttributes

# ═══════════════════════════════════════════════════════════════════════════════
# 工具元数据 - 用于生成元叙事小标题
# ═══════════════════════════════════════════════════════════════════════════════

TOOL_META = {
    "get_piece_attacks": "攻击关系",
    "get_piece_defenders": "保护关系",
    "get_threats_to_piece": "威胁关系",
    "get_piece_relations": "棋子关系",
    "analyze_move": "走法效果",
    "compare_moves": "走法对比",
    "get_forcing_sequence": "强制序列",
    "engine_deep_analysis": "局面评分",
    "engine_alternatives": "候选走法",
    "analyze_position_strategy": "战略分析",
}


STEP_PATTERN = re.compile(r"^\[STEP:\s*(.+?)\s*\]$")
_SECTION_RE = re.compile(r"^【(.+?)】")


def parse_step_blocks(content: str) -> List[Dict[str, str]]:
    """从带 [STEP: ...] 或 【节标题】 标记的文本中拆出步骤块。"""
    if not content:
        return []

    steps: List[Dict[str, str]] = []
    current_title: Optional[str] = None
    current_lines: List[str] = []
    saw_marker = False

    for raw_line in content.replace("\r\n", "\n").split("\n"):
        stripped = raw_line.strip()
        match = STEP_PATTERN.match(stripped)
        if not match:
            match = _SECTION_RE.match(stripped)
        if match:
            saw_marker = True
            if current_title is not None:
                steps.append({
                    "title": current_title,
                    "content": "\n".join(current_lines).strip(),
                })
            current_title = match.group(1).strip()
            current_lines = []
            continue

        if current_title is not None:
            current_lines.append(raw_line)

    if current_title is not None:
        steps.append({
            "title": current_title,
            "content": "\n".join(current_lines).strip(),
        })

    return steps if saw_marker else []


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class ExpertResult:
    """专家分析结果"""
    expert_name: str
    finding: str  # 专家的核心发现
    details: str  # 详细分析内容
    tool_calls: List[Dict] = field(default_factory=list)
    success: bool = True
    error: Optional[str] = None


@dataclass
class ExpertConfig:
    """专家配置"""
    name: str  # 英文名，如 "tactics"
    display_name: str  # 中文显示名，如 "战术专家"
    role: str  # 角色描述
    system_prompt: str  # 专家System Prompt
    tools: List[Dict]  # 该专家可用的工具Schema
    tool_names: List[str]  # 该专家可用的工具名列表
    max_rounds: int = 3  # 最大Agent循环轮次
    max_tokens: int = 1024  # 最大输出token（提升以支持深度分析）


class BaseExpert:
    """专家Agent基类"""

    PIECE_NAMES = {
        'K': '红帅', 'k': '黑将',
        'A': '红仕', 'a': '黑士',
        'B': '红相', 'b': '黑象',
        'N': '红马', 'n': '黑马',
        'R': '红车', 'r': '黑车',
        'C': '红炮', 'c': '黑炮',
        'P': '红兵', 'p': '黑卒',
    }

    def __init__(self, api_key: str = None, model: str = "glm-5",
                 base_url: str = "https://open.bigmodel.cn/api/paas/v4/",
                 debug_logger: "AgentDebugLogger" = None):
        self.api_key = api_key or os.getenv("ALIYUN_API_KEY")
        self.base_url = base_url
        self.model = model
        self.tools = AgentTools()
        self.debug_logger = debug_logger  # 调试日志记录器

        self._tool_functions = {
            "get_piece_attacks": self.tools.get_piece_attacks,
            "get_piece_defenders": self.tools.get_piece_defenders,
            "get_threats_to_piece": self.tools.get_threats_to_piece,
            "get_piece_relations": self.tools.get_piece_relations,
            "analyze_move": self.tools.analyze_move,
            "compare_moves": self.tools.compare_moves,
            "get_forcing_sequence": self.tools.get_forcing_sequence,
            "engine_deep_analysis": self.tools.engine_deep_analysis,
            "engine_alternatives": self.tools.engine_alternatives,
            "analyze_position_strategy": self.tools.analyze_position_strategy,
        }

    def _generate_board_layout(self, fen: str) -> str:
        """生成棋盘布局的可读格式"""
        try:
            board_part = fen.split()[0]
            rows = board_part.split('/')

            red_pieces = []
            black_pieces = []

            for row_idx, row in enumerate(rows):
                col_idx = 0
                for char in row:
                    if char.isdigit():
                        col_idx += int(char)
                    else:
                        x = col_idx + 1
                        y = 10 - row_idx
                        piece_name = self.PIECE_NAMES.get(char, char)
                        if char.isupper():
                            red_pieces.append(f"{piece_name}-({x},{y})")
                        else:
                            black_pieces.append(f"{piece_name}-({x},{y})")
                        col_idx += 1

            layout = "【红方棋子】\n"
            layout += "、".join(red_pieces) if red_pieces else "无"
            layout += "\n\n【黑方棋子】\n"
            layout += "、".join(black_pieces) if black_pieces else "无"
            return layout
        except Exception as e:
            return f"解析棋盘失败: {str(e)}"

    def _build_shared_context(
        self,
        fen: str,
        tag_summary: str,
        primary_tension: Dict,
        phase_info,
        question: str,
        move: str = None,
    ) -> str:
        """构建共享上下文（注入给每个专家）"""
        board_layout = self._generate_board_layout(fen)

        context = f"【当前局面】FEN: {fen}\n\n"
        context += f"【棋盘布局 - 这是唯一可信的棋子位置来源】\n{board_layout}\n\n"
        context += "[警告] 禁止编造任何未在此列出的棋子位置或坐标。\n\n"

        # 注入阶段信息，让专家知道当前阶段
        if phase_info:
            phase_name = getattr(phase_info, 'phase_name', str(phase_info))
            move_count = getattr(phase_info, 'move_count', 0)
            total_pieces = getattr(phase_info, 'total_pieces', 0)
            context += f"【当前阶段】{phase_name}（回合数≈{move_count}，剩余棋子≈{total_pieces}）\n\n"

        if tag_summary:
            tag_str = "\n".join(tag_summary) if isinstance(tag_summary, list) else tag_summary
            context += f"【局面事实 - 这是唯一可信的事实来源】\n"
            context += "以下结论由规则引擎计算得出，100%准确，你只能在这个范围内分析：\n"
            context += f"{tag_str}\n\n"
            context += "[警告] 禁止推断任何未在此列出的攻防关系。如需验证额外关系，必须调用工具。\n\n"

        if primary_tension:
            context += f"""【张力检测 - 已自动识别】
[张力] 主要张力：{primary_tension.get('tension_type', '')}（优先级：{primary_tension.get('priority', '')}）
[问题] 核心问题：{primary_tension.get('question', '')}
[假设] 初始假设：{primary_tension.get('hypothesis', '')}

"""

        if move:
            context += f"【刚走的棋】{move}\n\n"

        context += f"【问题】{question}"

        return context

    def _call_api(
        self,
        messages: List[Dict],
        tools: List[Dict] = None,
        agent_type: str = "expert",
    ) -> Dict:
        """调用LLM API（非流式），自动记录 OTEL Span"""
        if not self.api_key:
            return {"content": "API Key未配置", "tool_calls": [], "finish_reason": "error"}

        tracer = get_tracer()

        with tracer.start_as_current_span(
            SpanNames.LLM_CALL,
            attributes={
                SpanAttributes.LLM_MODEL: self.model,
                SpanAttributes.AGENT_TYPE: agent_type,
            }
        ) as span:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 2048,
                # GLM-5 原生支持 thinking 模式，内部推理链流式输出
                "thinking": {"type": "enabled"},
            }

            if tools:
                payload["tools"] = tools
                payload["tool_choice"] = "auto"

            # 记录输入
            if self.debug_logger:
                self.debug_logger.log_input(agent_type, {"messages": messages, "tools": [t.get("function", {}).get("name") for t in (tools or [])]})

            start_time = time.time()
            try:
                session = requests.Session()
                session.trust_env = False
                response = session.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=120,
                )

                duration_ms = int((time.time() - start_time) * 1000)
                span.set_attribute(SpanAttributes.LLM_DURATION_MS, duration_ms)

                if response.status_code == 200:
                    result = response.json()
                    choice = result.get("choices", [{}])[0]
                    message = choice.get("message", {})
                    api_result = {
                        "content": message.get("content", ""),
                        "reasoning_content": message.get("reasoning_content", ""),
                        "tool_calls": message.get("tool_calls", []),
                        "finish_reason": choice.get("finish_reason", "stop"),
                    }

                    # 记录 token 使用（如果有）
                    usage = result.get("usage", {})
                    if usage:
                        span.set_attribute(SpanAttributes.LLM_INPUT_TOKENS, usage.get("prompt_tokens", 0))
                        span.set_attribute(SpanAttributes.LLM_OUTPUT_TOKENS, usage.get("completion_tokens", 0))

                    # 记录输出
                    if self.debug_logger:
                        tool_names = []
                        for tc in api_result.get("tool_calls", []):
                            if isinstance(tc, dict):
                                func = tc.get("function")
                                if isinstance(func, dict):
                                    tool_names.append(func.get("name", "unknown"))
                                elif isinstance(func, str):
                                    tool_names.append(func)
                                else:
                                    tool_names.append("unknown")
                            else:
                                tool_names.append(str(tc)[:30])
                        self.debug_logger.log_output(agent_type, {
                            "content": api_result["content"][:500] if api_result["content"] else "",
                            "tool_calls": tool_names,
                            "finish_reason": api_result["finish_reason"],
                        }, duration_ms)
                    return api_result
                else:
                    error_result = {"content": f"API错误: {response.status_code}", "tool_calls": [], "finish_reason": "error"}
                    if self.debug_logger:
                        self.debug_logger.log_error(agent_type, f"API错误: {response.status_code}")
                    span.set_attribute(SpanAttributes.ERROR, True)
                    span.set_attribute(SpanAttributes.ERROR_MESSAGE, f"HTTP {response.status_code}")
                    return error_result
            except Exception as e:
                error_result = {"content": f"请求失败: {str(e)}", "tool_calls": [], "finish_reason": "error"}
                if self.debug_logger:
                    self.debug_logger.log_error(agent_type, str(e))
                span.set_attribute(SpanAttributes.ERROR, True)
                span.set_attribute(SpanAttributes.ERROR_MESSAGE, str(e))
                return error_result

    def _emit_structured_steps(
        self,
        expert_name: str,
        content: str,
        on_thinking: Callable[[str, str], None],
    ) -> bool:
        """将专家完整输出拆成结构化步骤事件。"""
        steps = parse_step_blocks(content)
        if not steps:
            return False

        for step_index, step in enumerate(steps):
            title = step["title"]
            body = step["content"]
            duration_ms = max(250, min(4000, len(body) * 18 if body else 300))

            on_thinking(
                "expert_step_start",
                json.dumps(
                    {
                        "expert": expert_name,
                        "step_index": step_index,
                        "title": title,
                    },
                    ensure_ascii=False,
                ),
            )

            if body:
                on_thinking(
                    "expert_step_content",
                    json.dumps(
                        {
                            "expert": expert_name,
                            "step_index": step_index,
                            "title": title,
                            "content": body,
                        },
                        ensure_ascii=False,
                    ),
                )

            on_thinking(
                "expert_step_end",
                json.dumps(
                    {
                        "expert": expert_name,
                        "step_index": step_index,
                        "title": title,
                        "duration_ms": duration_ms,
                    },
                    ensure_ascii=False,
                ),
            )

        return True

    def _call_expert(
        self,
        system_prompt: str,
        user_content: str,
        config: ExpertConfig,
        fen: str = None,
        on_thinking: Callable[[str, str], None] = None,
    ) -> ExpertResult:
        """
        通用专家分析流程：构建消息 → Agent循环 → 返回结论

        子类通过 config 提供专家特定的 system_prompt 和 tools
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

        tool_calls_log = []

        for round_num in range(config.max_rounds):
            if on_thinking:
                on_thinking(f"{config.name}_thinking", f"[{config.display_name}] 第{round_num + 1}轮分析...")

            response = self._call_api(messages, tools=config.tools)

            if response["finish_reason"] == "error":
                return ExpertResult(
                    expert_name=config.name,
                    finding="分析失败",
                    details=response["content"],
                    success=False,
                    error=response["content"],
                )

            content = response["content"]
            reasoning_content = response.get("reasoning_content", "")
            tool_calls = response.get("tool_calls", [])

            # GLM-5 thinking 内容单独 yield，前端可展示"正在思考"
            if on_thinking and reasoning_content:
                on_thinking(f"{config.name}_reasoning", reasoning_content)

            if on_thinking and content:
                emitted = self._emit_structured_steps(config.name, content, on_thinking)
                if not emitted:
                    on_thinking(f"{config.name}_chunk", content)

            # 工具调用循环
            if tool_calls:
                messages.append({"role": "assistant", "content": content or ""})
                assistant_tool_calls = []

                # 只读工具可并行执行（无副作用）
                READONLY_TOOLS = {
                    "get_piece_attacks", "get_piece_defenders", "get_threats_to_piece",
                    "get_piece_relations", "compare_moves", "analyze_position_strategy",
                }

                readonly_tcs = [tc for tc in tool_calls if tc["function"]["name"] in READONLY_TOOLS]
                other_tcs = [tc for tc in tool_calls if tc["function"]["name"] not in READONLY_TOOLS]

                # 1. 只读工具并行执行
                if readonly_tcs:
                    with ThreadPoolExecutor(max_workers=4) as executor:
                        futures = {}
                        for tc in readonly_tcs:
                            args = json.loads(tc["function"]["arguments"])
                            tool_calls_log.append({
                                "round": round_num,
                                "name": tc["function"]["name"],
                                "arguments": args,
                            })
                            if on_thinking:
                                tool_desc = TOOL_META.get(tc["function"]["name"], tc["function"]["name"])
                                on_thinking("headline", f"{config.display_name}正在验证{tool_desc}…")
                                on_thinking(f"{config.name}_tool", f"调用工具: {tc['function']['name']}")
                            if self.debug_logger:
                                self.debug_logger.log_tool_call(config.name, tc["function"]["name"], args)
                            futures[executor.submit(self._execute_tool, tc["function"]["name"], args, fen)] = tc

                        # 按 tool_call_id 排序后再 append，保持 LLM 上下文一致性
                        results = []
                        for future in futures:
                            tc = futures[future]
                            result = future.result()
                            results.append((tc["id"], tc, result))
                        results.sort(key=lambda x: x[0])

                        for tool_call_id, tc, result in results:
                            tool_msg = json.dumps(result, ensure_ascii=False)
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call_id,
                                "content": tool_msg,
                            })
                            if self.debug_logger:
                                self.debug_logger.log_tool_result(config.name, tc["function"]["name"], result)
                            if on_thinking:
                                msg_preview = result.get("message", str(result)[:80])
                                on_thinking(f"{config.name}_tool_result", f"{tc['function']['name']}: {msg_preview}")
                            assistant_tool_calls.append({
                                "id": tool_call_id,
                                "type": "function",
                                "function": {
                                    "name": tc["function"]["name"],
                                    "arguments": tc["function"]["arguments"],
                                }
                            })

                # 2. 其他工具（engine_deep_analysis 等）串行执行
                for tc in other_tcs:
                    tool_name = tc["function"]["name"]
                    tool_calls_log.append({
                        "round": round_num,
                        "name": tool_name,
                        "arguments": json.loads(tc["function"]["arguments"]),
                    })
                    if on_thinking:
                        tool_desc = TOOL_META.get(tool_name, tool_name)
                        on_thinking("headline", f"{config.display_name}正在验证{tool_desc}…")
                        on_thinking(f"{config.name}_tool", f"调用工具: {tool_name}")
                    if self.debug_logger:
                        self.debug_logger.log_tool_call(config.name, tool_name, json.loads(tc["function"]["arguments"]))

                    result = self._execute_tool(tool_name, json.loads(tc["function"]["arguments"]), fen)
                    tool_msg = json.dumps(result, ensure_ascii=False)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": tool_msg,
                    })
                    if self.debug_logger:
                        self.debug_logger.log_tool_result(config.name, tool_name, result)
                    if on_thinking:
                        msg_preview = result.get("message", str(result)[:80])
                        on_thinking(f"{config.name}_tool_result", f"{tool_name}: {msg_preview}")

                    assistant_tool_calls.append({
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["function"]["name"],
                            "arguments": tc["function"]["arguments"],
                        }
                    })

                messages[-1]["tool_calls"] = assistant_tool_calls
            else:
                # 无工具调用，分析完成
                finding = self._extract_finding(content, config.name)
                # 元叙事：专家结束时推摘要 headline
                if on_thinking:
                    on_thinking("headline", f"{config.display_name}：{finding[:25]}…")
                # 记录专家结果到debug_logger
                if self.debug_logger:
                    self.debug_logger.log_expert_result(config.name, finding, content, success=True)
                return ExpertResult(
                    expert_name=config.name,
                    finding=finding,
                    details=content,
                    tool_calls=tool_calls_log,
                    success=True,
                )

        # 达到最大轮数，强制结束
        final_response = self._call_api(messages, tools=None)
        final_reasoning = final_response.get("reasoning_content", "")
        if on_thinking and final_reasoning:
            on_thinking(f"{config.name}_reasoning", final_reasoning)
        final_finding = self._extract_finding(final_response["content"], config.name)
        # 元叙事：专家结束时推摘要 headline
        if on_thinking:
            on_thinking("headline", f"{config.display_name}：{final_finding[:25]}…")
        # 记录专家结果到debug_logger
        if self.debug_logger:
            self.debug_logger.log_expert_result(config.name, final_finding, final_response["content"], success=True)
        return ExpertResult(
            expert_name=config.name,
            finding=final_finding,
            details=final_response["content"],
            tool_calls=tool_calls_log,
            success=True,
        )

    # 工具超时配置（秒）
    TOOL_TIMEOUT = 30

    def _execute_tool(self, tool_name: str, arguments: Dict, fen: str) -> Dict:
        """执行工具（含超时保护 + OTEL Span）"""
        tracer = get_tracer()

        with tracer.start_as_current_span(
            SpanNames.TOOL_CALL,
            attributes={
                SpanAttributes.TOOL_NAME: tool_name,
            }
        ) as span:
            span.set_attribute("tool.arguments", json.dumps(arguments)[:200])  # 截断避免过长

            func = self._tool_functions.get(tool_name)
            if not func:
                span.set_attribute(SpanAttributes.ERROR, True)
                span.set_attribute(SpanAttributes.ERROR_MESSAGE, f"未知工具: {tool_name}")
                return {"error": f"未知工具: {tool_name}"}

            def _run():
                args = dict(arguments)
                args["fen"] = fen
                result = func(**args)
                if isinstance(result, ToolResult):
                    return {
                        "success": result.success,
                        "data": result.data,
                        "message": result.message,
                    }
                return result

            try:
                from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(_run)
                    return future.result(timeout=self.TOOL_TIMEOUT)
            except FuturesTimeoutError:
                span.set_attribute(SpanAttributes.ERROR, True)
                span.set_attribute(SpanAttributes.ERROR_MESSAGE, f"工具执行超时（>{self.TOOL_TIMEOUT}s）")
                span.set_attribute(SpanAttributes.TOOL_SUCCESS, False)
                return {"error": f"工具执行超时（>{self.TOOL_TIMEOUT}s）: {tool_name}"}
            except Exception as e:
                span.set_attribute(SpanAttributes.ERROR, True)
                span.set_attribute(SpanAttributes.ERROR_MESSAGE, str(e))
                span.set_attribute(SpanAttributes.TOOL_SUCCESS, False)
                return {"error": str(e)}

    def _extract_finding(self, content: str, expert_name: str) -> str:
        """从分析内容中提取核心发现（一句话摘要）"""
        if not content:
            return "无分析内容"
        content = STEP_PATTERN.sub("", content)
        content = _SECTION_RE.sub("", content)
        content = re.sub(r"\s+", " ", content).strip()
        # 取前100字作为发现摘要
        finding = content.strip()[:100]
        if len(content) > 100:
            finding += "..."
        return finding


# ═══════════════════════════════════════════════════════════════════════════════
# 自适应决策器 - 判断是否启用多Agent
# ═══════════════════════════════════════════════════════════════════════════════

def should_use_multi_agent(
    tensions: List[Dict],
    phase_name: str,
    user_request: str,
) -> bool:
    """
    判断是否使用多Agent并行分析

    简单局面 → 单Agent快速分析
    复杂局面 → 多Agent并行分析
    """
    # 强制深度模式
    if "深度" in user_request or "详细" in user_request:
        return True

    # 简单开局，无张力 → 单Agent
    if phase_name == "开局" and len(tensions) == 0:
        return False

    # 张力复杂度判断
    if tensions:
        primary = tensions[0]
        priority = primary.get("priority", "")

        if priority == "CRITICAL":
            return True
        if len(tensions) >= 3:
            return True

    return False
