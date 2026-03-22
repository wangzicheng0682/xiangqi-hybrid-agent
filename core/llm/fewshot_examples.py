"""
Few-shot示例库 - Agent调教与演示

包含9个经典示例（开局3个、中局3个、残局3个），
每个示例包含完整的思维链、工具调用、总结输出。

用途：
1. 演示展示 — 现场直接演示
2. Agent调教 — 嵌入System Prompt作Few-shot示例

文档依据: docs/reference/fewshot_examples.md
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class GamePhase(Enum):
    """局面阶段"""
    OPENING = "opening"
    MIDDLEGAME = "middlegame"
    ENDGAME = "endgame"


@dataclass
class ToolCall:
    """工具调用记录"""
    step: int                    # 步骤序号
    tool: str                    # 工具名称
    input_params: Dict[str, Any] # 输入参数
    output: Dict[str, Any]       # 输出结果（简化版）
    reason: str                  # 调用理由


@dataclass
class FewshotExample:
    """Few-shot示例"""
    id: int                          # 示例编号
    name: str                        # 示例名称
    phase: GamePhase                 # 阶段
    fen: str                         # 局面FEN
    move_count: int                  # 回合数
    description: str                 # 局面描述
    features: List[str]              # 局面特点
    thinking: str                    # 思维链
    tool_calls: List[ToolCall]       # 工具调用记录
    summary: str                     # 总结输出


# ============================================================================
# 开局示例（3个）
# ============================================================================

OPENING_EXAMPLES = [
    FewshotExample(
        id=1,
        name="中炮进三兵对屏风马（标准开局）",
        phase=GamePhase.OPENING,
        fen="rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 5",
        move_count=5,
        description="第5回合，双方出子均衡，红方中路有控制",
        features=[
            "开局阶段，32子完整",
            "红方中炮瞄准黑方中卒",
            "黑方双马形成屏风保护",
            "双方出子效率相当"
        ],
        thinking="""【阶段识别】开局（第5回合，32子完整）
【开局定式】可能是中炮进三兵对屏风马的前奏

【开局原则检查】
1. 出子效率：红方已出炮+马，黑方已出双马，双方相当
2. 中路控制：红炮瞄住中卒，黑马保护
3. 马炮活跃：红马正马位置，黑双马屏风
4. 先手判断：红方先手架炮，稍占主动""",
        tool_calls=[
            ToolCall(
                step=1,
                tool="analyze_position_strategy",
                input_params={"fen": "..."},
                output={"阶段": "开局", "主动权": "红方稍先", "关键特征": ["中路对峙", "出子均衡"]},
                reason="先了解整体，再深入细节"
            ),
            ToolCall(
                step=2,
                tool="engine_alternatives",
                input_params={"fen": "...", "top_n": 3},
                output={
                    "候选走法": [
                        {"走法": "兵三进一", "评估": "+0.3", "说明": "挺进三兵，活马控制"},
                        {"走法": "马八进七", "评估": "+0.2", "说明": "跳正马，稳固阵型"},
                        {"走法": "车一平二", "评估": "+0.2", "说明": "出直车，快速投入"}
                    ]
                },
                reason="了解引擎推荐，辅助判断"
            )
        ],
        summary="""【出子效率】红方已出动炮、马共2子；黑方已出动双马共2子，双方出子相当
【中心控制】红炮(5,2)瞄准黑方中卒，黑双马形成屏风保护中路
【子力活跃】红马正马位置可攻可守，黑双马屏风阵型稳固
【先手判断】红方稍先，因为先手架中炮，有中路控制权
【教练建议】红方可选择兵三进一继续挺进，或马八进七稳固阵型，保持先手"""
    ),

    FewshotExample(
        id=2,
        name="顺炮直车对横车（对攻开局）",
        phase=GamePhase.OPENING,
        fen="rn1akabnr/9/1c4c2/p1p1p1p1p/9/9/P1P1P1P1P/1C4C2/9/RN1AKABNR w - - 0 6",
        move_count=6,
        description="第6回合，顺炮局，红直车对黑横车，对攻激烈",
        features=[
            "顺炮定式，双方同架中炮",
            "红方直车已亮出",
            "中路对攻激烈",
            "需要精确计算"
        ],
        thinking="""【阶段识别】开局（第6回合）
【定式识别】顺炮直车对横车

