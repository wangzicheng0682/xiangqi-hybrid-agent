"""
深度分析记录器 - 完整记录LLM分析过程用于调试和优化

使用方法:
    recorder = AnalysisRecorder()
    recorder.start_record("test-001")
    recorder.record_input(fen=fen, question=question, ...)
    recorder.record_system_prompt(system_prompt)
    recorder.record_user_message(user_message)
    
    # LLM调用前
    recorder.record_llm_request(messages)
    
    # LLM响应chunk
    recorder.record_llm_chunk("这是LLM输出的片段...")
    
    # 工具调用
    recorder.record_tool_call("get_piece_defenders", {"piece": "红车"}, result)
    
    # 完成
    path = recorder.finish_record()
"""

import json
import os
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict


@dataclass
class ToolCallRecord:
    """工具调用记录"""
    tool_name: str
    arguments: Dict[str, Any]
    raw_result: Dict[str, Any]
    duration_ms: float
    timestamp: str = ""


@dataclass
class LLMCallRecord:
    """LLM调用记录"""
    round: int
    request_messages: List[Dict[str, Any]]
    response_content: str = ""
    response_chunks: List[str] = field(default_factory=list)
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    finish_reason: str = ""
    duration_ms: float = 0.0
    timestamp: str = ""


@dataclass
class AnalysisRecord:
    """完整分析记录"""
    record_id: str = ""
    timestamp: str = ""
    fen: str = ""
    question: str = ""
    move: Optional[str] = None
    tag_summary: List[str] = field(default_factory=list)
    engine_eval: Dict[str, Any] = field(default_factory=dict)
    tensions: List[Dict[str, Any]] = field(default_factory=list)
    system_prompt: str = ""
    user_message: str = ""
    rounds: List[LLMCallRecord] = field(default_factory=list)
    final_output: str = ""
    error: Optional[str] = None
    total_duration_ms: float = 0.0


