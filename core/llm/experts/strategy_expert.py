"""
战略专家 - 专注于全局战略和相位判断

像教练一样把控方向。
"""

import os
from typing import Dict, List, Callable, Optional
from core.llm.experts.base_expert import (
    BaseExpert, ExpertConfig, ExpertResult, CHESS_RULES_BLOCK,
)
from core.llm.thinking_templates import PhaseInfo


SYSTEM_PROMPT_STRATEGY = CHESS_RULES_BLOCK + """

---

# 你是谁

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
- 棋理参考：调用 `query_chess_principles` 获取当前局面适用的棋理原则

**深入**：如果发现战略失衡，必须分析**双方计划**：

战略分析的真正价值不在于描述"谁有优势"，而在于追问：
"优势方如何兑现？劣势方如何挣扎？"

**双方计划分析**（必须完成）：
1. 优势方的最佳推进路线是什么？（调用 `compare_moves` 对比候选）
2. 劣势方有哪些反击手段？（调用 `analyze_position_strategy` 获取建议）
3. 局面转换的关键点是什么？（什么情况下优劣势会逆转）
4. 如需验证某步棋对局面战略格局的影响，使用 `simulate_move` 对比变化

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

【输出格式要求】
在开始深入分析之前，先输出一行阶段标题，格式为：
## [N] [简短描述]

例如：
## 1 判断相位与整体态势
## 2 识别战略失衡点
## 3 推演双方计划

阶段标题输出后，再开始该阶段的详细分析。

在你开始一个新的分析步骤时，必须先单独输出一行：
[STEP: 你正在做什么的一句话]

示例：
[STEP: 判断当前属于开局中局还是残局]
[STEP: 评估双方子力和空间失衡]
[STEP: 推演优势方与劣势方的计划]

请完成分析后，给出：
【战略评估】一句话描述整体战略态势
【双方计划】优势方计划 + 劣势方挣扎 + 关键转折点（必须填写）
【详细分析】你的战略分析过程（200-500字）
【战略建议】给优势方和劣势方各一个建议
【结论可信度】高/中/低

---

# 结构化断言（必须）

分析结束时，用以下格式列出你的核心断言（1-3条）：

[CLAIM] 你的一条核心结论
[EVIDENCE] 支撑该结论的证据来源（哪个工具验证的，或纯推理）
[CONFIDENCE] 高/中/低

示例：
[CLAIM] 当前局面红方子力优势，进入有利残局
[EVIDENCE] analyze_position_strategy 显示红方多一车
[CONFIDENCE] 高
"""


# 战略专家的工具子集
STRATEGY_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_move_candidates",
            "description": "获取当前局面的合法候选走法列表。【高优先级】需要比较具体走法时，先取候选，再传 candidate_id。",
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
            "description": "对比多步棋的优劣。【什么时候用】用户问'选哪步更好'、分析候选走法。优先传 candidate_ids，不要自由编造 moves。",
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
    {
        "type": "function",
        "function": {
            "name": "simulate_move",
            "description": "模拟走一步棋，对比走棋前后局面变化。【什么时候用】验证战略计划的效果。优先传 candidate_id。",
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
            "name": "query_chess_principles",
            "description": "查询适用于当前局面的棋理原则。【什么时候用】需要理论支撑战略判断、参考经典棋理。",
            "parameters": {
                "type": "object",
                "properties": {
                    "tension_type": {"type": "string", "description": "张力类型，如material_vs_initiative, hidden_imbalance, crisis_with_resources, sleeping_piece等"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_chess_knowledge",
            "description": "语义检索象棋知识库（棋理原则+经典棋谱开局）。【什么时候用】需要查找特定战法、杀法、开局变例、棋书引用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "自然语言查询，如'中炮对屏风马'、'马后炮杀法'、'车马冷着配合'"},
                    "top_k": {"type": "integer", "description": "返回数量，默认5"}
                },
                "required": ["query"]
            }
        }
    },
]


class StrategyExpert(BaseExpert):
    """战略专家"""

    DEFAULT_MODEL = os.getenv("STRATEGY_EXPERT_MODEL", os.getenv("EXPERT_LLM_MODEL", "glm-4-flash"))
    DEFAULT_BASE_URL = os.getenv("STRATEGY_EXPERT_BASE_URL", os.getenv("EXPERT_LLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/"))

    CONFIG = ExpertConfig(
        name="strategy",
        display_name="战略专家",
        role="专注于全局战略和相位判断",
        system_prompt=SYSTEM_PROMPT_STRATEGY,
        tools=STRATEGY_TOOLS,
        tool_names=[
            "get_move_candidates",
            "analyze_position_strategy", "compare_moves",
            "get_piece_attacks", "get_piece_relations",
            "simulate_move", "query_chess_principles",
            "search_chess_knowledge",
        ],
        required_sections=["【战略评估】", "【双方计划】", "【详细分析】", "【战略建议】", "【结论可信度】"],
        max_rounds=3,
        max_tokens=1024,
    )

    def __init__(
        self,
        api_key: str = None,
        model: str = None,
        base_url: str = None,
        debug_logger=None,
    ):
        super().__init__(
            api_key=api_key,
            model=model or self.DEFAULT_MODEL,
            base_url=base_url or self.DEFAULT_BASE_URL,
            debug_logger=debug_logger,
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
        evidence_map: Dict = None,
    ) -> ExpertResult:
        """执行战略专家分析"""
        user_content = self._build_shared_context(
            fen=fen,
            tag_summary=tag_summary,
            primary_tension=primary_tension,
            phase_info=phase_info,
            question=question,
            move=move,
            evidence_map=evidence_map,
        )

        return self._call_expert(
            system_prompt=self.CONFIG.system_prompt,
            user_content=user_content,
            config=self.CONFIG,
            fen=fen,
            on_thinking=on_thinking,
        )
