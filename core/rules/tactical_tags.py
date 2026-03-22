"""
战术标签体系定义
基于象棋规则硬判定，六大核心层级
"""

from enum import Enum
from dataclasses import dataclass
from typing import List, Optional, Dict, Any


class TagCategory(Enum):
    """标签分类"""
    CHECK_MATE_STALEMATE = "将杀困毙层"      # 最高优先级
    CAPTURE = "捉子层"                       # 高优先级
    DISCOVERED_ATTACK = "闪击抽将层"         # 高优先级
    PIN_SKEWER = "牵制串打层"                # 中优先级
    STANDARD_MATE = "标准杀法层"             # 中优先级
    PIECE_STATUS = "子力状态层"              # 基础
    SEMANTIC = "局面语义层"                  # 语义中间变量


@dataclass
class TacticalTag:
    """战术标签定义"""
    name: str                           # 标签名（英文蛇形）
    category: TagCategory               # 所属层级
    description: str                    # 中文描述
    bind_pieces_required: bool          # 是否必须绑定棋子
    confidence_type: str                # 置信度类型（binary=二元化）
    
    def __repr__(self):
        return f"TacticalTag({self.name}, {self.category.value})"


# =============================================================================
# 六大层级战术标签定义
# =============================================================================

# -----------------------------------------------------------------------------
# 第一层：将杀困毙层（全局・最高优先级）
# -----------------------------------------------------------------------------
TAG_IS_CHECK = TacticalTag(
    name="is_check",
    category=TagCategory.CHECK_MATE_STALEMATE,
    description="被将军：一方将/帅处于对方棋子的合法攻击范围内",
    bind_pieces_required=True,
    confidence_type="binary"
)

TAG_IS_CHECKMATE = TacticalTag(
    name="is_checkmate",
    category=TagCategory.CHECK_MATE_STALEMATE,
    description="将死：一方将/帅被将军，且无任何合法解将手段",
    bind_pieces_required=True,
    confidence_type="binary"
)

TAG_IS_STALEMATE = TacticalTag(
    name="is_stalemate",
    category=TagCategory.CHECK_MATE_STALEMATE,
    description="困毙：一方行棋时无任何合法着法，且未被将军",
    bind_pieces_required=True,
    confidence_type="binary"
)

# -----------------------------------------------------------------------------
# 第二层：捉子层（全局/局部）
# -----------------------------------------------------------------------------
TAG_IS_ATTACK_UNPROTECTED = TacticalTag(
    name="is_attack_unprotected",
    category=TagCategory.CAPTURE,
    description="攻无根：一方棋子攻击对方无保护棋子",
    bind_pieces_required=True,
    confidence_type="binary"
)

TAG_IS_MUTUAL_ATTACK = TacticalTag(
    name="is_mutual_attack",
    category=TagCategory.CAPTURE,
    description="互吃：红黑双方棋子互相攻击，形成互捉",
    bind_pieces_required=True,
    confidence_type="binary"
)

TAG_IS_ATTACK_KING_ADJACENT = TacticalTag(
    name="is_attack_king_adjacent",
    category=TagCategory.CAPTURE,
    description="攻将邻：棋子攻击将/帅相邻空位（将军前兆）",
    bind_pieces_required=True,
    confidence_type="binary"
)

# -----------------------------------------------------------------------------
# 第三层：闪击抽将层（全局・战术型）
# -----------------------------------------------------------------------------
TAG_IS_DISCOVERED_CHECK = TacticalTag(
    name="is_discovered_check",
    category=TagCategory.DISCOVERED_ATTACK,
    description="闪将：移开己方棋子后，露出后方远程棋子将军",
    bind_pieces_required=True,
    confidence_type="binary"
)

TAG_IS_DOUBLE_ATTACK_WITH_CHECK = TacticalTag(
    name="is_double_attack_with_check",
    category=TagCategory.DISCOVERED_ATTACK,
    description="抽将：将军的同时，另一棋子攻击对方无根子/关键子",
    bind_pieces_required=True,
    confidence_type="binary"
)

