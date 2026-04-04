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
from typing import Dict, List, Any, Callable, Optional, TYPE_CHECKING
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from core.llm.agent_tools import AgentTools, ToolResult
    from core.llm.debug_logger import AgentDebugLogger

from core.llm.agent_tools import AgentTools, ToolResult
from core.llm.claim import (
    EvidenceChain, EvidenceItem, parse_claims, Claim,
)
from core.llm.contracts import AnalysisStatus, DegradationLevel, ExpertFailureType
from core.llm.reliable_client import ReliableLLMClient
from core.llm.tracing import get_tracer, SpanNames, SpanAttributes


def _backfill_tool_result(tool_calls_log: list, tool_name: str, result: dict):
    """将工具执行结果回填到 tool_calls_log 对应条目（倒序找第一个匹配且无 result_summary 的）"""
    for entry in reversed(tool_calls_log):
        if entry["name"] == tool_name and "result_summary" not in entry:
            entry["success"] = result.get("success", True)
            # 摘要：优先取 message，否则截断
            msg = result.get("message", "")
            if not msg:
                msg = str(result.get("data", result))[:120]
            entry["result_summary"] = msg[:200]
            break


def _build_evidence_chain(tool_calls_log: list) -> EvidenceChain:
    """从 tool_calls_log 构建 EvidenceChain"""
    items = []
    for entry in tool_calls_log:
        items.append(EvidenceItem(
            tool_name=entry["name"],
            arguments=entry.get("arguments", {}),
            result_summary=entry.get("result_summary", ""),
            success=entry.get("success", True),
        ))
    return EvidenceChain(tool_calls=items)

# ═══════════════════════════════════════════════════════════════════════════════
# 共享象棋规则 - 所有专家统一引用，避免重复（~800 tokens × 3 → 1次）
# ═══════════════════════════════════════════════════════════════════════════════

CHESS_RULES_BLOCK = """# 象棋基础规则 - 铁律，不可违背

**棋子走法**：
- 车：横竖直线任意格，不能跳越其他棋子
- 马：日字形（先横/竖一格，再斜一格），蹩马腿则不能走
- 炮：移动同车（横竖直线），但吃子必须隔一个棋子（炮架）
- 象/相：田字形（斜走两格），不能过河，塞象眼则不能走
- 士/仕：斜走一格，不出九宫
- 将/帅：九宫内横竖一格，将与帅不能照面（在同一列无遮挡）

**硬约束**：
- 你说任何棋子"保护"另一个棋子，必须先调用工具验证
- 炮架是被利用的棋子，不等于保护关系
- 你说任何走法合法，必须符合上述走法规则，否则禁止提及
- 你要分析具体走法时，优先先调用 get_move_candidates，再把 candidate_id 传给 analyze_move / compare_moves / get_forcing_sequence / simulate_move
- 不确定的关系，必须调用工具查询，禁止猜测"""

# ═══════════════════════════════════════════════════════════════════════════════
# 工具元数据 - 用于生成元叙事小标题
# ═══════════════════════════════════════════════════════════════════════════════

TOOL_META = {
    "get_move_candidates": "候选走法",
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
    "simulate_move": "走法模拟",
    "query_chess_principles": "棋理检索",
    "search_chess_knowledge": "知识库检索",
}


STEP_PATTERN = re.compile(r"^\[STEP:\s*(.+?)\s*\]$")
_SECTION_RE = re.compile(r"^【(.+?)】")

# 清除 LLM 遗留的原始标记，避免前端置入内部协议
_CLAIM_RE = re.compile(r"\[(?:CLAIM|EVIDENCE|CONFIDENCE)\]\s*")
_MD_HEADING_RE = re.compile(r"^##\s*\d+\s+.*$", re.MULTILINE)


def sanitize_display_text(text: str) -> str:
    """移除不应暴露给前端的内部标记。"""
    if not text:
        return text
    text = _CLAIM_RE.sub("", text)
    text = _MD_HEADING_RE.sub("", text)
    text = re.sub(r"\[STEP:[^\]]*\]", "", text)
    # 清理孤立的 ##； 或 ## 空行残留
    text = re.sub(r"^##\s*[;;；]?\s*$", "", text, flags=re.MULTILINE)
    # 压缩多余空行
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


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


