"""
局面分析标准化输出协议

三层语义标签体系：
- 几何/规则层：纯走法事实
- 位置语义层：棋理位置描述
- 战术模式层：可直接用于讲解或检索

输出分离：
- analysis_structured：机器可消费结构
- analysis_text：用户可读文本
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum


class GeometricTag(Enum):
    LEGAL_MOVE = "legal_move"
    ATTACKABLE = "attackable"
    BLOCKED = "blocked"
    PINNED = "pinned"
    CROSS_RIVER = "cross_river"
    PALACE_LIMITED = "palace_limited"
    ELEPHANT_BLOCKED = "elephant_blocked"
    HORSE_LEG_BLOCKED = "horse_leg_blocked"
    CANNON_SCREEN_READY = "cannon_screen_ready"
    CAN_CHECK = "can_check"
    IS_HANGING = "is_hanging"
    IS_DEFENDED = "is_defended"


class PositionalTag(Enum):
    RIVERBANK_ROOK = "riverbank_rook"
    BOTTOM_CANNON = "bottom_cannon"
    EDGE_PAWN = "edge_pawn"
    CENTRAL_PAWN = "central_pawn"
    PALACE_GUARDED = "palace_guarded"
    FLANK_PRESSURE = "flank_pressure"
    OPEN_FILE_ROOK = "open_file_rook"
    RIB_FILE = "rib_file"
    CENTER_FILE = "center_file"
    HIGH_PAWN = "high_pawn"
    RIB_PAWN = "rib_pawn"


class TacticalTag(Enum):
    JUOCAO_MA = "卧槽马"
    GUAJIAO_MA = "挂角马"
    CHENDI_PAO = "沉底炮"
    XUNHE_PAO = "巡河炮"
    KONGTOU_PAO = "空头炮"
    SHUANGCHE_CUO = "双车错"
    QIANZHI = "牵制"
    DINGMEN_PAO = "顶门炮"
    SHANJI = "闪击"
    MENGONG = "闷宫"
    DUIJIANG = "对将"
    DUIZI_XIANSHOU = "兑子先手"
    FORK = "双将"
    CHECK_THREAT = "将军威胁"


PIECE_TYPE_NAMES = {
    'k': 'king',
    'a': 'advisor', 
    'b': 'elephant',
    'r': 'rook',
    'c': 'cannon',
    'n': 'knight',
    'p': 'pawn'
}

PIECE_NAMES_CN = {
    'K': '帅', 'k': '将',
    'A': '仕', 'a': '士',
    'B': '相', 'b': '象',
    'R': '车', 'r': '车',
    'C': '炮', 'c': '炮',
    'N': '马', 'n': '马',
    'P': '兵', 'p': '卒',
}

PIECE_VALUES = {
    'K': 0, 'k': 0,
    'R': 9, 'r': 9,
    'C': 4.5, 'c': 4.5,
    'N': 4, 'n': 4,
    'B': 2, 'b': 2,
    'A': 2, 'a': 2,
    'P': 1, 'p': 1,
}


@dataclass
class LegalMove:
    to: List[int]
    move_type: str
    status: str
    direction: str
    note: str
    capture_target: Optional[str] = None
    capture_value: float = 0.0
    
    def to_dict(self) -> dict:
        return {
            "to": self.to,
            "type": self.move_type,
            "status": self.status,
            "direction": self.direction,
            "note": self.note,
            "capture_target": self.capture_target,
            "capture_value": self.capture_value
        }


@dataclass
class Constraint:
    kind: str
    target: Optional[List[int]]
    note: str
    block_piece: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "target": self.target,
            "note": self.note,
            "block_piece": self.block_piece
        }


@dataclass
class Mobility:
    legal_count: int
    attack_count: int
    activity_score: int = 0
    
    def to_dict(self) -> dict:
        return {
            "legal_count": self.legal_count,
            "attack_count": self.attack_count,
            "activity_score": self.activity_score
        }


@dataclass
class StandardizedPiece:
    piece_id: str
    side: str
    piece_type: str
    piece_name: str
    position: List[int]
    legal_moves: List[LegalMove] = field(default_factory=list)
    attacks: List[str] = field(default_factory=list)
    mobility: Optional[Mobility] = None
    constraints: List[Constraint] = field(default_factory=list)
    geometric_tags: List[str] = field(default_factory=list)
    positional_tags: List[str] = field(default_factory=list)
    tactical_patterns: List[str] = field(default_factory=list)
    material_value: float = 0.0
    attacked_by: List[str] = field(default_factory=list)
    defended_by: List[str] = field(default_factory=list)
    protects: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "piece_id": self.piece_id,
            "side": self.side,
            "piece_type": self.piece_type,
            "piece_name": self.piece_name,
            "position": self.position,
            "legal_moves": [m.to_dict() for m in self.legal_moves],
            "attacks": self.attacks,
            "mobility": self.mobility.to_dict() if self.mobility else None,
            "constraints": [c.to_dict() for c in self.constraints],
            "geometric_tags": self.geometric_tags,
            "positional_tags": self.positional_tags,
            "tactical_patterns": self.tactical_patterns,
            "material_value": self.material_value,
            "attacked_by": self.attacked_by,
            "defended_by": self.defended_by,
            "protects": self.protects
        }


@dataclass
class GlobalPattern:
    pattern_type: str
    side: str
    source_piece: Optional[str] = None
    target_piece: Optional[str] = None
    target_position: Optional[List[int]] = None
    note: str = ""
    
    def to_dict(self) -> dict:
        return {
            "type": self.pattern_type,
            "side": self.side,
            "source_piece": self.source_piece,
            "target_piece": self.target_piece,
            "target_position": self.target_position,
            "note": self.note
        }


@dataclass
class PressureMap:
    red_controls: List[List[int]] = field(default_factory=list)
    black_controls: List[List[int]] = field(default_factory=list)
    contested_points: List[List[int]] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "red_controls": self.red_controls,
            "black_controls": self.black_controls,
            "contested_points": self.contested_points
        }


@dataclass
class RetrievalInfo:
    tags: List[str] = field(default_factory=list)
    query_hints: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "tags": self.tags,
            "query_hints": self.query_hints
        }


@dataclass
class PositionSummary:
    red_piece_count: int = 0
    black_piece_count: int = 0
    red_material: float = 0.0
    black_material: float = 0.0
    material_balance: float = 0.0
    total_legal_moves_red: int = 0
    total_legal_moves_black: int = 0
    is_check: bool = False
    check_by: Optional[str] = None
    is_checkmate: bool = False
    
    def to_dict(self) -> dict:
        return {
            "red_piece_count": self.red_piece_count,
            "black_piece_count": self.black_piece_count,
            "red_material": self.red_material,
            "black_material": self.black_material,
            "material_balance": self.material_balance,
            "total_legal_moves_red": self.total_legal_moves_red,
            "total_legal_moves_black": self.total_legal_moves_black,
            "is_check": self.is_check,
            "check_by": self.check_by,
            "is_checkmate": self.is_checkmate
        }


@dataclass
class StandardizedPositionAnalysis:
    board_fen: str
    turn: str
    pieces: List[StandardizedPiece] = field(default_factory=list)
    global_patterns: List[GlobalPattern] = field(default_factory=list)
    pressure_map: Optional[PressureMap] = None
    retrieval_info: Optional[RetrievalInfo] = None
    summary: Optional[PositionSummary] = None
    
    def to_structured(self) -> dict:
        return {
            "board_fen": self.board_fen,
            "turn": self.turn,
            "pieces": [p.to_dict() for p in self.pieces],
            "global_patterns": [p.to_dict() for p in self.global_patterns],
            "pressure_map": self.pressure_map.to_dict() if self.pressure_map else None,
            "retrieval_info": self.retrieval_info.to_dict() if self.retrieval_info else None,
            "summary": self.summary.to_dict() if self.summary else None
        }
    
    def to_text(self) -> dict:
        lines = []
        lines.append(f"【局面分析】")
        lines.append(f"轮到: {'红方' if self.turn == 'red' else '黑方'}走棋")
        lines.append("")
        
        if self.summary:
            lines.append(f"子力对比: 红方{self.summary.red_material}分 vs 黑方{self.summary.black_material}分")
            if self.summary.is_check:
                lines.append(f"⚠️ 将军! 由{self.summary.check_by}发起")
            lines.append("")
        
        red_pieces = [p for p in self.pieces if p.side == 'red']
        black_pieces = [p for p in self.pieces if p.side == 'black']
        
        lines.append("【红方棋子状态】")
        for p in red_pieces:
            text = self._piece_to_text(p)
            if text:
                lines.append(text)
        
        lines.append("")
        lines.append("【黑方棋子状态】")
        for p in black_pieces:
            text = self._piece_to_text(p)
            if text:
                lines.append(text)
        
        if self.global_patterns:
            lines.append("")
            lines.append("【全局战术模式】")
            for pattern in self.global_patterns:
                lines.append(f"  - {pattern.note}")
        
        if self.retrieval_info and self.retrieval_info.tags:
            lines.append("")
            lines.append("【检索标签】")
            lines.append(f"  {', '.join(self.retrieval_info.tags)}")
        
        return {
            "analysis_text": "\n".join(lines),
            "retrieval_tags": self.retrieval_info.tags if self.retrieval_info else [],
            "retrieval_hints": self.retrieval_info.query_hints if self.retrieval_info else []
        }
    
    def _piece_to_text(self, piece: StandardizedPiece) -> str:
        parts = []
        
        if piece.tactical_patterns:
            parts.append(f"【{piece.piece_name}】@({piece.position[0]},{piece.position[1]})")
            parts.append(f"  战术: {', '.join(piece.tactical_patterns)}")
        elif piece.constraints:
            parts.append(f"【{piece.piece_name}】@({piece.position[0]},{piece.position[1]})")
            for c in piece.constraints[:2]:
                parts.append(f"  受限: {c.note}")
        elif piece.attacks:
            parts.append(f"【{piece.piece_name}】@({piece.position[0]},{piece.position[1]})")
            parts.append(f"  可攻击: {', '.join(piece.attacks[:3])}")
        
        if piece.geometric_tags:
            geo = [t for t in piece.geometric_tags if t in ['cross_river', 'is_hanging', 'can_check']]
            if geo:
                if not parts:
                    parts.append(f"【{piece.piece_name}】@({piece.position[0]},{piece.position[1]})")
                parts.append(f"  状态: {', '.join(geo)}")
        
        return "\n".join(parts) if parts else ""
    
    def to_dict(self) -> dict:
        return {
            "analysis_structured": self.to_structured(),
            "analysis_text": self.to_text()
        }


def extract_retrieval_tags(analysis: StandardizedPositionAnalysis) -> RetrievalInfo:
    tags = []
    query_hints = []
    
    has_hanging = False
    has_blocked_knight = False
    has_bottom_cannon = False
    
    for piece in analysis.pieces:
        side_cn = '红' if piece.side == 'red' else '黑'
        
        for pattern in piece.tactical_patterns:
            if pattern in ["卧槽马", "挂角马", "闷宫", "双将"]:
                tag = f"{side_cn}方{pattern}"
                tags.append(tag)
                query_hints.append(f"象棋 {pattern} 杀法")
        
        for constraint in piece.constraints:
            if constraint.kind == "horse_leg_blocked":
                has_blocked_knight = True
        
        if 'bottom_cannon' in piece.positional_tags:
            has_bottom_cannon = True
        
        if 'is_hanging' in piece.geometric_tags:
            if piece.material_value >= 4:
                has_hanging = True
    
    if has_blocked_knight:
        tags.append("马腿受堵")
        query_hints.append("象棋 马腿受阻 处理方法")
    
    if has_bottom_cannon:
        tags.append("沉底炮")
        query_hints.append("象棋 沉底炮 杀法")
    
    if has_hanging:
        tags.append("存在无根子")
        query_hints.append("象棋 无根子 防守")
    
    for pattern in analysis.global_patterns:
        if pattern.pattern_type == "check_threat":
            tags.append("存在将军威胁")
        elif pattern.pattern_type == "duijiang":
            tags.append("对将局面")
            query_hints.append("象棋 对将 处理")
    
    if analysis.summary and analysis.summary.is_check:
        tags.append("被将军")
    
    tags = list(dict.fromkeys(tags))
    query_hints = list(dict.fromkeys(query_hints))
    
    return RetrievalInfo(tags=tags[:6], query_hints=query_hints[:3])
