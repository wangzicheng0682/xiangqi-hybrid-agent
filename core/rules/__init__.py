"""
规则引擎模块

基于Pikafish引擎真值，不自行计算规则
"""

from .rule_engine import (
    RuleEngine,
    LegalMove,
    LegalMovesResult,
    get_legal_moves,
    is_legal_move,
)

from .tactical_tags import (
    # 标签分类
    TagCategory,
    TacticalTag,
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
    # 标签注册表
    ALL_TACTICAL_TAGS,
    TAGS_BY_CATEGORY,
    get_tag_by_name,
    get_tags_by_category,
    # 检测结果
    TagDetectionResult,
    PositionTacticalAnalysis,
)

from .piece_binding import (
    PieceBinding,
    PieceBindingFactory,
    format_bind_pieces,
    uci_to_coord,
    coord_to_uci,
)

# 战术标签检测器
from .tactical_detector import (
    TacticalDetector,
    DetectionMode,
    DynamicDetectionResult,
    FullDetectionResult,
    detect_tactical_tags,
    generate_evidence_map,
)

# 张力检测器
from .tension_detector import (
    TensionType,
    TensionPriority,
    Tension,
    TensionDetector,
    detect_tensions,
    get_primary_tension,
)

# 保留旧接口兼容性
from .xiangqi_rules import (
    XiangqiRulesEngine,
    get_legal_moves as _old_get_legal_moves,
    is_in_check as _old_is_in_check,
)

# 一致性检查器
from .consistency_checker import (
    ConsistencyRule,
    ConsistencyChecker,
    ConsistencyError,
    CONSISTENCY_RULES,
    check_position_consistency,
    validate_detection_result,
)

__all__ = [
    # 新接口（基于引擎）
    'RuleEngine',
    'LegalMove',
    'LegalMovesResult',
    'get_legal_moves',
    'is_legal_move',
    # 战术标签
    'TagCategory',
    'TacticalTag',
    'TagDetectionResult',
    'PositionTacticalAnalysis',
    # 标签常量
    'TAG_IS_CHECK',
    'TAG_IS_CHECKMATE',
    'TAG_IS_STALEMATE',
    'TAG_IS_ATTACK_UNPROTECTED',
    'TAG_IS_MUTUAL_ATTACK',
    'TAG_IS_DISCOVERED_CHECK',
    'TAG_IS_DOUBLE_ATTACK_WITH_CHECK',
    'TAG_IS_PINNED',
    'TAG_IS_CANNON_DOUBLE_ATTACK',
    'TAG_CHECKMATE_HORSE_BACK_CANNON',
    'TAG_CHECKMATE_IRON_GATE',
    'TAG_CHECKMATE_DOUBLE_ROOK',
    'TAG_CHECKMATE_HORSE_CORNER',
    'TAG_CHECKMATE_BARE_KING',
    'TAG_CHECKMATE_DOUBLE_CANNON_BATTERY',
    'TAG_CHECKMATE_SEA_BOTTOM_MOON',
    'TAG_CHECKMATE_SIDE_TIGER',
    'TAG_PIECE_IS_UNPROTECTED',
    'TAG_CANNON_HAS_PLATFORM',
    'TAG_PHASE_OPENING',
    'TAG_PHASE_MIDDLEGAME',
    'TAG_PHASE_ENDGAME',
    'TAG_KING_SAFETY_CRITICAL',
    'TAG_HAS_INITIATIVE',
    'TAG_IS_FORCING_MOVE',
    'TAG_HORSE_LEG_BLOCKED',
    'TAG_KINGS_FACE_TO_FACE',
    'TAG_CANNON_BATTERY',
    'TAG_FAVORABLE_EXCHANGE',
    # 标签注册表
    'ALL_TACTICAL_TAGS',
    'TAGS_BY_CATEGORY',
    'get_tag_by_name',
    'get_tags_by_category',
    # 棋子绑定
    'PieceBinding',
    'PieceBindingFactory',
    'format_bind_pieces',
    'uci_to_coord',
    'coord_to_uci',
    # 战术标签检测器
    'TacticalDetector',
    'DetectionMode',
    'DynamicDetectionResult',
    'FullDetectionResult',
    'detect_tactical_tags',
    'generate_evidence_map',
    # 张力检测器
    'TensionType',
    'TensionPriority',
    'Tension',
    'TensionDetector',
    'detect_tensions',
    'get_primary_tension',
    # 旧接口（自研规则，保留兼容性）
    'XiangqiRulesEngine',
    # 一致性检查器
    'ConsistencyRule',
    'ConsistencyChecker',
    'ConsistencyError',
    'CONSISTENCY_RULES',
    'check_position_consistency',
    'validate_detection_result',
]
