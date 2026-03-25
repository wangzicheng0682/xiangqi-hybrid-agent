"""
战略专家 - 专注于全局战略和相位判断

像教练一样把控方向。
"""

from typing import Dict, List, Callable, Optional
from core.llm.experts.base_expert import (
    BaseExpert, ExpertConfig, ExpertResult,
    should_use_multi_agent,
)
from core.llm.thinking_templates import PhaseInfo


SYSTEM_PROMPT_STRATEGY = """# 你是谁

你是象棋战略教练，专注于全局战略和相位判断。
看到一个局面，你脑子里第一个问题永远是"双方整体态势如何？谁有优势？战略方向是什么？"，而不是"这里有什么具体战术"。

你享受把控棋局发展方向的过程——识别失衡点、预测战略转换。
这种对全局的把握是你分析的核心。

---

# 你怎么思考

**起点**：先定相位（开局/中局/残局），再判断整体态势。
用"我初步判断..."开头写出你的战略评估。

**评估维度**：
- 出子效率：双方大子出动情况
- 空间控制：中路/边路控制权
- 子力平衡：子力对比和子力活跃度
- 战略主动：谁在进攻，谁在防守

**深入**：如果发现战略失衡，必须分析**双方计划**：

战略分析的真正价值不在于描述"谁有优势"，而在于追问：
"优势方如何兑现？劣势方如何挣扎？"

**双方计划分析**（必须完成）：
1. 优势方的最佳推进路线是什么？（调用 `compare_moves` 对比候选）
2. 劣势方有哪些反击手段？（调用 `analyze_position_strategy` 获取建议）
3. 局面转换的关键点是什么？（什么情况下优劣势会逆转）

**输出要求**（必须包含）：
【双方计划】
- 优势方计划：如何扩大优势（具体路线）
- 劣势方挣扎：有哪些反击/简化手段
- 关键转折点：什么信号意味着局势可能逆转

**边界**：不确定就说不知道，不要猜测。

---

# 你不能做什么

以下内容只能来自工具返回，绝对不能凭感觉填写：
- 任何具体棋子的坐标或位置
- 任何引擎评估数值

---

# 你的输出格式

请完成分析后，给出：
【战略评估】一句话描述整体战略态势
【双方计划】优势方计划 + 劣势方挣扎 + 关键转折点（必须填写）
【详细分析】你的战略分析过程（200-500字）
【战略建议】给优势方和劣势方各一个建议
【结论可信度】高/中/低
"""


# 战略专家的工具子集
STRATEGY_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "analyze_position_strategy",
            "description": "局面战略分析。【什么时候用】需要宏观把握局势、判断当前阶段、制定战略计划。",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "compare_moves",
            "description": "对比多步棋的优劣。【什么时候用】用户问'选哪步更好'、分析候选走法。",
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
    {
        "type": "function",
        "function": {
            "name": "get_piece_attacks",
            "description": "获取指定棋子的攻击范围。【什么时候用】分析棋子活动性、理解战略意图。",
            "parameters": {
                "type": "object",
                "properties": {
                    "piece": {"type": "string", "description": "棋子标识"}
                },
                "required": ["piece"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_piece_relations",
            "description": "综合查询棋子关系。【什么时候用】理解棋子之间的战略联系。",
            "parameters": {
                "type": "object",
                "properties": {
                    "piece": {"type": "string", "description": "棋子标识"}
                },
                "required": ["piece"]
            }
        }
    },
]


class StrategyExpert(BaseExpert):
    """战略专家"""

    CONFIG = ExpertConfig(
        name="strategy",
        display_name="战略专家",
        role="专注于全局战略和相位判断",
        system_prompt=SYSTEM_PROMPT_STRATEGY,
        tools=STRATEGY_TOOLS,
        tool_names=[
            "analyze_position_strategy", "compare_moves",
            "get_piece_attacks", "get_piece_relations",
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
        move: str = None,
        on_thinking: Callable[[str, str], None] = None,
    ) -> ExpertResult:
        """执行战略专家分析"""
        user_content = self._build_shared_context(
            fen=fen,
            tag_summary=tag_summary,
            primary_tension=primary_tension,
            phase_info=phase_info,
            question=question,
            move=move,
        )

        return self._call_expert(
            system_prompt=self.CONFIG.system_prompt,
            user_content=user_content,
            config=self.CONFIG,
            fen=fen,
            on_thinking=on_thinking,
        )
