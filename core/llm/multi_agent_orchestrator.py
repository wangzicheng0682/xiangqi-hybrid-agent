"""
多Agent协调器 + 合成器

核心职责：
1. 自适应决策：简单局面 → 单Agent，复杂局面 → 多Agent并行
2. 并行分发：同时调用三个专家
3. 结果收集：等待所有专家返回
4. 合成讲解：将三方结论汇合成统一讲解

SSE事件类型：
- expert_start: 专家开始分析
- expert_result: 专家完成分析
- synthesis: 合成结果（流式）
"""

import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Any, Callable, Optional

from core.llm.analysis_policy import choose_analysis_policy, ENGINE_KEYWORDS, TACTICAL_KEYWORDS
from core.llm.contracts import AnalysisStatus, DegradationLevel, ExpertFailureType
from core.llm.experts.base_expert import (
    ExpertResult, should_use_multi_agent, STEP_PATTERN, sanitize_display_text,
)
from core.llm.claim import format_claims_for_synthesis, ClaimSource, ClaimConfidence
from core.llm.experts.tactics_expert import TacticsExpert
from core.llm.experts.strategy_expert import StrategyExpert
from core.llm.experts.engine_expert import EngineExpert
from core.llm.reliable_client import ReliableLLMClient
from core.llm.thinking_templates import PhaseInfo, PhaseDetector
from core.rules.tension_detector import detect_tensions, get_primary_tension
from core.llm.debug_logger import AgentDebugLogger
from core.llm.opening_knowledge import OPENING_PRINCIPLES
from core.llm.tracing import (
    get_tracer, add_span_attributes,
    SpanNames, SpanAttributes,
)
from core.opening.opening_book import identify_opening, normalize_move


# ═══════════════════════════════════════════════════════════════════════════════
# 合成器 - Synthesizer
# ═══════════════════════════════════════════════════════════════════════════════

SYNTHESIZER_SYSTEM_PROMPT = """# 你是谁

你是一位证据裁决者，基于三位专家的结构化断言和证据链，生成统一的象棋讲解。

三位专家已经分别从不同角度分析了当前局面：
- 战术专家：专注于子力关系和战术细节
- 战略专家：专注于全局战略和相位判断
- 引擎专家：专注于解读引擎评估和候选走法

每位专家的输出包含：
- **断言 (CLAIM)**：一条核心结论
- **证据来源**：工具验证 / 推理 / 未验证
- **置信度**：高 / 中 / 低

---

# 你的任务

1. **断言对齐**：三位专家对同一论点各自给了什么断言？
2. **证据交叉验证**：
   - 同一断言被 2+ 专家用工具验证 → **高可信，直接采纳**
   - 只有 1 位专家声称且有工具验证 → **中可信，标注来源**
   - 只有推理无工具验证 → **低可信，说明缺乏验证**
   - 断言之间矛盾 → **需裁决，说明冲突原因**
3. **综合对手处境**：综合各方对对手选项的分析
4. **生成讲解**：用通俗语言生成面向学生的统一讲解

---

# 证据裁决规则

| 情况 | 处理方式 |
|------|----------|
| 工具验证断言 vs 纯推理断言 | 工具验证优先 |
| 引擎评估 vs 战术发现（都有工具验证） | 战术发现优先（精确规则） |
| 战略判断 vs 引擎评估 | 给出双方观点，解释原因 |
| 三方完全矛盾 | 标注为"复杂局面"，给出多个解读 |
| 有专家断言为"未验证" | 在最终结论中降低该断言权重 |

---

# 绝对约束

- 不能编造棋子位置（来自专家结论中的事实）
- 不能忽略任何一位专家的高置信度+工具验证断言
- 讲解必须回应用户原始问题
- 用"因为...所以..."的因果逻辑组织讲解
- 必须说明最终结论的证据基础

---

# 输出格式

请直接输出最终讲解正文，不要输出任何过程标题、Markdown 小节、[STEP:] 标记、草稿推理或自我说明。

最终结果必须且只能包含以下六个部分：
【综合评估】一句话综合（标注证据强度）
【证据基础】本结论基于哪些工具验证的断言
【对手处境】综合分析对手的选项和应对（必须包含）
【共识分析】三方一致同意的核心观点（标注验证状态）
【分歧解读】分歧点的详细分析和裁决依据
【教练建议】给学生的具体建议
"""

SYNTHESIZER_MODEL = "glm-5"
SYNTHESIZER_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"