TAG_IS_DISCOVERED_ATTACK = TacticalTag(
    name="is_discovered_attack",
    category=TagCategory.DISCOVERED_ATTACK,
    description="闪击：移开己方棋子后，露出后方棋子攻击对方无根子",
    bind_pieces_required=True,
    confidence_type="binary"
)

# -----------------------------------------------------------------------------
# 第四层：牵制串打层（全局・战术型）
# -----------------------------------------------------------------------------
TAG_IS_PINNED = TacticalTag(
    name="is_pinned",
    category=TagCategory.PIN_SKEWER,
    description="被牵制：一方棋子被对方车/炮牵制，移动后会导致己方将/帅被将军",
    bind_pieces_required=True,
    confidence_type="binary"
)

TAG_IS_CANNON_DOUBLE_ATTACK = TacticalTag(
    name="is_cannon_double_attack",
    category=TagCategory.PIN_SKEWER,
    description="炮串打：炮隔一个炮架同时攻击两个对方棋子",
    bind_pieces_required=True,
    confidence_type="binary"
)

# -----------------------------------------------------------------------------
# 第五层：标准杀法层（杀法型）
# -----------------------------------------------------------------------------
TAG_CHECKMATE_HORSE_BACK_CANNON = TacticalTag(
    name="checkmate_horse_back_cannon",
    category=TagCategory.STANDARD_MATE,
    description="马后炮：马和炮配合将死对方的经典杀法",
    bind_pieces_required=True,
    confidence_type="binary"
)

TAG_CHECKMATE_IRON_GATE = TacticalTag(
    name="checkmate_iron_gate",
    category=TagCategory.STANDARD_MATE,
    description="铁门栓：车在将/帅门线上配合其他子将死",
    bind_pieces_required=True,
    confidence_type="binary"
)

TAG_CHECKMATE_DOUBLE_ROOK = TacticalTag(
    name="checkmate_double_rook",
    category=TagCategory.STANDARD_MATE,
    description="双车错：双车交替将军将死",
    bind_pieces_required=True,
    confidence_type="binary"
)

# -----------------------------------------------------------------------------
# 第六层：子力状态层（单棋子属性）
# -----------------------------------------------------------------------------
TAG_PIECE_IS_UNPROTECTED = TacticalTag(
    name="piece_is_unprotected",
    category=TagCategory.PIECE_STATUS,
    description="子无根：某个棋子无任何己方棋子保护",
    bind_pieces_required=True,
    confidence_type="binary"
)

TAG_CANNON_HAS_PLATFORM = TacticalTag(
    name="cannon_has_platform",
    category=TagCategory.PIECE_STATUS,
    description="炮有架：炮有可用的炮架（任意棋子）",
    bind_pieces_required=True,
    confidence_type="binary"
)

TAG_CHECKMATE_HORSE_CORNER = TacticalTag(
    name="checkmate_horse_corner",
    category=TagCategory.STANDARD_MATE,
    description="卧槽马：马盘踞在敌方九宫格外攻击位，直接将死对方将/帅",
    bind_pieces_required=True,
    confidence_type="binary"
)

TAG_CHECKMATE_BARE_KING = TacticalTag(
    name="checkmate_bare_king",
    category=TagCategory.STANDARD_MATE,
    description="白脸将：利用双将不能对面规则，移开遮挡棋子后两将同列无阻挡形成将死",
    bind_pieces_required=True,
    confidence_type="binary"
)

TAG_CHECKMATE_DOUBLE_CANNON_BATTERY = TacticalTag(
    name="checkmate_double_cannon_battery",
    category=TagCategory.STANDARD_MATE,
    description="重炮杀：一门炮以另一门炮为炮架，攻击敌方将/帅形成将死",
    bind_pieces_required=True,
    confidence_type="binary"
)

TAG_CHECKMATE_SEA_BOTTOM_MOON = TacticalTag(
    name="checkmate_sea_bottom_moon",
    category=TagCategory.STANDARD_MATE,
    description="海底捞月：车深入敌方底线，在底线将死对方将/帅",
    bind_pieces_required=True,
    confidence_type="binary"
)

