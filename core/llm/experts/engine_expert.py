"""
引擎专家 - 专注于引擎评估和数据解读

像数据分析师一样精准。
"""

from typing import Dict, List, Callable, Optional
from core.llm.experts.base_expert import (
    BaseExpert, ExpertConfig, ExpertResult, CHESS_RULES_BLOCK,
)
from core.llm.thinking_templates import PhaseInfo


SYSTEM_PROMPT_ENGINE = CHESS_RULES_BLOCK + """
- 你解读引擎推荐走法时，必须检查是否符合上述走法规则

---

# 你是谁

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

**深入**：分析引擎推荐时，必须解读**候选走法落差**：

引擎分数的真正价值不在于"告诉我最佳走法"，而在于回答：
"如果我选第二候选，代价是什么？对手能利用吗？"

**候选落差分析**（必须调用 `engine_alternatives`）：
1. Top3候选的分数分别是多少？
2. 第一候选和第二候选的分数差说明了什么？
   - 差距<30cp：有选择空间，多条路差不多
   - 差距50-100cp：第一候选明显更好，但其他也可下
   - 差距>100cp：**唯一解**，必须走这步
3. 如果我不走引擎推荐，对手能惩罚我吗？

**输出要求**（必须包含）：
【候选分析】
- 第一候选：...（分数+一句话解释）
- 第二候选：...（分数+一句话解释）
- 分数落差：...cp → 是唯一解 / 有选择空间
- 不走最佳的风险：对手能/不能惩罚

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

【输出格式要求】
在开始深入分析之前，先输出一行阶段标题，格式为：
## [N] [简短描述]

例如：
## 1 读取引擎评估
## 2 比较候选分差
## 3 验证最佳着逻辑

阶段标题输出后，再开始该阶段的详细分析。

在你开始一个新的分析步骤时，必须先单独输出一行：
[STEP: 你正在做什么的一句话]

示例：
[STEP: 读取引擎评估和主变化]
[STEP: 比较前三候选走法的分差]
[STEP: 解读不走最佳着的风险]

请完成分析后，给出：
【引擎解读】一句话描述你对引擎评估的理解
【候选分析】第一/第二/第三候选对比 + 分数落差解读（必须填写）
【详细分析】你的引擎解读过程（200-500字）
【逻辑验证】用战术或战略逻辑验证引擎推荐的合理性
【结论可信度】高/中/低（基于工具验证了多少）

---

# 结构化断言（必须）

分析结束时，用以下格式列出你的核心断言（1-3条）：

[CLAIM] 你的一条核心结论
[EVIDENCE] 支撑该结论的证据来源（哪个工具验证的，或纯推理）
[CONFIDENCE] 高/中/低

示例：
[CLAIM] 引擎最佳着 e2e6 比次选强 200 分，有明显优势
[EVIDENCE] engine_deep_analysis 返回 best=e2e6 cp=+320，次选 cp=+120
[CONFIDENCE] 高
"""


# 引擎专家的工具子集
ENGINE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_move_candidates",
            "description": "获取当前局面的合法候选走法列表。需要验证具体走法时，优先基于 candidate_id 继续分析。",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "返回候选数，默认12", "default": 12}
                },
                "required": []
            }
        }
    },
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
            "description": "深度分析某步棋的效果。【什么时候用】验证引擎推荐的走法背后的逻辑。优先传 candidate_id。",
            "parameters": {
                "type": "object",
                "properties": {
                    "candidate_id": {"type": "string", "description": "候选走法ID，如cand_1，优先使用"},
                    "move": {"type": "string", "description": "UCI格式走法，仅兼容旧接口时使用"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "compare_moves",
            "description": "对比多步棋的优劣。【什么时候用】对比引擎候选走法和直觉走法的差异。优先传 candidate_ids。",
            "parameters": {
                "type": "object",
                "properties": {
                    "candidate_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "候选走法ID列表，如['cand_1', 'cand_2']，优先使用"
                    },
                    "moves": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "UCI格式走法列表，仅兼容旧接口时使用"
                    }
                },
                "required": []
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
            "get_move_candidates",
            "engine_deep_analysis", "engine_alternatives",
            "analyze_move", "compare_moves",
        ],
        max_rounds=3,
        max_tokens=1024,
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
        evidence_map: Dict = None,
    ) -> ExpertResult:
        """执行引擎专家分析"""
        user_content = self._build_shared_context(
            fen=fen,
            tag_summary=tag_summary,
            primary_tension=primary_tension,
            phase_info=phase_info,
            question=question,
            move=move,
            evidence_map=evidence_map,
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