【开局分析】
1. 双方同架中炮，中路对攻
2. 红方直车快速亮出，黑方准备横车
3. 顺炮局变化直接，对攻性强
4. 需要精确计算，避免失误""",
        tool_calls=[
            ToolCall(
                step=1,
                tool="get_piece_attacks",
                input_params={"fen": "...", "piece": "红车"},
                output={"棋子": "红车(2,1)", "攻击": ["黑卒(2,7)", "空位(2,8)"], "攻击数": 2},
                reason="了解红车的控制范围"
            ),
            ToolCall(
                step=2,
                tool="compare_moves",
                input_params={"fen": "...", "moves": ["h2h6", "h2e2"]},
                output={
                    "走法1": {"名称": "车二进六", "评估": "+0.4", "说明": "过河压制"},
                    "走法2": {"名称": "车二平五", "评估": "+0.2", "说明": "占中路"}
                },
                reason="顺炮局需要积极进攻"
            )
        ],
        summary="""【定式识别】顺炮直车对横车，经典对攻开局
【对攻态势】双方中路对攻激烈，红直车已亮出，黑方准备横车
【关键选择】红方可选择车二进六过河压制，积极进攻
【教练建议】顺炮局需要精确，红方应积极进攻但不可冒进"""
    ),

    FewshotExample(
        id=3,
        name="仙人指路对卒底炮（试探开局）",
        phase=GamePhase.OPENING,
        fen="rnbakabnr/9/1c7/p1p1p1p1p/9/9/P1P1P1P1P/9/1C3N3/RNBAKAB1R w - - 0 4",
        move_count=4,
        description="第4回合，红方仙人指路，黑方卒底炮反击",
        features=[
            "仙人指路定式",
            "黑方卒底炮针对性反击",
            "变化灵活",
            "可转多种阵型"
        ],
        thinking="""【阶段识别】开局（第4回合）
【定式识别】仙人指路对卒底炮

【开局分析】
1. 红方第一步挺兵试探
2. 黑方卒底炮反击，针对性很强
3. 红方需要应对黑炮的威胁
4. 变化灵活，可转多种阵型""",
        tool_calls=[
            ToolCall(
                step=1,
                tool="get_threats_to_piece",
                input_params={"fen": "...", "piece": "红兵"},
                output={"威胁者": ["黑炮(3,10)"], "危险等级": "high"},
                reason="了解黑方反击的威胁"
            ),
            ToolCall(
                step=2,
                tool="engine_alternatives",
                input_params={"fen": "...", "top_n": 3},
                output={
                    "候选走法": [
                        {"走法": "相三进五", "评估": "+0.1", "说明": "飞相保护"},
                        {"走法": "马二进三", "评估": "+0.0", "说明": "正常出子"}
                    ]
                },
                reason="了解应对方案"
            )
        ],
        summary="""【定式识别】仙人指路对卒底炮，试探性开局
【关键威胁】黑炮(3,10)威胁红兵，需要应对
【应对选择】红方可飞相保护，或正常出子暂不理会
【教练建议】仙人指路灵活多变，红方应按计划出子，不要被黑方打乱节奏"""
    )
]


# ============================================================================
# 中局示例（3个）
# ============================================================================

MIDDLEGAME_EXAMPLES = [
    FewshotExample(
        id=4,
        name="捉双战术（马踩双）",
        phase=GamePhase.MIDDLEGAME,
        fen="r1bakabnr/9/2n3c2/p1p1p1p1p/9/4N4/P1P1P1P1P/1C3N3/9/R1BAKAB1R w - - 0 12",
        move_count=12,
        description="第12回合，红马位置优越，可同时攻击两个目标",
        features=[
            "中局阶段，子力开始减少",
            "红马位于中心要点",
            "可同时攻击黑车和黑炮",
            "经典捉双战术"
        ],
        thinking="""【阶段识别】中局（第12回合，子力开始减少）
【战术扫描】
1. 红马(5,6)位置优越，在中心要点
2. 可同时攻击黑车和黑炮
3. 这是经典的"捉双"战术
4. 黑方只能保一个，必然丢子""",
        tool_calls=[
            ToolCall(
                step=1,
                tool="get_piece_attacks",
                input_params={"fen": "...", "piece": "红马(5,6)"},
                output={
                    "棋子": "红马(5,6)",
                    "攻击": ["黑车(1,10)", "黑炮(3,8)", "空位(4,4)"],
                    "高价值目标": 2
                },
                reason="确认红马可攻击的目标"
            ),
            ToolCall(
                step=2,
                tool="get_forcing_sequence",
                input_params={"fen": "...", "move": "马五进七", "depth": 4},
                output={
                    "序列": ["马五进七", "车1平3", "马七退六", "车3进1"],
                    "结果": "红方得子"
                },
                reason="确认战术是否成立"
            ),
            ToolCall(
                step=3,
                tool="engine_deep_analysis",
                input_params={"fen": "...", "depth": 20},
                output={"最佳走法": "马五进七", "评估": "+2.5"},
                reason="确认引擎也推荐捉双"
            )
        ],
        summary="""【战术发现】红马(5,6)可同时攻击黑车(1,10)和黑炮(3,8)