TAG_CHECKMATE_SIDE_TIGER = TacticalTag(
    name="checkmate_side_tiger",
    category=TagCategory.STANDARD_MATE,
    description="侧面虎：车与将/帅同行，横向将死",
    bind_pieces_required=True,
    confidence_type="binary"
)

TAG_PHASE_OPENING = TacticalTag(
    name="phase_opening",
    category=TagCategory.SEMANTIC,
    description="开局阶段：场上棋子总数 ≥ 28",
    bind_pieces_required=False,
    confidence_type="binary"
)

TAG_PHASE_MIDDLEGAME = TacticalTag(
    name="phase_middlegame",
    category=TagCategory.SEMANTIC,
    description="中局阶段：场上棋子总数在 15-27 之间",
    bind_pieces_required=False,
    confidence_type="binary"
)

TAG_PHASE_ENDGAME = TacticalTag(
    name="phase_endgame",
    category=TagCategory.SEMANTIC,
    description="残局阶段：场上棋子总数 ≤ 14",
    bind_pieces_required=False,
    confidence_type="binary"
)

TAG_KING_SAFETY_CRITICAL = TacticalTag(
    name="king_safety_critical",
    category=TagCategory.SEMANTIC,
    description="将帅危急：将/帅周围防守子力严重不足，且存在敌方进攻威胁",
    bind_pieces_required=True,
    confidence_type="binary"
)

TAG_HAS_INITIATIVE = TacticalTag(
    name="has_initiative",
    category=TagCategory.SEMANTIC,
    description="握有主动权：当前行棋方拥有明显更多的强制手段",
    bind_pieces_required=False,
    confidence_type="binary"
)

TAG_IS_FORCING_MOVE = TacticalTag(
    name="is_forcing_move",
    category=TagCategory.SEMANTIC,
    description="强制手段：走法是将军、捉对方无根子、或直接威胁将死",
    bind_pieces_required=True,
    confidence_type="binary"
)

TAG_HORSE_LEG_BLOCKED = TacticalTag(
    name="horse_leg_blocked",
    category=TagCategory.SEMANTIC,
    description="马脚被别：马的某个方向马脚被棋子占据",
    bind_pieces_required=True,
    confidence_type="binary"
)

TAG_KINGS_FACE_TO_FACE = TacticalTag(
    name="kings_face_to_face",
    category=TagCategory.SEMANTIC,
    description="双将对面：双方将/帅处于同一列且两将之间无任何棋子",
    bind_pieces_required=True,
    confidence_type="binary"
)

TAG_CANNON_BATTERY = TacticalTag(
    name="cannon_battery",
    category=TagCategory.SEMANTIC,
    description="重炮阵型：同色两门炮处于同一行或同一列，且两炮之间无任何棋子",
    bind_pieces_required=True,
    confidence_type="binary"
)

TAG_FAVORABLE_EXCHANGE = TacticalTag(
    name="favorable_exchange",
    category=TagCategory.SEMANTIC,
    description="有利兑换：己方可以吃掉对方价值更高的棋子，或免费吃掉对方无保护棋子",
    bind_pieces_required=True,
    confidence_type="binary"
)


# -----------------------------------------------------------------------------
# 第七层：走法质量层（动态分析・走法评估）
# -----------------------------------------------------------------------------
TAG_MOVE_IS_BLUNDER = TacticalTag(
    name="move_is_blunder",
    category=TagCategory.SEMANTIC,
    description="严重失误：走法导致丢子（价值≥300分）或被将死",
    bind_pieces_required=True,
    confidence_type="binary"
)

TAG_MOVE_IS_CAPTURE = TacticalTag(
    name="move_is_capture",
    category=TagCategory.SEMANTIC,
    description="吃子走法：走法目标位置有对方棋子",
    bind_pieces_required=True,
    confidence_type="binary"
)

TAG_MOVE_GIVES_CHECK = TacticalTag(
    name="move_gives_check",
    category=TagCategory.SEMANTIC,
    description="将军走法：走法后对方将/帅被将军",
    bind_pieces_required=True,
    confidence_type="binary"
)

