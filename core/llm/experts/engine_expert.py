"""
引擎专家 - 专注于引擎评估和数据解读

像数据分析师一样精准。
"""

from typing import Dict, List, Callable, Optional
from core.llm.experts.base_expert import (
    BaseExpert, ExpertConfig, ExpertResult,
    should_use_multi_agent,
)
from core.llm.thinking_templates import PhaseInfo


SYSTEM_PROMPT_ENGINE = """# 你是谁

你是象棋引擎数据分析师，专注于解读引擎评估和候选走法。
看到一个局面，你脑子里第一个问题永远是"引擎怎么看？分数合理吗？候选走法有什么深层含义？"，而不是"这里有什么战术"。

你享受挖掘引擎数据背后逻辑的过程——为什么引擎推荐这步？分数落差说明了什么？
这种对数据精确性的追求是你分析的核心。

---

# 你怎么思考

**起点**：先看引擎评估数字，理解其含义。
用"我初步判断..."开头写出你对引擎评估的解读。

**解读维度**：
- 评估分数：cp值或mate值的含义（占优/略优/均势/略劣/大劣）
- 候选走法：为什么引擎推荐这个走法而不是其他？
- 分数落差：直觉感受和引擎评估的差异说明了什么？
- 变化线：主要变化背后的战略逻辑

**深入**：如果发现评估异常，追问：
- 引擎分数和局面直观感受是否一致？
- 候选走法之间有什么质的区别？
- 引擎可能忽略了什么（非量化因素）？

**边界**：不确定就说不知道，不要猜测。引擎是工具，不是神。

---

# 你不能做什么

以下内容只能来自工具返回，绝对不能凭感觉填写：
- 引擎评估的具体数值（cp/mate）
- 候选走法的具体分数
- 引擎推荐的走法

**你可以通过工具验证的**：
- 引擎推荐背后的战术/战略逻辑
- 候选走法的相对优劣原因
- 引擎评估和局面直觉的对比

---

# 你的输出格式

请完成分析后，给出：
【引擎解读】一句话描述你对引擎评估的理解
【详细分析】你的引擎解读过程（200-500字）
【逻辑验证】用战术或战略逻辑验证引擎推荐的合理性
【结论可信度】高/中/低（基于工具验证了多少）
"""


# 引擎专家的工具子集
ENGINE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "engine_deep_analysis",
            "description": "引擎深度分析。【什么时候用】需要权威的局势评估、分析关键局面。",
            "parameters": {
                "type": "object",
                "properties": {
                    "depth": {"type": "integer", "description": "分析深度，默认20", "default": 20}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "engine_alternatives",
            "description": "获取引擎的多个候选走法对比。【什么时候用】用户问'还有什么选择'、分析候选走法优劣。",
            "parameters": {
                "type": "object",
                "properties": {
                    "top_n": {"type": "integer", "description": "返回候选数，默认3", "default": 3}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_move",
            "description": "深度分析某步棋的效果。【什么时候用】验证引擎推荐的走法背后的逻辑。",
            "parameters": {
                "type": "object",
                "properties": {
                    "move": {"type": "string", "description": "UCI格式走法"}
                },
                "required": ["move"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "compare_moves",
            "description": "对比多步棋的优劣。【什么时候用】对比引擎候选走法和直觉走法的差异。",
            "parameters": {
                "type": "object",
                "properties": {
                    "moves": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "UCI格式走法列表"
                    }
                },
                "required": ["moves"]
            }
        }
    },
]


class EngineExpert(BaseExpert):
    """引擎专家"""

    CONFIG = ExpertConfig(
        name="engine",
        display_name="引擎专家",
        role="专注于引擎评估和数据解读",
        system_prompt=SYSTEM_PROMPT_ENGINE,
        tools=ENGINE_TOOLS,
        tool_names=[
            "engine_deep_analysis", "engine_alternatives",
            "analyze_move", "compare_moves",
        ],
        max_rounds=3,
        max_tokens=512,
    )

    def analyze(
        self,
        fen: str,
        question: str,
        tag_summary: str,
        primary_tension: Dict,
        phase_info: PhaseInfo,
        engine_eval: Dict = None,
        move: str = None,
        on_thinking: Callable[[str, str], None] = None,
    ) -> ExpertResult:
        """执行引擎专家分析"""
        user_content = self._build_shared_context(
            fen=fen,
            tag_summary=tag_summary,
            primary_tension=primary_tension,
            phase_info=phase_info,
            question=question,
            move=move,
        )

        # 注入引擎评估数据（引擎专家独特的信息）
        if engine_eval:
            eval_parts = ["【引擎评估】（供参考）"]
            if "cp" in engine_eval:
                eval_parts.append("- 评估分数：%dcp" % engine_eval['cp'])
            if "best" in engine_eval and engine_eval['best']:
                eval_parts.append("- 最佳走法：%s" % engine_eval['best'])
            if "eval_human" in engine_eval:
                eval_parts.append("- 人类可读评估：%s" % engine_eval['eval_human'])
            user_content = (chr(10)).join(eval_parts) + chr(10) + chr(10) + user_content

        return self._call_expert(
            system_prompt=self.CONFIG.system_prompt,
            user_content=user_content,
            config=self.CONFIG,
            fen=fen,
            on_thinking=on_thinking,
        )
