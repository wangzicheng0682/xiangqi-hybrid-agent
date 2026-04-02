"""
象棋教练Agent - 基于Function Calling的智能分析

让LLM真正参与决策，像教练一样分析棋局。

核心设计:
1. System Prompt = 教练技能手册
2. Tools Schema = 10个专业工具
3. Agent Loop = 多轮自主调用
4. 阶段感知思维链 = 开局/中局/残局不同框架

文档依据: docs/reference/thinking_framework.md
"""

import os
import json
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

from core.llm.agent_tools import AgentTools, ToolResult
from core.llm.thinking_templates import (
    PhaseDetector,
    OpeningAnalyzer,
    get_phase_aware_prompt,
    PhaseInfo,
    GamePhase,
)
from core.llm.opening_knowledge import (
    OPENING_PRINCIPLES,
    OPENING_SYSTEMS,
    OPENING_PATTERNS,
    detect_opening_pattern,
    get_opening_advice,
)
from core.llm.fewshot_examples import (
    get_fewshot_prompt,
    get_examples_by_phase,
)
from core.llm.analysis_recorder import AnalysisRecorder
from core.llm.reliable_client import ReliableLLMClient
from core.rules.tension_detector import (
    TensionDetector,
    Tension,
    TensionPriority,
    detect_tensions,
    get_primary_tension,
)


@dataclass
class CoachConfig:
    api_key: str = ""
    base_url: str = "https://open.bigmodel.cn/api/paas/v4/"
    model: str = "glm-5"
    max_rounds: int = 3
    max_tools_per_round: int = 3


# ═══════════════════════════════════════════════════════════════════════════════
# 旧版 SYSTEM_PROMPT（备份）- 2026-03-17 "改革开放"前版本
# ═══════════════════════════════════════════════════════════════════════════════
# 包含强制格式要求：<张力扫描>、<主要矛盾>、<验证计划>等XML标签
# 问题：过度约束，违反推理模型最佳实践
# 如需回滚，取消下方注释并删除新版 SYSTEM_PROMPT
# ═══════════════════════════════════════════════════════════════════════════════
#
# SYSTEM_PROMPT_OLD = """你是象棋教练AI...（旧版内容已省略，完整版见git历史）"""
#

# ═══════════════════════════════════════════════════════════════════════════════
# 新版 SYSTEM_PROMPT - 2026-03-17 "改革开放"版本
# ═══════════════════════════════════════════════════════════════════════════════
# 设计原则：
# 1. 移除强制格式要求（XML标签、固定步骤）
# 2. 保留核心棋理约束（不编造、要具体）
# 3. 给模型自由探索空间
# 参考：OpenAI o系列、Claude Extended Thinking 最佳实践
# ═══════════════════════════════════════════════════════════════════════════════
# 三层分离Prompt框架 (Plan #001)
#
# Layer 1: 角色内核 - 最少改动，定调整体气质
# Layer 2: 认知偏好 - 主要迭代区，调思考风格
# Layer 3: 事实契约 - 最硬约束，几乎不动
# ═══════════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """
# 你是谁

你是一位象棋教练，思维方式接近特级大师：
看到一个局面，你脑子里第一个问题永远是"这里最有意思的张力是什么"，
而不是"我该分析哪些方面"。

你享受发现棋局里的矛盾——子力优势和攻势速度的赛跑、
沉睡的强子、引擎分数和直觉感受的落差。
这种好奇心驱动你的整个分析过程。

---

# 你怎么思考（认知偏好）

**起点**：每次分析从一个你自己的假设开始，用"我初步判断..."开头写出来。
不需要面面俱到，找到你觉得最关键的那一个张力就够了。

**探索**：带着这个假设去调工具验证。
工具结果支持假设——说清楚为什么支持。
工具结果推翻假设——明确说"我之前判断错了"，然后修正。
这个过程要让用户看见，不要藏起来。

**边界**：如果你不确定某件事，说"这需要进一步分析才能确认"，
然后说你会用什么工具去查，或者直接说这超出当前分析范围。
好教练知道自己知道什么。