TAG_MOVE_DEFENDS_PIECE = TacticalTag(
    name="move_defends_piece",
    category=TagCategory.SEMANTIC,
    description="防守走法：走法后保护了己方原本无根的棋子",
    bind_pieces_required=True,
    confidence_type="binary"
)

TAG_MOVE_ESCAPES_THREAT = TacticalTag(
    name="move_escapes_threat",
    category=TagCategory.SEMANTIC,
    description="逃脱走法：走法前被攻击，走法后安全",
    bind_pieces_required=True,
    confidence_type="binary"
)

TAG_MOVE_IMPROVES_POSITION = TacticalTag(
    name="move_improves_position",
    category=TagCategory.SEMANTIC,
    description="改善位置：走法后棋子活跃度提升，控制更多点",
    bind_pieces_required=True,
    confidence_type="binary"
)

# -----------------------------------------------------------------------------
# 第八层：战略评估层（局面战略）
# -----------------------------------------------------------------------------
TAG_CONTROLS_OPEN_FILE = TacticalTag(
    name="controls_open_file",
    category=TagCategory.SEMANTIC,
    description="控制开放线：车在某列无阻挡，控制该线路",
    bind_pieces_required=True,
    confidence_type="binary"
)

TAG_HAS_ACTIVE_PIECES = TacticalTag(
    name="has_active_pieces",
    category=TagCategory.SEMANTIC,
    description="子力活跃：多个子控制多个关键点",
    bind_pieces_required=False,
    confidence_type="binary"
)

TAG_PIECE_COORDINATION = TacticalTag(
    name="piece_coordination",
    category=TagCategory.SEMANTIC,
    description="子力协同：多个子攻击同一区域或形成配合",
    bind_pieces_required=True,
    confidence_type="binary"
)

TAG_KING_SAFETY_GOOD = TacticalTag(
    name="king_safety_good",
    category=TagCategory.SEMANTIC,
    description="将帅安全：将/帅周围有足够防守子力，无直接威胁",
    bind_pieces_required=True,
    confidence_type="binary"
)

TAG_HAS_SPACE_ADVANTAGE = TacticalTag(
    name="has_space_advantage",
    category=TagCategory.SEMANTIC,
    description="空间优势：己方控制的格子数多于对方",
    bind_pieces_required=False,
    confidence_type="binary"
)

# -----------------------------------------------------------------------------
# 第九层：引擎对齐层（引擎推荐解释）
# -----------------------------------------------------------------------------
TAG_ENGINE_ONLY_MOVE = TacticalTag(
    name="engine_only_move",
    category=TagCategory.SEMANTIC,
    description="唯一不输棋：引擎分析显示其他走法评估值大幅下降",
    bind_pieces_required=True,
    confidence_type="binary"
)

TAG_ENGINE_BEST_BY_MARGIN = TacticalTag(
    name="engine_best_by_margin",
    category=TagCategory.SEMANTIC,
    description="明显最佳：这步棋比第二选择高100分以上",
    bind_pieces_required=True,
    confidence_type="binary"
)

TAG_ENGINE_FORCING_SEQUENCE = TacticalTag(
    name="engine_forcing_sequence",
    category=TagCategory.SEMANTIC,
    description="强制序列：走法后形成强制应着序列",
    bind_pieces_required=True,
    confidence_type="binary"
)


# =============================================================================
# 标签注册表
# =============================================================================

