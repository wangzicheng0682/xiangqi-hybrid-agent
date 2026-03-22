"""
增强版棋子状态属性系统

为每个棋子输出完整的可走位置详细信息：
- 棋子编号系统（R1, R2, N1, N2...）
- 每个可走位置的详细分析
- 战术组合检测
- 兑子分析
- 线路分析

研发原则：规则优先，100%准确
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
import json


class PieceType(Enum):
    KING = "k"
    ADVISOR = "a"
    ELEPHANT = "b"
    ROOK = "r"
    CANNON = "c"
    KNIGHT = "n"
    PAWN = "p"


PIECE_VALUES = {
    'K': 0, 'k': 0,
    'R': 9, 'r': 9,
    'C': 4.5, 'c': 4.5,
    'N': 4, 'n': 4,
    'B': 2, 'b': 2,
    'A': 2, 'a': 2,
    'P': 1, 'p': 1,
}

PIECE_NAMES = {
    'K': '帅', 'k': '将',
    'A': '仕', 'a': '士',
    'B': '相', 'b': '象',
    'R': '车', 'r': '车',
    'C': '炮', 'c': '炮',
    'N': '马', 'n': '马',
    'P': '兵', 'p': '卒',
}


@dataclass
class MoveDetail:
    direction: str
    target_position: Tuple[int, int]
    is_valid: bool
    target_piece: Optional[str] = None
    target_is_enemy: Optional[bool] = None
    can_move: bool = False
    can_capture: bool = False
    capture_value: float = 0.0
    leg_blocked: bool = False
    leg_block_piece: Optional[str] = None
    leg_block_position: Optional[Tuple[int, int]] = None
    wing_blocked: bool = False
    wing_block_piece: Optional[str] = None
    wing_block_position: Optional[Tuple[int, int]] = None
    is_juocao: bool = False
    is_guajiao: bool = False
    is_fishing: bool = False
    can_check: bool = False
    check_target: Optional[str] = None
    can_fork: bool = False
    fork_targets: List[str] = field(default_factory=list)
    mutual_gaze: bool = False
    gazed_by: Optional[str] = None
    is_rib: bool = False
    is_press_elephant: bool = False
    is_river: bool = False
    is_bottom: bool = False
    has_rack: bool = False
    rack_piece: Optional[str] = None
    rack_position: Optional[Tuple[int, int]] = None
    in_palace: bool = False
    is_past_river: bool = False
    is_high_pawn: bool = False
    is_rib_pawn: bool = False
    line_pieces: List[str] = field(default_factory=list)
    description: str = ""
    
    def to_dict(self) -> dict:
        return {
            "direction": self.direction,
            "target_position": f"({self.target_position[0]}, {self.target_position[1]})" if self.target_position else None,
            "is_valid": self.is_valid,
            "target_piece": self.target_piece,
            "target_is_enemy": self.target_is_enemy,
            "can_move": self.can_move,
            "can_capture": self.can_capture,
            "capture_value": self.capture_value,
            "leg_blocked": self.leg_blocked,
            "leg_block_piece": self.leg_block_piece,
            "leg_block_position": f"({self.leg_block_position[0]}, {self.leg_block_position[1]})" if self.leg_block_position else None,
            "wing_blocked": self.wing_blocked,
            "wing_block_piece": self.wing_block_piece,
            "wing_block_position": f"({self.wing_block_position[0]}, {self.wing_block_position[1]})" if self.wing_block_position else None,
            "is_juocao": self.is_juocao,
            "is_guajiao": self.is_guajiao,
            "is_fishing": self.is_fishing,
            "can_check": self.can_check,
            "check_target": self.check_target,
            "can_fork": self.can_fork,
            "fork_targets": self.fork_targets,
            "mutual_gaze": self.mutual_gaze,
            "gazed_by": self.gazed_by,
            "is_rib": self.is_rib,
            "is_press_elephant": self.is_press_elephant,
            "is_river": self.is_river,
            "is_bottom": self.is_bottom,
            "has_rack": self.has_rack,
            "rack_piece": self.rack_piece,
            "rack_position": f"({self.rack_position[0]}, {self.rack_position[1]})" if self.rack_position else None,
            "in_palace": self.in_palace,
            "is_past_river": self.is_past_river,
            "is_high_pawn": self.is_high_pawn,
            "is_rib_pawn": self.is_rib_pawn,
            "line_pieces": self.line_pieces,
            "description": self.description
        }


@dataclass
class PieceState:
    piece_id: str
    piece_type: str
    piece_name: str
    is_red: bool
    is_alive: bool
    row: int
    col: int
    position: str
    
    legal_moves: List[Tuple[int, int]] = field(default_factory=list)
    legal_move_count: int = 0
    attack_targets: List[Tuple[int, int]] = field(default_factory=list)
    attack_target_count: int = 0
    
    move_details: List[MoveDetail] = field(default_factory=list)
    
    attacked_by: List[str] = field(default_factory=list)
    defended_by: List[str] = field(default_factory=list)
    protects: List[str] = field(default_factory=list)
    attacks: List[str] = field(default_factory=list)
    
    is_hanging: bool = False
    is_defended: bool = False
    can_fork: bool = False
    fork_targets: List[str] = field(default_factory=list)
    is_pinned: bool = False
    pin_by: Optional[str] = None
    can_check: bool = False
    is_checking: bool = False
    
    on_river: bool = False
    in_palace: bool = False
    on_center_file: bool = False
    on_rib_file: bool = False
    
    material_value: float = 0.0
    activity: int = 0
    mobility: int = 0
    
    tactical_combinations: List[str] = field(default_factory=list)
    line_control: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "piece_id": self.piece_id,
            "piece_type": self.piece_type,
            "piece_name": self.piece_name,
            "is_red": self.is_red,
            "is_alive": self.is_alive,
            "row": self.row,
            "col": self.col,
            "position": self.position,
            "legal_moves": [f"({r},{c})" for r, c in self.legal_moves],
            "legal_move_count": self.legal_move_count,
            "attack_targets": [f"({r},{c})" for r, c in self.attack_targets],
            "attack_target_count": self.attack_target_count,
            "move_details": [m.to_dict() for m in self.move_details],
            "attacked_by": self.attacked_by,
            "defended_by": self.defended_by,
            "protects": self.protects,
            "attacks": self.attacks,
            "is_hanging": self.is_hanging,
            "is_defended": self.is_defended,
            "can_fork": self.can_fork,
            "fork_targets": self.fork_targets,
            "is_pinned": self.is_pinned,
            "pin_by": self.pin_by,
            "can_check": self.can_check,
            "is_checking": self.is_checking,
            "on_river": self.on_river,
            "in_palace": self.in_palace,
            "on_center_file": self.on_center_file,
            "on_rib_file": self.on_rib_file,
            "material_value": self.material_value,
            "activity": self.activity,
            "mobility": self.mobility,
            "tactical_combinations": self.tactical_combinations,
            "line_control": self.line_control
        }


class EnhancedPieceAnalyzer:
    """增强版棋子状态分析器"""
    
    def __init__(self):
        self.board: List[List[str]] = []
        self.pieces: List[PieceState] = []
        self.piece_id_map: Dict[Tuple[int, int], str] = {}
        self.king_positions: Dict[bool, Tuple[int, int]] = {}
        
    def analyze(self, fen: str) -> Dict[str, Any]:
        self._parse_fen(fen)
        self._assign_piece_ids()
        self._analyze_all_pieces()
        self._detect_tactical_combinations()
        self._detect_line_control()
        
        return {
            "fen": fen,
            "side_to_move": self.side_to_move,
            "pieces": [p.to_dict() for p in self.pieces],
            "summary": self._generate_summary()
        }
    
    def _parse_fen(self, fen: str):
        parts = fen.split()
        board_str = parts[0]
        self.side_to_move = 'red' if (parts[1] if len(parts) > 1 else 'w') == 'w' else 'black'
        
        self.board = []
        for row_str in board_str.split('/'):
            row = []
            for c in row_str:
                if c.isdigit():
                    row.extend([''] * int(c))
                else:
                    row.append(c)
            self.board.append(row)
    
    def _assign_piece_ids(self):
        piece_counters: Dict[str, int] = {}
        self.pieces = []
        self.piece_id_map = {}
        
        for row in range(10):
            for col in range(9):
                piece = self.board[row][col]
                if piece:
                    piece_type = piece.upper()
                    is_red = piece.isupper()
                    
                    key = piece_type if is_red else piece_type.lower()
                    piece_counters[key] = piece_counters.get(key, 0) + 1
                    index = piece_counters[key]
                    
                    if is_red:
                        piece_id = f"{piece_type}{index}"
                    else:
                        piece_id = f"{piece_type.lower()}{index}"
                    
                    piece_name = f"{'红' if is_red else '黑'}{PIECE_NAMES.get(piece, piece)}{index}"
                    
                    state = PieceState(
                        piece_id=piece_id,
                        piece_type=piece.lower(),
                        piece_name=piece_name,
                        is_red=is_red,
                        is_alive=True,
                        row=row,
                        col=col,
                        position=f"({row},{col})",
                        material_value=PIECE_VALUES.get(piece, 0)
                    )
                    
                    self.pieces.append(state)
                    self.piece_id_map[(row, col)] = piece_id
                    
                    if piece.lower() == 'k':
                        self.king_positions[is_red] = (row, col)
    
    def _analyze_all_pieces(self):
        for piece in self.pieces:
            self._analyze_piece(piece)
        
        self._analyze_protections()
        self._analyze_hanging()
    
    def _analyze_piece(self, piece: PieceState):
        piece_type = piece.piece_type.lower()
        
        piece.on_river = (piece.row == 4 or piece.row == 5)
        piece.in_palace = self._is_in_palace(piece.row, piece.col, piece.is_red)
        piece.on_center_file = (piece.col == 4)
        piece.on_rib_file = (piece.col == 3 or piece.col == 5)
        
        if piece_type == 'r':
            self._analyze_rook(piece)
        elif piece_type == 'n':
            self._analyze_knight(piece)
        elif piece_type == 'c':
            self._analyze_cannon(piece)
        elif piece_type == 'b':
            self._analyze_elephant(piece)
        elif piece_type == 'a':
            self._analyze_advisor(piece)
        elif piece_type == 'k':
            self._analyze_king(piece)
        elif piece_type == 'p':
            self._analyze_pawn(piece)
        
        piece.legal_move_count = len(piece.legal_moves)
        piece.attack_target_count = len(piece.attack_targets)
        piece.mobility = min(piece.legal_move_count, 10)
        piece.activity = min(piece.attack_target_count * 2 + piece.legal_move_count, 10)
    
    def _analyze_rook(self, piece: PieceState):
        directions = [
            ("向前", -1, 0),
            ("向后", 1, 0),
            ("向左", 0, -1),
            ("向右", 0, 1)
        ]
        
        for dir_name, dr, dc in directions:
            move_detail = self._analyze_rook_direction(piece, dir_name, dr, dc)
            piece.move_details.append(move_detail)
            
            if move_detail.is_valid and move_detail.can_move:
                piece.legal_moves.append(move_detail.target_position)
            if move_detail.can_capture:
                piece.attack_targets.append(move_detail.target_position)
    
    def _analyze_rook_direction(self, piece: PieceState, dir_name: str, dr: int, dc: int) -> MoveDetail:
        row, col = piece.row, piece.col
        is_red = piece.is_red
        
        line_pieces = []
        target_position = None
        target_piece = None
        target_is_enemy = None
        can_capture = False
        capture_value = 0.0
        
        nr, nc = row + dr, col + dc
        while 0 <= nr < 10 and 0 <= nc < 9:
            cell = self.board[nr][nc]
            if cell:
                line_pieces.append(self.piece_id_map.get((nr, nc), cell))
                if not target_piece:
                    target_position = (nr, nc)
                    target_piece = self.piece_id_map.get((nr, nc), cell)
                    target_is_enemy = (cell.isupper() != is_red)
                    if target_is_enemy:
                        can_capture = True
                        capture_value = PIECE_VALUES.get(cell, 0)
            nr += dr
            nc += dc
        
        is_rib = (target_position and target_position[1] in [3, 5]) if target_position else False
        is_river = (target_position and target_position[0] in [4, 5]) if target_position else False
        
        enemy_king_pos = self.king_positions.get(not is_red)
        can_check = False
        check_target = None
        if enemy_king_pos and target_position:
            if target_position[0] == enemy_king_pos[0] or target_position[1] == enemy_king_pos[1]:
                can_check = True
                check_target = self.piece_id_map.get(enemy_king_pos, "将")
        
        description = f"{dir_name}方向"
        if target_piece:
            if target_is_enemy:
                description += f"，可打{target_piece}"
            else:
                description += f"，被{target_piece}阻挡"
        else:
            description += "，畅通"
        
        return MoveDetail(
            direction=dir_name,
            target_position=target_position,
            is_valid=target_position is not None,
            target_piece=target_piece,
            target_is_enemy=target_is_enemy,
            can_move=target_position is not None and (target_is_enemy or target_piece is None),
            can_capture=can_capture,
            capture_value=capture_value,
            is_rib=is_rib,
            is_river=is_river,
            can_check=can_check,
            check_target=check_target,
            line_pieces=line_pieces,
            description=description
        )
    
    def _analyze_knight(self, piece: PieceState):
        knight_moves = [
            ("左上", -2, -1, -1, 0),
            ("右上", -2, 1, -1, 0),
            ("左下", 2, -1, 1, 0),
            ("右下", 2, 1, 1, 0),
            ("上左", -1, -2, 0, -1),
            ("上右", -1, 2, 0, 1),
            ("下左", 1, -2, 0, -1),
            ("下右", 1, 2, 0, 1),
        ]
        
        for dir_name, dr, dc, br, bc in knight_moves:
            move_detail = self._analyze_knight_direction(piece, dir_name, dr, dc, br, bc)
            piece.move_details.append(move_detail)
            
            if move_detail.is_valid and move_detail.can_move and not move_detail.leg_blocked:
                piece.legal_moves.append(move_detail.target_position)
            if move_detail.can_capture and not move_detail.leg_blocked:
                piece.attack_targets.append(move_detail.target_position)
    
    def _analyze_knight_direction(self, piece: PieceState, dir_name: str, 
                                   dr: int, dc: int, br: int, bc: int) -> MoveDetail:
        row, col = piece.row, piece.col
        is_red = piece.is_red
        
        target_row, target_col = row + dr, col + dc
        leg_row, leg_col = row + br, col + bc
        
        is_valid = 0 <= target_row < 10 and 0 <= target_col < 9
        
        leg_blocked = False
        leg_block_piece = None
        leg_block_position = None
        
        if 0 <= leg_row < 10 and 0 <= leg_col < 9:
            leg_cell = self.board[leg_row][leg_col]
            if leg_cell:
                leg_blocked = True
                leg_block_piece = self.piece_id_map.get((leg_row, leg_col), leg_cell)
                leg_block_position = (leg_row, leg_col)
        
        target_piece = None
        target_is_enemy = None
        can_capture = False
        capture_value = 0.0
        can_move = False
        
        if is_valid:
            target_cell = self.board[target_row][target_col]
            if target_cell:
                target_piece = self.piece_id_map.get((target_row, target_col), target_cell)
                target_is_enemy = (target_cell.isupper() != is_red)
                if target_is_enemy:
                    can_capture = True
                    capture_value = PIECE_VALUES.get(target_cell, 0)
            else:
                can_move = True
        
        enemy_king_pos = self.king_positions.get(not is_red)
        is_juocao = False
        is_guajiao = False
        can_check = False
        check_target = None
        
        if is_valid and enemy_king_pos and not leg_blocked:
            kr, kc = enemy_king_pos
            if abs(target_row - kr) <= 2 and abs(target_col - kc) <= 2:
                if self._is_in_palace(target_row, target_col, not is_red):
                    is_juocao = True
                    can_check = True
                    check_target = self.piece_id_map.get(enemy_king_pos, "将")
        
        description = f"{dir_name}方向"
        if leg_blocked:
            description += f"，马腿被{leg_block_piece}别住"
        elif is_valid:
            if target_piece:
                if target_is_enemy:
                    description += f"，可打{target_piece}"
                else:
                    description += f"，被己方{target_piece}占据"
            else:
                description += "，可落子"
        else:
            description += "，出界"
        
        return MoveDetail(
            direction=dir_name,
            target_position=(target_row, target_col) if is_valid else None,
            is_valid=is_valid,
            target_piece=target_piece,
            target_is_enemy=target_is_enemy,
            can_move=can_move,
            can_capture=can_capture,
            capture_value=capture_value,
            leg_blocked=leg_blocked,
            leg_block_piece=leg_block_piece,
            leg_block_position=leg_block_position,
            is_juocao=is_juocao,
            is_guajiao=is_guajiao,
            can_check=can_check,
            check_target=check_target,
            description=description
        )
    
    def _analyze_cannon(self, piece: PieceState):
        directions = [
            ("向前", -1, 0),
            ("向后", 1, 0),
            ("向左", 0, -1),
            ("向右", 0, 1)
        ]
        
        for dir_name, dr, dc in directions:
            move_detail = self._analyze_cannon_direction(piece, dir_name, dr, dc)
            piece.move_details.append(move_detail)
            
            if move_detail.is_valid and move_detail.can_move:
                piece.legal_moves.append(move_detail.target_position)
            if move_detail.can_capture:
                piece.attack_targets.append(move_detail.target_position)
    
    def _analyze_cannon_direction(self, piece: PieceState, dir_name: str, dr: int, dc: int) -> MoveDetail:
        row, col = piece.row, piece.col
        is_red = piece.is_red
        
        line_pieces = []
        target_position = None
        target_piece = None
        target_is_enemy = None
        can_capture = False
        capture_value = 0.0
        can_move = False
        has_rack = False
        rack_piece = None
        rack_position = None
        
        nr, nc = row + dr, col + dc
        found_rack = False
        
        while 0 <= nr < 10 and 0 <= nc < 9:
            cell = self.board[nr][nc]
            if cell:
                piece_id = self.piece_id_map.get((nr, nc), cell)
                line_pieces.append(piece_id)
                
                if not found_rack:
                    found_rack = True
                    has_rack = True
                    rack_piece = piece_id
                    rack_position = (nr, nc)
                else:
                    target_position = (nr, nc)
                    target_piece = piece_id
                    target_is_enemy = (cell.isupper() != is_red)
                    if target_is_enemy:
                        can_capture = True
                        capture_value = PIECE_VALUES.get(cell, 0)
                    break
            else:
                if not found_rack:
                    pass
            
            nr += dr
            nc += dc
        
        nr, nc = row + dr, col + dc
        while 0 <= nr < 10 and 0 <= nc < 9:
            cell = self.board[nr][nc]
            if cell:
                break
            if not found_rack:
                target_position = (nr, nc)
                can_move = True
            nr += dr
            nc += dc
        
        is_river = (target_position and target_position[0] in [4, 5]) if target_position else False
        is_bottom = (target_position and target_position[0] in [0, 9]) if target_position else False
        
        enemy_king_pos = self.king_positions.get(not is_red)
        can_check = False
        check_target = None
        if enemy_king_pos and can_capture:
            can_check = True
            check_target = self.piece_id_map.get(enemy_king_pos, "将")
        
        description = f"{dir_name}方向"
        if has_rack:
            description += f"，炮架{rack_piece}"
            if can_capture:
                description += f"，可打{target_piece}"
        else:
            description += "，无炮架"
            if can_move:
                description += "，可移动"
        
        return MoveDetail(
            direction=dir_name,
            target_position=target_position,
            is_valid=target_position is not None,
            target_piece=target_piece,
            target_is_enemy=target_is_enemy,
            can_move=can_move,
            can_capture=can_capture,
            capture_value=capture_value,
            has_rack=has_rack,
            rack_piece=rack_piece,
            rack_position=rack_position,
            is_river=is_river,
            is_bottom=is_bottom,
            can_check=can_check,
            check_target=check_target,
            line_pieces=line_pieces,
            description=description
        )
    
    def _analyze_elephant(self, piece: PieceState):
        elephant_moves = [
            ("左上", -2, -2, -1, -1),
            ("右上", -2, 2, -1, 1),
            ("左下", 2, -2, 1, -1),
            ("右下", 2, 2, 1, 1),
        ]
        
        for dir_name, dr, dc, wr, wc in elephant_moves:
            move_detail = self._analyze_elephant_direction(piece, dir_name, dr, dc, wr, wc)
            piece.move_details.append(move_detail)
            
            if move_detail.is_valid and move_detail.can_move and not move_detail.wing_blocked:
                piece.legal_moves.append(move_detail.target_position)
    
    def _analyze_elephant_direction(self, piece: PieceState, dir_name: str,
                                     dr: int, dc: int, wr: int, wc: int) -> MoveDetail:
        row, col = piece.row, piece.col
        is_red = piece.is_red
        
        target_row, target_col = row + dr, col + dc
        wing_row, wing_col = row + wr, col + wc
        
        is_valid = 0 <= target_row < 10 and 0 <= target_col < 9
        
        if is_red:
            if target_row < 5:
                is_valid = False
        else:
            if target_row > 4:
                is_valid = False
        
        wing_blocked = False
        wing_block_piece = None
        wing_block_position = None
        
        if 0 <= wing_row < 10 and 0 <= wing_col < 9:
            wing_cell = self.board[wing_row][wing_col]
            if wing_cell:
                wing_blocked = True
                wing_block_piece = self.piece_id_map.get((wing_row, wing_col), wing_cell)
                wing_block_position = (wing_row, wing_col)
        
        target_piece = None
        target_is_enemy = None
        can_move = False
        
        if is_valid:
            target_cell = self.board[target_row][target_col]
            if target_cell:
                target_piece = self.piece_id_map.get((target_row, target_col), target_cell)
                target_is_enemy = (target_cell.isupper() != is_red)
            else:
                can_move = True
        
        description = f"{dir_name}方向"
        if wing_blocked:
            description += f"，象眼被{wing_block_piece}塞住"
        elif is_valid:
            if target_piece:
                if target_is_enemy:
                    description += f"，被{target_piece}占据"
                else:
                    description += f"，被己方{target_piece}占据"
            else:
                description += "，可落子"
        else:
            description += "，过河"
        
        return MoveDetail(
            direction=dir_name,
            target_position=(target_row, target_col) if is_valid else None,
            is_valid=is_valid,
            target_piece=target_piece,
            target_is_enemy=target_is_enemy,
            can_move=can_move,
            wing_blocked=wing_blocked,
            wing_block_piece=wing_block_piece,
            wing_block_position=wing_block_position,
            description=description
        )
    
    def _analyze_advisor(self, piece: PieceState):
        advisor_moves = [
            ("左上", -1, -1),
            ("右上", -1, 1),
            ("左下", 1, -1),
            ("右下", 1, 1),
        ]
        
        for dir_name, dr, dc in advisor_moves:
            move_detail = self._analyze_advisor_direction(piece, dir_name, dr, dc)
            piece.move_details.append(move_detail)
            
            if move_detail.is_valid and move_detail.can_move:
                piece.legal_moves.append(move_detail.target_position)
            if move_detail.can_capture:
                piece.attack_targets.append(move_detail.target_position)
    
    def _analyze_advisor_direction(self, piece: PieceState, dir_name: str, dr: int, dc: int) -> MoveDetail:
        row, col = piece.row, piece.col
        is_red = piece.is_red
        
        target_row, target_col = row + dr, col + dc
        
        is_valid = self._is_in_palace(target_row, target_col, is_red)
        
        target_piece = None
        target_is_enemy = None
        can_capture = False
        capture_value = 0.0
        can_move = False
        
        if is_valid:
            target_cell = self.board[target_row][target_col]
            if target_cell:
                target_piece = self.piece_id_map.get((target_row, target_col), target_cell)
                target_is_enemy = (target_cell.isupper() != is_red)
                if target_is_enemy:
                    can_capture = True
                    capture_value = PIECE_VALUES.get(target_cell, 0)
            else:
                can_move = True
        
        description = f"{dir_name}方向"
        if is_valid:
            if target_piece:
                if target_is_enemy:
                    description += f"，可打{target_piece}"
                else:
                    description += f"，被己方{target_piece}占据"
            else:
                description += "，可落子"
        else:
            description += "，出九宫"
        
        return MoveDetail(
            direction=dir_name,
            target_position=(target_row, target_col) if is_valid else None,
            is_valid=is_valid,
            target_piece=target_piece,
            target_is_enemy=target_is_enemy,
            can_move=can_move,
            can_capture=can_capture,
            capture_value=capture_value,
            in_palace=is_valid,
            description=description
        )
    
    def _analyze_king(self, piece: PieceState):
        king_moves = [
            ("向前", -1 if piece.is_red else 1, 0),
            ("向后", 1 if piece.is_red else -1, 0),
            ("向左", 0, -1),
            ("向右", 0, 1),
        ]
        
        for dir_name, dr, dc in king_moves:
            move_detail = self._analyze_king_direction(piece, dir_name, dr, dc)
            piece.move_details.append(move_detail)
            
            if move_detail.is_valid and move_detail.can_move:
                piece.legal_moves.append(move_detail.target_position)
            if move_detail.can_capture:
                piece.attack_targets.append(move_detail.target_position)
    
    def _analyze_king_direction(self, piece: PieceState, dir_name: str, dr: int, dc: int) -> MoveDetail:
        row, col = piece.row, piece.col
        is_red = piece.is_red
        
        target_row, target_col = row + dr, col + dc
        
        is_valid = self._is_in_palace(target_row, target_col, is_red)
        
        target_piece = None
        target_is_enemy = None
        can_capture = False
        capture_value = 0.0
        can_move = False
        
        if is_valid:
            target_cell = self.board[target_row][target_col]
            if target_cell:
                target_piece = self.piece_id_map.get((target_row, target_col), target_cell)
                target_is_enemy = (target_cell.isupper() != is_red)
                if target_is_enemy:
                    can_capture = True
                    capture_value = PIECE_VALUES.get(target_cell, 0)
            else:
                can_move = True
        
        description = f"{dir_name}方向"
        if is_valid:
            if target_piece:
                if target_is_enemy:
                    description += f"，可吃{target_piece}"
                else:
                    description += f"，被己方{target_piece}占据"
            else:
                description += "，可移动"
        else:
            description += "，出九宫"
        
        return MoveDetail(
            direction=dir_name,
            target_position=(target_row, target_col) if is_valid else None,
            is_valid=is_valid,
            target_piece=target_piece,
            target_is_enemy=target_is_enemy,
            can_move=can_move,
            can_capture=can_capture,
            capture_value=capture_value,
            in_palace=is_valid,
            description=description
        )
    
    def _analyze_pawn(self, piece: PieceState):
        is_red = piece.is_red
        forward_dr = -1 if is_red else 1
        is_past_river = (is_red and piece.row <= 4) or (not is_red and piece.row >= 5)
        
        move_detail = self._analyze_pawn_forward(piece, forward_dr)
        piece.move_details.append(move_detail)
        
        if move_detail.is_valid and move_detail.can_move:
            piece.legal_moves.append(move_detail.target_position)
        if move_detail.can_capture:
            piece.attack_targets.append(move_detail.target_position)
        
        if is_past_river:
            for dir_name, dc in [("左移", -1), ("右移", 1)]:
                move_detail = self._analyze_pawn_lateral(piece, dir_name, dc)
                piece.move_details.append(move_detail)
                
                if move_detail.is_valid and move_detail.can_move:
                    piece.legal_moves.append(move_detail.target_position)
                if move_detail.can_capture:
                    piece.attack_targets.append(move_detail.target_position)
    
    def _analyze_pawn_forward(self, piece: PieceState, dr: int) -> MoveDetail:
        row, col = piece.row, piece.col
        is_red = piece.is_red
        
        target_row, target_col = row + dr, col
        
        is_valid = 0 <= target_row < 10
        
        target_piece = None
        target_is_enemy = None
        can_capture = False
        capture_value = 0.0
        can_move = False
        
        is_past_river = (is_red and target_row <= 4) or (not is_red and target_row >= 5)
        is_rib_pawn = (target_col in [3, 5])
        is_high_pawn = (is_red and target_row <= 3) or (not is_red and target_row >= 6)
        
        if is_valid:
            target_cell = self.board[target_row][target_col]
            if target_cell:
                target_piece = self.piece_id_map.get((target_row, target_col), target_cell)
                target_is_enemy = (target_cell.isupper() != is_red)
                if target_is_enemy:
                    can_capture = True
                    capture_value = PIECE_VALUES.get(target_cell, 0)
            else:
                can_move = True
        
        description = "前进"
        if is_valid:
            if target_piece:
                if target_is_enemy:
                    description += f"，可吃{target_piece}"
                else:
                    description += f"，被己方{target_piece}阻挡"
            else:
                description += "，可前进"
        else:
            description += "，到底"
        
        return MoveDetail(
            direction="前进",
            target_position=(target_row, target_col) if is_valid else None,
            is_valid=is_valid,
            target_piece=target_piece,
            target_is_enemy=target_is_enemy,
            can_move=can_move,
            can_capture=can_capture,
            capture_value=capture_value,
            is_past_river=is_past_river,
            is_rib_pawn=is_rib_pawn,
            is_high_pawn=is_high_pawn,
            description=description
        )
    
    def _analyze_pawn_lateral(self, piece: PieceState, dir_name: str, dc: int) -> MoveDetail:
        row, col = piece.row, piece.col
        is_red = piece.is_red
        
        target_row, target_col = row, col + dc
        
        is_valid = 0 <= target_col < 9
        
        target_piece = None
        target_is_enemy = None
        can_capture = False
        capture_value = 0.0
        can_move = False
        
        is_rib_pawn = (target_col in [3, 5])
        
        if is_valid:
            target_cell = self.board[target_row][target_col]
            if target_cell:
                target_piece = self.piece_id_map.get((target_row, target_col), target_cell)
                target_is_enemy = (target_cell.isupper() != is_red)
                if target_is_enemy:
                    can_capture = True
                    capture_value = PIECE_VALUES.get(target_cell, 0)
            else:
                can_move = True
        
        description = dir_name
        if is_valid:
            if target_piece:
                if target_is_enemy:
                    description += f"，可吃{target_piece}"
                else:
                    description += f"，被己方{target_piece}阻挡"
            else:
                description += "，可横走"
        else:
            description += "，到边"
        
        return MoveDetail(
            direction=dir_name,
            target_position=(target_row, target_col) if is_valid else None,
            is_valid=is_valid,
            target_piece=target_piece,
            target_is_enemy=target_is_enemy,
            can_move=can_move,
            can_capture=can_capture,
            capture_value=capture_value,
            is_past_river=True,
            is_rib_pawn=is_rib_pawn,
            description=description
        )
    
    def _analyze_protections(self):
        for piece in self.pieces:
            for move_detail in piece.move_details:
                if move_detail.target_piece and not move_detail.target_is_enemy:
                    piece.protects.append(move_detail.target_piece)
        
        for piece in self.pieces:
            for protector_id in piece.protects:
                for other in self.pieces:
                    if other.piece_id == protector_id:
                        other.defended_by.append(piece.piece_id)
    
    def _analyze_hanging(self):
        for piece in self.pieces:
            if piece.attacked_by and not piece.defended_by:
                piece.is_hanging = True
            if piece.defended_by:
                piece.is_defended = True
    
    def _detect_tactical_combinations(self):
        for piece in self.pieces:
            if piece.piece_type == 'n':
                for move in piece.move_details:
                    if move.is_juocao:
                        piece.tactical_combinations.append("卧槽马")
                    if move.is_guajiao:
                        piece.tactical_combinations.append("挂角马")
            
            if piece.piece_type == 'c':
                for move in piece.move_details:
                    if move.is_bottom:
                        piece.tactical_combinations.append("沉底炮")
                    if move.is_river:
                        piece.tactical_combinations.append("巡河炮")
    
    def _detect_line_control(self):
        for piece in self.pieces:
            if piece.piece_type == 'r':
                if piece.on_rib_file:
                    piece.line_control.append("占肋")
                if piece.on_center_file:
                    piece.line_control.append("中路")
    
    def _is_in_palace(self, row: int, col: int, is_red: bool) -> bool:
        if col < 3 or col > 5:
            return False
        if is_red:
            return 7 <= row <= 9
        else:
            return 0 <= row <= 2
    
    def _generate_summary(self) -> dict:
        red_pieces = [p for p in self.pieces if p.is_red]
        black_pieces = [p for p in self.pieces if not p.is_red]
        
        return {
            "red_piece_count": len(red_pieces),
            "black_piece_count": len(black_pieces),
            "red_material": sum(p.material_value for p in red_pieces),
            "black_material": sum(p.material_value for p in black_pieces),
            "total_moves": sum(p.legal_move_count for p in self.pieces),
            "total_attacks": sum(p.attack_target_count for p in self.pieces)
        }


def analyze_pieces(fen: str) -> Dict[str, Any]:
    """
    便捷函数：分析棋子状态
    
    Args:
        fen: FEN字符串
        
    Returns:
        增强版棋子状态信息
    """
    analyzer = EnhancedPieceAnalyzer()
    return analyzer.analyze(fen)


if __name__ == "__main__":
    test_fens = [
        "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1",
        "2baka3/9/2R6/p8/4PP3/3p5/9/4r4/4A4/3AK4 b - - 40 40",
    ]
    
    for i, fen in enumerate(test_fens, 1):
        print(f"\n{'='*80}")
        print(f"测试 {i}: {fen[:50]}...")
        print('='*80)
        
        result = analyze_pieces(fen)
        
        for piece in result['pieces'][:5]:
            print(f"\n【{piece['piece_name']}】@ {piece['position']}")
            print(f"  合法走法: {piece['legal_move_count']}个")
            print(f"  可攻击: {piece['attack_target_count']}个")
            
            for move in piece['move_details'][:3]:
                print(f"  - {move['direction']}: {move['description']}")