【战术类型】捉双战术（马踩双）
【战术结果】黑方只能保一个，红方必然得子
【教练建议】立即走马五进七捉双，这是必得子的战术机会，不要错过！"""
    ),

    FewshotExample(
        id=5,
        name="弃子攻杀（弃马抢攻）",
        phase=GamePhase.MIDDLEGAME,
        fen="r2ak1b1r/9/2n3n2/p1p1p1p1p/9/4N4/P1P1P1P1P/1C3N3/9/R1BAKAB1R w - - 0 15",
        move_count=15,
        description="第15回合，红马可弃子打开黑方防线",
        features=[
            "中局阶段",
            "红马位置突出但有危险",
            "可选择弃子攻杀",
            "风险与收益并存"
        ],
        thinking="""【阶段识别】中局（第15回合）
【战术扫描】
1. 红马(5,6)位置突出，但有危险
2. 可选择弃子攻杀，打开黑方防线
3. 弃子后后续攻势需要计算
4. 风险与收益并存""",
        tool_calls=[
            ToolCall(
                step=1,
                tool="analyze_move",
                input_params={"fen": "...", "move": "e5f7"},
                output={
                    "走法": "马五进六",
                    "质量": "aggressive",
                    "变化": {"物质损失": "-450分(弃马)", "攻势价值": "+600分", "综合评估": "值得尝试"}
                },
                reason="评估弃子的风险收益"
            ),
            ToolCall(
                step=2,
                tool="engine_deep_analysis",
                input_params={"fen": "...", "depth": 25},
                output={"最佳走法": "e5f7", "评估": "+1.2", "说明": "弃子攻杀成立"},
                reason="确认引擎支持弃子"
            ),
            ToolCall(
                step=3,
                tool="get_forcing_sequence",
                input_params={"fen": "...", "move": "e5f7", "depth": 5},
                output={"序列": ["马五进六", "士5退4", "车一进三..."], "结果": "红方形成强大攻势"},
                reason="确认后续攻势"
            )
        ],
        summary="""【战术发现】红马可弃子(马五进六)打开黑方防线
【风险评估】弃马损失450分，但后续攻势价值600分以上
【引擎观点】引擎评估+1.2，支持弃子攻杀
【教练建议】如果计算清晰、后续攻势明确，可果断弃子攻杀！但若不确定，先稳固阵型"""
    ),

    FewshotExample(
        id=6,
        name="防守反击（劣势守和）",
        phase=GamePhase.MIDDLEGAME,
        fen="r2ak1b1r/4a4/2n3n2/p1p1N1p1p/9/9/P1P1P1P1P/4N3/4A4/R2AKAB1R b - - 0 18",
        move_count=18,
        description="第18回合，黑方劣势，需要防守反击",
        features=[
            "中局后期",
            "红方多一马，物质优势",
            "黑方需要防守反击",
            "寻找兑子机会"
        ],
        thinking="""【阶段识别】中局后期
【局势判断】
1. 红方多一马，物质优势
2. 黑方需要防守反击
3. 寻找兑子机会简化局面
4. 或者制造战术机会""",
        tool_calls=[
            ToolCall(
                step=1,
                tool="get_piece_relations",
                input_params={"fen": "...", "piece": "黑将"},
                output={"保护者": ["士", "象"], "威胁者": ["红马"], "安全等级": "需要警惕"},
                reason="了解防守压力"
            ),
            ToolCall(
                step=2,
                tool="analyze_move",
                input_params={"fen": "...", "move": "c6e5"},
                output={"走法": "马3进5", "质量": "solid", "变化": {"物质变化": "红多兵", "简化程度": "大幅简化"}},
                reason="评估兑子选择"
            ),
            ToolCall(
                step=3,
                tool="engine_deep_analysis",
                input_params={"fen": "...", "depth": 25},
                output={"最佳走法": "兑子简化", "评估": "-0.8", "说明": "虽劣但可守"},
                reason="获取引擎建议"
            )
        ],
        summary="""【局势判断】红方多一马，黑方处于劣势