class Synthesizer:
    """合成器 - 将三位专家的结论合成为统一讲解"""

    REQUIRED_SECTIONS = [
        "【综合评估】",
        "【证据基础】",
        "【对手处境】",
        "【共识分析】",
        "【分歧解读】",
        "【教练建议】",
    ]

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("ALIYUN_API_KEY")
        self.base_url = SYNTHESIZER_BASE_URL
        self.model = SYNTHESIZER_MODEL
        self.llm_client = ReliableLLMClient(
            api_key=self.api_key,
            base_url=self.base_url,
            model=self.model,
            timeout=120,
            max_retries=2,
        )

    def _sanitize_expert_details(self, details: str, limit: int = 360) -> str:
        if not details:
            return ""

        cleaned_lines: List[str] = []
        for raw_line in details.splitlines():
            stripped = raw_line.strip()
            if not stripped:
                continue
            if STEP_PATTERN.match(stripped):
                continue
            if _SECTION_PATTERN.match(stripped):
                continue
            if _SUBTITLE_PATTERN.match(stripped):
                continue
            stripped = re.sub(r"^[-*•]\s*", "", stripped)
            cleaned_lines.append(stripped)
            if len(cleaned_lines) >= 6:
                break

        cleaned = " ".join(cleaned_lines)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        if len(cleaned) <= limit:
            return cleaned
        return cleaned[:limit].rstrip() + "..."

    def _sanitize_synthesis_output(self, content: str) -> str:
        if not content:
            return ""

        cleaned_lines: List[str] = []
        for raw_line in content.splitlines():
            stripped = raw_line.strip()
            if not stripped:
                cleaned_lines.append("")
                continue
            if STEP_PATTERN.match(stripped):
                continue
            if _SUBTITLE_PATTERN.match(stripped):
                continue
            cleaned_lines.append(raw_line)

        cleaned = "\n".join(cleaned_lines)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
        return cleaned

    def _format_expert_block(self, label: str, result: ExpertResult) -> str:
        lines = [f"【{label}】"]
        lines.append(f"状态：{result.status}")
        lines.append(f"结论：{result.finding}")

        # Phase 2: 优先注入结构化断言
        if result.claims:
            claims_text = format_claims_for_synthesis(result.claims, label)
            lines.append(claims_text)
        else:
            # 回退：传统详情
            if result.details:
                sanitized_details = self._sanitize_expert_details(result.details)
                if sanitized_details:
                    lines.append(f"详情摘要：{sanitized_details}")

        if result.confidence:
            lines.append(f"可信度：{result.confidence}")
        if result.error:
            lines.append(f"错误：{result.error}")
        if result.missing_evidence:
            lines.append(f"缺失证据：{', '.join(result.missing_evidence)}")

        # Phase 2: 证据链摘要
        if result.evidence_chain and result.evidence_chain.tool_calls:
            lines.append("工具证据链：")
            for ev in result.evidence_chain.tool_calls[:5]:
                status = "✓" if ev.success else "✗"
                args_preview = str(ev.arguments)[:60]
                result_preview = ev.result_summary[:60] if ev.result_summary else "N/A"
                lines.append(f"  {status} {ev.tool_name}({args_preview}) → {result_preview}")
        elif result.tool_calls:
            lines.append("工具验证：")
            for tc in result.tool_calls[:5]:
                lines.append(f"  - 调用 {tc.get('name', '?')}({tc.get('arguments', {})})")
        return "\n".join(lines)

    def _build_degraded_response(
        self,
        tactics_result: ExpertResult,
        strategy_result: ExpertResult,
        engine_result: ExpertResult,
        user_question: str,
    ) -> str:
        available = [r for r in [tactics_result, strategy_result, engine_result] if r.success]
        failed = [r for r in [tactics_result, strategy_result, engine_result] if not r.success]

        if not available:
            reasons = "；".join(filter(None, [r.error for r in failed])) or "关键专家均失败"
            return (
                "【系统状态】本次分析失败\n"
                f"【失败原因】{reasons}\n"
                "【说明】当前没有足够证据支持可靠讲解，系统选择显式失败而不是伪造结论。"
            )

        primary = available[0]
        failed_names = "、".join(r.expert_name for r in failed) if failed else "无"
        return (
            "【系统状态】降级分析\n"
            f"【用户问题】{user_question}\n"
            f"【可用专家】{primary.expert_name}\n"
            f"【缺失专家】{failed_names}\n"
            f"【当前可得结论】{primary.finding}\n"
            f"【可信度】{primary.confidence}\n"
            "【说明】由于关键专家失败，本次仅返回部分结论，未输出完整综合讲解。"
        )

    def synthesize(
        self,
        tactics_result: ExpertResult,
        strategy_result: ExpertResult,
        engine_result: ExpertResult,
        user_question: str,
        on_event: Callable[[str, Dict[str, Any]], None] = None,
    ) -> str:
        """
        合成三位专家的结论，生成统一讲解

        Args:
            tactics_result: 战术专家结论
            strategy_result: 战略专家结论
            engine_result: 引擎专家结论
            user_question: 用户原始问题
            on_event: 流式事件回调

        Returns:
            统一讲解文本
        """
        success_count = sum(1 for result in [tactics_result, strategy_result, engine_result] if result.success)
        if success_count < 2:
            return self._build_degraded_response(
                tactics_result=tactics_result,
                strategy_result=strategy_result,
                engine_result=engine_result,
                user_question=user_question,
            )

        expert_summaries = "\n\n".join([
            self._format_expert_block("战术专家", tactics_result),
            self._format_expert_block("战略专家", strategy_result),
            self._format_expert_block("引擎专家", engine_result),
        ])

        user_content = f"""请基于三位专家的断言和证据链，进行证据裁决并生成讲解。

【用户原始问题】
{user_question}

【三位专家的分析与断言】
{expert_summaries}

【裁决要求】
- 先对齐三方断言，再交叉验证证据
- 工具验证的断言权重 > 纯推理断言
- 明确指出失败或降级的专家，不得把失败专家当作正常证据
- 如果证据不完整，要主动降低最终结论的置信度
- 最终结论必须写清证据基础

请按照你的任务，进行证据裁决并生成最终讲解。
"""

        messages = [
            {"role": "system", "content": SYNTHESIZER_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]

        synthesis = self._sanitize_synthesis_output(self._call_stream(messages, on_event=on_event))
        if self._is_valid_synthesis(synthesis):
            return synthesis

        fallback = self._build_fallback_synthesis(
            tactics_result=tactics_result,
            strategy_result=strategy_result,
            engine_result=engine_result,
            user_question=user_question,
        )
        if on_event:
            on_event("synthesis_step_start", {"step_index": 0, "title": "生成保底综合讲解"})
            on_event("synthesis_step_content", {"step_index": 0, "title": "生成保底综合讲解", "content": fallback})
            on_event("synthesis_step_end", {"step_index": 0, "title": "生成保底综合讲解", "duration_ms": 0})
        return fallback

    def _is_valid_synthesis(self, content: str) -> bool:
        if not content or not content.strip():
            return False
        return all(section in content for section in self.REQUIRED_SECTIONS)

    def _build_fallback_synthesis(
        self,
        tactics_result: ExpertResult,
        strategy_result: ExpertResult,
        engine_result: ExpertResult,
        user_question: str,
    ) -> str:
        def short(text: str, limit: int = 120) -> str:
            text = sanitize_display_text(text or "")
            text = re.sub(r"\s+", " ", text).strip()
            if len(text) <= limit:
                return text
            return text[:limit] + "..."

        consensus = []
        if tactics_result.success:
            consensus.append(f"战术专家认为：{short(tactics_result.finding)}")
        if strategy_result.success:
            consensus.append(f"战略专家认为：{short(strategy_result.finding)}")
        if engine_result.success:
            consensus.append(f"引擎专家认为：{short(engine_result.finding)}")

        evidence = []
        for result in [tactics_result, strategy_result, engine_result]:
            if not result.success:
                continue
            if result.claims:
                claim = result.claims[0]
                evidence.append(f"{result.expert_name}: {sanitize_display_text(claim.statement)}")
            elif result.evidence_chain and result.evidence_chain.tool_calls:
                tool = result.evidence_chain.tool_calls[0]
                evidence.append(f"{result.expert_name}: {tool.tool_name}={tool.result_summary}")

        combined_text = " ".join(filter(None, [
            user_question,
            tactics_result.finding,
            strategy_result.finding,
            engine_result.finding,
        ]))
        is_opening_context = any(keyword in combined_text for keyword in ["开局", "布局", "中炮", "屏风马", "定式"])
        overview = (
            "当前更该关注开局主线、出子顺序与是否脱离熟悉定式，而不是把弱结构标签误当成主导矛盾。"
            if is_opening_context
            else "当前更该关注先手、结构与子力协调如何影响计划兑现，而不是把单个孤立标签直接抬成结论。"
        )
        opponent_plan = (
            "对手首先要做的是回到稳健出子与熟悉结构，避免因为脱谱或次序错误直接把局面送入被动。"
            if is_opening_context
            else "对手首先要处理最直接的被动点，争取简化压力源并恢复可执行的计划。"
        )
        disagreement = (
            "当前分歧主要在“应继续按主线稳健推进，还是已经出现值得脱谱处理的具体信号”。没有额外验证前，不应为了显得深刻而过度解读阵型名词。"
            if is_opening_context
            else "当前分歧主要在“优势更多来自先手与结构，还是已经转化为可兑现的具体子力/战术收益”。这类判断必须以后续验证为准。"
        )

        return (
            f"【综合评估】围绕“{user_question}”，当前可确认的共识是先抓主导矛盾，再决定推进方式；{overview}\n\n"
            f"【证据基础】{'；'.join(evidence) if evidence else '本次合成器未产出完整正文，以下结论基于三位专家的已验证结果整理。'}\n\n"
            f"【对手处境】{opponent_plan}\n\n"
            f"【共识分析】{'；'.join(consensus) if consensus else '当前可用专家结果不足，只能给出低置信度保底结论。'}\n\n"
            f"【分歧解读】{disagreement}\n\n"
            f"【教练建议】先给学生讲清当前阶段真正该盯的焦点，再给出双方计划和风险点，最后才落到具体走法；不要为了显得复杂而堆砌不关键的术语。"
        )

    def _call_stream(
        self,
        messages: List[Dict],
        on_event: Callable[[str, Dict[str, Any]], None] = None,
    ) -> str:
        """流式调用合成"""
        step_parser = SynthesisStepStreamParser(on_event) if on_event else None

        def _on_chunk(chunk: str):
            if on_event:
                on_event("synthesis_chunk", {"message": chunk})
            if step_parser:
                step_parser.feed(chunk)

        response = self.llm_client.stream_complete(
            messages=messages,
            tools=None,
            temperature=0.7,
            max_tokens=2048,
            thinking_enabled=False,
            on_chunk=_on_chunk,
        )
        if step_parser:
            step_parser.finalize()
        if not response.success:
            return f"合成失败: {response.error_message}"
        return response.content or ""


# 中文节标题 → 用作隐式 STEP 标记（模型几乎总会输出这些）
_SECTION_PATTERN = re.compile(r"^【(.+?)】")
_SUBTITLE_PATTERN = re.compile(r"^##\s*(\d+)\s+(.+?)\s*$")


class SynthesisStepStreamParser:
    """将协调者流式输出按 [STEP:] / 【节标题】 解析为结构化事件。"""

    def __init__(self, on_event: Callable[[str, Dict[str, Any]], None]):
        self.on_event = on_event
        self.pending = ""
        self.current_title: Optional[str] = None
        self.current_subtitle: Optional[str] = None
        self.current_index = -1
        self.current_started_at = 0.0
        self.saw_marker = False

    def feed(self, chunk: str) -> None:
        self.pending += chunk
        while "\n" in self.pending:
            line, self.pending = self.pending.split("\n", 1)
            self._process_line(line.rstrip("\r"))

    def finalize(self) -> None:
        if self.pending:
            self._process_line(self.pending.rstrip("\r"))
            self.pending = ""
        self._finish_step()

    def _process_line(self, line: str) -> None:
        stripped = line.strip()

        subtitle_match = _SUBTITLE_PATTERN.match(stripped)
        if subtitle_match:
            subtitle = subtitle_match.group(2).strip()
            self.current_subtitle = subtitle
            self.on_event("orchestrator_subtitle", {"message": subtitle})
            # 同时作为步骤起点（避免 ## 标题后的内容丢失）
            self.saw_marker = True
            self._finish_step()
            self.current_index += 1
            self.current_title = subtitle
            self.current_started_at = time.time()
            self.on_event(
                "synthesis_step_start",
                {"step_index": self.current_index, "title": subtitle},
            )
            return

        # 优先检查 [STEP:] 显式标记
        match = STEP_PATTERN.match(stripped)
        if match:
            self.saw_marker = True
            self._finish_step()
            self.current_index += 1
            self.current_title = match.group(1).strip()
            self.current_subtitle = self.current_title
            self.current_started_at = time.time()
            self.on_event("orchestrator_subtitle", {"message": self.current_title})
            self.on_event(
                "synthesis_step_start",
                {
                    "step_index": self.current_index,
                    "title": self.current_title,
                },
            )
            return

        # 其次检查【节标题】作为隐式步骤（模型几乎总会输出）
        section_match = _SECTION_PATTERN.match(stripped)
        if section_match:
            self.saw_marker = True
            self._finish_step()
            self.current_index += 1
            self.current_title = section_match.group(1).strip()
            self.current_subtitle = self.current_title
            self.current_started_at = time.time()
            self.on_event("orchestrator_subtitle", {"message": self.current_title})
            self.on_event(
                "synthesis_step_start",
                {
                    "step_index": self.current_index,
                    "title": self.current_title,
                },
            )
            return

        if self.current_title is None:
            return

        if stripped:
            self.on_event(
                "synthesis_step_content",
                {
                    "step_index": self.current_index,
                    "title": self.current_title,
                    "content": f"{stripped}\n",
                },
            )

    def _finish_step(self) -> None:
        if self.current_title is None:
            return

        duration_ms = max(250, int((time.time() - self.current_started_at) * 1000))
        self.on_event(
            "synthesis_step_end",
            {
                "step_index": self.current_index,
                "title": self.current_title,
                "duration_ms": duration_ms,
            },
        )
        self.current_title = None
        self.current_started_at = 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# 多Agent协调器 - MultiAgentOrchestrator
# ═══════════════════════════════════════════════════════════════════════════════

class MultiAgentOrchestrator:
    """
    多Agent协调器

    决策逻辑：
    - 简单局面：委托给单Agent（现有逻辑）
    - 复杂局面：并行调用三个专家，然后合成
    """

    def __init__(self, api_key: str = None, debug_logger: AgentDebugLogger = None):
        self.debug_logger = debug_logger
        self.api_key = api_key or os.getenv("ALIYUN_API_KEY")
        self.tactics_expert = TacticsExpert(api_key=self.api_key, debug_logger=debug_logger)
        self.strategy_expert = StrategyExpert(api_key=self.api_key, debug_logger=debug_logger)
        self.engine_expert = EngineExpert(api_key=self.api_key, debug_logger=debug_logger)
        self.synthesizer = Synthesizer(api_key=self.api_key)

    def _skipped_result(self, expert_name: str, reason: str) -> ExpertResult:
        return ExpertResult(
            expert_name=expert_name,
            finding="策略裁剪未执行",
            details="",
            success=False,
            error=reason,
            status=AnalysisStatus.SKIPPED,
            failure_type=ExpertFailureType.POLICY_SKIPPED,
            confidence="low",
            missing_evidence=["expert_not_scheduled"],
            degraded=True,
            degradation_level=DegradationLevel.SINGLE_EXPERT,
        )

    def _detect_phase(self, fen: str, move_count: int, move_history: Optional[List[str]] = None) -> PhaseInfo:
        """检测当前阶段"""
        normalized_history = self._normalize_move_history(move_history)
        move_count_source = "history" if normalized_history else "fen"
        return PhaseDetector.detect(fen, move_count, move_count_source=move_count_source)

    def _detect_tensions(
        self,
        evidence_map: Dict,
        engine_eval: Dict,
        phase_name: str,
    ) -> tuple:
        """检测张力"""
        tensions = []
        if evidence_map:
            tensions = detect_tensions(evidence_map, engine_eval or {}, phase_name)
        primary = tensions[0] if tensions else None
        return tensions, primary

    def _build_structured_evidence_map(
        self,
        fen: str,
        evidence_map: Dict = None,
        engine_eval: Dict = None,
        phase_info: "PhaseInfo" = None,
        tensions: list = None,
    ) -> Dict:
        """
        构建结构化Evidence Map，供专家消费。

        将离散的tag_summary、engine_eval、tensions等整合为
        一个结构化JSON对象，让LLM获得精确的事实锚点。
        """
        structured = {
            "tags": [],
            "tensions": [],
            "engine": {},
            "phase": phase_info.phase_name if phase_info else "未知",
            "initiative": "未知",
            "piece_count": {"red": 0, "black": 0},
        }

        # 从 evidence_map 提取结构化标签
        if evidence_map:
            facts = evidence_map.get("facts_rules", [])
            if isinstance(facts, list):
                for fact in facts:
                    if isinstance(fact, dict):
                        structured["tags"].append({
                            "name": fact.get("tag", ""),
                            "bind_pieces": fact.get("bind_pieces", []),
                            "description": fact.get("description", ""),
                        })
                    elif isinstance(fact, str):
                        structured["tags"].append({
                            "name": fact,
                            "bind_pieces": [],
                            "description": "",
                        })

        # 注入引擎评估
        if engine_eval:
            structured["engine"] = {
                "cp": engine_eval.get("cp", 0),
                "best": engine_eval.get("best", ""),
                "pv": engine_eval.get("pv", []),
                "eval_human": engine_eval.get("eval_human", ""),
            }

        # 注入张力
        if tensions:
            for t in tensions:
                if isinstance(t, dict):
                    structured["tensions"].append({
                        "type": t.get("tension_type", ""),
                        "description": t.get("description", ""),
                        "severity": t.get("priority", ""),
                    })

        # 子力统计
        try:
            board_part = fen.split()[0]
            red_count = sum(1 for c in board_part if c.isupper() and c != '/')
            black_count = sum(1 for c in board_part if c.islower() and c != '/')
            structured["piece_count"] = {"red": red_count, "black": black_count}
        except Exception:
            pass

        return structured

    def _normalize_move_history(self, move_history: Optional[List[str]]) -> List[str]:
        return [normalize_move(move) for move in (move_history or []) if normalize_move(move)]

    def _infer_move_count(self, fen: str, move_count: int, move_history: Optional[List[str]]) -> int:
        history_count = len(self._normalize_move_history(move_history))
        fen_count = PhaseDetector._extract_move_count_from_fen(fen)
        return max(move_count or 0, history_count, fen_count)

    def _select_opening_principles(self, opening_name: str) -> List[Dict[str, Any]]:
        opening_name = opening_name or ""
        if "中炮" in opening_name or "炮" in opening_name:
            principle_ids = [1, 3, 9]
        elif "飞相" in opening_name or "飞象" in opening_name:
            principle_ids = [2, 3, 10]
        elif "起马" in opening_name or "马" in opening_name:
            principle_ids = [1, 2, 7]
        elif "仙人指路" in opening_name or "挺兵" in opening_name:
            principle_ids = [1, 3, 6]
        else:
            principle_ids = [1, 3, 6]

        principle_map = {item["id"]: item for item in OPENING_PRINCIPLES}
        return [principle_map[pid] for pid in principle_ids if pid in principle_map]

    def _build_opening_context(
        self,
        move_history: Optional[List[str]],
        move: Optional[str],
    ) -> Dict[str, Any]:
        history = self._normalize_move_history(move_history)
        normalized_move = normalize_move(move or "")
        effective_line = list(history)
        position_line = list(history)

        if normalized_move:
            if not effective_line or effective_line[-1] != normalized_move:
                effective_line = [*effective_line, normalized_move]
            elif position_line:
                position_line = position_line[:-1]

        opening = identify_opening(effective_line) if effective_line else None

        return {
            "history": history,
            "position_line": position_line,
            "effective_line": effective_line,
            "normalized_move": normalized_move,
            "opening": opening,
            "effective_move_count": len(effective_line),
            "position_move_count": len(position_line),
        }

    def _should_use_opening_fast_path(
        self,
        question: str,
        phase_info: PhaseInfo,
        tensions: List[Dict[str, Any]],
        opening_context: Dict[str, Any],
        force_multi: bool,
    ) -> bool:
        if phase_info.phase_name != "开局":
            return False

        effective_move_count = opening_context["effective_move_count"]
        opening = opening_context["opening"]
        text = question or ""

        if any(keyword in text for keyword in ENGINE_KEYWORDS):
            return False
        if any(keyword in text for keyword in TACTICAL_KEYWORDS):
            return False
        if len(tensions) > 1:
            return False
        if not opening:
            if effective_move_count > 2:
                return False
            if effective_move_count == 0:
                return bool(
                    phase_info.confidence >= 0.65
                    and phase_info.move_count > 0
                    and phase_info.move_count <= 2
                    and phase_info.total_pieces >= PhaseDetector.OPENING_MIN_PIECES
                )
            if phase_info.confidence < 0.8:
                return False

        return effective_move_count <= 6 or (opening is not None and effective_move_count <= 8)

    def _format_engine_hint(self, engine_eval: Optional[Dict[str, Any]]) -> str:
        if not engine_eval:
            return ""

        cp = engine_eval.get("cp")
        best = engine_eval.get("best")
        if cp is None and not best:
            return ""

        if cp is None:
            score_text = "评分暂未返回"
        elif cp >= 120:
            score_text = f"红方先手效率更好（约{cp}cp）"
        elif cp <= -120:
            score_text = f"黑方应对较为从容（约{cp}cp）"
        else:
            score_text = f"局面大致均衡（约{cp}cp）"

        best_text = f"，引擎建议后续关注 {best}" if best else ""
        return score_text + best_text

    def _build_opening_expert_insights(
        self,
        opening_context: Dict[str, Any],
        engine_eval: Optional[Dict[str, Any]],
        move: Optional[str],
    ) -> Dict[str, Any]:
        opening = opening_context["opening"]
        opening_name = opening.name if opening else "常规开局阶段"
        opening_desc = opening.description if opening else "双方仍在完成基础出子，局面信息高度模板化。"
        opening_eval = opening.evaluation if opening else "此时最重要的是出子效率、中路控制和避免无谓重复走子。"
        principles = self._select_opening_principles(opening_name)
        normalized_move = opening_context["normalized_move"] or normalize_move(move or "")
        engine_hint = self._format_engine_hint(engine_eval)

        principle_lines = []
        for principle in principles:
            tip = principle["tips"][0] if principle.get("tips") else principle["description"]
            principle_lines.append(
                {
                    "name": principle["name"],
                    "tip": tip,
                }
            )

        if normalized_move:
            move_line = (
                f"这步 {normalized_move} 仍在 {opening_name} 的常见节奏内，优先价值是把布局走顺，而不是立刻追求复杂算杀。"
                if opening
                else f"这步 {normalized_move} 仍处在开局信息量较低的窗口，更应按开局原则评估出子效率与阵型协调。"
            )
        else:
            move_line = "当前更值得关注的是阵型是否顺、子力是否出净、谁先占到中路与节奏点。"

        evidence_bits = ["规则阶段识别=开局"]
        if opening:
            evidence_bits.append(f"开局书命中={opening_name}")
        if engine_hint:
            evidence_bits.append(f"轻量引擎评估={engine_hint}")

        return {
            "opening_name": opening_name,
            "opening_desc": opening_desc,
            "opening_eval": opening_eval,
            "principles": principle_lines,
            "move_line": move_line,
            "engine_hint": engine_hint,
            "evidence_bits": evidence_bits,
        }

    def _build_opening_fast_response(
        self,
        question: str,
        move: Optional[str],
        phase_info: PhaseInfo,
        opening_context: Dict[str, Any],
        engine_eval: Optional[Dict[str, Any]],
    ) -> str:
        insights = self._build_opening_expert_insights(opening_context, engine_eval, move)
        principle_lines = [f"- {item['name']}：{item['tip']}" for item in insights["principles"]]

        return (
            f"【开局判断】{insights['opening_name']}。{insights['opening_desc']}\n\n"
            f"【局面评价】{insights['opening_eval']}"
            + (f" {insights['engine_hint']}" if insights['engine_hint'] else "")
            + "\n\n"
            + (f"【这步棋怎么看】{insights['move_line']}\n\n" if insights['move_line'] else "")
            + "【此时最该讲清的原则】\n"
            + "\n".join(principle_lines)
            + "\n\n"
            + "【教练建议】开局前几步先看是否完成合理出子、是否占住中路、是否留下明显薄弱点；只有这些基础信息出现分歧时，才值得升级到重型深度分析。\n\n"
            + f"【证据基础】{'；'.join(insights['evidence_bits'])}"
        )

    def _emit_dispatch_info(
        self,
        on_thinking: Optional[Callable[[str, str], None]],
        payload: Dict[str, Any],
    ) -> None:
        if on_thinking:
            on_thinking("dispatch_info", json.dumps(payload, ensure_ascii=False))

        if self.debug_logger:
            summary = (
                f"dispatch={payload.get('mode', 'unknown')}"
                f", reason={payload.get('reason', '')}"
                f", experts={payload.get('selected_experts', [])}"
            )
            self.debug_logger.log_thinking("orchestrator", summary)

    def _emit_expert_prelude(
        self,
        on_thinking: Optional[Callable[[str, str], None]],
        expert: str,
        title: str,
        content: str,
    ) -> None:
        if not on_thinking:
            return

        on_thinking("expert_step_start", json.dumps({
            "expert": expert,
            "step_index": -1,
            "title": title,
        }, ensure_ascii=False))
        on_thinking("expert_step_content", json.dumps({
            "expert": expert,
            "step_index": -1,
            "title": title,
            "content": content,
        }, ensure_ascii=False))
        on_thinking("expert_step_end", json.dumps({
            "expert": expert,
            "step_index": -1,
            "title": title,
            "duration_ms": 0,
        }, ensure_ascii=False))

    def _emit_opening_fast_path_events(
        self,
        on_thinking: Optional[Callable[[str, str], None]],
        opening_context: Dict[str, Any],
        response: str,
        engine_eval: Optional[Dict[str, Any]] = None,
        move: Optional[str] = None,
    ) -> None:
        opening = opening_context["opening"]
        insights = self._build_opening_expert_insights(opening_context, engine_eval, move)
        opening_name = insights["opening_name"]

        self._emit_dispatch_info(
            on_thinking,
            {
                "mode": "opening_fast_path",
                "reason": "opening_knowledge_shortcut",
                "opening_name": opening_name,
                "move_count": opening_context["effective_move_count"],
                "selected_experts": ["strategy", "engine"],
            },
        )

        if not on_thinking:
            return

        on_thinking("orchestrator_subtitle", json.dumps({"message": f"协调开局分析：{opening_name}"}, ensure_ascii=False))

        on_thinking("expert_start", json.dumps({"expert": "strategy"}, ensure_ascii=False))
        on_thinking("expert_strategy_tool", json.dumps({"message": "query_chess_principles"}, ensure_ascii=False))
        on_thinking("expert_step_start", json.dumps({"expert": "strategy", "step_index": 0, "title": "识别开局脉络"}, ensure_ascii=False))
        on_thinking(
            "expert_step_content",
            json.dumps(
                {
                    "expert": "strategy",
                    "step_index": 0,
                    "title": "识别开局脉络",
                    "content": f"识别到 {opening_name}，先按开局书与原则库判断局面骨架：{insights['opening_desc']}",
                },
                ensure_ascii=False,
            ),
        )
        on_thinking("expert_step_end", json.dumps({"expert": "strategy", "step_index": 0, "title": "识别开局脉络", "duration_ms": 0}, ensure_ascii=False))
        principle_preview = "；".join(
            f"{item['name']}：{item['tip']}" for item in insights["principles"][:2]
        )
        on_thinking("expert_strategy_tool_result", json.dumps({"message": principle_preview}, ensure_ascii=False))
        on_thinking(
            "expert_result",
            json.dumps(
                {
                    "expert": "strategy",
                    "summary": f"{opening_name} 以布局效率为主线",
                    "finding": f"{insights['move_line']} 重点原则：{principle_preview}",
                    "success": True,
                },
                ensure_ascii=False,
            ),
        )

        on_thinking("expert_start", json.dumps({"expert": "engine"}, ensure_ascii=False))
        on_thinking("expert_engine_tool", json.dumps({"message": "engine_deep_analysis"}, ensure_ascii=False))
        on_thinking("expert_step_start", json.dumps({"expert": "engine", "step_index": 0, "title": "核对局面倾向"}, ensure_ascii=False))
        on_thinking(
            "expert_step_content",
            json.dumps(
                {
                    "expert": "engine",
                    "step_index": 0,
                    "title": "核对局面倾向",
                    "content": insights["engine_hint"] or "当前评分波动很小，说明还是标准开局节奏，重点不在暴力算杀而在谁更快完成布局。",
                },
                ensure_ascii=False,
            ),
        )
        on_thinking("expert_step_end", json.dumps({"expert": "engine", "step_index": 0, "title": "核对局面倾向", "duration_ms": 0}, ensure_ascii=False))
        on_thinking(
            "expert_engine_tool_result",
            json.dumps(
                {
                    "message": insights["engine_hint"] or "局面接近均势，开局信息仍偏模板化。",
                },
                ensure_ascii=False,
            ),
        )
        on_thinking(
            "expert_result",
            json.dumps(
                {
                    "expert": "engine",
                    "summary": insights["engine_hint"] or "轻量评估显示局面仍属常规开局",
                    "finding": insights["engine_hint"] or "当前不需要高成本深搜，先围绕出子效率与中路控制给出判断即可。",
                    "success": True,
                },
                ensure_ascii=False,
            ),
        )

        on_thinking("synthesis_step_start", json.dumps({"step_index": 0, "title": "汇总开局证据"}, ensure_ascii=False))
        on_thinking(
            "synthesis_step_content",
            json.dumps(
                {
                    "step_index": 0,
                    "title": "汇总开局证据",
                    "content": f"协调者已汇总开局识别、棋理原则与轻量评估，结论指向：{opening_name}。",
                },
                ensure_ascii=False,
            ),
        )
        on_thinking("synthesis_step_end", json.dumps({"step_index": 0, "title": "汇总开局证据", "duration_ms": 0}, ensure_ascii=False))
        on_thinking("synthesis_step_start", json.dumps({"step_index": 1, "title": "整理教学讲解"}, ensure_ascii=False))
        on_thinking(
            "synthesis_step_content",
            json.dumps(
                {
                    "step_index": 1,
                    "title": "整理教学讲解",
                    "content": response,
                },
                ensure_ascii=False,
            ),
        )
        on_thinking("synthesis_step_end", json.dumps({"step_index": 1, "title": "整理教学讲解", "duration_ms": 0}, ensure_ascii=False))

    def analyze_multi(
        self,
        fen: str,
        question: str,
        evidence_map: Dict = None,
        tag_summary: str = None,
        move_count: int = 0,
        engine_eval: Dict = None,
        move: str = None,
        move_history: Optional[List[str]] = None,
        on_thinking: Callable[[str, str], None] = None,
        force_full_team: bool = False,
    ) -> str:
        """
        多Agent并行分析

        1. 阶段检测 + 张力检测
        2. 自适应决策
        3. 并行调用三个专家
        4. 合成结果
        """
        tracer = get_tracer()

        with tracer.start_as_current_span(
            SpanNames.ORCHESTRATOR_ANALYZE_MULTI,
            attributes={
                SpanAttributes.FEN_HASH: _hash_fen(fen),
                SpanAttributes.MOVE_COUNT: move_count,
            }
        ) as span:
            # ===== 开始调试会话 =====
            if self.debug_logger:
                self.debug_logger.start_session(fen, question)

            # ===== 1. 预检测 =====
            phase_info = self._detect_phase(fen, move_count)
            tensions, primary_tension = self._detect_tensions(
                evidence_map or {}, engine_eval or {}, phase_info.phase_name
            )

            span.set_attribute(SpanAttributes.PHASE, phase_info.phase_name)
            span.set_attribute(SpanAttributes.TENSION_COUNT, len(tensions))
            if primary_tension:
                span.set_attribute(SpanAttributes.TENSION_TYPE, primary_tension.get("tension_type", ""))

            if self.debug_logger:
                self.debug_logger.log_thinking("orchestrator", f"阶段: {phase_info.phase_name}, 张力数: {len(tensions)}")

            tag_list = tag_summary if isinstance(tag_summary, list) else []
            primary_tension_dict = primary_tension if primary_tension else {}

            # 构建结构化 Evidence Map
            structured_em = self._build_structured_evidence_map(
                fen=fen,
                evidence_map=evidence_map,
                engine_eval=engine_eval,
                phase_info=phase_info,
                tensions=tensions,
            )

            if on_thinking and primary_tension_dict:
                core_question = primary_tension_dict.get("question", "关键问题")
                on_thinking("headline", f"正在围绕「{core_question[:30]}」展开分析…")

            # ===== 2. 并行调用三位专家 =====
            results = {}
            experts_start = time.time()
            policy = choose_analysis_policy(
                question=question,
                tensions=tensions,
                phase_name=phase_info.phase_name,
                engine_eval=engine_eval,
                move_count=move_count,
                force_full_team=force_full_team,
            )
            span.set_attribute("policy.selected_experts", ",".join(policy.selected_experts))
            span.set_attribute("policy.parallelism", policy.parallelism)
            span.set_attribute("policy.reason", policy.reason)

            self._emit_dispatch_info(
                on_thinking,
                {
                    "mode": "multi_agent",
                    "reason": policy.reason,
                    "selected_experts": policy.selected_experts,
                    "parallelism": policy.parallelism,
                    "phase": phase_info.phase_name,
                    "move_count": move_count,
                },
            )

            if on_thinking:
                on_thinking("headline", f"调度策略：{','.join(policy.selected_experts)}；并发={policy.parallelism}")

            def run_expert(name: str, span_name: str, func) -> tuple:
                """包装专家执行，捕获异常，加入 OTEL Span"""
                expert_tracer = get_tracer()
                with expert_tracer.start_as_current_span(
                    span_name,
                    attributes={SpanAttributes.AGENT_NAME: name}
                ) as expert_span:
                    try:
                        result = func()
                        expert_span.set_attribute(SpanAttributes.EXPERT_SUCCESS, result.success)
                        if result.success:
                            expert_span.set_attribute(SpanAttributes.EXPERT_FINDING, result.finding[:100])
                        else:
                            expert_span.set_attribute(SpanAttributes.ERROR, True)
                            expert_span.set_attribute(SpanAttributes.ERROR_MESSAGE, str(result.error or ""))
                        return (name, result)
                    except Exception as e:
                        expert_span.set_attribute(SpanAttributes.ERROR, True)
                        expert_span.set_attribute(SpanAttributes.ERROR_MESSAGE, str(e))
                        return (name, ExpertResult(
                            expert_name=name, finding="执行失败",
                            details=str(e), success=False, error=str(e),
                            status=AnalysisStatus.FAILED,
                            failure_type=ExpertFailureType.REQUEST_EXCEPTION,
                            confidence="low",
                            missing_evidence=["expert_execution"],
                            degraded=True,
                            degradation_level=DegradationLevel.PARTIAL_EXPERTS,
                        ))

            def call_tactics():
                if on_thinking:
                    on_thinking("expert_start", json.dumps({"expert": "tactics"}, ensure_ascii=False))
                self._emit_expert_prelude(
                    on_thinking,
                    "tactics",
                    "预读战术冲突",
                    f"优先核对将军、互吃、炮串打和无根子。当前阶段={phase_info.phase_name}，已检测张力数={len(tensions)}。",
                )
                result = self.tactics_expert.analyze(
                    fen=fen, question=question,
                    tag_summary=tag_list, primary_tension=primary_tension_dict,
                    phase_info=phase_info, move=move, on_thinking=on_thinking,
                    evidence_map=structured_em,
                )
                if on_thinking:
                    on_thinking("expert_result", json.dumps({
                        "expert": "tactics",
                        "summary": result.finding,
                        "finding": result.details if result.details else result.finding,
                        "success": result.success,
                    }, ensure_ascii=False))
                return result

            def call_strategy():
                if on_thinking:
                    on_thinking("expert_start", json.dumps({"expert": "strategy"}, ensure_ascii=False))
                self._emit_expert_prelude(
                    on_thinking,
                    "strategy",
                    "预读局面主线",
                    f"先读阶段、子力与主导矛盾。当前阶段={phase_info.phase_name}，主张力={primary_tension_dict.get('tension_type', '待判定')}。",
                )
                result = self.strategy_expert.analyze(
                    fen=fen, question=question,
                    tag_summary=tag_list, primary_tension=primary_tension_dict,
                    phase_info=phase_info, move=move, on_thinking=on_thinking,
                    evidence_map=structured_em,
                )
                if on_thinking:
                    on_thinking("expert_result", json.dumps({
                        "expert": "strategy",
                        "summary": result.finding,
                        "finding": result.details if result.details else result.finding,
                        "success": result.success,
                    }, ensure_ascii=False))
                return result

            def call_engine():
                if on_thinking:
                    on_thinking("expert_start", json.dumps({"expert": "engine"}, ensure_ascii=False))
                engine_preview = self._format_engine_hint(engine_eval) or "先核对评分、主变化和候选分差。"
                self._emit_expert_prelude(
                    on_thinking,
                    "engine",
                    "预读引擎快照",
                    engine_preview,
                )
                result = self.engine_expert.analyze(
                    fen=fen, question=question,
                    tag_summary=tag_list, primary_tension=primary_tension_dict,
                    phase_info=phase_info, engine_eval=engine_eval,
                    move=move, on_thinking=on_thinking,
                    evidence_map=structured_em,
                )
                if on_thinking:
                    on_thinking("expert_result", json.dumps({
                        "expert": "engine",
                        "summary": result.finding,
                        "finding": result.details if result.details else result.finding,
                        "success": result.success,
                    }, ensure_ascii=False))
                return result

            expert_jobs = {
                "tactics": (SpanNames.TACTICS_EXPERT_ANALYZE, call_tactics),
                "strategy": (SpanNames.STRATEGY_EXPERT_ANALYZE, call_strategy),
                "engine": (SpanNames.ENGINE_EXPERT_ANALYZE, call_engine),
            }

            for expert_name in ["tactics", "strategy", "engine"]:
                if expert_name not in policy.selected_experts:
                    results[expert_name] = self._skipped_result(expert_name, f"policy:{policy.reason}")

            selected_jobs = [(name, *expert_jobs[name]) for name in policy.selected_experts]
            if policy.parallelism <= 1:
                for name, span_name, func in selected_jobs:
                    _, result = run_expert(name, span_name, func)
                    results[name] = result
            else:
                with ThreadPoolExecutor(max_workers=policy.parallelism) as executor:
                    futures = [
                        executor.submit(run_expert, name, span_name, func)
                        for name, span_name, func in selected_jobs
                    ]
                    for future in futures:
                        name, result = future.result(timeout=180)
                        results[name] = result

            span.set_attribute("experts.duration_ms", int((time.time() - experts_start) * 1000))

            # ===== 3. 合成结果 =====
            synthesis_start = time.time()

            def on_synthesis_event(event_type: str, payload: Dict[str, Any]):
                if on_thinking:
                    on_thinking(event_type, json.dumps(payload, ensure_ascii=False))

            tactics_r = results.get("tactics")
            strategy_r = results.get("strategy")
            engine_r = results.get("engine")

            synthesis_tracer = get_tracer()
            with synthesis_tracer.start_as_current_span(
                SpanNames.SYNTHESIZER_SYNTHESIZE,
                attributes={SpanAttributes.AGENT_NAME: "synthesizer"}
            ):
                synthesis = self.synthesizer.synthesize(
                    tactics_result=tactics_r if tactics_r else self._skipped_result("tactics", "missing_result"),
                    strategy_result=strategy_r if strategy_r else self._skipped_result("strategy", "missing_result"),
                    engine_result=engine_r if engine_r else self._skipped_result("engine", "missing_result"),
                    user_question=question,
                    on_event=on_synthesis_event,
                )
                span.set_attribute("synthesis.duration_ms", int((time.time() - synthesis_start) * 1000))
                span.set_attribute("synthesis.length", len(synthesis))

            if self.debug_logger:
                self.debug_logger.end_session()

            return synthesis

    def analyze_single(
        self,
        fen: str,
        question: str,
        evidence_map: Dict = None,
        tag_summary: str = None,
        move_count: int = 0,
        engine_eval: Dict = None,
        move: str = None,
        on_thinking: Callable[[str, str], None] = None,
        max_rounds: int = 5,
    ) -> str:
        """
        单Agent分析（用于简单局面或降级）
        复用现有的 XiangqiCoachAgent.analyze() 逻辑
        """
        from core.llm.xiangqi_coach import XiangqiCoachAgent
        agent = XiangqiCoachAgent(enable_recording=False)
        return agent.analyze(
            fen=fen, question=question,
            evidence_map=evidence_map,
            tag_summary=tag_summary,
            move_count=move_count,
            engine_eval=engine_eval,
            move=move,
            on_thinking=on_thinking,
        )

    def analyze(
        self,
        fen: str,
        question: str,
        evidence_map: Dict = None,
        tag_summary: str = None,
        move_count: int = 0,
        engine_eval: Dict = None,
        move: str = None,
        move_history: Optional[List[str]] = None,
        on_thinking: Callable[[str, str], None] = None,
        force_multi: bool = False,
    ) -> str:
        """
        自适应分析入口

        根据局面复杂度自动选择：
        - 简单局面 → 单Agent（快速）
        - 复杂局面 → 多Agent并行 + 合成
        """
        tracer = get_tracer()

        with tracer.start_as_current_span(
            SpanNames.ORCHESTRATOR_ANALYZE,
            attributes={
                SpanAttributes.FEN_HASH: _hash_fen(fen),
                SpanAttributes.MOVE_COUNT: move_count or len(move_history or []),
            }
        ) as span:
            actual_move_count = self._infer_move_count(fen, move_count, move_history)

            # ===== 预检测 =====
            phase_info = self._detect_phase(fen, actual_move_count, move_history)
            tensions, _ = self._detect_tensions(
                evidence_map or {}, engine_eval or {}, phase_info.phase_name
            )

            # 设置阶段属性
            span.set_attribute(SpanAttributes.PHASE, phase_info.phase_name)
            span.set_attribute(SpanAttributes.TENSION_COUNT, len(tensions))

            # ===== 自适应决策 =====
            opening_context = self._build_opening_context(move_history, move)
            if self._should_use_opening_fast_path(question, phase_info, tensions, opening_context, force_multi):
                if self.debug_logger:
                    self.debug_logger.start_session(fen, question)
                response = self._build_opening_fast_response(
                    question=question,
                    move=move,
                    phase_info=phase_info,
                    opening_context=opening_context,
                    engine_eval=engine_eval,
                )
                self._emit_opening_fast_path_events(on_thinking, opening_context, response, engine_eval=engine_eval, move=move)
                span.set_attribute("decision.opening_fast_path", True)
                if self.debug_logger:
                    self.debug_logger.end_session()
                return response

            use_multi = bool(on_thinking) or force_multi or should_use_multi_agent(
                tensions=tensions,
                phase_name=phase_info.phase_name,
                user_request=question,
            )
            span.set_attribute("decision.use_multi_agent", use_multi)

            if use_multi:
                return self.analyze_multi(
                    fen=fen, question=question,
                    evidence_map=evidence_map,
                    tag_summary=tag_summary,
                    move_count=actual_move_count,
                    engine_eval=engine_eval,
                    move=move,
                    move_history=move_history,
                    on_thinking=on_thinking,
                    force_full_team=force_multi,
                )
            else:
                return self.analyze_single(
                    fen=fen, question=question,
                    evidence_map=evidence_map,
                    tag_summary=tag_summary,
                    move_count=actual_move_count,
                    engine_eval=engine_eval,
                    move=move,
                    on_thinking=on_thinking,
                )


# ═══════════════════════════════════════════════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════════════════════════════════════════════

def _hash_fen(fen: str, length: int = 16) -> str:
    """生成 FEN 的短哈希（避免在 Span 中记录完整 FEN）"""
    import hashlib
    return hashlib.sha256(fen.encode()).hexdigest()[:length]

