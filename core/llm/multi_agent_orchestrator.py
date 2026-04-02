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

from core.llm.analysis_policy import choose_analysis_policy
from core.llm.contracts import AnalysisStatus, DegradationLevel, ExpertFailureType
from core.llm.experts.base_expert import (
    ExpertResult, should_use_multi_agent, STEP_PATTERN,
)
from core.llm.claim import format_claims_for_synthesis, ClaimSource, ClaimConfidence
from core.llm.experts.tactics_expert import TacticsExpert
from core.llm.experts.strategy_expert import StrategyExpert
from core.llm.experts.engine_expert import EngineExpert
from core.llm.reliable_client import ReliableLLMClient
from core.llm.thinking_templates import PhaseInfo, PhaseDetector
from core.rules.tension_detector import detect_tensions, get_primary_tension
from core.llm.debug_logger import AgentDebugLogger
from core.llm.tracing import (
    get_tracer, add_span_attributes,
    SpanNames, SpanAttributes,
)


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

在每个综合阶段开始前，先单独输出一行阶段标题，格式为：
## [数字] [简短描述]

例如：
## 1 对齐三方断言
## 2 交叉验证证据
## 3 形成最终教练建议

在你开始一个新的综合步骤时，必须先单独输出一行：
[STEP: 你正在做什么的一句话]

示例：
[STEP: 识别三位专家的共识断言]
[STEP: 裁决战术与引擎之间的分歧]
[STEP: 生成面向学生的教练建议]

请生成最终讲解：
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
                lines.append(f"详情：{result.details}")

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

        return self._call_stream(messages, on_event=on_event)

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
            max_tokens=1024,
            thinking_enabled=False,
            on_chunk=_on_chunk,
        )
        if step_parser:
            step_parser.finalize()
        if not response.success:
            return f"合成失败: {response.error_message}"
        return response.content


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

    def _detect_phase(self, fen: str, move_count: int) -> PhaseInfo:
        """检测当前阶段"""
        return PhaseDetector.detect(fen, move_count)

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

    def analyze_multi(
        self,
        fen: str,
        question: str,
        evidence_map: Dict = None,
        tag_summary: str = None,
        move_count: int = 0,
        engine_eval: Dict = None,
        move: str = None,
        on_thinking: Callable[[str, str], None] = None,
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
                force_full_team=False,
            )
            span.set_attribute("policy.selected_experts", ",".join(policy.selected_experts))
            span.set_attribute("policy.parallelism", policy.parallelism)
            span.set_attribute("policy.reason", policy.reason)

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
                SpanAttributes.MOVE_COUNT: move_count,
            }
        ) as span:
            # ===== 预检测 =====
            phase_info = self._detect_phase(fen, move_count)
            tensions, _ = self._detect_tensions(
                evidence_map or {}, engine_eval or {}, phase_info.phase_name
            )

            # 设置阶段属性
            span.set_attribute(SpanAttributes.PHASE, phase_info.phase_name)
            span.set_attribute(SpanAttributes.TENSION_COUNT, len(tensions))

            # ===== 自适应决策 =====
            use_multi = force_multi or should_use_multi_agent(
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
                    move_count=move_count,
                    engine_eval=engine_eval,
                    move=move,
                    on_thinking=on_thinking,
                )
            else:
                return self.analyze_single(
                    fen=fen, question=question,
                    evidence_map=evidence_map,
                    tag_summary=tag_summary,
                    move_count=move_count,
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