【防守要点】黑将安全等级一般，需要注意红马威胁
【反击选择】可尝试马3进5兑子，简化局面
【教练建议】劣势情况下应寻求兑子简化，不要强行对攻，争取守和"""
    )
]


# ============================================================================
# 残局示例（3个）
# ============================================================================

ENDGAME_EXAMPLES = [
    FewshotExample(
        id=7,
        name="单车对马士象全（理论残局）",
        phase=GamePhase.ENDGAME,
        fen="4k4/4a4/4b4/9/4n4/9/9/9/4R4/4K4 w - - 0 30",
        move_count=30,
        description="第30回合，单车对马士象全，理论和棋",
        features=[
            "残局阶段，子力仅5个",
            "经典理论残局",
            "理论结果：和棋",
            "条件：黑方防守正确"
        ],
        thinking="""【阶段识别】残局（子力仅5个）
【理论判断】
1. 单车对马士象全是经典理论残局
2. 理论结果：和棋
3. 条件：黑方防守正确
4. 红方需要制造麻烦""",
        tool_calls=[
            ToolCall(
                step=1,
                tool="engine_deep_analysis",
                input_params={"fen": "...", "depth": 30},
                output={"评估": "0.0", "理论结果": "和棋"},
                reason="确认理论判断"
            ),
            ToolCall(
                step=2,
                tool="get_piece_attacks",
                input_params={"fen": "...", "piece": "红车"},
                output={"攻击": ["黑马(5,7)", "黑士(4,10)", "空位..."], "高价值目标": 2},
                reason="了解红方可制造的压力"
            )
        ],
        summary="""【定式判断】单车对马士象全，理论和棋
【防守要点】黑方需保持士象完整，马不乱走，阵型不散
【进攻难点】红车难以突破马士象的联防
【教练建议】红方可尝试制造麻烦，但黑方防守正确必和；黑方不要贪功冒进"""
    ),

    FewshotExample(
        id=8,
        name="车兵对单车（胜势残局）",
        phase=GamePhase.ENDGAME,
        fen="4k4/9/9/9/9/9/4P4/9/4R4/4K4 w - - 0 35",
        move_count=35,
        description="第35回合，红方车兵对黑方单车，红方胜势",
        features=[
            "残局阶段",
            "红方车兵对单车",
            "红方胜势",
            "关键是兵的升变"
        ],
        thinking="""【阶段识别】残局
【理论判断】
1. 车兵对单车是胜势残局
2. 关键：兵的升变
3. 红方需要配合车兵推进
4. 黑方需要阻止兵升变""",
        tool_calls=[
            ToolCall(
                step=1,
                tool="analyze_move",
                input_params={"fen": "...", "move": "e3e4"},
                output={"走法": "兵进一", "质量": "good", "说明": "兵逐步接近底线"},
                reason="评估兵的推进"
            ),
            ToolCall(
                step=2,
                tool="engine_deep_analysis",
                input_params={"fen": "...", "depth": 30},
                output={"评估": "+3.5", "结果": "红方胜势"},
                reason="确认胜势"
            ),
            ToolCall(
                step=3,
                tool="get_forcing_sequence",
                input_params={"fen": "...", "move": "e3e4", "depth": 8},
                output={"序列": [...], "结果": "红兵升变胜"},
                reason="确认升变路线"
            )
        ],
        summary="""【定式判断】车兵对单车，红方胜势
【胜法要点】1.兵逐步推进 2.车配合保护 3.最终兵升变
【防守难点】黑车难以同时防守底线和兵
【教练建议】红方应稳步推进，不要急躁；兵到对方底线前需要注意车的配合"""
    ),

    FewshotExample(
        id=9,
        name="马炮对士象全（巧胜残局）",
        phase=GamePhase.ENDGAME,
        fen="4k4/4a4/4b4/9/9/9/9/9/4N4/3NK4 w - - 0 40",
        move_count=40,
        description="第40回合，红方马炮对黑方士象全，需要技巧",
        features=[
            "残局阶段",
            "马炮对士象全",
            "有胜机但需要技巧",
            "关键是马炮配合"
        ],
        thinking="""【阶段识别】残局
