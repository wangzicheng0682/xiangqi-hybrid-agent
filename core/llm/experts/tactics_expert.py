"""
战术专家 - 专注于子力关系和战术细节

像裁判一样审视每一步棋。
"""

from typing import Dict, List, Callable, Optional
from core.llm.experts.base_expert import (
    BaseExpert, ExpertConfig, ExpertResult, CHESS_RULES_BLOCK,
)
from core.llm.thinking_templates import PhaseInfo


SYSTEM_PROMPT_TACTICS = CHESS_RULES_BLOCK + """

---

# 你是谁

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
- 当你想对比"走这步前后局面有什么变化"时，使用 `simulate_move` 工具

**深入**：如果发现战术机会，必须完成**对手处境分析**：

特级大师和普通棋手的区别就在这里：普通棋手只看"我发现了什么战术"，
特级大师会追问"如果我走这步，对手能怎么办？每条路结果如何？"

**对手视角三问**（必须调用工具验证）：
1. 对手有几种应着？调用 `get_forcing_sequence` 或分析后续变化
2. 每种应着的后果？分析对手各选项的走向
3. 对手是否被锁死？所有应着都通向更差局面 = 这步棋的真正价值

**输出要求**（必须包含）：
【对手处境】
- 对手可选：A、B、C（列出主要应着）
- A后果：...（基于分析）
- B后果：...（基于分析）
- 战术结论：对手的XX路被锁死 / 对手可用XX化解

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

【输出格式要求】
在开始深入分析之前，先输出一行阶段标题，格式为：
## [N] [简短描述]

例如：
## 1 扫描战术机会
## 2 验证关键攻防关系
## 3 评估对手应着

阶段标题输出后，再开始该阶段的详细分析。

在你开始一个新的分析步骤时，必须先单独输出一行：
[STEP: 你正在做什么的一句话]

示例：
[STEP: 扫描局面找将军和捉子威胁]
[STEP: 调用工具验证牵制与保护关系]
[STEP: 站在对手视角检查主要应着]

请完成分析后，给出：
【战术发现】一句话描述最重要的战术发现
【对手处境】对手选项分析（必须填写，不能跳过）
【详细分析】你的战术分析过程（200-500字）
【结论可信度】高/中/低（基于你有多少工具验证）

---

# 结构化断言（必须）

分析结束时，用以下格式列出你的核心断言（1-3条）：

[CLAIM] 你的一条核心结论
[EVIDENCE] 支撑该结论的证据来源（哪个工具验证的，或纯推理）
[CONFIDENCE] 高/中/低

示例：
[CLAIM] 红车d8控制将门，黑将无法逃离
[EVIDENCE] get_piece_attacks(红车) 显示攻击范围覆盖黑将所在行
[CONFIDENCE] 高

[CLAIM] 黑马被牵制，无法参与防守
[EVIDENCE] 通过 simulate_move 验证黑马移动后红车直接将军
[CONFIDENCE] 高
"""


# 战术专家的工具子集
TACTICS_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_move_candidates",
            "description": "获取当前局面的合法候选走法列表。【高优先级】当你想分析具体走法时，先拿候选，再用 candidate_id 调其他工具，禁止自由编造走法。",
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
            "description": "深度分析某步棋的效果和质量。【什么时候用】用户问'这步棋怎么样'、评估走法质量。优先传 candidate_id，不要自由编造走法。",
            "parameters": {
                "type": "object",
                "properties": {
                    "candidate_id": {"type": "string", "description": "候选走法ID，如cand_1，优先使用"},
                    "move": {"type": "string", "description": "UCI格式走法，如h2e2；仅兼容旧接口时使用"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_forcing_sequence",
            "description": "分析走法后的强制序列（将军、捉子等）。【什么时候用】分析连续将军、验证战术组合。优先传 candidate_id。",
            "parameters": {
                "type": "object",
                "properties": {
                    "candidate_id": {"type": "string", "description": "候选走法ID，如cand_1，优先使用"},
                    "move": {"type": "string", "description": "UCI格式走法，仅兼容旧接口时使用"},
                    "depth": {"type": "integer", "description": "分析深度，默认3", "default": 3}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "simulate_move",
            "description": "模拟走一步棋，对比走棋前后局面标签变化。【什么时候用】验证'走这步后局面会怎样'、分析走法的实际效果。优先传 candidate_id。",
            "parameters": {
                "type": "object",
                "properties": {
                    "candidate_id": {"type": "string", "description": "候选走法ID，如cand_1，优先使用"},
                    "move": {"type": "string", "description": "UCI格式走法，如h2e2；仅兼容旧接口时使用"}
                },
                "required": []
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
            "get_move_candidates",
            "get_piece_attacks", "get_piece_defenders",
            "get_threats_to_piece", "get_piece_relations",
            "analyze_move", "get_forcing_sequence",
            "simulate_move",
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
        move: str = None,
        on_thinking: Callable[[str, str], None] = None,
        evidence_map: Dict = None,
    ) -> ExpertResult:
        """执行战术专家分析"""
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
