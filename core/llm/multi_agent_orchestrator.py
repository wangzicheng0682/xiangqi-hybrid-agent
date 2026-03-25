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
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Callable, Optional

import requests

from core.llm.agent_tools import AgentTools, ToolResult
from core.llm.experts.base_expert import (
    BaseExpert, ExpertResult, ExpertConfig,
    should_use_multi_agent, ToolCall,
)
from core.llm.experts.tactics_expert import TacticsExpert
from core.llm.experts.strategy_expert import StrategyExpert
from core.llm.experts.engine_expert import EngineExpert
from core.llm.thinking_templates import PhaseInfo, PhaseDetector
from core.rules.tension_detector import (
    detect_tensions, get_primary_tension,
    Tension, TensionPriority,
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

请生成最终讲解：
【综合评估】一句话综合三位专家的观点
【对手处境】综合分析对手的选项和应对（必须包含）
【共识分析】三方一致同意的核心观点
【分歧解读】分歧点的详细分析和你的综合判断
【教练建议】给学生的具体建议
"""

SYNTHESIZER_MODEL = "glm-5"
SYNTHESIZER_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"


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
        on_chunk: Callable[[str], None] = None,
    ) -> str:
        """
        合成三位专家的结论，生成统一讲解

        Args:
            tactics_result: 战术专家结论
            strategy_result: 战略专家结论
            engine_result: 引擎专家结论
            user_question: 用户原始问题
            on_chunk: 流式回调

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

        return self._call_stream(messages, on_chunk=on_chunk)

    def _call_stream(
        self,
        messages: List[Dict],
        on_chunk: Callable[[str], None] = None,
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
                        if on_chunk:
                            on_chunk(chunk)
                except json.JSONDecodeError:
                    continue

            return "".join(full_content)

        except Exception as e:
            return f"合成失败: {str(e)}"


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

    def __init__(self, api_key: str = None):
        self.tactics_expert = TacticsExpert(api_key=api_key)
        self.strategy_expert = StrategyExpert(api_key=api_key)
        self.engine_expert = EngineExpert(api_key=api_key)
        self.synthesizer = Synthesizer(api_key=api_key)
        self._tool_functions = {
            "get_piece_attacks": AgentTools().get_piece_attacks,
            "get_piece_defenders": AgentTools().get_piece_defenders,
            "get_threats_to_piece": AgentTools().get_threats_to_piece,
            "get_piece_relations": AgentTools().get_piece_relations,
            "analyze_move": AgentTools().analyze_move,
            "compare_moves": AgentTools().compare_moves,
            "get_forcing_sequence": AgentTools().get_forcing_sequence,
            "engine_deep_analysis": AgentTools().engine_deep_analysis,
            "engine_alternatives": AgentTools().engine_alternatives,
            "analyze_position_strategy": AgentTools().analyze_position_strategy,
        }

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

        Args:
            on_thinking: SSE回调，参数为(event_type, message)
                - "expert_start": 专家开始 {"expert": "tactics"|"strategy"|"engine"}
                - "expert_result": 专家完成 {"expert": "...", "finding": "...", "success": true}
                - "synthesis_chunk": 合成内容片段
                - "synthesis": 合成完成

        Returns:
            统一讲解文本
        """
        # ===== 1. 预检测 =====
        phase_info = self._detect_phase(fen, move_count)
        tensions, primary_tension = self._detect_tensions(
            evidence_map or {}, engine_eval or {}, phase_info.phase_name
        )

        tag_list = tag_summary if isinstance(tag_summary, list) else []
        # get_primary_tension already returns Dict, not Tension object
        primary_tension_dict = primary_tension if primary_tension else {}

        # ===== 2. 并行调用三位专家 =====
        def call_tactics():
            if on_thinking:
                on_thinking("expert_start", json.dumps({"expert": "tactics"}, ensure_ascii=False))
            result = self.tactics_expert.analyze(
                fen=fen, question=question,
                tag_summary=tag_list,
                primary_tension=primary_tension_dict,
                phase_info=phase_info,
                move=move,
                on_thinking=on_thinking,
            )
            if on_thinking:
                on_thinking("expert_result", json.dumps({
                    "expert": "tactics",
                    "finding": result.finding,
                    "details": result.details[:200] if result.details else "",
                    "success": result.success,
                }, ensure_ascii=False))
            return result

        def call_strategy():
            if on_thinking:
                on_thinking("expert_start", json.dumps({"expert": "strategy"}, ensure_ascii=False))
            result = self.strategy_expert.analyze(
                fen=fen, question=question,
                tag_summary=tag_list,
                primary_tension=primary_tension_dict,
                phase_info=phase_info,
                move=move,
                on_thinking=on_thinking,
            )
            if on_thinking:
                on_thinking("expert_result", json.dumps({
                    "expert": "strategy",
                    "finding": result.finding,
                    "details": result.details[:200] if result.details else "",
                    "success": result.success,
                }, ensure_ascii=False))
            return result

        def call_engine():
            if on_thinking:
                on_thinking("expert_start", json.dumps({"expert": "engine"}, ensure_ascii=False))
            result = self.engine_expert.analyze(
                fen=fen, question=question,
                tag_summary=tag_list,
                primary_tension=primary_tension_dict,
                phase_info=phase_info,
                engine_eval=engine_eval,
                move=move,
                on_thinking=on_thinking,
            )
            if on_thinking:
                on_thinking("expert_result", json.dumps({
                    "expert": "engine",
                    "finding": result.finding,
                    "details": result.details[:200] if result.details else "",
                    "success": result.success,
                }, ensure_ascii=False))
            return result

        # 并行执行
        results = {}
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(call_tactics): "tactics",
                executor.submit(call_strategy): "strategy",
                executor.submit(call_engine): "engine",
            }

            for future in as_completed(futures):
                name = futures[future]
                try:
                    results[name] = future.result()
                except Exception as e:
                    results[name] = ExpertResult(
                        expert_name=name,
                        finding="执行失败",
                        details=str(e),
                        success=False,
                        error=str(e),
                    )

        # ===== 3. 合成结果 =====
        def on_synthesis_chunk(chunk: str):
            if on_thinking:
                on_thinking("synthesis_chunk", chunk)

        synthesis = self.synthesizer.synthesize(
            tactics_result=results.get("tactics", ExpertResult(
                expert_name="tactics", finding="未执行", details="", success=False
            )),
            strategy_result=results.get("strategy", ExpertResult(
                expert_name="strategy", finding="未执行", details="", success=False
            )),
            engine_result=results.get("engine", ExpertResult(
                expert_name="engine", finding="未执行", details="", success=False
            )),
            user_question=question,
            on_chunk=on_synthesis_chunk,
        )

        # synthesis 事件由 orchestrator.analyze() 返回后，在 API 层统一发送
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

        Args:
            force_multi: 强制使用多Agent（忽略自适应判断）
        """
        # ===== 预检测 =====
        phase_info = self._detect_phase(fen, move_count)
        tensions, _ = self._detect_tensions(
            evidence_map or {}, engine_eval or {}, phase_info.phase_name
        )

        # ===== 自适应决策 =====
        use_multi = force_multi or should_use_multi_agent(
            tensions=tensions,
            phase_name=phase_info.phase_name,
            user_request=question,
        )

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