---

# 对手处境（必须分析）

分析完你的假设后，你**必须**从对手视角审视局面。

特级大师和普通棋手的区别就在这里：普通棋手只看"我看到了什么机会"，
特级大师会追问"如果我走这步，对手能怎么办？每条路结果如何？"

**必问问题**：
1. 对手现在有几种主要应着？（调用 `engine_alternatives` 获取候选）
2. 如果我走这步，对手最佳应着是什么？（调用 `analyze_move` 验证后果）
3. 有没有强制序列？（调用 `get_forcing_sequence` 检查将军/捉子）
4. 对手所有应着是否都通向更差局面？（这步棋的真正价值——锁死选项）

**输出格式**：
在分析中明确写出：
【对手处境】
- 对手可选：A、B、C三种应对（列出工具返回的候选）
- A后果：...（基于工具结果）
- B后果：...（基于工具结果）
- C后果：...（基于工具结果）
- 战术结论：这步棋锁死了对手的XX选项 / 对手有XX化解方式

**禁止**：
- 不能跳过这个分析步骤
- 不能只说"对手可能应对"而不分析后果
- 必须调用工具验证，不能凭感觉猜测

---

# 你不能做什么（事实契约）

以下内容只能来自 Evidence Map 或工具返回，绝对不能凭感觉填写：
- 任何具体棋子的坐标或位置
- 任何走法的具体效果
- 任何引擎评估数值

**关于具体走法的硬规则**：
如果你要分析、比较、模拟某一步具体走法，优先先调用 `get_move_candidates` 获取合法候选，
再把返回的 `candidate_id` 传给 `analyze_move`、`compare_moves`、`get_forcing_sequence` 或 `simulate_move`。

**禁止**：
- 不要自由编造 UCI 走法再直接分析
- 不要在没有候选依据时声称某步棋合法

**关于"保护"关系的硬规则**：
如果你在分析中提到"保护"这个词，必须满足以下条件之一：
1. 调用 `get_piece_defenders` 工具并得到 `defender_count > 0` 的结果
2. 或者调用 `get_piece_relations` 工具并看到 `defended_by` 非空

**禁止**：
- 绝对不能在没有调用工具验证的情况下说"XX保护了YY"
- 绝对不能把"炮架"说成"保护"
- 绝对不能说"有炮架"等同于"有保护"

**"炮架"和"保护"的根本区别**：
- 炮架（cannon platform）是炮攻击的目标，炮需要隔一个棋子打另一个棋子，炮架是被吃的对象，不是保护
- 保护（defense/guarding）是己方棋子保护另一个己方棋子，如果敌方吃被保护的子，我方可以吃回

如果你不确定某个棋子是否被保护，**必须调用工具验证**，不能说"看起来有保护"或"应该是保护的"。

如果这些信息在 Evidence Map 和工具结果里都没有，你不知道，就说不知道。
"""


# 结构化自省Prompt（用于最终检查）
SELF_REFLECTION_PROMPT = """
在生成最终讲解前，请完成以下自省检查：

1. **一致性检查**：
   - 工具返回的结果是否互相支持？
   - 有没有发现矛盾的地方？

2. **盲点检查**：
   - 将帅安全是否已检查？
   - 主要矛盾是否得到了验证？
   - 是否有重要棋子未分析？

3. **充分性判断**：
   - 分析是否完整回答了用户的问题？
   - 是否需要追加工具调用？

如果发现任何问题，请在最终输出中说明。
"""


TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "get_move_candidates",
            "description": """获取当前局面的合法候选走法列表，并返回稳定的 candidate_id。

【什么时候用】
- 你要分析具体走法之前
- 你要比较多个候选时
- 你不确定走法是否合法时

【高优先级规则】
先拿候选，再把 candidate_id 传给 analyze_move / compare_moves / get_forcing_sequence / simulate_move。""",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "返回候选数，默认12",
                        "default": 12
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
            "description": """获取指定棋子的攻击范围和攻击目标。

