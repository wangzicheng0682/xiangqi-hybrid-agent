"""
局面级分析器

实现全局分析：
- 将军检测
- 对将检测
- 被捉检测
- 子力受攻/受守计数
- 控制点分析
- 攻防关系

输出标准化JSON Schema
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Set
from core.semantic.position_analysis_schema import (
    StandardizedPositionAnalysis, StandardizedPiece, LegalMove, Constraint,
    Mobility, GlobalPattern, PressureMap, PositionSummary, RetrievalInfo,
    extract_retrieval_tags, PIECE_TYPE_NAMES, PIECE_NAMES_CN, PIECE_VALUES
)


class PositionAnalyzer:
    """局面级分析器"""
    
    def __init__(self):
        self.board: List[List[str]] = []
        self.pieces: List[StandardizedPiece] = []
        self.piece_id_map: Dict[Tuple[int, int], str] = {}
        self.king_positions: Dict[bool, Tuple[int, int]] = {}
        self.side_to_move: str = 'red'
        self.control_map: Dict[Tuple[int, int], Set[str]] = {}
        
    def analyze(self, fen: str) -> StandardizedPositionAnalysis:
        self._parse_fen(fen)
        self._assign_piece_ids()
        self._analyze_all_pieces()
        self._build_control_map()
        self._analyze_attacks_and_defenses()
        self._detect_global_patterns()
        self._generate_summary()
        
        analysis = StandardizedPositionAnalysis(
            board_fen=fen,
            turn=self.side_to_move,
            pieces=self.pieces,
            global_patterns=self.global_patterns,
            pressure_map=self.pressure_map,
            summary=self.summary
        )
        
        analysis.retrieval_info = extract_retrieval_tags(analysis)
        
        return analysis
    
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
            while len(row) < 9:
                row.append('')
            self.board.append(row)
    
    def _assign_piece_ids(self):
        piece_counters: Dict[str, int] = {}
        self.pieces = []
        self.piece_id_map = {}
        
        for row in range(10):
            for col in range(9):
                piece = self.board[row][col]
                if piece:
                    is_red = piece.isupper()
                    piece_type = piece.lower()
                    
                    key = piece_type if is_red else piece_type.lower()
                    piece_counters[key] = piece_counters.get(key, 0) + 1
                    index = piece_counters[key]
                    
                    if is_red:
                        piece_id = f"{piece_type.upper()}{index}"
                    else:
                        piece_id = f"{piece_type}{index}"
                    
                    piece_name = f"{'红' if is_red else '黑'}{PIECE_NAMES_CN.get(piece, piece)}{index}"
                    
                    std_piece = StandardizedPiece(
                        piece_id=piece_id,
                        side='red' if is_red else 'black',
                        piece_type=PIECE_TYPE_NAMES.get(piece_type, piece_type),
                        piece_name=piece_name,
                        position=[row, col],
                        material_value=PIECE_VALUES.get(piece, 0)
                    )
                    
                    self.pieces.append(std_piece)
                    self.piece_id_map[(row, col)] = piece_id
                    
                    if piece_type == 'k':
                        self.king_positions[is_red] = (row, col)
    
    def _analyze_all_pieces(self):
        for piece in self.pieces:
            self._analyze_piece(piece)
    
    def _analyze_piece(self, piece: StandardizedPiece):
        row, col = piece.position
        piece_type = piece.piece_type
        is_red = piece.side == 'red'
        
        legal_moves = []
        constraints = []
        attacks = []
        geometric_tags = []
        positional_tags = []
        tactical_patterns = []
        
        if piece_type == 'rook':
            legal_moves, constraints, attacks, positional_tags = self._analyze_rook(piece)
        elif piece_type == 'knight':
            legal_moves, constraints, attacks, tactical_patterns = self._analyze_knight(piece)
        elif piece_type == 'cannon':
            legal_moves, constraints, attacks, positional_tags = self._analyze_cannon(piece)
        elif piece_type == 'elephant':
            legal_moves, constraints = self._analyze_elephant(piece)
        elif piece_type == 'advisor':
            legal_moves, attacks = self._analyze_advisor(piece)
        elif piece_type == 'king':
            legal_moves, attacks = self._analyze_king(piece)
        elif piece_type == 'pawn':
            legal_moves, attacks, positional_tags = self._analyze_pawn(piece)
        
        piece.legal_moves = legal_moves
        piece.constraints = constraints
        piece.attacks = attacks
        piece.geometric_tags = geometric_tags
        piece.positional_tags = positional_tags
        piece.tactical_patterns = tactical_patterns
        
        self._add_geometric_tags(piece)
        self._add_positional_tags(piece)
        
        piece.mobility = Mobility(
            legal_count=len(legal_moves),
            attack_count=len(attacks),
            activity_score=min(len(attacks) * 2 + len(legal_moves), 10)
        )
    
    def _analyze_rook(self, piece: StandardizedPiece) -> Tuple:
        row, col = piece.position
        is_red = piece.side == 'red'
        legal_moves = []
        constraints = []
        attacks = []
        positional_tags = []
        
        directions = [
            ("forward", -1 if is_red else 1, 0),
            ("backward", 1 if is_red else -1, 0),
            ("left", 0, -1),
            ("right", 0, 1)
        ]
        
        for dir_name, dr, dc in directions:
            nr, nc = row + dr, col + dc
            while 0 <= nr < 10 and 0 <= nc < 9:
                target_cell = self.board[nr][nc]
                if target_cell:
                    target_is_enemy = target_cell.isupper() != is_red
                    target_id = self.piece_id_map.get((nr, nc), target_cell)
                    
                    if target_is_enemy:
                        legal_moves.append(LegalMove(
                            to=[nr, nc],
                            move_type="capture",
                            status="legal",
                            direction=dir_name,
                            note=f"可吃{target_id}",
                            capture_target=target_id,
                            capture_value=PIECE_VALUES.get(target_cell, 0)
                        ))
                        attacks.append(target_id)
                    else:
                        constraints.append(Constraint(
                            kind="blocked",
                            target=[nr, nc],
                            note=f"被己方{target_id}阻挡",
                            block_piece=target_id
                        ))
                    break
                else:
                    legal_moves.append(LegalMove(
                        to=[nr, nc],
                        move_type="move",
                        status="legal",
                        direction=dir_name,
                        note="可移动"
                    ))
                nr += dr
                nc += dc
        
        if row in [4, 5]:
            positional_tags.append("riverbank_rook")
        if col == 4:
            positional_tags.append("center_file")
        if col in [3, 5]:
            positional_tags.append("rib_file")
        
        return legal_moves, constraints, attacks, positional_tags
    
    def _analyze_knight(self, piece: StandardizedPiece) -> Tuple:
        row, col = piece.position
        is_red = piece.side == 'red'
        legal_moves = []
        constraints = []
        attacks = []
        tactical_patterns = []
        
        knight_moves = [
            ("left_up", -2, -1, -1, 0),
            ("right_up", -2, 1, -1, 0),
            ("left_down", 2, -1, 1, 0),
            ("right_down", 2, 1, 1, 0),
            ("up_left", -1, -2, 0, -1),
            ("up_right", -1, 2, 0, 1),
            ("down_left", 1, -2, 0, -1),
            ("down_right", 1, 2, 0, 1),
        ]
        
        enemy_king_pos = self.king_positions.get(not is_red)
        
        for dir_name, dr, dc, br, bc in knight_moves:
            target_row, target_col = row + dr, col + dc
            leg_row, leg_col = row + br, col + bc
            
            if not (0 <= target_row < 10 and 0 <= target_col < 9):
                continue
            
            leg_blocked = False
            leg_block_piece = None
            if 0 <= leg_row < 10 and 0 <= leg_col < 9:
                leg_cell = self.board[leg_row][leg_col]
                if leg_cell:
                    leg_is_enemy = leg_cell.isupper() != is_red
                    if leg_is_enemy:
                        leg_blocked = True
                        leg_block_piece = self.piece_id_map.get((leg_row, leg_col), leg_cell)
                        constraints.append(Constraint(
                            kind="horse_leg_blocked",
                            target=[leg_row, leg_col],
                            note=f"马腿被敌方{leg_block_piece}别住",
                            block_piece=leg_block_piece
                        ))
            
            if leg_blocked:
                continue
            
            target_cell = self.board[target_row][target_col]
            if target_cell:
                target_is_enemy = target_cell.isupper() != is_red
                target_id = self.piece_id_map.get((target_row, target_col), target_cell)
                
                if target_is_enemy:
                    legal_moves.append(LegalMove(
                        to=[target_row, target_col],
                        move_type="capture",
                        status="legal",
                        direction=dir_name,
                        note=f"可吃{target_id}",
                        capture_target=target_id,
                        capture_value=PIECE_VALUES.get(target_cell, 0)
                    ))
                    attacks.append(target_id)
            else:
                legal_moves.append(LegalMove(
                    to=[target_row, target_col],
                    move_type="move",
                    status="legal",
                    direction=dir_name,
                    note="可落子"
                ))
            
            if enemy_king_pos and not leg_blocked:
                kr, kc = enemy_king_pos
                if self._is_in_palace(target_row, target_col, not is_red):
                    if abs(target_row - kr) <= 1 and abs(target_col - kc) <= 1:
                        tactical_patterns.append("卧槽马")
        
        return legal_moves, constraints, attacks, tactical_patterns
    
    def _analyze_cannon(self, piece: StandardizedPiece) -> Tuple:
        row, col = piece.position
        is_red = piece.side == 'red'
        legal_moves = []
        constraints = []
        attacks = []
        positional_tags = []
        
        directions = [
            ("forward", -1 if is_red else 1, 0),
            ("backward", 1 if is_red else -1, 0),
            ("left", 0, -1),
            ("right", 0, 1)
        ]
        
        for dir_name, dr, dc in directions:
            nr, nc = row + dr, col + dc
            found_rack = False
            rack_piece = None
            
            while 0 <= nr < 10 and 0 <= nc < 9:
                target_cell = self.board[nr][nc]
                if target_cell:
                    if not found_rack:
                        found_rack = True
                        rack_piece = self.piece_id_map.get((nr, nc), target_cell)
                    else:
                        target_is_enemy = target_cell.isupper() != is_red
                        target_id = self.piece_id_map.get((nr, nc), target_cell)
                        
                        if target_is_enemy:
                            legal_moves.append(LegalMove(
                                to=[nr, nc],
                                move_type="capture",
                                status="legal",
                                direction=dir_name,
                                note=f"炮架{rack_piece}，可打{target_id}",
                                capture_target=target_id,
                                capture_value=PIECE_VALUES.get(target_cell, 0)
                            ))
                            attacks.append(target_id)
                            
                            if is_red and nr == 0 and target_cell.lower() == 'k':
                                positional_tags.append("bottom_cannon")
                            elif not is_red and nr == 9 and target_cell.upper() == 'K':
                                positional_tags.append("bottom_cannon")
                            if nr in [4, 5]:
                                positional_tags.append("riverbank_cannon")
                        break
                else:
                    if not found_rack:
                        legal_moves.append(LegalMove(
                            to=[nr, nc],
                            move_type="move",
                            status="legal",
                            direction=dir_name,
                            note="可移动"
                        ))
                
                nr += dr
                nc += dc
        
        return legal_moves, constraints, attacks, positional_tags
    
    def _analyze_elephant(self, piece: StandardizedPiece) -> Tuple:
        row, col = piece.position
        is_red = piece.side == 'red'
        legal_moves = []
        constraints = []
        
        elephant_moves = [
            ("left_up", -2, -2, -1, -1),
            ("right_up", -2, 2, -1, 1),
            ("left_down", 2, -2, 1, -1),
            ("right_down", 2, 2, 1, 1),
        ]
        
        for dir_name, dr, dc, wr, wc in elephant_moves:
            target_row, target_col = row + dr, col + dc
            wing_row, wing_col = row + wr, col + wc
            
            is_valid = 0 <= target_row < 10 and 0 <= target_col < 9
            
            if is_red and target_row < 5:
                is_valid = False
            elif not is_red and target_row > 4:
                is_valid = False
            
            wing_blocked = False
            wing_block_piece = None
            if 0 <= wing_row < 10 and 0 <= wing_col < 9:
                wing_cell = self.board[wing_row][wing_col]
                if wing_cell:
                    wing_blocked = True
                    wing_block_piece = self.piece_id_map.get((wing_row, wing_col), wing_cell)
                    constraints.append(Constraint(
                        kind="elephant_blocked",
                        target=[wing_row, wing_col],
                        note=f"象眼被{wing_block_piece}塞住",
                        block_piece=wing_block_piece
                    ))
            
            if wing_blocked or not is_valid:
                continue
            
            target_cell = self.board[target_row][target_col]
            if not target_cell:
                legal_moves.append(LegalMove(
                    to=[target_row, target_col],
                    move_type="move",
                    status="legal",
                    direction=dir_name,
                    note="可落子"
                ))
        
        return legal_moves, constraints
    
    def _analyze_advisor(self, piece: StandardizedPiece) -> Tuple:
        row, col = piece.position
        is_red = piece.side == 'red'
        legal_moves = []
        attacks = []
        
        advisor_moves = [
            ("left_up", -1, -1),
            ("right_up", -1, 1),
            ("left_down", 1, -1),
            ("right_down", 1, 1),
        ]
        
        for dir_name, dr, dc in advisor_moves:
            target_row, target_col = row + dr, col + dc
            
            if not self._is_in_palace(target_row, target_col, is_red):
                continue
            
            target_cell = self.board[target_row][target_col]
            if target_cell:
                target_is_enemy = target_cell.isupper() != is_red
                if target_is_enemy:
                    target_id = self.piece_id_map.get((target_row, target_col), target_cell)
                    legal_moves.append(LegalMove(
                        to=[target_row, target_col],
                        move_type="capture",
                        status="legal",
                        direction=dir_name,
                        note=f"可吃{target_id}",
                        capture_target=target_id
                    ))
                    attacks.append(target_id)
            else:
                legal_moves.append(LegalMove(
                    to=[target_row, target_col],
                    move_type="move",
                    status="legal",
                    direction=dir_name,
                    note="可落子"
                ))
        
        return legal_moves, attacks
    
    def _analyze_king(self, piece: StandardizedPiece) -> Tuple:
        row, col = piece.position
        is_red = piece.side == 'red'
        legal_moves = []
        attacks = []
        
        king_moves = [
            ("forward", -1 if is_red else 1, 0),
            ("backward", 1 if is_red else -1, 0),
            ("left", 0, -1),
            ("right", 0, 1),
        ]
        
        for dir_name, dr, dc in king_moves:
            target_row, target_col = row + dr, col + dc
            
            if not self._is_in_palace(target_row, target_col, is_red):
                continue
            
            target_cell = self.board[target_row][target_col]
            if target_cell:
                target_is_enemy = target_cell.isupper() != is_red
                if target_is_enemy:
                    target_id = self.piece_id_map.get((target_row, target_col), target_cell)
                    legal_moves.append(LegalMove(
                        to=[target_row, target_col],
                        move_type="capture",
                        status="legal",
                        direction=dir_name,
                        note=f"可吃{target_id}",
                        capture_target=target_id
                    ))
                    attacks.append(target_id)
            else:
                legal_moves.append(LegalMove(
                    to=[target_row, target_col],
                    move_type="move",
                    status="legal",
                    direction=dir_name,
                    note="可移动"
                ))
        
        return legal_moves, attacks
    
    def _analyze_pawn(self, piece: StandardizedPiece) -> Tuple:
        row, col = piece.position
        is_red = piece.side == 'red'
        legal_moves = []
        attacks = []
        positional_tags = []
        
        forward_dr = -1 if is_red else 1
        is_past_river = (is_red and row <= 4) or (not is_red and row >= 5)
        
        target_row = row + forward_dr
        if 0 <= target_row < 10:
            target_cell = self.board[target_row][col]
            if target_cell:
                target_is_enemy = target_cell.isupper() != is_red
                if target_is_enemy:
                    target_id = self.piece_id_map.get((target_row, col), target_cell)
                    legal_moves.append(LegalMove(
                        to=[target_row, col],
                        move_type="capture",
                        status="legal",
                        direction="forward",
                        note=f"可吃{target_id}",
                        capture_target=target_id
                    ))
                    attacks.append(target_id)
            else:
                legal_moves.append(LegalMove(
                    to=[target_row, col],
                    move_type="move",
                    status="legal",
                    direction="forward",
                    note="可前进"
                ))
        
        if is_past_river:
            for dc in [-1, 1]:
                target_col = col + dc
                if 0 <= target_col < 9:
                    target_cell = self.board[row][target_col]
                    if target_cell:
                        target_is_enemy = target_cell.isupper() != is_red
                        if target_is_enemy:
                            target_id = self.piece_id_map.get((row, target_col), target_cell)
                            legal_moves.append(LegalMove(
                                to=[row, target_col],
                                move_type="capture",
                                status="legal",
                                direction="left" if dc < 0 else "right",
                                note=f"可吃{target_id}",
                                capture_target=target_id
                            ))
                            attacks.append(target_id)
                    else:
                        legal_moves.append(LegalMove(
                            to=[row, target_col],
                            move_type="move",
                            status="legal",
                            direction="left" if dc < 0 else "right",
                            note="可横走"
                        ))
        
        if is_past_river:
            positional_tags.append("cross_river")
        if col in [0, 8]:
            positional_tags.append("edge_pawn")
        if col == 4:
            positional_tags.append("central_pawn")
        if col in [3, 5]:
            positional_tags.append("rib_pawn")
        if (is_red and row <= 3) or (not is_red and row >= 6):
            positional_tags.append("high_pawn")
        
        return legal_moves, attacks, positional_tags
    
    def _add_geometric_tags(self, piece: StandardizedPiece):
        row, col = piece.position
        is_red = piece.side == 'red'
        
        if piece.legal_moves:
            piece.geometric_tags.append("legal_move")
        
        if piece.attacks:
            piece.geometric_tags.append("attackable")
        
        if piece.constraints:
            piece.geometric_tags.append("blocked")
            for c in piece.constraints:
                if c.kind == "horse_leg_blocked":
                    piece.geometric_tags.append("horse_leg_blocked")
                elif c.kind == "elephant_blocked":
                    piece.geometric_tags.append("elephant_blocked")
        
        if piece.piece_type in ['king', 'advisor', 'elephant']:
            piece.geometric_tags.append("palace_limited")
        
        if piece.piece_type == 'pawn':
            if (is_red and row <= 4) or (not is_red and row >= 5):
                piece.geometric_tags.append("cross_river")
    
    def _add_positional_tags(self, piece: StandardizedPiece):
        row, col = piece.position
        
        if row in [4, 5]:
            if "riverbank_rook" not in piece.positional_tags:
                pass
        
        if col == 4:
            if "center_file" not in piece.positional_tags:
                piece.positional_tags.append("center_file")
        if col in [3, 5]:
            if "rib_file" not in piece.positional_tags:
                piece.positional_tags.append("rib_file")
    
    def _build_control_map(self):
        self.control_map = {}
        
        for piece in self.pieces:
            for move in piece.legal_moves:
                pos = tuple(move.to)
                if pos not in self.control_map:
                    self.control_map[pos] = set()
                self.control_map[pos].add(piece.piece_id)
    
    def _analyze_attacks_and_defenses(self):
        for piece in self.pieces:
            row, col = piece.position
            pos = (row, col)
            
            attackers = []
            for other in self.pieces:
                if other.side != piece.side:
                    for move in other.legal_moves:
                        if tuple(move.to) == pos:
                            attackers.append(other.piece_id)
            
            for other in self.pieces:
                if other.side == piece.side and other.piece_id != piece.piece_id:
                    for attacker_id in attackers:
                        for move in other.legal_moves:
                            if move.move_type == "capture" and move.capture_target == attacker_id:
                                piece.defended_by.append(other.piece_id)
                                break
            
            if piece.defended_by:
                piece.geometric_tags.append("is_defended")
            
            piece.attacked_by = attackers
            
            if attackers and not piece.defended_by:
                piece.geometric_tags.append("is_hanging")
    
    def _detect_global_patterns(self):
        self.global_patterns = []
        
        self._detect_check()
        self._detect_duijiang()
        self._detect_check_threats()
        
        self._build_pressure_map()
    
    def _detect_check(self):
        for piece in self.pieces:
            for move in piece.legal_moves:
                if move.capture_target:
                    target_piece = next((p for p in self.pieces if p.piece_id == move.capture_target), None)
                    if target_piece and target_piece.piece_type == 'king':
                        self.global_patterns.append(GlobalPattern(
                            pattern_type="check",
                            side=piece.side,
                            source_piece=piece.piece_id,
                            target_piece=target_piece.piece_id,
                            note=f"{piece.piece_name}将军"
                        ))
    
    def _detect_duijiang(self):
        red_king = self.king_positions.get(True)
        black_king = self.king_positions.get(False)
        
        if red_king and black_king:
            if red_king[1] == black_king[1]:
                col = red_king[1]
                min_row = min(red_king[0], black_king[0])
                max_row = max(red_king[0], black_king[0])
                
                has_blocker = False
                for r in range(min_row + 1, max_row):
                    if self.board[r][col]:
                        has_blocker = True
                        break
                
                if not has_blocker:
                    self.global_patterns.append(GlobalPattern(
                        pattern_type="duijiang",
                        side="both",
                        note="对将局面"
                    ))
    
    def _detect_check_threats(self):
        for piece in self.pieces:
            if piece.piece_type == 'knight':
                for pattern in piece.tactical_patterns:
                    if pattern == "卧槽马":
                        self.global_patterns.append(GlobalPattern(
                            pattern_type="check_threat",
                            side=piece.side,
                            source_piece=piece.piece_id,
                            note=f"{piece.piece_name}存在卧槽马将军威胁"
                        ))
    
    def _build_pressure_map(self):
        red_controls = []
        black_controls = []
        contested = []
        
        for pos, controllers in self.control_map.items():
            red_ctrl = [c for c in controllers if c[0].isupper()]
            black_ctrl = [c for c in controllers if c[0].islower()]
            
            if red_ctrl and black_ctrl:
                contested.append(list(pos))
            elif red_ctrl:
                red_controls.append(list(pos))
            elif black_ctrl:
                black_controls.append(list(pos))
        
        self.pressure_map = PressureMap(
            red_controls=red_controls,
            black_controls=black_controls,
            contested_points=contested
        )
    
    def _generate_summary(self):
        red_pieces = [p for p in self.pieces if p.side == 'red']
        black_pieces = [p for p in self.pieces if p.side == 'black']
        
        is_check = any(p.pattern_type == "check" for p in self.global_patterns)
        check_by = None
        if is_check:
            for p in self.global_patterns:
                if p.pattern_type == "check":
                    check_by = p.source_piece
                    break
        
        self.summary = PositionSummary(
            red_piece_count=len(red_pieces),
            black_piece_count=len(black_pieces),
            red_material=sum(p.material_value for p in red_pieces),
            black_material=sum(p.material_value for p in black_pieces),
            material_balance=sum(p.material_value for p in red_pieces) - sum(p.material_value for p in black_pieces),
            total_legal_moves_red=sum(len(p.legal_moves) for p in red_pieces),
            total_legal_moves_black=sum(len(p.legal_moves) for p in black_pieces),
            is_check=is_check,
            check_by=check_by
        )
    
    def _is_in_palace(self, row: int, col: int, is_red: bool) -> bool:
        if col < 3 or col > 5:
            return False
        if is_red:
            return 7 <= row <= 9
        else:
            return 0 <= row <= 2


def analyze_position(fen: str) -> StandardizedPositionAnalysis:
    """
    便捷函数：分析局面
    
    Args:
        fen: FEN字符串
        
    Returns:
        标准化局面分析结果
    """
    analyzer = PositionAnalyzer()
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
        
        result = analyze_position(fen)
        output = result.to_dict()
        
        print("\n【结构化输出】")
        print(f"棋子数量: {len(output['analysis_structured']['pieces'])}")
        print(f"全局模式: {len(output['analysis_structured']['global_patterns'])}")
        
        print("\n【文本输出】")
        print(output['analysis_text']['analysis_text'][:500])
        
        print("\n【检索标签】")
        print(output['analysis_text']['retrieval_tags'])
