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

import requests

from core.llm.experts.base_expert import (
    ExpertResult, should_use_multi_agent, STEP_PATTERN,
)
from core.llm.experts.tactics_expert import TacticsExpert
from core.llm.experts.strategy_expert import StrategyExpert
from core.llm.experts.engine_expert import EngineExpert
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

你是一位综合裁判，汇总三位专家的观点，生成统一的象棋讲解。

三位专家已经分别从不同角度分析了当前局面：
- 战术专家：专注于子力关系和战术细节
- 战略专家：专注于全局战略和相位判断
- 引擎专家：专注于解读引擎评估和候选走法

---

# 你的任务

1. **找出共识**：三位专家都同意的点是什么？
2. **找出分歧**：哪些地方专家们看法不一致？
3. **综合对手处境**（关键任务）：
   - 三位专家对对手选项的分析是否一致？
   - 是否有专家发现了其他专家忽略的对手应着？
   - 综合判断：对手是被锁死还是有化解方式？
4. **解决分歧**：当专家意见冲突时，给出你的综合判断
5. **生成讲解**：用通俗语言生成面向学生的统一讲解

---

# 解决分歧的规则

| 冲突类型 | 解决策略 |
|----------|----------|
| 引擎评估 vs 战术发现 | 战术发现优先（战术是精确规则，引擎可能误判相位） |
| 战略判断 vs 引擎评估 | 差异说明：给出双方观点，解释原因 |
| 三方完全矛盾 | 标注为"复杂局面"，给出多个可能解读 |

---

# 绝对约束

- 不能编造棋子位置（来自专家结论中的事实）
- 不能忽略任何一位专家的高置信度结论
- 讲解必须回应用户原始问题
- 用"因为...所以..."的因果逻辑组织讲解

---

# 输出格式

在每个综合阶段开始前，先单独输出一行阶段标题，格式为：
## [数字] [简短描述]

例如：
## 1 汇总三位专家共识
## 2 识别关键分歧
## 3 形成最终教练建议

在你开始一个新的综合步骤时，必须先单独输出一行：
[STEP: 你正在做什么的一句话]

示例：
[STEP: 识别三位专家的共识]
[STEP: 解决战术与引擎之间的分歧]
[STEP: 生成面向学生的教练建议]

请生成最终讲解：
【综合评估】一句话综合三位专家的观点
【对手处境】综合分析对手的选项和应对（必须包含）
【共识分析】三方一致同意的核心观点
【分歧解读】分歧点的详细分析和你的综合判断
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
        # 构建专家结论摘要
        expert_summaries = f"""【战术专家结论】
发现：{tactics_result.finding}
详情：{tactics_result.details}

【战略专家结论】
发现：{strategy_result.finding}
详情：{strategy_result.details}

【引擎专家结论】
发现：{engine_result.finding}
详情：{engine_result.details}
"""

        user_content = f"""请综合三位专家的结论，生成统一的象棋讲解。

【用户原始问题】
{user_question}

【三位专家的分析结论】
{expert_summaries}

请按照你的任务，生成最终讲解。
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
        if not self.api_key:
            return "API Key未配置"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1024,
            "stream": True,
        }

        try:
            session = requests.Session()
            session.trust_env = False
            response = session.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                stream=True,
                timeout=120,
            )

            if response.status_code != 200:
                return f"合成器API错误: {response.status_code}"

            full_content = []
            step_parser = SynthesisStepStreamParser(on_event) if on_event else None
            for line in response.iter_lines():
                if not line:
                    continue
                line = line.decode('utf-8')
                if not line.startswith('data: '):
                    continue
                data_str = line[6:]
                if data_str == '[DONE]':
                    break
                try:
                    data = json.loads(data_str)
                    delta = data.get("choices", [{}])[0].get("delta", {})
                    chunk = delta.get("content", "")
                    if chunk:
                        full_content.append(chunk)
                        # 始终实时推送 chunk，确保前端降级方案有内容
                        if on_event:
                            on_event("synthesis_chunk", {"message": chunk})
                        if step_parser:
                            step_parser.feed(chunk)
                except json.JSONDecodeError:
                    continue

            final_content = "".join(full_content)
            if step_parser:
                step_parser.finalize()

            return final_content

        except Exception as e:
            return f"合成失败: {str(e)}"


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

            if on_thinking and primary_tension_dict:
                core_question = primary_tension_dict.get("question", "关键问题")
                on_thinking("headline", f"正在围绕「{core_question[:30]}」展开分析…")

            # ===== 2. 并行调用三位专家 =====
            results = {}
            experts_start = time.time()

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
                        ))

            def call_tactics():
                if on_thinking:
                    on_thinking("expert_start", json.dumps({"expert": "tactics"}, ensure_ascii=False))
                result = self.tactics_expert.analyze(
                    fen=fen, question=question,
                    tag_summary=tag_list, primary_tension=primary_tension_dict,
                    phase_info=phase_info, move=move, on_thinking=on_thinking,
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
                )
                if on_thinking:
                    on_thinking("expert_result", json.dumps({
                        "expert": "engine",
                        "summary": result.finding,
                        "finding": result.details if result.details else result.finding,
                        "success": result.success,
                    }, ensure_ascii=False))
                return result

            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = [
                    executor.submit(run_expert, "tactics", SpanNames.TACTICS_EXPERT_ANALYZE, call_tactics),
                    executor.submit(run_expert, "strategy", SpanNames.STRATEGY_EXPERT_ANALYZE, call_strategy),
                    executor.submit(run_expert, "engine", SpanNames.ENGINE_EXPERT_ANALYZE, call_engine),
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
                    tactics_result=tactics_r if tactics_r and tactics_r.success else
                        ExpertResult(expert_name="tactics", finding="未执行", details="", success=False),
                    strategy_result=strategy_r if strategy_r and strategy_r.success else
                        ExpertResult(expert_name="strategy", finding="未执行", details="", success=False),
                    engine_result=engine_r if engine_r and engine_r.success else
                        ExpertResult(expert_name="engine", finding="未执行", details="", success=False),
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