class AnalysisRecorder:
    """
    深度分析记录器
    
    完整记录每次深度分析的完整上下文，用于：
    1. 调试LLM幻觉问题
    2. 观察LLM调用工具的模式
    3. 分析prompt效果
    4. 复现问题
    """
    
    LOG_DIR = "logs/deep_analysis"
    
    def __init__(self, log_dir: str = None):
        self.log_dir = log_dir or self.LOG_DIR
        self.current_record: Optional[AnalysisRecord] = None
        self._round_start_time: float = 0
        self._tool_start_time: float = 0
        self._total_start_time: float = 0
        
    def start_record(self, request_id: str = None) -> str:
        """开始一条新的记录"""
        self._total_start_time = time.time()
        
        if request_id is None:
            request_id = str(uuid.uuid4())[:8]
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        record_id = f"{timestamp}_{request_id}"
        
        self.current_record = AnalysisRecord(
            record_id=record_id,
            timestamp=datetime.now().isoformat()
        )
        
        self._ensure_log_dir()
        
        return record_id
    
    def _ensure_log_dir(self):
        """确保日志目录存在"""
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
    
    def record_input(self, fen: str, question: str, move: str = None,
                     tag_summary: List[str] = None, engine_eval: Dict = None,
                     tensions: List[Dict] = None):
        """记录分析输入参数"""
        if not self.current_record:
            raise RuntimeError("must call start_record() first")
        
        self.current_record.fen = fen
        self.current_record.question = question
        self.current_record.move = move
        self.current_record.tag_summary = tag_summary or []
        self.current_record.engine_eval = engine_eval or {}
        self.current_record.tensions = tensions or []
    
    def record_system_prompt(self, prompt: str):
        """记录system prompt"""
        if not self.current_record:
            raise RuntimeError("must call start_record() first")
        self.current_record.system_prompt = prompt
    
    def record_user_message(self, message: str):
        """记录构建后的user message"""
        if not self.current_record:
            raise RuntimeError("must call start_record() first")
        self.current_record.user_message = message
    
    def start_llm_round(self, round_num: int):
        """开始一轮LLM调用"""
        if not self.current_record:
            raise RuntimeError("must call start_record() first")
        self._round_start_time = time.time()
        
        self.current_record.rounds.append(LLMCallRecord(
            round=round_num,
            request_messages=[],
            timestamp=datetime.now().isoformat()
        ))
    
    def record_llm_request(self, messages: List[Dict[str, Any]]):
        """记录发送给LLM的完整消息列表"""
        if not self.current_record or not self.current_record.rounds:
            return
        self.current_record.rounds[-1].request_messages = messages
    
    def record_llm_chunk(self, chunk: str):
        """记录LLM输出的chunk片段"""
        if not self.current_record or not self.current_record.rounds:
            return
        self.current_record.rounds[-1].response_chunks.append(chunk)
    
    def record_llm_response(self, content: str, tool_calls: List[Dict] = None,
                            finish_reason: str = ""):
        """记录LLM完整响应"""
        if not self.current_record or not self.current_record.rounds:
            return
        
        round_record = self.current_record.rounds[-1]
        round_record.response_content = content
        round_record.tool_calls = tool_calls or []
        round_record.finish_reason = finish_reason
        round_record.duration_ms = (time.time() - self._round_start_time) * 1000
    
    def start_tool_call(self, tool_name: str):
        """开始一个工具调用"""
        self._tool_start_time = time.time()
        self._current_tool_name = tool_name
        self._current_tool_args = None
    
    def record_tool_args(self, args: Dict[str, Any]):
        """记录工具参数"""
        self._current_tool_args = args
    
    def record_tool_result(self, result: Dict[str, Any]):
        """记录工具执行结果"""
        if not self.current_record or not self.current_record.rounds:
            return
        
        duration_ms = (time.time() - self._tool_start_time) * 1000
        
        tool_record = ToolCallRecord(
            tool_name=self._current_tool_name,
            arguments=self._current_tool_args or {},
            raw_result=result,
            duration_ms=duration_ms,
            timestamp=datetime.now().isoformat()
        )
        
        # 将工具调用记录追加到当前round
        # 由于工具结果是通过tool message返回的，我们需要在LLMCallRecord中创建一个占位结构
        round_record = self.current_record.rounds[-1]
        
        # 查找是否已有相同工具名的待记录结果
        # 这里我们直接在round中记录工具调用
        tool_entry = {
            "tool_name": tool_record.tool_name,
            "arguments": tool_record.arguments,
            "result": tool_record.raw_result,
            "duration_ms": tool_record.duration_ms,
            "timestamp": tool_record.timestamp
        }
        
        # 追加到round的工具调用列表
        if not hasattr(round_record, 'tool_call_records'):
            round_record.tool_call_records = []
        round_record.tool_call_records.append(tool_entry)
    
    def record_final_output(self, output: str):
        """记录最终输出"""
        if not self.current_record:
            raise RuntimeError("must call start_record() first")
        self.current_record.final_output = output
    
    def record_error(self, error: str):
        """记录错误信息"""
        if not self.current_record:
            raise RuntimeError("must call start_record() first")
        self.current_record.error = error
    
    def finish_record(self) -> str:
        """完成记录并保存到文件"""
        if not self.current_record:
            raise RuntimeError("must call start_record() first")
        
        self.current_record.total_duration_ms = (time.time() - self._total_start_time) * 1000
        
        # 转换记录为字典
        record_dict = self._record_to_dict(self.current_record)
        
        # 保存到文件
        filepath = os.path.join(self.log_dir, f"{self.current_record.record_id}.json")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(record_dict, f, ensure_ascii=False, indent=2)
        
        # 清理当前记录
        saved_path = filepath
        self.current_record = None
        
        return saved_path
    
    def _record_to_dict(self, record: AnalysisRecord) -> Dict[str, Any]:
        """将记录转换为字典"""
        result = {
            "record_id": record.record_id,
            "timestamp": record.timestamp,
            "total_duration_ms": record.total_duration_ms,
            "input": {
                "fen": record.fen,
                "question": record.question,
                "move": record.move,
                "tag_summary": record.tag_summary,
                "engine_eval": record.engine_eval,
                "tensions": record.tensions
            },
            "system_prompt": record.system_prompt,
            "user_message": record.user_message,
            "rounds": []
        }
        
        for round_record in record.rounds:
            round_dict = {
                "round": round_record.round,
                "duration_ms": round_record.duration_ms,
                "finish_reason": round_record.finish_reason,
                "request_messages_count": len(round_record.request_messages),
                "response_content_preview": round_record.response_content[:500] if round_record.response_content else "",
                "response_chunks_count": len(round_record.response_chunks),
                "tool_calls": []
            }
            
            # 处理工具调用记录
            if hasattr(round_record, 'tool_call_records'):
                for tc in round_record.tool_call_records:
                    round_dict["tool_calls"].append({
                        "tool_name": tc["tool_name"],
                        "arguments": tc["arguments"],
                        "result_preview": json.dumps(tc["result"], ensure_ascii=False)[:500] if tc["result"] else "",
                        "duration_ms": tc["duration_ms"]
                    })
            
            # 处理LLM返回的tool_calls
            for tc in round_record.tool_calls:
                round_dict["tool_calls"].append({
                    "tool_name": tc.get("name", ""),
                    "arguments": json.loads(tc.get("arguments", "{}")) if isinstance(tc.get("arguments"), str) else tc.get("arguments", {}),
                    "source": "llm_response"
                })
            
            result["rounds"].append(round_dict)
        
        result["final_output"] = record.final_output
        result["error"] = record.error
        
        return result
    
    @classmethod
    def get_records(cls, limit: int = 20) -> List[Dict[str, Any]]:
        """获取最近的记录列表"""
        log_dir = cls.LOG_DIR
        if not os.path.exists(log_dir):
            return []
        
        files = []
        for f in os.listdir(log_dir):
            if f.endswith('.json'):
                filepath = os.path.join(log_dir, f)
                files.append({
                    "filename": f,
                    "record_id": f.replace('.json', ''),
                    "size_bytes": os.path.getsize(filepath),
                    "modified": datetime.fromtimestamp(os.path.getmtime(filepath)).isoformat()
                })
        
        files.sort(key=lambda x: x["modified"], reverse=True)
        return files[:limit]
    
    @classmethod
    def load_record(cls, record_id: str) -> Optional[Dict[str, Any]]:
        """加载指定记录"""
        filepath = os.path.join(cls.LOG_DIR, f"{record_id}.json")
        if not os.path.exists(filepath):
            return None
        
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)