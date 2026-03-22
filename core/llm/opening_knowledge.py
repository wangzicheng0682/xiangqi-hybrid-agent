"""
象棋开局知识库

来源: 联网搜索整理的专业象棋知识
整理时间: 2026-03-15

内容:
1. 开局十大原则
2. 开局分类体系
3. 常见开局定式
4. 阶段判断标准
5. 局面评估要点

用途: 为LLM提供结构化的开局知识，增强思维链的专业性
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum


# ============================================================
# 第一部分：开局十大原则
# ============================================================

OPENING_PRINCIPLES = [
    {
        "id": 1,
        "name": "尽早出动大子",
        "description": "车、马、炮三类兵种威力最大，应尽早从原始位置部署到最佳位置",
        "tips": [
            "三步出车：前三回合分别走中炮、跳马、出车",
            "车是最强子，必须尽快投入战斗",
            "马炮配合，控制要道"
        ],
        "common_mistakes": [
            "重复走同一子浪费步数",
            "过早走兵卒忽略大子"
        ]
    },
    {
        "id": 2,
        "name": "避免子力拥堵",
        "description": "注意阵型协调，避免子力拥堵在一个区域中互相限制行动",
        "tips": [
            "左右两翼均衡发展",
            "避免一侧大子堆积",
            "保持子力灵活性"
        ],
        "common_mistakes": [
            "金钩炮开局（新手不易驾驭）",
            "一侧出子过多另一侧停滞"
        ]
    },
    {
        "id": 3,
        "name": "重视中央区域控制",
        "description": "帅将位于棋盘中央的九宫内，控制中路是攻防关键",
        "tips": [
            "中路炮控制中心",
            "双正马或正边马组合",
            "兵卒挺进占据中路"
        ],
        "common_mistakes": [
            "飞双边相削弱中路保护",
            "双边马组合中路空虚"
        ]
    },
    {
        "id": 4,
        "name": "避免走动帅将",
        "description": "初始位置是帅将最安全的位置，被士相中兵保护",
        "tips": [
            "保持帅将在九宫中心",
            "需要时再补士象",
            "避免过早暴露"
        ],
        "common_mistakes": [
            "无意义地移动老帅",
            "过早让帅将离开安全位置"
        ]
    },
    {
        "id": 5,
        "name": "避免孤军深入",
        "description": "子力之间要互相配合，避免单个子力缺乏支援深入敌阵",
        "tips": [
            "过河子要有后续支援",
            "保持子力联系",
            "避免单打独斗"
        ],
        "common_mistakes": [
            "开局第一步走过河炮",
            "单车深入无援"
        ]
    },
    {
        "id": 6,
        "name": "避免无意义浪费步数",
        "description": "提高运子效率，抓紧时间部署子力，避免重复走子",
        "tips": [
            "每步棋要有明确目的",
            "避免来回走同一子",
            "不要贪小兵小卒"
        ],
        "common_mistakes": [
            "沿河十八打（巡河炮来回平移）",
            "重复进退同一子"
        ]
    },
    {
        "id": 7,
        "name": "尽可能活马",
        "description": "马的走动受轧马脚限制，畅通马路是发挥威力的关键",
        "tips": [
            "马前兵前进一步即可活马",
            "同时限制对方马路",
            "避免马被蹩脚"
        ],
        "common_mistakes": [
            "马被困在角落",
            "过早让马深入被围"
        ]
    },
    {
        "id": 8,
        "name": "发挥车的威力",
        "description": "车是威力最大的棋子，最大化发挥车的威力至关重要",
        "tips": [
            "横车：车九进一（灵活）",
            "直车：车一平二（快速）",
            "贴身车：帅旁出车（安全）"
        ],
        "common_mistakes": [
            "缓开车变成不开车",
            "车被困在原地"
        ]
    },
    {
        "id": 9,
        "name": "开局炮价值略高于马",
        "description": "开局阶段子力多，马易受限，炮有炮架可远程威慑",
        "tips": [
            "第一步炮换马极不划算",
            "保持炮的灵活性",
            "利用炮架威胁远处"
        ],
        "common_mistakes": [
            "开局用炮换马",
            "炮轻发失去先手"
        ]
    },
    {
        "id": 10,
        "name": "适当联动士象",
        "description": "士象是重要防守兵种，可适当联动构筑防线",
        "tips": [
            "在需要时适当补士象",
            "不耽误大子出动前提下",
            "增强防守能力"
        ],
        "common_mistakes": [
            "过早补士象耽误出子",
            "完全不补士象"
        ]
    }
]


# ============================================================
# 第二部分：开局分类体系
# ============================================================

class OpeningCategory(Enum):
    """开局大类"""
    CENTRAL_CANNON = "中炮类"      # 进攻型
    ELEPHANT = "飞相类"            # 防守型
    PAWN_ADVANCE = "挺兵类"        # 试探型
    HORSE = "起马类"               # 稳健型
    OTHER = "其他类"               # 冷门开局


@dataclass
class OpeningSystem:
    """开局体系"""
    name: str                          # 体系名称
    category: OpeningCategory          # 所属大类
    first_move: str                    # 第一步走法
    description: str                   # 体系描述
    characteristics: List[str]         # 特点
    variations: List[str] = field(default_factory=list)  # 主要变例
    suitable_for: str = ""             # 适合人群


# 主要开局体系定义
OPENING_SYSTEMS = {
    # === 中炮类（进攻型）===
    "中炮对屏风马": OpeningSystem(
        name="中炮对屏风马",
        category=OpeningCategory.CENTRAL_CANNON,
        first_move="炮二平五",
        description="中炮进攻，屏风马防守，最主流的对局体系",
        characteristics=[
            "攻防激烈，变化复杂",
            "红方主动进攻，黑方稳固防守",
            "双方争夺中路控制权"
        ],
        variations=[
            "中炮进三兵对屏风马",
            "中炮进七兵对屏风马",
            "中炮急进中兵对屏风马",
            "五七炮对屏风马",
            "五八炮对屏风马"
        ],
        suitable_for="所有水平棋手必修"
    ),

    "中炮对反宫马": OpeningSystem(
        name="中炮对反宫马",
        category=OpeningCategory.CENTRAL_CANNON,
        first_move="炮二平五",
        description="黑方炮8平6形成反宫马阵型，限制红方三路马",
        characteristics=[
            "黑方阵型紧凑",
            "红方中路压力较大",
            "变化相对屏风马少"
        ],
        variations=[
            "中炮进七兵对反宫马",
            "五七炮对反宫马"
        ],
        suitable_for="喜欢防守反击的棋手"
    ),

    "顺炮": OpeningSystem(
        name="顺炮",
        category=OpeningCategory.CENTRAL_CANNON,
        first_move="炮二平五 炮8平5",
        description="双方同向架中炮，对攻激烈",
        characteristics=[
            "对攻激烈",
            "变化直接",
            "容易形成激烈战斗"
        ],
        variations=[
            "顺炮直车对横车",
            "顺炮横车对直车",
            "顺炮缓开车"
        ],
        suitable_for="喜欢对攻的棋手"
    ),

    "列炮": OpeningSystem(
        name="列炮",
        category=OpeningCategory.CENTRAL_CANNON,
        first_move="炮二平五 炮2平5",
        description="双方反向架中炮，各攻一翼",
        characteristics=[
            "各攻一翼",
            "对攻性强",
            "变化相对较少"
        ],
        variations=[
            "列炮直车",
            "中途列炮"
        ],
        suitable_for="喜欢对攻的棋手"
    ),

    # === 飞相类（防守型）===
    "飞相局": OpeningSystem(
        name="飞相局",
        category=OpeningCategory.ELEPHANT,
        first_move="相三进五",
        description="第一步飞相，加固中路，稳健开局",
        characteristics=[
            "稳健防守",
            "后发制人",
            "变化多端"
        ],
        variations=[
            "飞相对左中炮",
            "飞相对右正马",
            "飞相对进七卒"
        ],
        suitable_for="喜欢稳健的棋手"
    ),

    # === 挺兵类（试探型）===
    "仙人指路": OpeningSystem(
        name="仙人指路",
        category=OpeningCategory.PAWN_ADVANCE,
        first_move="兵七进一",
        description="第一步挺兵试探，灵活多变",
        characteristics=[
            "试探性强",
            "可转多种阵型",
            "灵活多变"
        ],
        variations=[
            "仙人指路对卒底炮",
            "仙人指路对还中炮",
            "仙人指路对飞象"
        ],
        suitable_for="喜欢灵活应变的棋手"
    ),

    # === 其他类 ===
    "起马局": OpeningSystem(
        name="起马局",
        category=OpeningCategory.HORSE,
        first_move="马二进三",
        description="第一步起马，稳健开局",
        characteristics=[
            "稳健开局",
            "灵活多变",
            "可转中炮或飞相"
        ],
        variations=[],
        suitable_for="喜欢稳健的棋手"
    ),

    "过宫炮": OpeningSystem(
        name="过宫炮",
        category=OpeningCategory.OTHER,
        first_move="炮二平六",
        description="炮移到六路，集中子力于一翼",
        characteristics=[
            "集中火力",
            "一侧强势",
            "需要经验驾驭"
        ],
        variations=[],
        suitable_for="有经验的棋手"
    )
}


# ============================================================
# 第三部分：黑方应对中炮四大体系
# ============================================================

DEFENSE_AGAINST_CANNON = {
    "屏风马": {
        "moves": "马8进7，马2进3",
        "description": "双马并踞形成屏风状，稳固防守中寻求反击",
        "advantages": ["防守稳固", "变化丰富", "主流应对"],
        "disadvantages": ["中路压力较大", "需要精确应对"],
        "key_points": [
            "挺卒活马",
            "炮8平9形成三步虎",
            "注意中路防守"
        ]
    },

    "反宫马": {
        "moves": "马2进3，炮8平6",
        "description": "右马保卒，左炮占肋，限制红方三路马",
        "advantages": ["阵型紧凑", "限制对方", "反击力强"],
        "disadvantages": ["中路防守压力", "变化相对少"],
        "key_points": [
            "炮8平6占肋",
            "注意中路补防",
            "伺机反击"
        ]
    },

    "顺炮": {
        "moves": "炮8平5",
        "description": "同向架中炮，以攻对攻",
        "advantages": ["对攻激烈", "变化直接", "容易掌握"],
        "disadvantages": ["风险较大", "需要精确"],
        "key_points": [
            "快速出车",
            "争夺中路",
            "注意防守"
        ]
    },

    "列炮": {
        "moves": "炮2平5",
        "description": "反向架中炮，各攻一翼",
        "advantages": ["各攻一翼", "对攻性强"],
        "disadvantages": ["变化较少", "需要经验"],
        "key_points": [
            "马8进7保中卒",
            "快速出车",
            "注意配合"
        ]
    }
}


# ============================================================
# 第四部分：常见开局定式（前10回合）
# ============================================================

OPENING_PATTERNS = {
    # 中炮进三兵对屏风马
    "中炮进三兵对屏风马": {
        "moves": [
            "炮二平五", "马8进7",
            "马二进三", "车9平8",
            "车一平二", "马2进3",
            "兵三进一", "卒3进1",
            "马八进九", "卒1进1"
        ],
        "description": "双方互进三兵卒，红方跳边马，黑方进边卒",
        "key_ideas": [
            "红方控制三路线",
            "黑方准备大出车",
            "双方争夺中路"
        ],
        "evaluations": {
            "red_plan": "利用五七炮或五八炮进攻",
            "black_plan": "大出车占肋道反击",
            "balance": "红方稍先"
        }
    },

    # 中炮进七兵对屏风马
    "中炮进七兵对屏风马": {
        "moves": [
            "炮二平五", "马8进7",
            "马二进三", "车9平8",
            "车一平二", "卒7进1",
            "车二进六", "马2进3",
            "兵七进一", "马7进6"
        ],
        "description": "红方过河车压制，黑方跃马河口反击",
        "key_ideas": [
            "红方过河车控制",
            "黑方跃马反击",
            "双方对峙"
        ],
        "evaluations": {
            "red_plan": "继续压制或兑车",
            "black_plan": "马踩兵或炮8平9兑车",
            "balance": "红方稍先"
        }
    },

    # 急进中兵
    "急进中兵对屏风马": {
        "moves": [
            "炮二平五", "马8进7",
            "马二进三", "车9平8",
            "车一平二", "卒7进1",
            "车二进六", "马2进3",
            "兵五进一", "士4进5",
            "兵五进一"
        ],
        "description": "红方急进中兵，猛烈进攻",
        "key_ideas": [
            "红方中路强攻",
            "黑方固守待变",
            "变化复杂激烈"
        ],
        "evaluations": {
            "red_plan": "中兵突破，马配合进攻",
            "black_plan": "固守中路，伺机反击",
            "balance": "红方主动"
        }
    },

    # 顺炮直车对横车
    "顺炮直车对横车": {
        "moves": [
            "炮二平五", "炮8平5",
            "马二进三", "马8进7",
            "车一平二", "车9进1"
        ],
        "description": "红方直车，黑方横车，顺炮经典对局",
        "key_ideas": [
            "红方直车快速",
            "黑方横车灵活",
            "双方争夺中路"
        ],
        "evaluations": {
            "red_plan": "利用直车快速进攻",
            "black_plan": "横车占肋反击",
            "balance": "红方稍先"
        }
    },

    # 仙人指路对卒底炮
    "仙人指路对卒底炮": {
        "moves": [
            "兵七进一", "炮2平3",
            "炮二平五", "象3进5",
            "马二进三", "卒3进1"
        ],
        "description": "黑方卒底炮反击，红方还架中炮",
        "key_ideas": [
            "红方试探后转中炮",
            "黑方卒底炮反击",
            "黑方进卒威胁"
        ],
        "evaluations": {
            "red_plan": "马八进七稳固，控制中心",
            "black_plan": "卒3进1反击",
            "balance": "红方稍先"
        }
    }
}


# ============================================================
# 第五部分：开局评估函数
# ============================================================

def evaluate_opening_development(fen: str) -> Dict[str, Any]:
    """
    评估开局出子效率

    Args:
        fen: 局面FEN

    Returns:
        开局评估结果
    """
    from core.llm.thinking_templates import OpeningAnalyzer

    analysis = OpeningAnalyzer.analyze(fen)

    # 计算综合评分
    dev = analysis["development"]
    center = analysis["center_control"]
    activity = analysis["piece_activity"]
    initiative = analysis["initiative"]

    # 红方评分
    red_score = 0
    red_score += dev["red_developed"] * 10  # 每出一子+10
    red_score += center["red_center_pieces"] * 5  # 中路控制+5
    red_score += activity["red_active_count"] * 3  # 活跃子力+3
    if initiative["initiative"] == "red":
        red_score += 15  # 先手+15

    # 黑方评分
    black_score = 0
    black_score += dev["black_developed"] * 10
    black_score += center["black_center_pieces"] * 5
    black_score += activity["black_active_count"] * 3
    if initiative["initiative"] == "black":
        black_score += 15

    return {
        "red_score": red_score,
        "black_score": black_score,
        "advantage": "red" if red_score > black_score else
                     "black" if black_score > red_score else "equal",
        "score_difference": abs(red_score - black_score),
        "analysis": analysis
    }


def detect_opening_pattern(moves: List[str]) -> Optional[Dict[str, Any]]:
    """
    检测当前走法是否匹配已知开局定式

    Args:
        moves: 走法列表（中文记谱）

    Returns:
        匹配的开局定式信息，或None
    """
    if not moves:
        return None

    # 检测第一步
    first_move = moves[0] if len(moves) > 0 else ""

    # 中炮开局
    if first_move == "炮二平五":
        if len(moves) >= 4:
            # 检测黑方应对
            black_first = moves[1] if len(moves) > 1 else ""
            black_second = moves[3] if len(moves) > 3 else ""

            if "马8进7" in black_first:
                # 可能是屏风马或三步虎
                if len(moves) >= 6 and "马2进3" in moves[5]:
                    return {
                        "pattern": "中炮对屏风马",
                        "confidence": 0.9,
                        "matched_moves": moves[:6]
                    }
            elif "炮8平5" in black_first:
                return {
                    "pattern": "顺炮",
                    "confidence": 0.95,
                    "matched_moves": moves[:2]
                }
            elif "炮2平5" in black_first:
                return {
                    "pattern": "列炮",
                    "confidence": 0.95,
                    "matched_moves": moves[:2]
                }
            elif "马2进3" in black_first:
                # 可能是反宫马
                if len(moves) >= 4 and "炮8平6" in black_second:
                    return {
                        "pattern": "反宫马",
                        "confidence": 0.85,
                        "matched_moves": moves[:4]
                    }

    # 飞相局
    elif first_move in ["相三进五", "相七进五"]:
        return {
            "pattern": "飞相局",
            "confidence": 0.9,
            "matched_moves": moves[:1]
        }

    # 仙人指路
    elif first_move in ["兵七进一", "兵三进一"]:
        return {
            "pattern": "仙人指路",
            "confidence": 0.9,
            "matched_moves": moves[:1]
        }

    # 起马局
    elif first_move in ["马二进三", "马八进七"]:
        return {
            "pattern": "起马局",
            "confidence": 0.8,
            "matched_moves": moves[:1]
        }

    return None


def get_opening_advice(fen: str, move_count: int, moves: List[str] = None) -> str:
    """
    根据开局情况生成教练建议

    Args:
        fen: 当前局面FEN
        move_count: 回合数
        moves: 已走的棋步列表

    Returns:
        教练建议文本
    """
    from core.llm.thinking_templates import PhaseDetector, OpeningAnalyzer

    # 检测阶段
    phase_info = PhaseDetector.detect(fen, move_count)

    if not phase_info.is_opening():
        return ""

    # 分析开局
    analysis = OpeningAnalyzer.analyze(fen, move_count)
    summary = OpeningAnalyzer.generate_summary(analysis)

    # 检测定式
    pattern_info = None
    if moves:
        pattern_info = detect_opening_pattern(moves)

    # 生成建议
    advice_lines = [f"【开局分析】（第{move_count}回合）"]
    advice_lines.append(summary)

    if pattern_info:
        advice_lines.append(f"\n【开局定式】{pattern_info['pattern']}（置信度{pattern_info['confidence']*100:.0f}%）")
        if pattern_info['pattern'] in OPENING_SYSTEMS:
            system = OPENING_SYSTEMS[pattern_info['pattern']]
            advice_lines.append(f"特点：{'、'.join(system.characteristics[:2])}")

    # 添加原则建议
    advice_lines.append("\n【开局要点】")
    dev = analysis["development"]
    if dev["advantage"] == "red":
        advice_lines.append("• 红方出子领先，继续保持")
    elif dev["advantage"] == "black":
        advice_lines.append("• 黑方出子领先，红方需加快出子")

    center = analysis["center_control"]
    if center["center_control"] == "equal":
        advice_lines.append("• 中路争夺激烈，注意控制")

    return "\n".join(advice_lines)


# ============================================================
# 导出接口
# ============================================================

__all__ = [
    # 原则
    "OPENING_PRINCIPLES",
    # 体系
    "OpeningCategory",
    "OpeningSystem",
    "OPENING_SYSTEMS",
    # 应对
    "DEFENSE_AGAINST_CANNON",
    # 定式
    "OPENING_PATTERNS",
    # 函数
    "evaluate_opening_development",
    "detect_opening_pattern",
    "get_opening_advice",
]