【什么时候用】
- 分析"这步棋威胁了什么"时
- 解释"为什么要走这步"时
- 用户问"这个棋子有什么用"时
- 需要评估棋子活动性和威胁时

【不什么时候用】
- 只需要知道棋子位置时（直接看局面事实）
- 需要完整关系网络时（用get_piece_relations更高效）""",
            "parameters": {
                "type": "object",
                "properties": {
                    "piece": {
                        "type": "string",
                        "description": "棋子标识，如'红车'、'黑马'、'(5,8)'等"
                    }
                },
                "required": ["piece"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_piece_defenders",
            "description": """查询谁在保护某个棋子（是否有根）。

【什么时候用】
- 判断棋子是否安全时
- 分析"能不能吃这个子"时
- 看到子无根标签后深入分析时

【不什么时候用】
- 需要完整关系时（用get_piece_relations）""",
            "parameters": {
                "type": "object",
                "properties": {
                    "piece": {
                        "type": "string",
                        "description": "棋子标识，如'红车'、'黑马'、'(5,8)'等"
                    }
                },
                "required": ["piece"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_threats_to_piece",
            "description": """查询谁在威胁某个棋子。

【什么时候用】
- 分析棋子是否危险时
- 看到威胁标签后深入分析时
- 判断是否需要防守时

【不什么时候用】
- 需要完整关系时（用get_piece_relations）""",
            "parameters": {
                "type": "object",
                "properties": {
                    "piece": {
                        "type": "string",
                        "description": "棋子标识，如'红车'、'黑马'、'(5,8)'等"
                    }
                },
                "required": ["piece"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_piece_relations",
            "description": """综合查询某棋子的攻击、防守、威胁信息（一站式）。

【什么时候用 - 推荐优先使用】
- 需要了解棋子完整状态时
- 看到战术标签（如子无根、捉子）后深入分析时
- 分析复杂战术关系时

【优势】
一次调用获取所有关系，比分别调用3个工具更高效。

【示例用法】
- 看到is_attack_unprotected标签 → 用此工具查具体攻击关系
- 看到is_pinned标签 → 用此工具查牵制细节""",
            "parameters": {
                "type": "object",
                "properties": {
                    "piece": {
                        "type": "string",
                        "description": "棋子标识，如'红车'、'黑马'、'(5,8)'等"
                    }
                },
                "required": ["piece"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_move",
            "description": """深度分析某步棋的效果和质量。

【什么时候用】
- 用户问"这步棋怎么样"时
- 需要评估走法质量时
- 需要解释某步棋的意图时

【不什么时候用】
- 只需要知道是否合法时（直接看局面事实）
- 需要引擎评估时（用engine_deep_analysis）""",
            "parameters": {
                "type": "object",
                "properties": {
                    "candidate_id": {
                        "type": "string",
                        "description": "候选走法ID，如'cand_1'，优先使用"
                    },
                    "move": {
                        "type": "string",
                        "description": "UCI格式走法，如'h2e2'；仅兼容旧接口时使用"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "compare_moves",
            "description": """对比多步棋的优劣。

【什么时候用】
- 用户问"选哪步更好"时
- 需要解释为什么推荐A而不是B时
- 分析候选走法时

【典型场景】
对比引擎推荐的多个走法，找出最佳选择。""",
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
                        "description": "UCI格式走法列表，如['h2e2', 'h2h6']；仅兼容旧接口时使用"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_forcing_sequence",
            "description": """分析走法后的强制序列（将军、捉子等）。

【什么时候用】
- 分析是否有连续将军时
- 分析强制应着时
- 验证战术组合是否成立时

【注意】
主要用于分析将军序列和强制走法。""",
            "parameters": {
                "type": "object",
                "properties": {
                    "candidate_id": {
                        "type": "string",
                        "description": "候选走法ID，如'cand_1'，优先使用"
                    },
                    "move": {
                        "type": "string",
                        "description": "UCI格式走法；仅兼容旧接口时使用"
                    },
                    "depth": {
                        "type": "integer",
                        "description": "分析深度，默认3",
                        "default": 3
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "engine_deep_analysis",
            "description": """引擎深度分析，获取专业评估和最佳走法。