【理论判断】
1. 马炮对士象全需要技巧
2. 理论上有胜机，但不简单
3. 需要制造破绽
4. 关键是马炮配合""",
        tool_calls=[
            ToolCall(
                step=1,
                tool="get_piece_attacks",
                input_params={"fen": "...", "piece": "红马"},
                output={"攻击": ["黑士", "空位..."]},
                reason="了解马的攻击点"
            ),
            ToolCall(
                step=2,
                tool="engine_deep_analysis",
                input_params={"fen": "...", "depth": 35},
                output={"评估": "+0.8", "说明": "有胜机但需精确"},
                reason="确认胜机"
            ),
            ToolCall(
                step=3,
                tool="engine_alternatives",
                input_params={"fen": "...", "top_n": 3},
                output={
                    "候选走法": [
                        {"走法": "马六进八", "评估": "+1.0", "说明": "攻击黑士"},
                        {"走法": "炮五平六", "评估": "+0.8", "说明": "控制肋道"}
                    ]
                },
                reason="分析最佳走法"
            )
        ],
        summary="""【定式判断】马炮对士象全，有胜机但需要技巧
【进攻要点】马炮配合，寻找士象的破绽
【关键走法】马六进八攻击黑士，配合炮的控制
【教练建议】马炮残局需要耐心，逐步制造破绽；不要急躁，否则容易被守和"""
    )
]


# ============================================================================
# 汇总与工具函数
# ============================================================================

FEWSHOT_EXAMPLES = {
    "opening": OPENING_EXAMPLES,
    "middlegame": MIDDLEGAME_EXAMPLES,
    "endgame": ENDGAME_EXAMPLES
}


def get_fewshot_prompt(phase: str, count: int = 1) -> str:
    """
    获取阶段感知的Few-shot Prompt

    Args:
        phase: 阶段名称（opening/middlegame/endgame）
        count: 返回示例数量

    Returns:
        格式化的Few-shot Prompt
    """
    examples = FEWSHOT_EXAMPLES.get(phase, [])[:count]
    if not examples:
        return ""

    parts = []
    for ex in examples:
        # 格式化工具调用
        tool_calls_text = ""
        for tc in ex.tool_calls:
            tool_calls_text += f"""
步骤{tc.step}：{tc.tool}
→ 输入：{tc.input_params}
→ 输出：{tc.output}
→ 理由：{tc.reason}
"""

        parts.append(f"""
【示例{ex.id}：{ex.name}】
局面：{ex.description}
FEN：{ex.fen}

思维链：
{ex.thinking}

工具调用：{tool_calls_text}
总结输出：
{ex.summary}
""")

    return "\n".join(parts)


def get_all_examples() -> List[FewshotExample]:
    """获取所有示例（用于文档生成）"""
    all_examples = []
    for phase_examples in FEWSHOT_EXAMPLES.values():
        all_examples.extend(phase_examples)
    return all_examples


def get_example_by_id(example_id: int) -> Optional[FewshotExample]:
    """根据ID获取示例"""
    for ex in get_all_examples():
        if ex.id == example_id:
            return ex
    return None


def get_examples_by_phase(phase: str) -> List[FewshotExample]:
    """根据阶段获取示例"""
    return FEWSHOT_EXAMPLES.get(phase, [])


def format_example_for_display(example: FewshotExample) -> str:
    """
    格式化示例用于显示（演示用）

    Args:
        example: FewshotExample对象

    Returns:
        格式化的显示文本
    """
    # 格式化工具调用
    tool_calls_text = ""
    for tc in example.tool_calls:
        tool_calls_text += f"""
┌─ 步骤{tc.step}：{tc.tool}
│ 输入：{tc.input_params}
│ 输出：{tc.output}
│ 理由：{tc.reason}
└─────────────────
"""

    return f"""
╔══════════════════════════════════════════════════════════════╗
║ 示例{example.id}：{example.name}
╠══════════════════════════════════════════════════════════════╣
║ 【局面信息】
║ 阶段：{example.phase.value}（第{example.move_count}回合）
║ 特点：{', '.join(example.features[:2])}
║ FEN：{example.fen[:50]}...
╠══════════════════════════════════════════════════════════════╣
║ 【思维链】
{example.thinking}
╠══════════════════════════════════════════════════════════════╣
║ 【工具调用】
{tool_calls_text}
╠══════════════════════════════════════════════════════════════╣
║ 【总结输出】
{example.summary}
╚══════════════════════════════════════════════════════════════╝
"""


# ============================================================================
# 导出
# ============================================================================

__all__ = [
    # 类
    "GamePhase",
    "ToolCall",
    "FewshotExample",
    # 数据
    "OPENING_EXAMPLES",
    "MIDDLEGAME_EXAMPLES",
    "ENDGAME_EXAMPLES",
    "FEWSHOT_EXAMPLES",
    # 函数
    "get_fewshot_prompt",
    "get_all_examples",
    "get_example_by_id",
    "get_examples_by_phase",
    "format_example_for_display",
]
