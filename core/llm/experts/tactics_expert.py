"""
战术专家 - 专注于子力关系和战术细节

像裁判一样审视每一步棋。
"""

from typing import Dict, List, Callable, Optional
from core.llm.experts.base_expert import (
    BaseExpert, ExpertConfig, ExpertResult,
    should_use_multi_agent,
)
from core.llm.thinking_templates import PhaseInfo


SYSTEM_PROMPT_TACTICS = """# 你是谁

你是象棋战术裁判，专注于子力关系和战术细节。
看到一个局面，你脑子里第一个问题永远是"这里有什么战术机会？捉子、牵制、将军？"，
而不是"这个局面整体怎么样"。

你享受发现战术组合的过程——闪击、抽将、牵制、串打。
这种对战术精确性的追求是你分析的核心。

---

# 你怎么思考

**起点**：先找战术机会——谁在攻击谁？有没有捉子？有没有将军？
用"我初步判断..."开头写出你的战术假设。

**验证**：调用工具验证你的假设。
- 工具结果支持假设 → 说清楚为什么支持
- 工具结果推翻假设 → 明确说"我之前判断错了"

**深入**：如果发现战术机会，追问：
- 这个战术是真实的还是虚招？
- 对方有什么应着？
- 如果是真的，最佳应对是什么？

**边界**：不确定就说不知道，不要猜测。

---

# 你不能做什么

以下内容只能来自工具返回，绝对不能凭感觉填写：
- 任何具体棋子的坐标或位置
- 任何棋子是否有保护（必须调用工具验证）
- 任何走法的具体效果

**关于"保护"关系的硬规则**：
- 如果你提到"保护"，必须调用 get_piece_defenders 或 get_piece_relations 验证
- 炮架 不等于 保护（炮架是被吃的对象）

---

# 你的输出格式

请完成分析后，给出：
【战术发现】一句话描述最重要的战术发现
【详细分析】你的战术分析过程（200-500字）
【结论可信度】高/中/低（基于你有多少工具验证）
"""


# 战术专家的工具子集
TACTICS_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_piece_attacks",
            "description": "获取指定棋子的攻击范围。【什么时候用】分析'这步棋威胁了什么'、评估棋子活动性。",
            "parameters": {
                "type": "object",
                "properties": {
                    "piece": {"type": "string", "description": "棋子标识，如'红车'、'黑马'、'(5,8)'等"}
                },
                "required": ["piece"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_piece_defenders",
            "description": "查询谁在保护某个棋子。【什么时候用】判断棋子是否安全、分析'能不能吃这个子'。",
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
            "name": "get_threats_to_piece",
            "description": "查询谁在威胁某个棋子。【什么时候用】分析棋子是否危险、判断是否需要防守。",
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
            "description": "综合查询某棋子的攻击、防守、威胁信息（一站式）。【推荐优先使用】",
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
            "name": "analyze_move",
            "description": "深度分析某步棋的效果和质量。【什么时候用】用户问'这步棋怎么样'、评估走法质量。",
            "parameters": {
                "type": "object",
                "properties": {
                    "move": {"type": "string", "description": "UCI格式走法，如h2e2"}
                },
                "required": ["move"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_forcing_sequence",
            "description": "分析走法后的强制序列（将军、捉子等）。【什么时候用】分析连续将军、验证战术组合。",
            "parameters": {
                "type": "object",
                "properties": {
                    "move": {"type": "string", "description": "UCI格式走法"},
                    "depth": {"type": "integer", "description": "分析深度，默认3", "default": 3}
                },
                "required": ["move"]
            }
        }
    },
]


class TacticsExpert(BaseExpert):
    """战术专家"""

    CONFIG = ExpertConfig(
        name="tactics",
        display_name="战术专家",
        role="专注于子力关系和战术细节",
        system_prompt=SYSTEM_PROMPT_TACTICS,
        tools=TACTICS_TOOLS,
        tool_names=[
            "get_piece_attacks", "get_piece_defenders",
            "get_threats_to_piece", "get_piece_relations",
            "analyze_move", "get_forcing_sequence",
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
        """执行战术专家分析"""
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