ALL_TACTICAL_TAGS: List[TacticalTag] = [
    # 将杀困毙层
    TAG_IS_CHECK,
    TAG_IS_CHECKMATE,
    TAG_IS_STALEMATE,
    # 捉子层
    TAG_IS_ATTACK_UNPROTECTED,
    TAG_IS_MUTUAL_ATTACK,
    TAG_IS_ATTACK_KING_ADJACENT,
    # 闪击抽将层
    TAG_IS_DISCOVERED_CHECK,
    TAG_IS_DOUBLE_ATTACK_WITH_CHECK,
    TAG_IS_DISCOVERED_ATTACK,
    # 牵制串打层
    TAG_IS_PINNED,
    TAG_IS_CANNON_DOUBLE_ATTACK,
    # 标准杀法层
    TAG_CHECKMATE_HORSE_BACK_CANNON,
    TAG_CHECKMATE_IRON_GATE,
    TAG_CHECKMATE_DOUBLE_ROOK,
    TAG_CHECKMATE_HORSE_CORNER,
    TAG_CHECKMATE_BARE_KING,
    TAG_CHECKMATE_DOUBLE_CANNON_BATTERY,
    TAG_CHECKMATE_SEA_BOTTOM_MOON,
    TAG_CHECKMATE_SIDE_TIGER,
    # 子力状态层
    TAG_PIECE_IS_UNPROTECTED,
    TAG_CANNON_HAS_PLATFORM,
    # 局面语义层
    TAG_PHASE_OPENING,
    TAG_PHASE_MIDDLEGAME,
    TAG_PHASE_ENDGAME,
    TAG_KING_SAFETY_CRITICAL,
    TAG_HAS_INITIATIVE,
    TAG_IS_FORCING_MOVE,
    TAG_HORSE_LEG_BLOCKED,
    TAG_KINGS_FACE_TO_FACE,
    TAG_CANNON_BATTERY,
    TAG_FAVORABLE_EXCHANGE,
    # 走法质量层
    TAG_MOVE_IS_BLUNDER,
    TAG_MOVE_IS_CAPTURE,
    TAG_MOVE_GIVES_CHECK,
    TAG_MOVE_DEFENDS_PIECE,
    TAG_MOVE_ESCAPES_THREAT,
    TAG_MOVE_IMPROVES_POSITION,
    # 战略评估层
    TAG_CONTROLS_OPEN_FILE,
    TAG_HAS_ACTIVE_PIECES,
    TAG_PIECE_COORDINATION,
    TAG_KING_SAFETY_GOOD,
    TAG_HAS_SPACE_ADVANTAGE,
    # 引擎对齐层
    TAG_ENGINE_ONLY_MOVE,
    TAG_ENGINE_BEST_BY_MARGIN,
    TAG_ENGINE_FORCING_SEQUENCE,
]

# 按层级分组的标签
TAGS_BY_CATEGORY: Dict[TagCategory, List[TacticalTag]] = {
    category: [tag for tag in ALL_TACTICAL_TAGS if tag.category == category]
    for category in TagCategory
}


def get_tag_by_name(name: str) -> Optional[TacticalTag]:
    """根据名称获取标签定义"""
    for tag in ALL_TACTICAL_TAGS:
        if tag.name == name:
            return tag
    return None


def get_tags_by_category(category: TagCategory) -> List[TacticalTag]:
    """获取指定层级的所有标签"""
    return TAGS_BY_CATEGORY.get(category, [])


# =============================================================================
# 标签检测结果
# =============================================================================

@dataclass
class TagDetectionResult:
    """标签检测结果"""
    tag: TacticalTag                    # 标签定义
    detected: bool                      # 是否检测到
    confidence: float                   # 置信度（0.0或1.0）
    bind_pieces: List[str]              # 绑定的棋子列表 ["红车-(5,8)", ...]
    metadata: Optional[Dict[str, Any]] = None  # 额外元数据
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "tag": self.tag.name,
            "detected": self.detected,
            "confidence": self.confidence,
            "bind_pieces": self.bind_pieces,
            "metadata": self.metadata or {}
        }


@dataclass
class PositionTacticalAnalysis:
    """局面战术分析结果"""
    fen: str                                    # 局面FEN
    tags: List[TagDetectionResult]              # 所有标签检测结果
    
    def get_detected_tags(self) -> List[TagDetectionResult]:
        """获取检测到的标签"""
        return [t for t in self.tags if t.detected]
    
    def to_evidence_map(self) -> Dict[str, Any]:
        """转换为Evidence Map格式"""
        return {
            "facts_rules": [
                {
                    "tag": t.tag.name,
                    "confidence": t.confidence,
                    "bind_pieces": t.bind_pieces,
                    "description": t.tag.description
                }
                for t in self.get_detected_tags()
            ]
        }