def split_step_content_chunks(content: str, limit: int = 72) -> List[str]:
    """将长步骤内容切成多个较短片段，方便前端渐进渲染。"""
    if not content:
        return []
    content = sanitize_display_text(content)

    chunks: List[str] = []
    for paragraph in [item.strip() for item in content.split("\n") if item.strip()]:
        current = ""
        sentence = ""
        for char in paragraph:
            sentence += char
            if char in "，。！？；：":
                if len(current) + len(sentence) > limit and current:
                    chunks.append(current)
                    current = sentence
                else:
                    current += sentence
                sentence = ""

        if sentence:
            if len(current) + len(sentence) > limit and current:
                chunks.append(current)
                current = sentence
            else:
                current += sentence

        if current:
            chunks.append(current)

    return chunks or [content]


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
    status: str = AnalysisStatus.SUCCESS
    failure_type: Optional[str] = None
    confidence: str = "high"
    missing_evidence: List[str] = field(default_factory=list)
    retry_count: int = 0
    degraded: bool = False
    degradation_level: str = DegradationLevel.NONE
    # Phase 2: 结构化断言与证据链
    claims: List[Claim] = field(default_factory=list)
    evidence_chain: Optional[EvidenceChain] = None


@dataclass
class ExpertConfig:
    """专家配置"""
    name: str  # 英文名，如 "tactics"
    display_name: str  # 中文显示名，如 "战术专家"
    role: str  # 角色描述
    system_prompt: str  # 专家System Prompt
    tools: List[Dict]  # 该专家可用的工具Schema
    tool_names: List[str]  # 该专家可用的工具名列表
    required_sections: List[str] = field(default_factory=list)  # 成稿必须包含的章节
    max_rounds: int = 2  # 最大Agent循环轮次
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
        self.llm_client = ReliableLLMClient(
            api_key=self.api_key,
            base_url=self.base_url,
            model=self.model,
            timeout=120,
            max_retries=2,
        )

        self._tool_functions = {
            "get_move_candidates": self.tools.get_move_candidates,
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
            "simulate_move": self.tools.simulate_move,
            "query_chess_principles": self.tools.query_chess_principles,
            "search_chess_knowledge": self.tools.search_chess_knowledge,
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
        evidence_map: Dict = None,
    ) -> str:
        """构建共享上下文（注入给每个专家）

        支持两种模式：
        - 结构化 evidence_map（优先）：包含tags/tensions/engine/phase的结构化JSON
        - 文本 tag_summary（兼容）：旧的文本格式
        """
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

        # 优先使用结构化 Evidence Map（P0修复）
        if evidence_map and isinstance(evidence_map, dict):
            # 结构化事实表：标签 + 绑定棋子
            em_tags = evidence_map.get("tags", [])
            if em_tags:
                context += "【Evidence Map - 规则引擎检测的事实（100%准确）】\n"
                for tag_item in em_tags:
                    tag_name = tag_item.get("name", "")
                    bind_pieces = tag_item.get("bind_pieces", [])
                    desc = tag_item.get("description", "")
                    pieces_str = "、".join(bind_pieces) if bind_pieces else ""
                    line = f"- {tag_name}"
                    if pieces_str:
                        line += f" [{pieces_str}]"
                    if desc:
                        line += f": {desc}"
                    context += line + "\n"
                context += "\n[警告] 禁止推断任何未在此列出的攻防关系。如需验证额外关系，必须调用工具。\n\n"

            # 引擎评估
            em_engine = evidence_map.get("engine", {})
            if em_engine:
                context += "【引擎评估数据】\n"
                if "cp" in em_engine:
                    context += f"- 评估分: {em_engine['cp']}cp\n"
                if "best" in em_engine and em_engine["best"]:
                    context += f"- 最佳走法: {em_engine['best']}\n"
                if "pv" in em_engine and em_engine["pv"]:
                    context += f"- 主变化: {' '.join(em_engine['pv'][:5])}\n"
                context += "\n"

            # 子力统计
            em_pieces = evidence_map.get("piece_count", {})
            if em_pieces:
                context += f"【子力统计】红方{em_pieces.get('red', '?')}子 vs 黑方{em_pieces.get('black', '?')}子\n\n"

        elif tag_summary:
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
        thinking_enabled: bool = False,
        on_content_chunk: Optional[Callable[[str], None]] = None,
        on_reasoning_chunk: Optional[Callable[[str], None]] = None,
    ) -> Dict:
        """调用LLM API（非流式），自动记录 OTEL Span"""
        if not self.api_key:
            return {
                "content": "API Key未配置",
                "tool_calls": [],
                "finish_reason": "error",
                "error_type": ExpertFailureType.REQUEST_EXCEPTION,
                "status": AnalysisStatus.FAILED,
                "retry_count": 0,
                "degraded": False,
            }

        tracer = get_tracer()

        with tracer.start_as_current_span(
            SpanNames.LLM_CALL,
            attributes={
                SpanAttributes.LLM_MODEL: self.model,
                SpanAttributes.AGENT_TYPE: agent_type,
            }
        ) as span:
            # 记录输入
            if self.debug_logger:
                self.debug_logger.log_input(agent_type, {"messages": messages, "tools": [t.get("function", {}).get("name") for t in (tools or [])]})

            start_time = time.time()
            try:
                response = self.llm_client.stream_complete(
                    messages=messages,
                    tools=tools,
                    temperature=0.7,
                    max_tokens=2048,
                    thinking_enabled=thinking_enabled,
                    on_chunk=on_content_chunk,
                    on_reasoning_chunk=on_reasoning_chunk,
                )
                duration_ms = int((time.time() - start_time) * 1000)
                span.set_attribute(SpanAttributes.LLM_DURATION_MS, duration_ms)

                if response.success:
                    api_result = {
                        "content": response.content,
                        "reasoning_content": response.reasoning_content,
                        "tool_calls": response.tool_calls,
                        "finish_reason": response.finish_reason,
                        "status": response.status,
                        "error_type": response.error_type,
                        "retry_count": response.retry_count,
                        "degraded": response.degraded,
                        "degradation_level": response.degradation_level,
                    }

                    usage = response.metadata.get("usage", {})
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
                            "status": api_result["status"],
                            "retry_count": api_result["retry_count"],
                        }, duration_ms)
                    return api_result
                else:
                    error_result = {
                        "content": response.error_message,
                        "tool_calls": [],
                        "finish_reason": "error",
                        "error_type": response.error_type,
                        "status": response.status,
                        "retry_count": response.retry_count,
                        "degraded": response.degraded,
                        "degradation_level": response.degradation_level,
                    }
                    if self.debug_logger:
                        self.debug_logger.log_error(agent_type, response.error_message)
                    span.set_attribute(SpanAttributes.ERROR, True)
                    span.set_attribute(SpanAttributes.ERROR_MESSAGE, response.error_message)
                    return error_result
            except Exception as e:
                error_result = {"content": f"请求失败: {str(e)}", "tool_calls": [], "finish_reason": "error"}
                if self.debug_logger:
                    self.debug_logger.log_error(agent_type, str(e))
                span.set_attribute(SpanAttributes.ERROR, True)
                span.set_attribute(SpanAttributes.ERROR_MESSAGE, str(e))
                return error_result

    def _is_valid_expert_output(self, content: str, config: ExpertConfig) -> bool:
        """检查专家输出是否为可展示的正式成稿。"""
        if not content or not content.strip():
            return False

        normalized = content.strip()
        forbidden_markers = [
            "tool_calls参数",
            "需要保持原语言不变",
            '"arguments":',
            '"name":',
        ]
        if any(marker in normalized for marker in forbidden_markers):
            return False

        if config.required_sections:
            return all(section in normalized for section in config.required_sections)

        return True

    def _repair_expert_output(
        self,
        messages: List[Dict],
        invalid_content: str,
        config: ExpertConfig,
    ) -> Dict:
        """当专家只输出思维碎片或缺少章节时，要求其重写为正式成稿。"""
        repair_messages = list(messages)
        repair_messages.append({"role": "assistant", "content": invalid_content or ""})
        repair_messages.append({
            "role": "user",
            "content": (
                "你上一条回复不是可展示的正式分析成稿。"
                "现在禁止继续思维发散、禁止输出英文思维、禁止输出 tool_calls 或参数 JSON、禁止复述工具调用。"
                "请仅基于上文已有工具结果，直接重写为面向用户展示的最终分析，并严格包含这些章节："
                f"{', '.join(config.required_sections)}。"
                "不要新增工具调用，不要解释你如何思考。"
            ),
        })
        return self._call_api(
            repair_messages,
            tools=None,
            agent_type=f"{config.name}_repair",
            thinking_enabled=False,
        )

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
                for body_chunk in split_step_content_chunks(body):
                    on_thinking(
                        "expert_step_content",
                        json.dumps(
                            {
                                "expert": expert_name,
                                "step_index": step_index,
                                "title": title,
                                "content": body_chunk,
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

        default_rounds = {
            "tactics": 2,
            "strategy": 2,
            "engine": 2,
        }.get(config.name, config.max_rounds)
        effective_max_rounds = min(
            config.max_rounds,
            int(
                os.getenv(
                    f"{config.name.upper()}_EXPERT_MAX_ROUNDS",
                    os.getenv("EXPERT_MAX_ROUNDS", str(default_rounds)),
                )
            ),
        )

        tool_calls_log = []
        tool_failures: List[str] = []

        for round_num in range(effective_max_rounds):
            if on_thinking:
                on_thinking(f"{config.name}_thinking", f"[{config.display_name}] 第{round_num + 1}轮分析...")

            streamed_content = False
            content_buffer = ""
            reasoning_buffer = ""
            last_content_flush_at = time.time()
            last_reasoning_flush_at = time.time()

            def flush_content(force: bool = False) -> None:
                nonlocal content_buffer, last_content_flush_at
                if not content_buffer:
                    return
                if (
                    force
                    or len(content_buffer) >= 8
                    or content_buffer.endswith(("。", "！", "？", "\n", "；", ":", "："))
                    or (time.time() - last_content_flush_at) >= 0.2
                ):
                    if on_thinking:
                        on_thinking(f"{config.name}_chunk", content_buffer)
                    content_buffer = ""
                    last_content_flush_at = time.time()

            def flush_reasoning(force: bool = False) -> None:
                nonlocal reasoning_buffer, last_reasoning_flush_at
                if not reasoning_buffer:
                    return
                if (
                    force
                    or len(reasoning_buffer) >= 8
                    or reasoning_buffer.endswith(("。", "！", "？", "\n", "；", ":", "："))
                    or (time.time() - last_reasoning_flush_at) >= 0.2
                ):
                    if on_thinking:
                        on_thinking(f"{config.name}_thinking", reasoning_buffer)
                    reasoning_buffer = ""
                    last_reasoning_flush_at = time.time()

            def handle_content_chunk(chunk: str) -> None:
                nonlocal streamed_content, content_buffer
                if not chunk:
                    return
                streamed_content = True
                content_buffer += chunk
                flush_content()

            def handle_reasoning_chunk(chunk: str) -> None:
                nonlocal reasoning_buffer
                if not chunk:
                    return
                reasoning_buffer += chunk
                flush_reasoning()

            response = self._call_api(
                messages,
                tools=config.tools,
                agent_type=config.name,
                on_content_chunk=handle_content_chunk,
                on_reasoning_chunk=handle_reasoning_chunk,
            )
            flush_content(force=True)
            flush_reasoning(force=True)

            if response["finish_reason"] == "error":
                return ExpertResult(
                    expert_name=config.name,
                    finding="分析失败",
                    details=response["content"],
                    success=False,
                    error=response["content"],
                    status=response.get("status", AnalysisStatus.FAILED),
                    failure_type=response.get("error_type", ExpertFailureType.UNKNOWN),
                    confidence="low",
                    missing_evidence=["llm_response"],
                    retry_count=response.get("retry_count", 0),
                    degraded=response.get("degraded", False),
                    degradation_level=response.get("degradation_level", DegradationLevel.NONE),
                )

            content = response["content"]
            reasoning_content = response.get("reasoning_content", "")
            tool_calls = response.get("tool_calls", [])

            # GLM-5 thinking 内容单独 yield，前端可展示"正在思考"
            if on_thinking and reasoning_content:
                on_thinking(f"{config.name}_reasoning", reasoning_content)

            if on_thinking and content:
                emitted = self._emit_structured_steps(config.name, content, on_thinking)
                if not emitted and not streamed_content:
                    on_thinking(f"{config.name}_chunk", content)

            # 工具调用循环
            if tool_calls:
                messages.append({"role": "assistant", "content": content or ""})
                assistant_tool_calls = []

                # 只读工具可并行执行（无副作用）
                READONLY_TOOLS = {
                    "get_move_candidates",
                    "get_piece_attacks", "get_piece_defenders", "get_threats_to_piece",
                    "get_piece_relations", "compare_moves", "analyze_position_strategy",
                    "simulate_move", "query_chess_principles", "search_chess_knowledge",
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
                            if result.get("error") or result.get("success") is False:
                                tool_failures.append(result.get("error") or result.get("message", "tool_failed"))
                            # Phase 2: 回填工具输出到 tool_calls_log
                            _backfill_tool_result(tool_calls_log, tc["function"]["name"], result)
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
                    if result.get("error") or result.get("success") is False:
                        tool_failures.append(result.get("error") or result.get("message", "tool_failed"))
                    # Phase 2: 回填工具输出到 tool_calls_log
                    _backfill_tool_result(tool_calls_log, tool_name, result)
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
                if not self._is_valid_expert_output(content, config):
                    repaired_response = self._repair_expert_output(messages, content, config)
                    repaired_content = repaired_response.get("content", "")
                    if repaired_response.get("finish_reason") == "error" or not self._is_valid_expert_output(repaired_content, config):
                        tool_failures.append("invalid_expert_output")
                        continue
                    content = repaired_content
                finding = self._extract_finding(content, config.name)
                # 元叙事：专家结束时推摘要 headline
                if on_thinking:
                    on_thinking("headline", f"{config.display_name}：{finding[:25]}…")
                # 记录专家结果到debug_logger
                if self.debug_logger:
                    self.debug_logger.log_expert_result(config.name, finding, content, success=True)
                degraded = bool(tool_failures) or response.get("degraded", False)
                confidence = "high"
                if degraded and tool_calls_log:
                    confidence = "medium"
                elif degraded:
                    confidence = "low"
                # Phase 2: 构建证据链并解析 Claim
                ev_chain = _build_evidence_chain(tool_calls_log)
                claims = parse_claims(content, ev_chain)
                return ExpertResult(
                    expert_name=config.name,
                    finding=finding,
                    details=content,
                    tool_calls=tool_calls_log,
                    success=True,
                    status=AnalysisStatus.DEGRADED if degraded else AnalysisStatus.SUCCESS,
                    failure_type=ExpertFailureType.TOOL_ERROR if tool_failures else response.get("error_type"),
                    confidence=confidence,
                    missing_evidence=["tool_validation"] if tool_failures else [],
                    retry_count=response.get("retry_count", 0),
                    degraded=degraded,
                    degradation_level=(
                        response.get("degradation_level", DegradationLevel.NONE)
                        if response.get("degraded", False)
                        else (DegradationLevel.PARTIAL_EXPERTS if tool_failures else DegradationLevel.NONE)
                    ),
                    error="；".join(tool_failures[:2]) if tool_failures else None,
                    claims=claims,
                    evidence_chain=ev_chain,
                )

        # 达到最大轮数，强制结束
        final_response = self._call_api(messages, tools=None)
        if final_response["finish_reason"] == "error":
            return ExpertResult(
                expert_name=config.name,
                finding="分析失败",
                details=final_response["content"],
                tool_calls=tool_calls_log,
                success=False,
                error=final_response["content"],
                status=final_response.get("status", AnalysisStatus.FAILED),
                failure_type=final_response.get("error_type", ExpertFailureType.UNKNOWN),
                confidence="low",
                missing_evidence=["llm_final_response"],
                retry_count=final_response.get("retry_count", 0),
                degraded=final_response.get("degraded", False),
                degradation_level=final_response.get("degradation_level", DegradationLevel.NONE),
            )
        final_reasoning = final_response.get("reasoning_content", "")
        if on_thinking and final_reasoning:
            on_thinking(f"{config.name}_reasoning", final_reasoning)
        final_content = final_response["content"]
        if not self._is_valid_expert_output(final_content, config):
            repaired_response = self._repair_expert_output(messages, final_content, config)
            repaired_content = repaired_response.get("content", "")
            if repaired_response.get("finish_reason") != "error" and self._is_valid_expert_output(repaired_content, config):
                final_content = repaired_content
            else:
                return ExpertResult(
                    expert_name=config.name,
                    finding="分析失败",
                    details=final_content or "专家未生成合格成稿",
                    tool_calls=tool_calls_log,
                    success=False,
                    error="专家未生成合格成稿",
                    status=AnalysisStatus.FAILED,
                    failure_type=ExpertFailureType.INVALID_OUTPUT,
                    confidence="low",
                    missing_evidence=["expert_final_output"],
                    retry_count=final_response.get("retry_count", 0),
                    degraded=True,
                    degradation_level=DegradationLevel.PARTIAL_EXPERTS,
                )
        final_finding = self._extract_finding(final_content, config.name)
        # 元叙事：专家结束时推摘要 headline
        if on_thinking:
            on_thinking("headline", f"{config.display_name}：{final_finding[:25]}…")
        # 记录专家结果到debug_logger
        if self.debug_logger:
            self.debug_logger.log_expert_result(config.name, final_finding, final_content, success=True)
        final_degraded = bool(tool_failures) or final_response.get("degraded", False)
        # Phase 2: 构建证据链并解析 Claim
        ev_chain_final = _build_evidence_chain(tool_calls_log)
        claims_final = parse_claims(final_content, ev_chain_final)
        return ExpertResult(
            expert_name=config.name,
            finding=final_finding,
            details=final_content,
            tool_calls=tool_calls_log,
            success=True,
            status=AnalysisStatus.DEGRADED if final_degraded else AnalysisStatus.SUCCESS,
            failure_type=ExpertFailureType.TOOL_ERROR if tool_failures else final_response.get("error_type"),
            confidence="medium" if final_degraded else "high",
            missing_evidence=["tool_validation"] if tool_failures else [],
            retry_count=final_response.get("retry_count", 0),
            degraded=final_degraded,
            degradation_level=(
                final_response.get("degradation_level", DegradationLevel.NONE)
                if final_response.get("degraded", False)
                else (DegradationLevel.PARTIAL_EXPERTS if tool_failures else DegradationLevel.NONE)
            ),
            error="；".join(tool_failures[:2]) if tool_failures else None,
            claims=claims_final,
            evidence_chain=ev_chain_final,
        )

    # 工具超时配置（秒）
    TOOL_TIMEOUT = 45

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
                return {
                    "success": False,
                    "error": f"未知工具: {tool_name}",
                    "error_type": ExpertFailureType.TOOL_ERROR,
                }

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
                return {
                    "success": False,
                    "error": f"工具执行超时（>{self.TOOL_TIMEOUT}s）: {tool_name}",
                    "error_type": ExpertFailureType.TOOL_TIMEOUT,
                }
            except Exception as e:
                span.set_attribute(SpanAttributes.ERROR, True)
                span.set_attribute(SpanAttributes.ERROR_MESSAGE, str(e))
                span.set_attribute(SpanAttributes.TOOL_SUCCESS, False)
                return {
                    "success": False,
                    "error": str(e),
                    "error_type": ExpertFailureType.TOOL_ERROR,
                }

    def _extract_finding(self, content: str, expert_name: str) -> str:
        """从分析内容中提取核心发现（一句话摘要）"""
        if not content:
            return "无分析内容"
        content = sanitize_display_text(content)
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