【什么时候用】
- 需要权威的局势评估时
- 用户问"该怎么走"时
- 分析关键局面时

【返回内容】
- 局面评估（分数和人类可读形式）
- 引擎推荐的最佳走法
- 主要变化线

【注意】
这是最权威的分析，但耗时较长。""",
            "parameters": {
                "type": "object",
                "properties": {
                    "depth": {
                        "type": "integer",
                        "description": "分析深度，默认20",
                        "default": 20
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "engine_alternatives",
            "description": """获取引擎的多个候选走法对比。

【什么时候用】
- 用户问"还有什么选择"时
- 需要解释为什么推荐某步时
- 分析候选走法优劣时

【典型场景】
"引擎推荐车八平六，但还有其他选择吗？"
用此工具获取top3候选并对比。""",
            "parameters": {
                "type": "object",
                "properties": {
                    "top_n": {
                        "type": "integer",
                        "description": "返回候选数，默认3",
                        "default": 3
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_position_strategy",
            "description": """局面战略分析，获取阶段、主动权、关键特征。

【什么时候用】
- 用户问"当前局面如何"时
- 需要宏观把握局势时
- 开局/中局/残局判断时

【返回内容】
- 当前阶段（开局/中局/残局）
- 主动权归属
- 关键战术特征
- 建议的战略计划

【推荐】
分析整体局面时优先使用此工具。""",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class AgentResponse:
    content: str
    tool_calls: List[ToolCall] = field(default_factory=list)
    finish_reason: str = "stop"


class XiangqiCoachAgent:
    """象棋教练Agent - 基于Function Calling"""

    PIECE_NAMES = {
        'K': '红帅', 'k': '黑将',
        'A': '红仕', 'a': '黑士',
        'B': '红相', 'b': '黑象',
        'N': '红马', 'n': '黑马',
        'R': '红车', 'r': '黑车',
        'C': '红炮', 'c': '黑炮',
        'P': '红兵', 'p': '黑卒',
    }

    def __init__(self, config: CoachConfig = None, enable_recording: bool = True):
        self.config = config or CoachConfig()
        self.api_key = self.config.api_key or os.getenv("ALIYUN_API_KEY")
        self.base_url = self.config.base_url
        self.model = self.config.model
        self.tools = AgentTools()
        self.enable_recording = enable_recording
        self.recorder = AnalysisRecorder() if enable_recording else None
        self._current_request_id = None
        self.llm_client = ReliableLLMClient(
            api_key=self.api_key,
            base_url=self.base_url,
            model=self.model,
            timeout=120,
            max_retries=2,
        )

        self._tool_functions = {
            "get_move_candidates": self.tools.get_move_candidates,
            "get_piece_attacks": self.tools.get_piece_attacks,
            "get_piece_defenders": self.tools.get_piece_defenders,
            "get_threats_to_piece": self.tools.get_threats_to_piece,
            "get_piece_relations": self.tools.get_piece_relations,
            "analyze_move": self.tools.analyze_move,
            "compare_moves": self.tools.compare_moves,
            "get_forcing_sequence": self.tools.get_forcing_sequence,
            "engine_deep_analysis": self.tools.engine_deep_analysis,
            "engine_alternatives": self.tools.engine_alternatives,
            "analyze_position_strategy": self.tools.analyze_position_strategy,
        }

    def _generate_board_layout(self, fen: str) -> str:
        """
        生成棋盘布局的可读格式，防止LLM编造棋子位置

        Args:
            fen: 局面FEN

        Returns:
            棋盘布局的可读文本
        """
        try:
            # 解析FEN
            board_part = fen.split()[0]
            rows = board_part.split('/')

            red_pieces = []
            black_pieces = []

            for row_idx, row in enumerate(rows):
                col_idx = 0
                for char in row:
                    if char.isdigit():
                        col_idx += int(char)
                    else:
                        # 计算坐标（1-based，符合象棋习惯）
                        x = col_idx + 1  # 列 1-9
                        y = 10 - row_idx  # 行 1-10（红方底部为1）

                        piece_name = self.PIECE_NAMES.get(char, char)

                        if char.isupper():
                            red_pieces.append(f"{piece_name}-({x},{y})")
                        else:
                            black_pieces.append(f"{piece_name}-({x},{y})")

                        col_idx += 1

            # 格式化输出
            layout = "【红方棋子】\n"
            layout += "、".join(red_pieces) if red_pieces else "无"
            layout += "\n\n【黑方棋子】\n"
            layout += "、".join(black_pieces) if black_pieces else "无"

            return layout

        except Exception as e:
            return f"解析棋盘失败: {str(e)}"

    def _build_opening_prompt(self, fen: str, move_count: int, phase_info: PhaseInfo, moves: List[str] = None) -> str:
        """
        构建开局阶段的增强Prompt

        Args:
            fen: 局面FEN
            move_count: 回合数
            phase_info: 阶段信息
            moves: 已走的棋步列表（可选）

        Returns:
            开局思维链Prompt
        """
        # 执行开局分析
        analysis = OpeningAnalyzer.analyze(fen, move_count)
        summary = OpeningAnalyzer.generate_summary(analysis)

        # 检测开局定式
        pattern_info = None
        if moves:
            pattern_info = detect_opening_pattern(moves)

        # 构建原则文本
        principles_text = "\n".join([
            f"{i+1}. {p['name']}：{p['description']}"
            for i, p in enumerate(OPENING_PRINCIPLES[:5])
        ])

        # 构建定式信息
        pattern_text = ""
        if pattern_info and pattern_info['pattern'] in OPENING_SYSTEMS:
            system = OPENING_SYSTEMS[pattern_info['pattern']]
            pattern_text = f"""
【开局定式识别】
当前局面符合「{system.name}」定式（置信度{pattern_info['confidence']*100:.0f}%）
特点：{'、'.join(system.characteristics)}
适合：{system.suitable_for}
"""

        # 获取Few-shot示例（精简版，只取1个）
        fewshot_text = get_fewshot_prompt("opening", count=1)

        return f"""
【当前阶段：开局】（回合 {move_count}，棋子 {phase_info.total_pieces} 枚）

开局是棋局的根基，你的分析应围绕以下十大原则展开：

{principles_text}

【开局分析数据】（基于规则检测，100%准确）
{summary}
{pattern_text}
【分析问题清单】
- 双方各出动了几枚大子？
- 谁控制中路（5线）？
- 马是否有根？炮是否有架？
- 有没有重复走同一子？
- 当前谁握有先手？

【输出格式】
【出子效率】描述双方出子情况
【中心控制】描述中路控制情况
【子力活跃】描述马炮车的活跃度
【先手判断】谁握有先手，为什么
【教练建议】给玩家的具体建议

{fewshot_text}
"""
    
    def _call_api(self, messages: List[Dict], tools = None) -> AgentResponse:
        """调用LLM API"""
        response = self.llm_client.complete(
            messages=messages,
            tools=tools,
            temperature=0.7,
            max_tokens=1024,
            thinking_enabled=False,
        )
        if not response.success:
            return AgentResponse(content=response.error_message, finish_reason="error")

        tool_calls = []
        for tc in response.tool_calls:
            try:
                arguments = tc.get("function", {}).get("arguments", {})
                if isinstance(arguments, str):
                    arguments = json.loads(arguments) if arguments else {}
                tool_calls.append(ToolCall(
                    id=tc["id"],
                    name=tc["function"]["name"],
                    arguments=arguments,
                ))
            except Exception:
                continue

        return AgentResponse(
            content=response.content,
            tool_calls=tool_calls,
            finish_reason=response.finish_reason,
        )

    def _call_api_stream(
        self,
        messages: List[Dict],
        tools = None,
        on_chunk: Callable[[str], None] = None
    ) -> AgentResponse:
        """
        流式调用LLM API，实时推送内容

        Args:
            messages: 对话消息列表
            tools: 工具定义
            on_chunk: 内容片段回调函数

        Returns:
            完整的AgentResponse
        """
        response = self.llm_client.stream_complete(
            messages=messages,
            tools=tools,
            temperature=0.7,
            max_tokens=1024,
            thinking_enabled=False,
            on_chunk=on_chunk,
        )
        if not response.success:
            return AgentResponse(content=response.error_message, finish_reason="error")

        tool_calls = []
        for tc in response.tool_calls:
            try:
                arguments = tc.get("function", {}).get("arguments", {})
                if isinstance(arguments, str):
                    arguments = json.loads(arguments) if arguments else {}
                tool_calls.append(ToolCall(
                    id=tc["id"],
                    name=tc["function"]["name"],
                    arguments=arguments,
                ))
            except Exception:
                continue

        return AgentResponse(
            content=response.content,
            tool_calls=tool_calls,
            finish_reason=response.finish_reason or "stop",
        )

    def _execute_tool(self, tool_call: ToolCall, fen: str) -> Dict[str, Any]:
        """执行工具调用"""
        func = self._tool_functions.get(tool_call.name)
        if not func:
            return {"error": f"未知工具: {tool_call.name}"}
        
        try:
            args = tool_call.arguments
            args["fen"] = fen
            
            result = func(**args)
            
            if isinstance(result, ToolResult):
                return {
                    "success": result.success,
                    "data": result.data,
                    "message": result.message
                }
            return result
            
        except Exception as e:
            return {"error": str(e)}
    
    def analyze(
        self,
        fen: str,
        question: str,
        move: str = None,
        evidence_map: Dict = None,
        tag_summary: str = None,
        move_count: int = 0,
        engine_eval: Dict = None,
        on_thinking: Callable[[str, str], None] = None
    ) -> str:
        """
        深度分析局面

        Args:
            fen: 局面FEN
            question: 用户问题
            move: 可选的走法（UCI格式）
            evidence_map: Evidence Map（标签检测结果）
            tag_summary: 标签摘要（人类可读的标签列表）
            move_count: 当前回合数（用于阶段检测）
            engine_eval: 引擎评估结果（包含cp、best等）
            on_thinking: 思考过程回调函数，参数为(stage, message)

        Returns:
            分析结果文本
        """
        # ===== 启动记录器 =====
        if self.recorder:
            self._current_request_id = self.recorder.start_record()

        try:
            # ===== 阶段感知思维链 =====
            phase_info = PhaseDetector.detect(fen, move_count)

            # ===== 张力检测 =====
            tensions = []
            primary_tension = None

            if evidence_map:
                tensions = detect_tensions(
                    evidence_map,
                    engine_eval or {},
                    phase_info.phase_name
                )
                if tensions:
                    primary_tension = tensions[0]

            # ===== 记录输入（在tensions检测之后）=====
            if self.recorder:
                tag_summary_list = tag_summary if isinstance(tag_summary, list) else []
                self.recorder.record_input(
                    fen=fen,
                    question=question,
                    move=move,
                    tag_summary=tag_summary_list,
                    engine_eval=engine_eval or {},
                    tensions=tensions
                )

            # 构建阶段感知的System Prompt
            if phase_info.is_opening():
                phase_prompt = self._build_opening_prompt(fen, move_count, phase_info)
                system_prompt = SYSTEM_PROMPT + "\n\n" + phase_prompt
            else:
                system_prompt = SYSTEM_PROMPT

            if self.recorder:
                self.recorder.record_system_prompt(system_prompt)

            messages = [
                {"role": "system", "content": system_prompt}
            ]

            board_layout = self._generate_board_layout(fen)

            user_content = f"【当前局面】FEN: {fen}\n\n"
            user_content += f"【棋盘布局 - 只能使用以下棋子】\n{board_layout}\n\n"

            if tag_summary:
                tag_str = "\n".join(tag_summary) if isinstance(tag_summary, list) else tag_summary
                user_content += f"【局面事实 - 必须基于此分析】\n{tag_str}\n\n"

            if primary_tension:
                user_content += f"""【张力检测 - 已自动识别】
[张力] 主要张力：{primary_tension['tension_type']}（优先级：{primary_tension['priority']}）
[问题] 核心问题：{primary_tension['question']}
[假设] 初始假设：{primary_tension['hypothesis']}
📋 支持证据：{', '.join(primary_tension['evidence'])}
🔧 建议工具：{', '.join(primary_tension['suggested_tools']) if primary_tension['suggested_tools'] else '根据情况选择'}

"""

            if move:
                user_content += f"【刚走的棋】{move}\n\n"
            user_content += f"【问题】{question}"

            if self.recorder:
                self.recorder.record_user_message(user_content)

            messages.append({"role": "user", "content": user_content})

            for round_num in range(self.config.max_rounds):
                if self.recorder:
                    self.recorder.start_llm_round(round_num)
                    self.recorder.record_llm_request(messages.copy())

                external_callback = on_thinking
                full_response_chunks = []

                def make_chunk_handler(external_cb):
                    def handle_chunk(chunk: str):
                        full_response_chunks.append(chunk)
                        if self.recorder:
                            self.recorder.record_llm_chunk(chunk)
                        if external_cb:
                            external_cb("thinking_chunk", chunk)
                    return handle_chunk

                response = self._call_api_stream(
                    messages,
                    tools=TOOLS_SCHEMA,
                    on_chunk=make_chunk_handler(external_callback)
                )

                if response.finish_reason == "error":
                    if self.recorder:
                        self.recorder.record_error(f"API error: {response.content}")
                    return response.content

                if self.recorder:
                    tool_calls_data = []
                    if response.tool_calls:
                        for tc in response.tool_calls:
                            tool_calls_data.append({
                                "name": tc.name,
                                "arguments": json.dumps(tc.arguments)
                            })
                    self.recorder.record_llm_response(
                        content=response.content or "",
                        tool_calls=tool_calls_data,
                        finish_reason=response.finish_reason
                    )

                if response.tool_calls:
                    if on_thinking:
                        tool_names = [tc.name for tc in response.tool_calls]
                        on_thinking("tool_call", ", ".join(tool_names))

                    assistant_message = {"role": "assistant", "content": response.content or ""}
                    if response.tool_calls:
                        assistant_message["tool_calls"] = [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.name,
                                    "arguments": json.dumps(tc.arguments)
                                }
                            }
                            for tc in response.tool_calls
                        ]
                    messages.append(assistant_message)

                    for tool_call in response.tool_calls:
                        if self.recorder:
                            self.recorder.start_tool_call(tool_call.name)
                            self.recorder.record_tool_args(tool_call.arguments)

                        result = self._execute_tool(tool_call, fen)

                        if self.recorder:
                            self.recorder.record_tool_result(result)

                        if on_thinking:
                            msg = result.get("message", str(result)[:100])
                            on_thinking("tool_result", f"{tool_call.name}: {msg}")

                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(result, ensure_ascii=False)
                        })
                else:
                    if on_thinking:
                        on_thinking("result", "分析完成")
                    if self.recorder:
                        self.recorder.record_final_output(response.content or "")
                    return response.content

            if on_thinking:
                on_thinking("result", "达到最大轮数限制")

            final_response = self._call_api(messages)
            
            if self.recorder:
                self.recorder.record_final_output(final_response.content)
            
            return final_response.content

        finally:
            if self.recorder:
                saved_path = self.recorder.finish_record()
                print(f"[Recorder] 分析记录已保存: {saved_path}")


def create_coach_agent() -> XiangqiCoachAgent:
    """创建象棋教练Agent实例"""
    return XiangqiCoachAgent()
