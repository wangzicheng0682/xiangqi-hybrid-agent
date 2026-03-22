"""
战术标签检测器

职责: 基于规则引擎检测六大层级战术标签
原则: 100%规则硬检，置信度二元化，棋子必绑定

文档依据: docs/03_DEVELOPMENT_GUIDE/03.3_CORE_TECH_SPEC.md
"""

from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum

from .tactical_tags import (
    TacticalTag,
    TagDetectionResult,
    PositionTacticalAnalysis,
    TagCategory,
    ALL_TACTICAL_TAGS,
    get_tag_by_name,
)
from .piece_binding import PieceBinding, PieceBindingFactory
from .xiangqi_rules import XiangqiRulesEngine


class DetectionMode(Enum):
    """检测模式"""
    STATIC = "static"
    DYNAMIC = "dynamic"
    FULL = "full"


@dataclass
class DynamicDetectionResult:
    """动态检测结果（针对单步走法）"""
    move: str
    tags: List[TagDetectionResult]
    
    def get_detected_tags(self) -> List[TagDetectionResult]:
        return [t for t in self.tags if t.detected]


@dataclass
class FullDetectionResult:
    """完整检测结果"""
    fen: str
    static_result: PositionTacticalAnalysis
    dynamic_results: Dict[str, DynamicDetectionResult] = field(default_factory=dict)
    
    def to_evidence_map(self) -> Dict[str, Any]:
        """转换为Evidence Map格式"""
        facts_rules = []
        
        for t in self.static_result.get_detected_tags():
            facts_rules.append({
                "tag": t.tag.name,
                "confidence": t.confidence,
                "bind_pieces": t.bind_pieces,
                "description": t.tag.description,
                "source": "static",
                "move": None
            })
        
        for move, dyn in self.dynamic_results.items():
            for t in dyn.get_detected_tags():
                facts_rules.append({
                    "tag": t.tag.name,
                    "confidence": t.confidence,
                    "bind_pieces": t.bind_pieces,
                    "description": t.tag.description,
                    "source": "dynamic",
                    "move": move
                })
        
        return {
            "facts_rules": facts_rules,
            "evidence_source": {
                "rules": "TACTICAL_DETECTOR"
            }
        }


class TacticalDetector:
    """
    战术标签检测器
    
    检测六大层级战术标签:
    1. 将杀困毙层 - is_check, is_checkmate, is_stalemate
    2. 捉子层 - is_attack_unprotected, is_mutual_attack, is_attack_king_adjacent
    3. 闪击抽将层 - is_discovered_check, is_double_attack_with_check, is_discovered_attack
    4. 牵制串打层 - is_pinned, is_cannon_double_attack
    5. 标准杀法层 - checkmate_horse_back_cannon, checkmate_iron_gate, checkmate_double_rook
    6. 子力状态层 - piece_is_unprotected, cannon_has_platform
    """
    
    PIECE_NAMES = {
        'K': ('帅', '红'), 'k': ('将', '黑'),
        'A': ('仕', '红'), 'a': ('士', '黑'),
        'B': ('相', '红'), 'b': ('象', '黑'),
        'N': ('马', '红'), 'n': ('马', '黑'),
        'R': ('车', '红'), 'r': ('车', '黑'),
        'C': ('炮', '红'), 'c': ('炮', '黑'),
        'P': ('兵', '红'), 'p': ('卒', '黑'),
    }

    PIECE_VALUES = {
        'k': 100000,
        'r': 900,
        'n': 450,
        'c': 450,
        'b': 200,
        'a': 200,
        'p': 100,
    }
    
    def __init__(self):
        self.rules_engine = XiangqiRulesEngine()
    
    def detect_static(self, fen: str, debug_mode: bool = False) -> PositionTacticalAnalysis:
        """
        静态检测：分析当前局面状态

        Args:
            fen: 当前局面FEN
            debug_mode: 是否启用调试模式（包含一致性检查）

        Returns:
            PositionTacticalAnalysis: 静态检测结果
        """
        board = self._fen_to_board(fen)
        is_red_turn = self._is_red_turn(fen)

        tags = []

        # 原有检测
        tags.extend(self._detect_check_mate_stalemate(board, is_red_turn))
        tags.extend(self._detect_capture(board, True))
        tags.extend(self._detect_capture(board, False))
        tags.extend(self._detect_pin_skewer(board, is_red_turn))
        tags.extend(self._detect_standard_mate(board, is_red_turn))
        tags.extend(self._detect_piece_status(board))
        tags.extend(self._detect_phase(board))
        tags.extend(self._detect_king_safety(board, is_red_turn))
        tags.extend(self._detect_initiative(board, is_red_turn))
        tags.extend(self._detect_horse_leg_blocked(board))
        tags.extend(self._detect_kings_face_to_face(board))
        tags.extend(self._detect_cannon_battery(board))
        tags.extend(self._detect_favorable_exchange(board, is_red_turn))

        # Phase 2 新增：战略评估检测
        tags.extend(self.detect_strategic_tags(fen))

        result = PositionTacticalAnalysis(fen=fen, tags=tags)

        # 一致性检查（仅debug_mode）
        if debug_mode:
            from .consistency_checker import ConsistencyChecker
            checker = ConsistencyChecker()
            detected_tags = result.get_detected_tags()
            tags_dict = {t.tag.name: t for t in detected_tags}
            violations = checker.check(tags_dict, fen)

            if violations:
                print(f"[DEBUG] Consistency violations for FEN: {fen}")
                for v in violations:
                    severity = v.get("severity", "UNKNOWN")
                    rule = v.get("rule", "unknown")
                    detail = v.get("detail", "")
                    print(f"  [{severity}] {rule}: {detail}")

            # 将违规信息附加到结果中
            result.consistency_violations = violations

        return result

    def detect_dynamic(self, fen: str, move: str) -> DynamicDetectionResult:
        """
        动态检测：分析某步棋产生的战术效果

        Args:
            fen: 当前局面FEN
            move: UCI格式走法 (如 "h2e2")

        Returns:
            DynamicDetectionResult: 动态检测结果
        """
        board = self._fen_to_board(fen)
        is_red_turn = self._is_red_turn(fen)

        tags = []
        # 原有动态检测
        tags.extend(self._detect_discovered_attack(board, move, is_red_turn))
        tags.extend(self._detect_double_attack_with_check(board, move, is_red_turn))
        tags.extend(self._detect_forcing_move(board, move, is_red_turn))

        # Phase 1 新增：走法质量检测
        tags.extend(self.detect_move_quality(fen, move))

        # 检测走法后是否造成将军（用于动态测试）
        new_board = self._apply_move(board, move)
        if self._is_in_check(new_board, not is_red_turn):
            tag = get_tag_by_name("is_check")
            if tag:
                # 找出攻击者
                attacker_pieces = []
                enemy_king_pos = self._find_king(new_board, not is_red_turn)
                if enemy_king_pos:
                    for r in range(10):
                        for c in range(9):
                            piece = new_board[r][c]
                            if piece and self._is_red(piece) == is_red_turn:
                                attacks = self._get_attacks(new_board, r, c)
                                if enemy_king_pos in attacks:
                                    attacker_pieces.append(self._bind_piece(piece, r, c))
                if attacker_pieces:
                    tags.append(TagDetectionResult(
                        tag=tag,
                        detected=True,
                        confidence=1.0,
                        bind_pieces=attacker_pieces,
                        metadata={"move": move, "dynamic": True}
                    ))

        return DynamicDetectionResult(move=move, tags=tags)
    
    def detect_full(self, fen: str, 
                    include_moves: Optional[List[str]] = None) -> FullDetectionResult:
        """
        完整检测：静态+动态
        
        Args:
            fen: 当前局面FEN
            include_moves: 指定要分析的走法（None=分析所有合法走法）
            
        Returns:
            FullDetectionResult: 完整检测结果
        """
        static_result = self.detect_static(fen)
        
        dynamic_results = {}
        
        if include_moves is None:
            board = self._fen_to_board(fen)
            include_moves = self._get_all_legal_moves(board)
        
        for move in include_moves:
            dyn_result = self.detect_dynamic(fen, move)
            if dyn_result.get_detected_tags():
                dynamic_results[move] = dyn_result
        
        return FullDetectionResult(
            fen=fen,
            static_result=static_result,
            dynamic_results=dynamic_results
        )
    
    def _fen_to_board(self, fen: str) -> List[List[str]]:
        """FEN转棋盘二维数组"""
        board = []
        parts = fen.split()
        rows = parts[0].split('/')
        
        for row_str in rows:
            row = []
            for char in row_str:
                if char.isdigit():
                    row.extend([''] * int(char))
                else:
                    row.append(char)
            while len(row) < 9:
                row.append('')
            board.append(row)
        
        while len(board) < 10:
            board.append([''] * 9)
        
        return board
    
    def _is_red_turn(self, fen: str) -> bool:
        """判断是否红方走棋"""
        parts = fen.split()
        if len(parts) >= 2:
            return parts[1] == 'w'
        return True
    
    def _is_red(self, piece: str) -> bool:
        """判断棋子是否为红方"""
        return piece.isupper() if piece else False
    
    def _is_black(self, piece: str) -> bool:
        """判断棋子是否为黑方"""
        return piece.islower() if piece else False
    
    def _bind_piece(self, piece: str, row: int, col: int) -> str:
        """绑定棋子到坐标"""
        if not piece:
            return ""
        piece_info = self.PIECE_NAMES.get(piece, ('未知', '红' if piece.isupper() else '黑'))
        piece_type = piece_info[0]
        color = piece_info[1]
        x = col + 1
        y = 10 - row
        return f"{color}{piece_type}-({x},{y})"
    
    def _find_king(self, board: List[List[str]], is_red: bool) -> Optional[Tuple[int, int]]:
        """查找将/帅位置"""
        king = 'K' if is_red else 'k'
        for r in range(10):
            for c in range(9):
                if board[r][c] == king:
                    return (r, c)
        return None
    
    def _get_all_legal_moves(self, board: List[List[str]]) -> List[str]:
        """获取所有合法走法（UCI格式）"""
        moves = []
        for r in range(10):
            for c in range(9):
                piece = board[r][c]
                if piece:
                    legal = self.rules_engine.get_legal_moves(board, r, c)
                    for nr, nc in legal:
                        move = self._to_uci(r, c, nr, nc)
                        moves.append(move)
        return moves
    
    def _to_uci(self, from_row: int, from_col: int, to_row: int, to_col: int) -> str:
        """坐标转UCI格式（中国象棋：列a-i，行0-9从红方视角）"""
        files = 'abcdefghi'
        from_sq = f"{files[from_col]}{9 - from_row}"
        to_sq = f"{files[to_col]}{9 - to_row}"
        return f"{from_sq}{to_sq}"
    
    def _parse_uci(self, move: str) -> Tuple[Tuple[int, int], Tuple[int, int]]:
        """UCI格式转坐标（中国象棋：列a-i，行0-9从红方视角）"""
        if len(move) < 4:
            raise ValueError(f"UCI格式错误: {move}")
        
        files = 'abcdefghi'
        move = move.lower()
        
        try:
            from_col = files.index(move[0])
            from_row = 9 - int(move[1])
            to_col = files.index(move[2])
            to_row = 9 - int(move[3])
        except (ValueError, IndexError) as e:
            raise ValueError(f"UCI格式解析失败: {move}, 错误: {e}")
        
        return (from_row, from_col), (to_row, to_col)
    
    def _apply_move(self, board: List[List[str]], move: str) -> List[List[str]]:
        """执行走法，返回新棋盘"""
        new_board = [row[:] for row in board]
        (from_row, from_col), (to_row, to_col) = self._parse_uci(move)
        new_board[to_row][to_col] = new_board[from_row][from_col]
        new_board[from_row][from_col] = ''
        return new_board
    
    def _get_attacks(self, board: List[List[str]], row: int, col: int) -> List[Tuple[int, int]]:
        """获取棋子的攻击范围"""
        return self.rules_engine.get_legal_moves(board, row, col)
    
    def _is_protected(self, board: List[List[str]], row: int, col: int, is_red: bool) -> bool:
        """
        判断棋子是否被保护（有根）
        
        正确的有根定义：如果敌方吃掉这个子，我方能否吃回去。
        需要模拟目标位置被敌方棋子占据后的局面来判断。
        
        Args:
            board: 棋盘
            row: 目标位置行
            col: 目标位置列
            is_red: 目标棋子是否为红方（即要检查哪一方的保护）
        
        Returns:
            是否被保护
        """
        import copy
        test_board = copy.deepcopy(board)
        enemy_piece = 'P' if not is_red else 'p'
        test_board[row][col] = enemy_piece
        
        for r in range(10):
            for c in range(9):
                piece = test_board[r][c]
                if piece and self._is_red(piece) == is_red:
                    if (r, c) == (row, col):
                        continue
                    attacks = self._get_attacks(test_board, r, c)
                    if (row, col) in attacks:
                        return True
        return False
    
    def _can_attack(self, board: List[List[str]], from_pos: Tuple[int, int], 
                    to_pos: Tuple[int, int]) -> bool:
        """判断棋子是否能攻击目标位置"""
        r, c = from_pos
        attacks = self._get_attacks(board, r, c)
        return to_pos in attacks
    
    def _get_my_pieces(self, board: List[List[str]], is_red: bool) -> List[Tuple[int, int]]:
        """获取己方所有棋子位置"""
        pieces = []
        for r in range(10):
            for c in range(9):
                piece = board[r][c]
                if piece and self._is_red(piece) == is_red:
                    pieces.append((r, c))
        return pieces
    
    def _get_enemy_pieces(self, board: List[List[str]], is_red: bool) -> List[Tuple[int, int]]:
        """获取敌方所有棋子位置"""
        pieces = []
        for r in range(10):
            for c in range(9):
                piece = board[r][c]
                if piece and self._is_red(piece) != is_red:
                    pieces.append((r, c))
        return pieces
    
    def _is_in_check(self, board: List[List[str]], is_red: bool) -> bool:
        """判断是否被将军"""
        king_pos = self._find_king(board, is_red)
        if not king_pos:
            return False
        
        for r in range(10):
            for c in range(9):
                piece = board[r][c]
                if piece and self._is_red(piece) != is_red:
                    attacks = self._get_attacks(board, r, c)
                    if king_pos in attacks:
                        return True
        return False
    
    def _find_check_attackers(self, board: List[List[str]], 
                               is_red: bool) -> List[Tuple[int, int]]:
        """找到将军的攻击者"""
        king_pos = self._find_king(board, is_red)
        if not king_pos:
            return []
        
        attackers = []
        for r in range(10):
            for c in range(9):
                piece = board[r][c]
                if piece and self._is_red(piece) != is_red:
                    attacks = self._get_attacks(board, r, c)
                    if king_pos in attacks:
                        attackers.append((r, c))
        return attackers
    
    def _has_legal_moves(self, board: List[List[str]], is_red: bool) -> bool:
        """
        判断是否有合法走法
        
        合法走法定义：走法后不会导致自己被将军
        """
        for r in range(10):
            for c in range(9):
                piece = board[r][c]
                if piece and self._is_red(piece) == is_red:
                    moves = self.rules_engine.get_legal_moves(board, r, c)
                    for nr, nc in moves:
                        new_board = [row[:] for row in board]
                        new_board[nr][nc] = new_board[r][c]
                        new_board[r][c] = ''
                        if not self._is_in_check(new_board, is_red):
                            return True
        return False
    
    def _get_line_positions(self, start: Tuple[int, int], 
                            end: Tuple[int, int]) -> List[Tuple[int, int]]:
        """获取两点连线上的所有位置（不包含端点）"""
        dr = 0 if end[0] == start[0] else (1 if end[0] > start[0] else -1)
        dc = 0 if end[1] == start[1] else (1 if end[1] > start[1] else -1)
        
        if dr == 0 and dc == 0:
            return []
        
        positions = []
        r, c = start[0] + dr, start[1] + dc
        while (r, c) != end:
            positions.append((r, c))
            r += dr
            c += dc
        
        return positions
    
    def _is_on_same_line(self, pos1: Tuple[int, int], pos2: Tuple[int, int]) -> bool:
        """判断两点是否在同一直线上"""
        return pos1[0] == pos2[0] or pos1[1] == pos2[1]
    
    def _get_distance(self, pos1: Tuple[int, int], pos2: Tuple[int, int]) -> int:
        """获取两点间的距离（曼哈顿距离）"""
        return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])
    
    def _is_pinner(self, piece: str) -> bool:
        """判断棋子是否能牵制（车、炮）"""
        return piece.lower() in ('r', 'c')
    
    def _get_adjacent_positions(self, pos: Tuple[int, int]) -> List[Tuple[int, int]]:
        """获取相邻位置（上下左右）"""
        r, c = pos
        adjacent = []
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < 10 and 0 <= nc < 9:
                adjacent.append((nr, nc))
        return adjacent
    
    def _is_in_palace(self, pos: Tuple[int, int], is_red: bool) -> bool:
        """判断位置是否在九宫格内"""
        r, c = pos
        if is_red:
            return 7 <= r <= 9 and 3 <= c <= 5
        else:
            return 0 <= r <= 2 and 3 <= c <= 5
    
    def _count_legal_moves(self, board: List[List[str]], is_red: bool) -> int:
        """统计合法走法数量"""
        count = 0
        for r in range(10):
            for c in range(9):
                piece = board[r][c]
                if piece and self._is_red(piece) == is_red:
                    moves = self.rules_engine.get_legal_moves(board, r, c)
                    count += len(moves)
        return count
    
    def _detect_check_mate_stalemate(self, board: List[List[str]], 
                                      is_red_turn: bool) -> List[TagDetectionResult]:
        """
        检测将杀困毙层标签
        
        - is_check: 被将军
        - is_checkmate: 将死
        - is_stalemate: 困毙
        """
        results = []
        
        is_in_check = self._is_in_check(board, is_red_turn)
        has_legal_moves = self._has_legal_moves(board, is_red_turn)
        king_pos = self._find_king(board, is_red_turn)
        
        is_check_tag = get_tag_by_name("is_check")
        if is_check_tag and is_in_check:
            attackers = self._find_check_attackers(board, is_red_turn)
            bind_pieces = []
            if king_pos:
                bind_pieces.append(self._bind_piece(board[king_pos[0]][king_pos[1]], 
                                                     king_pos[0], king_pos[1]))
            for attacker in attackers:
                bind_pieces.append(self._bind_piece(board[attacker[0]][attacker[1]],
                                                     attacker[0], attacker[1]))
            
            results.append(TagDetectionResult(
                tag=is_check_tag,
                detected=True,
                confidence=1.0,
                bind_pieces=bind_pieces
            ))
        
        is_checkmate_tag = get_tag_by_name("is_checkmate")
        if is_checkmate_tag and is_in_check and not has_legal_moves:
            bind_pieces = []
            if king_pos:
                bind_pieces.append(self._bind_piece(board[king_pos[0]][king_pos[1]],
                                                     king_pos[0], king_pos[1]))
            
            results.append(TagDetectionResult(
                tag=is_checkmate_tag,
                detected=True,
                confidence=1.0,
                bind_pieces=bind_pieces
            ))
        
        is_stalemate_tag = get_tag_by_name("is_stalemate")
        if is_stalemate_tag and not is_in_check and not has_legal_moves:
            bind_pieces = []
            if king_pos:
                bind_pieces.append(self._bind_piece(board[king_pos[0]][king_pos[1]],
                                                     king_pos[0], king_pos[1]))
            
            results.append(TagDetectionResult(
                tag=is_stalemate_tag,
                detected=True,
                confidence=1.0,
                bind_pieces=bind_pieces
            ))
        
        return results
    
    def _detect_capture(self, board: List[List[str]], 
                        is_red_turn: bool) -> List[TagDetectionResult]:
        """
        检测捉子层标签
        
        - is_attack_unprotected: 攻无根
        - is_mutual_attack: 互吃
        - is_attack_king_adjacent: 攻将邻
        """
        results = []
        seen_unprotected = set()
        seen_mutual = set()
        seen_king_adjacent = set()
        
        my_pieces = self._get_my_pieces(board, is_red_turn)
        enemy_king_pos = self._find_king(board, not is_red_turn)
        
        for piece_pos in my_pieces:
            attacks = self._get_attacks(board, piece_pos[0], piece_pos[1])
            
            for target_pos in attacks:
                target_piece = board[target_pos[0]][target_pos[1]]
                if not target_piece:
                    continue
                
                is_enemy = self._is_red(target_piece) != is_red_turn
                if not is_enemy:
                    continue
                
                is_protected = self._is_protected(board, target_pos[0], target_pos[1], 
                                                   not is_red_turn)
                
                if not is_protected:
                    key = (piece_pos, target_pos)
                    if key not in seen_unprotected:
                        seen_unprotected.add(key)
                        tag = get_tag_by_name("is_attack_unprotected")
                        if tag:
                            results.append(TagDetectionResult(
                                tag=tag,
                                detected=True,
                                confidence=1.0,
                                bind_pieces=[
                                    self._bind_piece(board[piece_pos[0]][piece_pos[1]],
                                                    piece_pos[0], piece_pos[1]),
                                    self._bind_piece(target_piece, target_pos[0], target_pos[1])
                                ]
                            ))
                
                if self._can_attack(board, target_pos, piece_pos):
                    key = tuple(sorted([piece_pos, target_pos]))
                    if key not in seen_mutual:
                        seen_mutual.add(key)
                        tag = get_tag_by_name("is_mutual_attack")
                        if tag:
                            results.append(TagDetectionResult(
                                tag=tag,
                                detected=True,
                                confidence=1.0,
                                bind_pieces=[
                                    self._bind_piece(board[piece_pos[0]][piece_pos[1]],
                                                    piece_pos[0], piece_pos[1]),
                                    self._bind_piece(target_piece, target_pos[0], target_pos[1])
                                ]
                            ))
        
        if enemy_king_pos:
            adjacent_positions = self._get_adjacent_positions(enemy_king_pos)
            for piece_pos in my_pieces:
                attacks = self._get_attacks(board, piece_pos[0], piece_pos[1])
                for adj_pos in adjacent_positions:
                    if adj_pos in attacks and board[adj_pos[0]][adj_pos[1]] == '':
                        key = (piece_pos, adj_pos)
                        if key not in seen_king_adjacent:
                            seen_king_adjacent.add(key)
                            tag = get_tag_by_name("is_attack_king_adjacent")
                            if tag:
                                results.append(TagDetectionResult(
                                    tag=tag,
                                    detected=True,
                                    confidence=1.0,
                                    bind_pieces=[
                                        self._bind_piece(board[piece_pos[0]][piece_pos[1]],
                                                        piece_pos[0], piece_pos[1]),
                                        self._bind_piece(board[enemy_king_pos[0]][enemy_king_pos[1]],
                                                        enemy_king_pos[0], enemy_king_pos[1])
                                    ]
                                ))
        
        return results
    
    def _detect_discovered_attack(self, board: List[List[str]], 
                                   move: str, is_red_turn: bool) -> List[TagDetectionResult]:
        """
        检测闪击抽将层标签（动态检测）
        
        - is_discovered_check: 闪将
        - is_discovered_attack: 闪击
        """
        results = []
        
        (from_row, from_col), (to_row, to_col) = self._parse_uci(move)
        moving_piece = board[from_row][from_col]
        if not moving_piece:
            return results
        
        back_attackers = self._find_back_attackers(board, from_row, from_col, is_red_turn)
        
        new_board = self._apply_move(board, move)
        
        for back_pos in back_attackers:
            back_piece = board[back_pos[0]][back_pos[1]]
            if not back_piece:
                continue
            
            if self._is_in_check(new_board, not is_red_turn):
                tag = get_tag_by_name("is_discovered_check")
                if tag:
                    results.append(TagDetectionResult(
                        tag=tag,
                        detected=True,
                        confidence=1.0,
                        bind_pieces=[
                            self._bind_piece(moving_piece, from_row, from_col),
                            self._bind_piece(back_piece, back_pos[0], back_pos[1])
                        ],
                        metadata={"move": move}
                    ))
            else:
                old_attacks = set(self._get_attacks(board, back_pos[0], back_pos[1]))
                new_attacks = set(self._get_attacks(new_board, back_pos[0], back_pos[1]))
                
                new_targets = new_attacks - old_attacks
                
                for target_pos in new_targets:
                    target_piece = new_board[target_pos[0]][target_pos[1]]
                    if target_piece and self._is_red(target_piece) != is_red_turn:
                        if not self._is_protected(new_board, target_pos[0], target_pos[1],
                                                  not is_red_turn):
                            tag = get_tag_by_name("is_discovered_attack")
                            if tag:
                                results.append(TagDetectionResult(
                                    tag=tag,
                                    detected=True,
                                    confidence=1.0,
                                    bind_pieces=[
                                        self._bind_piece(moving_piece, from_row, from_col),
                                        self._bind_piece(back_piece, back_pos[0], back_pos[1]),
                                        self._bind_piece(target_piece, target_pos[0], target_pos[1])
                                    ],
                                    metadata={"move": move}
                                ))
        
        return results
    
    def _find_back_attackers(self, board: List[List[str]], 
                              row: int, col: int, is_red: bool) -> List[Tuple[int, int]]:
        """找到移动棋子后方的远程攻击棋子（车、炮）"""
        attackers = []
        
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            r, c = row + dr, col + dc
            while 0 <= r < 10 and 0 <= c < 9:
                piece = board[r][c]
                if piece:
                    if self._is_red(piece) == is_red and piece.lower() in ('r', 'c'):
                        attackers.append((r, c))
                    break
                r += dr
                c += dc
        
        return attackers
    
    def _detect_double_attack_with_check(self, board: List[List[str]], 
                                          move: str, is_red_turn: bool) -> List[TagDetectionResult]:
        """
        检测抽将标签（动态检测）
        
        - is_double_attack_with_check: 抽将
        """
        results = []
        
        new_board = self._apply_move(board, move)
        
        if not self._is_in_check(new_board, not is_red_turn):
            return results
        
        (from_row, from_col), (to_row, to_col) = self._parse_uci(move)
        attacker_piece = new_board[to_row][to_col]
        if not attacker_piece:
            return results
        
        attacks = self._get_attacks(new_board, to_row, to_col)
        
        for target_pos in attacks:
            target_piece = new_board[target_pos[0]][target_pos[1]]
            if target_piece and self._is_red(target_piece) != is_red_turn:
                tag = get_tag_by_name("is_double_attack_with_check")
                if tag:
                    results.append(TagDetectionResult(
                        tag=tag,
                        detected=True,
                        confidence=1.0,
                        bind_pieces=[
                            self._bind_piece(attacker_piece, to_row, to_col),
                            self._bind_piece(target_piece, target_pos[0], target_pos[1])
                        ],
                        metadata={"move": move}
                    ))
        
        return results
    
    def _detect_pin_skewer(self, board: List[List[str]],
                           is_red_turn: bool) -> List[TagDetectionResult]:
        """
        检测牵制串打层标签

        - is_pinned: 被牵制（双向检测：我方被牵制 + 对方被牵制）
        - is_cannon_double_attack: 炮串打
        """
        results = []
        seen_pinned = set()
        seen_cannon_double = set()

        # 双向检测牵制：检测双方的棋子被牵制
        for target_is_red in [True, False]:
            king_pos = self._find_king(board, target_is_red)
            if not king_pos:
                continue

            # 找对方的牵制者（车或炮）
            enemy_pinners = []
            for r in range(10):
                for c in range(9):
                    piece = board[r][c]
                    if piece and self._is_red(piece) != target_is_red:
                        if piece.lower() in ('r', 'c'):
                            enemy_pinners.append((r, c))

            for pinner_pos in enemy_pinners:
                if not self._is_on_same_line(pinner_pos, king_pos):
                    continue

                line_positions = self._get_line_positions(pinner_pos, king_pos)

                # 找被牵制的棋子（与王同色的棋子）
                pinned_pieces = []
                for pos in line_positions:
                    piece = board[pos[0]][pos[1]]
                    if piece and self._is_red(piece) == target_is_red:
                        pinned_pieces.append(pos)

                if len(pinned_pieces) == 1:
                    pinned_pos = pinned_pieces[0]
                    key = (pinned_pos, pinner_pos)
                    if key not in seen_pinned:
                        seen_pinned.add(key)
                        tag = get_tag_by_name("is_pinned")
                        if tag:
                            results.append(TagDetectionResult(
                                tag=tag,
                                detected=True,
                                confidence=1.0,
                                bind_pieces=[
                                    self._bind_piece(board[pinned_pos[0]][pinned_pos[1]],
                                                    pinned_pos[0], pinned_pos[1]),
                                    self._bind_piece(board[pinner_pos[0]][pinner_pos[1]],
                                                    pinner_pos[0], pinner_pos[1])
                                ]
                            ))

        my_cannons = []
        for r in range(10):
            for c in range(9):
                piece = board[r][c]
                if piece and piece.lower() == 'c' and self._is_red(piece) == is_red_turn:
                    my_cannons.append((r, c))

        for cannon_pos in my_cannons:
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                targets = self._find_cannon_double_targets(board, cannon_pos, dr, dc, is_red_turn)
                
                if len(targets) >= 2:
                    key = (cannon_pos, tuple(targets[:2]))
                    if key not in seen_cannon_double:
                        seen_cannon_double.add(key)
                        tag = get_tag_by_name("is_cannon_double_attack")
                        if tag:
                            bind_pieces = [
                                self._bind_piece(board[cannon_pos[0]][cannon_pos[1]],
                                                cannon_pos[0], cannon_pos[1])
                            ]
                            for t in targets[:2]:
                                bind_pieces.append(
                                    self._bind_piece(board[t[0]][t[1]], t[0], t[1])
                                )
                            results.append(TagDetectionResult(
                                tag=tag,
                                detected=True,
                                confidence=1.0,
                                bind_pieces=bind_pieces
                            ))
        
        return results
    
    def _find_cannon_double_targets(self, board: List[List[str]], 
                                     cannon_pos: Tuple[int, int],
                                     dr: int, dc: int, is_red: bool) -> List[Tuple[int, int]]:
        """
        找到炮串打的目标
        
        串打定义：炮通过同一个炮架，可以攻击两个敌方棋子。
        即：炮 -> 炮架 -> 敌方棋子1 -> ... -> 敌方棋子2
        无论移开哪一个，另一个都会被打。
        
        注意：如果目标是将/帅，这是牵制，不是串打。
        """
        targets = []
        r, c = cannon_pos
        
        found_platform = False
        r += dr
        c += dc
        
        while 0 <= r < 10 and 0 <= c < 9:
            piece = board[r][c]
            
            if not found_platform:
                if piece:
                    found_platform = True
            else:
                if piece:
                    if self._is_red(piece) != is_red:
                        if piece.lower() != 'k':
                            targets.append((r, c))
                        else:
                            break
                    else:
                        break
                    if len(targets) >= 2:
                        break
            
            r += dr
            c += dc
        
        return targets
    
    def _detect_standard_mate(self, board: List[List[str]], 
                               is_red_turn: bool) -> List[TagDetectionResult]:
        """
        检测标准杀法层标签
        
        - checkmate_horse_back_cannon: 马后炮
        - checkmate_iron_gate: 铁门栓
        - checkmate_double_rook: 双车错
        - checkmate_horse_corner: 卧槽马
        - checkmate_bare_king: 白脸将
        - checkmate_double_cannon_battery: 重炮杀
        - checkmate_sea_bottom_moon: 海底捞月
        - checkmate_side_tiger: 侧面虎
        """
        results = []
        
        horse_back_cannon = self._detect_horse_back_cannon(board, is_red_turn)
        results.extend(horse_back_cannon)
        
        iron_gate = self._detect_iron_gate(board, is_red_turn)
        results.extend(iron_gate)
        
        double_rook = self._detect_double_rook(board, is_red_turn)
        results.extend(double_rook)
        
        horse_corner = self._detect_horse_corner(board, is_red_turn)
        results.extend(horse_corner)
        
        bare_king = self._detect_bare_king(board, is_red_turn)
        results.extend(bare_king)
        
        double_cannon_battery = self._detect_double_cannon_battery_checkmate(board, is_red_turn)
        results.extend(double_cannon_battery)
        
        sea_bottom_moon = self._detect_sea_bottom_moon(board, is_red_turn)
        results.extend(sea_bottom_moon)
        
        side_tiger = self._detect_side_tiger(board, is_red_turn)
        results.extend(side_tiger)
        
        return results
    
    def _detect_horse_back_cannon(self, board: List[List[str]], 
                                   is_red_turn: bool) -> List[TagDetectionResult]:
        """检测马后炮杀法"""
        results = []
        
        enemy_king_pos = self._find_king(board, not is_red_turn)
        if not enemy_king_pos:
            return results
        
        my_horses = []
        my_cannons = []
        
        for r in range(10):
            for c in range(9):
                piece = board[r][c]
                if piece and self._is_red(piece) == is_red_turn:
                    if piece.lower() == 'n':
                        my_horses.append((r, c))
                    elif piece.lower() == 'c':
                        my_cannons.append((r, c))
        
        for horse_pos in my_horses:
            horse_attacks = self._get_attacks(board, horse_pos[0], horse_pos[1])
            
            for cannon_pos in my_cannons:
                if self._is_on_same_line(cannon_pos, enemy_king_pos):
                    line = self._get_line_positions(cannon_pos, enemy_king_pos)
                    pieces_on_line = [p for p in line if board[p[0]][p[1]]]
                    has_screen = len(pieces_on_line) == 1
                    
                    if has_screen:
                        escape_blocked = self._is_king_escape_blocked_by_horse(
                            board, enemy_king_pos, horse_pos, is_red_turn
                        )
                        
                        if escape_blocked:
                            tag = get_tag_by_name("checkmate_horse_back_cannon")
                            if tag:
                                results.append(TagDetectionResult(
                                    tag=tag,
                                    detected=True,
                                    confidence=1.0,
                                    bind_pieces=[
                                        self._bind_piece(board[horse_pos[0]][horse_pos[1]],
                                                        horse_pos[0], horse_pos[1]),
                                        self._bind_piece(board[cannon_pos[0]][cannon_pos[1]],
                                                        cannon_pos[0], cannon_pos[1]),
                                        self._bind_piece(board[enemy_king_pos[0]][enemy_king_pos[1]],
                                                        enemy_king_pos[0], enemy_king_pos[1])
                                    ]
                                ))
        
        return results
    
    def _is_king_escape_blocked_by_horse(self, board: List[List[str]], 
                                          king_pos: Tuple[int, int],
                                          horse_pos: Tuple[int, int],
                                          is_red: bool) -> bool:
        """判断马是否封锁了将/帅的逃跑路线"""
        horse_attacks = set(self._get_attacks(board, horse_pos[0], horse_pos[1]))
        
        king_adjacent = self._get_adjacent_positions(king_pos)
        king_adjacent = [p for p in king_adjacent if self._is_in_palace(p, not is_red)]
        
        blocked_count = 0
        for adj in king_adjacent:
            if adj in horse_attacks:
                blocked_count += 1
        
        return blocked_count >= 2
    
    def _detect_iron_gate(self, board: List[List[str]], 
                          is_red_turn: bool) -> List[TagDetectionResult]:
        """检测铁门栓杀法"""
        results = []
        
        enemy_king_pos = self._find_king(board, not is_red_turn)
        if not enemy_king_pos:
            return results
        
        my_rooks = []
        for r in range(10):
            for c in range(9):
                piece = board[r][c]
                if piece and piece.lower() == 'r' and self._is_red(piece) == is_red_turn:
                    my_rooks.append((r, c))
        
        for rook_pos in my_rooks:
            if rook_pos[1] == enemy_king_pos[1]:
                is_gate_line = True
                
                min_row = min(rook_pos[0], enemy_king_pos[0])
                max_row = max(rook_pos[0], enemy_king_pos[0])
                
                blocking_pieces = []
                for r in range(min_row + 1, max_row):
                    if board[r][rook_pos[1]]:
                        blocking_pieces.append((r, rook_pos[1]))
                
                if not blocking_pieces:
                    tag = get_tag_by_name("checkmate_iron_gate")
                    if tag:
                        results.append(TagDetectionResult(
                            tag=tag,
                            detected=True,
                            confidence=1.0,
                            bind_pieces=[
                                self._bind_piece(board[rook_pos[0]][rook_pos[1]],
                                                rook_pos[0], rook_pos[1]),
                                self._bind_piece(board[enemy_king_pos[0]][enemy_king_pos[1]],
                                                enemy_king_pos[0], enemy_king_pos[1])
                            ]
                        ))
        
        return results
    
    def _detect_double_rook(self, board: List[List[str]], 
                            is_red_turn: bool) -> List[TagDetectionResult]:
        """检测双车错杀法"""
        results = []
        
        enemy_king_pos = self._find_king(board, not is_red_turn)
        if not enemy_king_pos:
            return results
        
        my_rooks = []
        for r in range(10):
            for c in range(9):
                piece = board[r][c]
                if piece and piece.lower() == 'r' and self._is_red(piece) == is_red_turn:
                    my_rooks.append((r, c))
        
        if len(my_rooks) < 2:
            return results
        
        for i, rook1 in enumerate(my_rooks):
            for rook2 in my_rooks[i+1:]:
                attacks1 = set(self._get_attacks(board, rook1[0], rook1[1]))
                attacks2 = set(self._get_attacks(board, rook2[0], rook2[1]))
                
                if enemy_king_pos in attacks1 or enemy_king_pos in attacks2:
                    tag = get_tag_by_name("checkmate_double_rook")
                    if tag:
                        results.append(TagDetectionResult(
                            tag=tag,
                            detected=True,
                            confidence=1.0,
                            bind_pieces=[
                                self._bind_piece(board[rook1[0]][rook1[1]],
                                                rook1[0], rook1[1]),
                                self._bind_piece(board[rook2[0]][rook2[1]],
                                                rook2[0], rook2[1]),
                                self._bind_piece(board[enemy_king_pos[0]][enemy_king_pos[1]],
                                                enemy_king_pos[0], enemy_king_pos[1])
                            ]
                        ))
        
        return results
    
    def _cannon_attacks_via_platform(self, board: List[List[str]], 
                                      cannon_pos: Tuple[int, int],
                                      platform_pos: Tuple[int, int], 
                                      target_pos: Tuple[int, int]) -> bool:
        """
        验证炮是否通过指定棋子为炮架攻击目标位置
        
        要求：
        1. 炮、炮架、目标必须三点共线（同行或同列）
        2. 炮架必须在炮和目标之间
        3. 炮与目标之间恰好只有炮架这一个棋子（炮规则：隔一子）
        """
        cr, cc = cannon_pos
        pr, pc = platform_pos
        tr, tc = target_pos
        
        same_row = (cr == pr == tr)
        same_col = (cc == pc == tc)
        if not same_row and not same_col:
            return False
        
        line = self._get_line_positions(cannon_pos, target_pos)
        
        if platform_pos not in line:
            return False
        
        pieces_on_line = [p for p in line if board[p[0]][p[1]]]
        return len(pieces_on_line) == 1 and pieces_on_line[0] == platform_pos
    
    def _detect_horse_corner(self, board: List[List[str]], 
                              is_red_turn: bool) -> List[TagDetectionResult]:
        """
        检测卧槽马杀法
        
        步骤1: 确认将死（被将军 + 无合法走法）
        步骤2: 找攻击将/帅的己方马
        步骤3: 验证马在宫外（卧槽位）
        """
        results = []
        
        if not self._is_in_check(board, not is_red_turn):
            return results
        if self._has_legal_moves(board, not is_red_turn):
            return results
        
        enemy_king_pos = self._find_king(board, not is_red_turn)
        if not enemy_king_pos:
            return results
        
        for r in range(10):
            for c in range(9):
                piece = board[r][c]
                if not piece:
                    continue
                if piece.lower() != 'n':
                    continue
                if self._is_red(piece) != is_red_turn:
                    continue
                
                attacks = self._get_attacks(board, r, c)
                if enemy_king_pos not in attacks:
                    continue
                
                if self._is_in_palace((r, c), not is_red_turn):
                    continue
                
                tag = get_tag_by_name("checkmate_horse_corner")
                if tag:
                    results.append(TagDetectionResult(
                        tag=tag,
                        detected=True,
                        confidence=1.0,
                        bind_pieces=[
                            self._bind_piece(piece, r, c),
                            self._bind_piece(
                                board[enemy_king_pos[0]][enemy_king_pos[1]],
                                enemy_king_pos[0], enemy_king_pos[1]
                            )
                        ]
                    ))
        
        return results
    
    def _detect_bare_king(self, board: List[List[str]], 
                           is_red_turn: bool) -> List[TagDetectionResult]:
        """
        检测白脸将杀法
        
        步骤1: 确认将死
        步骤2: 找双方将/帅位置
        步骤3: 检查同列且无阻挡
        """
        results = []
        
        if not self._is_in_check(board, not is_red_turn):
            return results
        if self._has_legal_moves(board, not is_red_turn):
            return results
        
        my_king_pos = self._find_king(board, is_red_turn)
        enemy_king_pos = self._find_king(board, not is_red_turn)
        if not my_king_pos or not enemy_king_pos:
            return results
        
        if my_king_pos[1] != enemy_king_pos[1]:
            return results
        
        col = my_king_pos[1]
        min_row = min(my_king_pos[0], enemy_king_pos[0])
        max_row = max(my_king_pos[0], enemy_king_pos[0])
        
        for r in range(min_row + 1, max_row):
            if board[r][col]:
                return results
        
        my_king_piece = board[my_king_pos[0]][my_king_pos[1]]
        enemy_king_piece = board[enemy_king_pos[0]][enemy_king_pos[1]]
        
        tag = get_tag_by_name("checkmate_bare_king")
        if tag:
            results.append(TagDetectionResult(
                tag=tag,
                detected=True,
                confidence=1.0,
                bind_pieces=[
                    self._bind_piece(my_king_piece, my_king_pos[0], my_king_pos[1]),
                    self._bind_piece(enemy_king_piece, enemy_king_pos[0], enemy_king_pos[1])
                ]
            ))
        
        return results
    
    def _detect_double_cannon_battery_checkmate(self, board: List[List[str]], 
                                                 is_red_turn: bool) -> List[TagDetectionResult]:
        """
        检测重炮杀法
        
        步骤1: 确认将死
        步骤2: 找所有己方炮
        步骤3: 检查炮A以炮B为炮架将死的配置
        """
        results = []
        
        if not self._is_in_check(board, not is_red_turn):
            return results
        if self._has_legal_moves(board, not is_red_turn):
            return results
        
        enemy_king_pos = self._find_king(board, not is_red_turn)
        if not enemy_king_pos:
            return results
        
        my_cannons = []
        for r in range(10):
            for c in range(9):
                piece = board[r][c]
                if piece and piece.lower() == 'c' and self._is_red(piece) == is_red_turn:
                    my_cannons.append((r, c))
        
        if len(my_cannons) < 2:
            return results
        
        for i, cannon_a in enumerate(my_cannons):
            for cannon_b in my_cannons[i + 1:]:
                if self._cannon_attacks_via_platform(
                        board, cannon_a, cannon_b, enemy_king_pos):
                    tag = get_tag_by_name("checkmate_double_cannon_battery")
                    if tag:
                        results.append(TagDetectionResult(
                            tag=tag,
                            detected=True,
                            confidence=1.0,
                            bind_pieces=[
                                self._bind_piece(board[cannon_a[0]][cannon_a[1]],
                                                 cannon_a[0], cannon_a[1]),
                                self._bind_piece(board[cannon_b[0]][cannon_b[1]],
                                                 cannon_b[0], cannon_b[1]),
                                self._bind_piece(board[enemy_king_pos[0]][enemy_king_pos[1]],
                                                 enemy_king_pos[0], enemy_king_pos[1])
                            ]
                        ))
                    break
                
                if self._cannon_attacks_via_platform(
                        board, cannon_b, cannon_a, enemy_king_pos):
                    tag = get_tag_by_name("checkmate_double_cannon_battery")
                    if tag:
                        results.append(TagDetectionResult(
                            tag=tag,
                            detected=True,
                            confidence=1.0,
                            bind_pieces=[
                                self._bind_piece(board[cannon_b[0]][cannon_b[1]],
                                                 cannon_b[0], cannon_b[1]),
                                self._bind_piece(board[cannon_a[0]][cannon_a[1]],
                                                 cannon_a[0], cannon_a[1]),
                                self._bind_piece(board[enemy_king_pos[0]][enemy_king_pos[1]],
                                                 enemy_king_pos[0], enemy_king_pos[1])
                            ]
                        ))
                    break
        
        return results
    
    def _detect_sea_bottom_moon(self, board: List[List[str]], 
                                 is_red_turn: bool) -> List[TagDetectionResult]:
        """
        检测海底捞月杀法
        
        步骤1: 确认将死
        步骤2: 确定敌方底线
        步骤3: 找底线上的己方车
        步骤4: 验证车将军将/帅
        """
        results = []
        
        if not self._is_in_check(board, not is_red_turn):
            return results
        if self._has_legal_moves(board, not is_red_turn):
            return results
        
        enemy_king_pos = self._find_king(board, not is_red_turn)
        if not enemy_king_pos:
            return results
        
        back_rank = 0 if is_red_turn else 9
        
        for c in range(9):
            piece = board[back_rank][c]
            if not piece:
                continue
            if piece.lower() != 'r':
                continue
            if self._is_red(piece) != is_red_turn:
                continue
            
            attacks = self._get_attacks(board, back_rank, c)
            if enemy_king_pos in attacks:
                tag = get_tag_by_name("checkmate_sea_bottom_moon")
                if tag:
                    results.append(TagDetectionResult(
                        tag=tag,
                        detected=True,
                        confidence=1.0,
                        bind_pieces=[
                            self._bind_piece(piece, back_rank, c),
                            self._bind_piece(
                                board[enemy_king_pos[0]][enemy_king_pos[1]],
                                enemy_king_pos[0], enemy_king_pos[1]
                            )
                        ]
                    ))
        
        return results
    
    def _detect_side_tiger(self, board: List[List[str]], 
                           is_red_turn: bool) -> List[TagDetectionResult]:
        """
        检测侧面虎杀法
        
        步骤1: 确认将死
        步骤2: 找将/帅所在行
        步骤3: 找同行的己方车
        步骤4: 验证车横向攻击将/帅
        """
        results = []
        
        if not self._is_in_check(board, not is_red_turn):
            return results
        if self._has_legal_moves(board, not is_red_turn):
            return results
        
        enemy_king_pos = self._find_king(board, not is_red_turn)
        if not enemy_king_pos:
            return results
        
        king_row = enemy_king_pos[0]
        
        for c in range(9):
            if c == enemy_king_pos[1]:
                continue
            
            piece = board[king_row][c]
            if not piece:
                continue
            if piece.lower() != 'r':
                continue
            if self._is_red(piece) != is_red_turn:
                continue
            
            attacks = self._get_attacks(board, king_row, c)
            if enemy_king_pos in attacks:
                tag = get_tag_by_name("checkmate_side_tiger")
                if tag:
                    results.append(TagDetectionResult(
                        tag=tag,
                        detected=True,
                        confidence=1.0,
                        bind_pieces=[
                            self._bind_piece(piece, king_row, c),
                            self._bind_piece(
                                board[enemy_king_pos[0]][enemy_king_pos[1]],
                                enemy_king_pos[0], enemy_king_pos[1]
                            )
                        ]
                    ))
        
        return results
    
    def _detect_piece_status(self, board: List[List[str]]) -> List[TagDetectionResult]:
        """
        检测子力状态层标签
        
        - piece_is_unprotected: 子无根
        - cannon_has_platform: 炮有架
        """
        results = []
        seen_unprotected = set()
        seen_cannon_platform = set()
        
        for r in range(10):
            for c in range(9):
                piece = board[r][c]
                if not piece:
                    continue
                
                is_red = self._is_red(piece)
                
                if not self._is_protected(board, r, c, is_red):
                    key = (r, c)
                    if key not in seen_unprotected:
                        seen_unprotected.add(key)
                        tag = get_tag_by_name("piece_is_unprotected")
                        if tag:
                            results.append(TagDetectionResult(
                                tag=tag,
                                detected=True,
                                confidence=1.0,
                                bind_pieces=[self._bind_piece(piece, r, c)]
                            ))
                
                if piece.lower() == 'c':
                    has_platform = self._has_cannon_platform(board, r, c, is_red)
                    if has_platform:
                        key = (r, c)
                        if key not in seen_cannon_platform:
                            seen_cannon_platform.add(key)
                            tag = get_tag_by_name("cannon_has_platform")
                            if tag:
                                results.append(TagDetectionResult(
                                    tag=tag,
                                    detected=True,
                                    confidence=1.0,
                                    bind_pieces=[self._bind_piece(piece, r, c)]
                                ))
        
        return results
    
    def _has_cannon_platform(self, board: List[List[str]], 
                              row: int, col: int, is_red: bool) -> bool:
        """判断炮是否有炮架"""
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            r, c = row + dr, col + dc
            found_piece = False
            
            while 0 <= r < 10 and 0 <= c < 9:
                piece = board[r][c]
                if piece:
                    if not found_piece:
                        found_piece = True
                    else:
                        if self._is_red(piece) != is_red:
                            return True
                        break
                r += dr
                c += dc
        
        return False

    def _get_blocked_horse_legs(self, board: List[List[str]], 
                                 row: int, col: int) -> List[Dict[str, Any]]:
        """
        获取马的被别马脚信息

        四个马脚方向：
        - 上马脚 (row-1, col)：被别时影响上左(row-2, col-1)和上右(row-2, col+1)
        - 下马脚 (row+1, col)：被别时影响下左(row+2, col-1)和下右(row+2, col+1)
        - 左马脚 (row, col-1)：被别时影响左上(row-1, col-2)和左下(row+1, col-2)
        - 右马脚 (row, col+1)：被别时影响右上(row-1, col+2)和右下(row+1, col+2)

        有意义的被别：被阻塞的目标位置必须是空位或敌方棋子（可落子或可吃子）

        Args:
            board: 棋盘
            row: 马的行位置
            col: 马的列位置

        Returns:
            被别马脚信息列表，每个元素包含：
            - leg_pos: 马脚位置
            - blocker: 阻塞棋子
            - blocked_targets: 被阻塞的目标位置列表（仅包含有意义的目标）
        """
        blocked = []
        horse_is_red = self._is_red(board[row][col])

        leg_map = [
            ((-1, 0), [(-2, -1), (-2, 1)]),
            ((1, 0), [(2, -1), (2, 1)]),
            ((0, -1), [(-1, -2), (1, -2)]),
            ((0, 1), [(-1, 2), (1, 2)]),
        ]

        for (leg_dr, leg_dc), blocked_moves_offsets in leg_map:
            leg_r = row + leg_dr
            leg_c = col + leg_dc

            if not (0 <= leg_r < 10 and 0 <= leg_c < 9):
                continue

            if board[leg_r][leg_c]:
                meaningful_blocked = []
                for dr, dc in blocked_moves_offsets:
                    tr, tc = row + dr, col + dc
                    if not (0 <= tr < 10 and 0 <= tc < 9):
                        continue
                    
                    target_piece = board[tr][tc]
                    if target_piece:
                        if self._is_red(target_piece) != horse_is_red:
                            meaningful_blocked.append((tr, tc))
                    else:
                        meaningful_blocked.append((tr, tc))

                if meaningful_blocked:
                    blocked.append({
                        "leg_pos": (leg_r, leg_c),
                        "blocker": board[leg_r][leg_c],
                        "blocked_targets": meaningful_blocked
                    })

        return blocked

    def _detect_horse_leg_blocked(self, board: List[List[str]]) -> List[TagDetectionResult]:
        """
        检测马脚被别

        步骤1: 找所有马
        步骤2: 检查四个马脚方向
        步骤3: 统计被别数量
        步骤4: 生成标签
        """
        results = []
        seen = set()

        for r in range(10):
            for c in range(9):
                piece = board[r][c]
                if not piece or piece.lower() != 'n':
                    continue

                is_red = self._is_red(piece)
                blocked_info = self._get_blocked_horse_legs(board, r, c)

                if not blocked_info:
                    continue

                key = (r, c)
                if key in seen:
                    continue
                seen.add(key)

                bind_pieces = [self._bind_piece(piece, r, c)]
                for info in blocked_info:
                    lr, lc = info["leg_pos"]
                    blocker = board[lr][lc]
                    if blocker:
                        bind_pieces.append(self._bind_piece(blocker, lr, lc))

                tag = get_tag_by_name("horse_leg_blocked")
                if tag:
                    all_blocked_targets = []
                    for info in blocked_info:
                        all_blocked_targets.extend(info["blocked_targets"])
                    
                    results.append(TagDetectionResult(
                        tag=tag,
                        detected=True,
                        confidence=1.0,
                        bind_pieces=bind_pieces,
                        metadata={
                            "horse_color": "red" if is_red else "black",
                            "blocked_directions": len(blocked_info),
                            "total_directions": 4,
                            "blocked_legs": [info["leg_pos"] for info in blocked_info],
                            "blocked_targets": all_blocked_targets
                        }
                    ))

        return results

    def _detect_kings_face_to_face(self, board: List[List[str]]) -> List[TagDetectionResult]:
        """
        检测双将对面（位置特征）

        步骤1: 找双方将/帅
        步骤2: 检查同列
        步骤3: 检查无阻挡
        """
        results = []

        red_king_pos = self._find_king(board, True)
        black_king_pos = self._find_king(board, False)

        if not red_king_pos or not black_king_pos:
            return results

        if red_king_pos[1] != black_king_pos[1]:
            return results

        col = red_king_pos[1]
        min_row = min(red_king_pos[0], black_king_pos[0])
        max_row = max(red_king_pos[0], black_king_pos[0])

        for r in range(min_row + 1, max_row):
            if board[r][col]:
                return results

        tag = get_tag_by_name("kings_face_to_face")
        if tag:
            results.append(TagDetectionResult(
                tag=tag,
                detected=True,
                confidence=1.0,
                bind_pieces=[
                    self._bind_piece(board[red_king_pos[0]][red_king_pos[1]],
                                     red_king_pos[0], red_king_pos[1]),
                    self._bind_piece(board[black_king_pos[0]][black_king_pos[1]],
                                     black_king_pos[0], black_king_pos[1])
                ],
                metadata={
                    "shared_col": col + 1,
                    "distance": max_row - min_row - 1
                }
            ))

        return results

    def _detect_cannon_battery(self, board: List[List[str]]) -> List[TagDetectionResult]:
        """
        检测重炮阵型（位置特征）

        步骤1: 找双方各自的所有炮
        步骤2: 检查同色炮两两组合
        步骤3: 验证同行/列且无阻隔
        """
        results = []
        seen = set()

        for color in [True, False]:
            cannons = []
            for r in range(10):
                for c in range(9):
                    piece = board[r][c]
                    if piece and piece.lower() == 'c' and self._is_red(piece) == color:
                        cannons.append((r, c))

            if len(cannons) < 2:
                continue

            for i, cannon1 in enumerate(cannons):
                for cannon2 in cannons[i + 1:]:
                    if not self._is_on_same_line(cannon1, cannon2):
                        continue

                    line = self._get_line_positions(cannon1, cannon2)
                    pieces_between = [p for p in line if board[p[0]][p[1]]]

                    if pieces_between:
                        continue

                    key = tuple(sorted([cannon1, cannon2]))
                    if key in seen:
                        continue
                    seen.add(key)

                    tag = get_tag_by_name("cannon_battery")
                    if tag:
                        results.append(TagDetectionResult(
                            tag=tag,
                            detected=True,
                            confidence=1.0,
                            bind_pieces=[
                                self._bind_piece(board[cannon1[0]][cannon1[1]],
                                                 cannon1[0], cannon1[1]),
                                self._bind_piece(board[cannon2[0]][cannon2[1]],
                                                 cannon2[0], cannon2[1])
                            ],
                            metadata={
                                "color": "red" if color else "black",
                                "orientation": "horizontal" if cannon1[0] == cannon2[0]
                                               else "vertical"
                            }
                        ))

        return results

    def _detect_favorable_exchange(self, board: List[List[str]], 
                                    is_red_turn: bool) -> List[TagDetectionResult]:
        """
        检测有利兑换机会

        步骤1: 遍历己方棋子的攻击范围
        步骤2: 找可吃的敌方棋子
        步骤3: 判断是否有利（吃大子 or 吃无根子）
        """
        results = []
        seen = set()

        for r in range(10):
            for c in range(9):
                piece = board[r][c]
                if not piece or self._is_red(piece) != is_red_turn:
                    continue

                attacker_value = self.PIECE_VALUES.get(piece.lower(), 0)
                attacks = self._get_attacks(board, r, c)

                for target_pos in attacks:
                    tr, tc = target_pos
                    target = board[tr][tc]
                    if not target:
                        continue
                    if self._is_red(target) == is_red_turn:
                        continue

                    target_value = self.PIECE_VALUES.get(target.lower(), 0)
                    is_unprotected = not self._is_protected(
                        board, tr, tc, not is_red_turn
                    )

                    favorable_by_value = target_value > attacker_value
                    favorable_free = is_unprotected

                    if not (favorable_by_value or favorable_free):
                        continue

                    key = ((r, c), target_pos)
                    if key in seen:
                        continue
                    seen.add(key)

                    tag = get_tag_by_name("favorable_exchange")
                    if tag:
                        results.append(TagDetectionResult(
                            tag=tag,
                            detected=True,
                            confidence=1.0,
                            bind_pieces=[
                                self._bind_piece(piece, r, c),
                                self._bind_piece(target, tr, tc)
                            ],
                            metadata={
                                "attacker_value": attacker_value,
                                "target_value": target_value,
                                "value_gain": target_value - attacker_value,
                                "target_is_unprotected": is_unprotected,
                                "exchange_type": "material_gain" if favorable_by_value
                                                else "free_capture"
                            }
                        ))

        return results

    def _detect_phase(self, board: List[List[str]]) -> List[TagDetectionResult]:
        """
        检测局面阶段

        步骤1: 统计总棋子数
        步骤2: 按阈值判断阶段（三标签互斥）
        步骤3: 附带详细棋子清单到 metadata
        """
        results = []

        red_count = 0
        black_count = 0
        for r in range(10):
            for c in range(9):
                piece = board[r][c]
                if piece:
                    if self._is_red(piece):
                        red_count += 1
                    else:
                        black_count += 1

        total = red_count + black_count

        if total >= 28:
            tag_name = "phase_opening"
            phase_label = "开局"
        elif total >= 15:
            tag_name = "phase_middlegame"
            phase_label = "中局"
        else:
            tag_name = "phase_endgame"
            phase_label = "残局"

        tag = get_tag_by_name(tag_name)
        if tag:
            results.append(TagDetectionResult(
                tag=tag,
                detected=True,
                confidence=1.0,
                bind_pieces=[],
                metadata={
                    "phase": phase_label,
                    "total_pieces": total,
                    "red_pieces": red_count,
                    "black_pieces": black_count
                }
            ))

        return results

    def _detect_king_safety(self, board: List[List[str]], 
                            is_red_turn: bool) -> List[TagDetectionResult]:
        """
        检测将/帅安全度

        步骤1: 遍历双方各自检测
        步骤2: 统计防守子力
        步骤3: 统计逃跑路线
        步骤4: 统计威胁源
        步骤5: 计算安全分，低于阈值触发标签
        """
        results = []

        for color in [True, False]:
            king_pos = self._find_king(board, color)
            if not king_pos:
                continue

            defenders = self._count_king_defenders(board, king_pos, color)

            escape_routes = len(
                self.rules_engine.get_legal_moves(board, king_pos[0], king_pos[1])
            )

            adjacent = self._get_adjacent_positions(king_pos)
            palace_adj = [p for p in adjacent if self._is_in_palace(p, color)]
            threat_count = 0
            for adj_pos in palace_adj:
                for r in range(10):
                    for c in range(9):
                        piece = board[r][c]
                        if piece and self._is_red(piece) != color:
                            if adj_pos in self._get_attacks(board, r, c):
                                threat_count += 1
                                break

            safety_score = (defenders * 2) + escape_routes - (threat_count * 2)
            if self._is_in_check(board, color):
                safety_score -= 4

            if safety_score <= 1:
                tag = get_tag_by_name("king_safety_critical")
                if tag:
                    king_piece = board[king_pos[0]][king_pos[1]]
                    results.append(TagDetectionResult(
                        tag=tag,
                        detected=True,
                        confidence=1.0,
                        bind_pieces=[
                            self._bind_piece(king_piece, king_pos[0], king_pos[1])
                        ],
                        metadata={
                            "color": "red" if color else "black",
                            "defenders": defenders,
                            "escape_routes": escape_routes,
                            "threat_count": threat_count,
                            "safety_score": safety_score
                        }
                    ))

        return results

    def _count_king_defenders(self, board: List[List[str]], 
                               king_pos: Tuple[int, int], is_red: bool) -> int:
        """
        统计保护将/帅的同色棋子数
        
        包括：
        1. 士/仕：在九宫内保护将/帅
        2. 象/相：可以飞到将/帅相邻位置
        3. 其他棋子：攻击范围包含将/帅相邻位置
        """
        count = 0
        king_adjacent = self._get_adjacent_positions(king_pos)
        palace_adj = [p for p in king_adjacent if self._is_in_palace(p, is_red)]
        
        for r in range(10):
            for c in range(9):
                piece = board[r][c]
                if not piece:
                    continue
                if self._is_red(piece) != is_red:
                    continue
                if (r, c) == king_pos:
                    continue
                
                piece_type = piece.lower()
                
                if piece_type == 'a':
                    if self._is_in_palace((r, c), is_red):
                        count += 1
                elif piece_type == 'b':
                    attacks = self._get_attacks(board, r, c)
                    if any(adj in attacks for adj in palace_adj):
                        count += 1
                else:
                    attacks = self._get_attacks(board, r, c)
                    if any(adj in attacks for adj in palace_adj):
                        count += 1
        
        return count

    def _detect_initiative(self, board: List[List[str]], 
                           is_red_turn: bool) -> List[TagDetectionResult]:
        """
        检测主动权

        步骤1: 统计己方强制手段数
        步骤2: 统计敌方强制手段数
        步骤3: 对比判断主动权归属
        """
        results = []

        my_forcing = self._count_forcing_potential(board, is_red_turn)
        enemy_forcing = self._count_forcing_potential(board, not is_red_turn)

        has_initiative = (my_forcing > 0) and (my_forcing >= enemy_forcing)

        if has_initiative:
            tag = get_tag_by_name("has_initiative")
            if tag:
                results.append(TagDetectionResult(
                    tag=tag,
                    detected=True,
                    confidence=1.0,
                    bind_pieces=[],
                    metadata={
                        "my_forcing_count": my_forcing,
                        "enemy_forcing_count": enemy_forcing
                    }
                ))

        return results

    def _count_forcing_potential(self, board: List[List[str]], is_red: bool) -> int:
        """
        统计一方的强制手段潜力

        强制手段包括：
        1. 当前已将军（权重最高）
        2. 可捉对方无根子的棋子数
        3. 可直接将军的着法数（试走检测）

        返回加权计数
        """
        score = 0

        if self._is_in_check(board, not is_red):
            score += 3

        for r in range(10):
            for c in range(9):
                piece = board[r][c]
                if not piece or self._is_red(piece) != is_red:
                    continue

                attacks = self._get_attacks(board, r, c)
                for target_pos in attacks:
                    target = board[target_pos[0]][target_pos[1]]
                    if not target:
                        continue
                    if self._is_red(target) == is_red:
                        continue
                    if not self._is_protected(board, target_pos[0], target_pos[1],
                                              not is_red):
                        score += 1

        return score

    def _detect_forcing_move(self, board: List[List[str]], 
                              move: str, is_red_turn: bool) -> List[TagDetectionResult]:
        """
        检测强制手段（动态）

        步骤1: 执行走法
        步骤2: 检查是否将军
        步骤3: 检查是否吃无根子
        步骤4: 检查是否将死
        """
        results = []

        (from_row, from_col), (to_row, to_col) = self._parse_uci(move)
        moving_piece = board[from_row][from_col]
        if not moving_piece:
            return results

        new_board = self._apply_move(board, move)

        gives_check = self._is_in_check(new_board, not is_red_turn)

        captures_unprotected = False
        target_piece = board[to_row][to_col]
        if target_piece and self._is_red(target_piece) != is_red_turn:
            if not self._is_protected(board, to_row, to_col, not is_red_turn):
                captures_unprotected = True

        threatens_checkmate = False
        if gives_check and not self._has_legal_moves(new_board, not is_red_turn):
            threatens_checkmate = True

        is_forcing = gives_check or captures_unprotected or threatens_checkmate

        if is_forcing:
            tag = get_tag_by_name("is_forcing_move")
            if tag:
                results.append(TagDetectionResult(
                    tag=tag,
                    detected=True,
                    confidence=1.0,
                    bind_pieces=[
                        self._bind_piece(moving_piece, from_row, from_col)
                    ],
                    metadata={
                        "move": move,
                        "gives_check": gives_check,
                        "captures_unprotected": captures_unprotected,
                        "threatens_checkmate": threatens_checkmate
                    }
                ))

        return results

    # =========================================================================
    # 走法质量检测（Phase 1 新增）
    # =========================================================================

    def detect_move_quality(self, fen_before: str, move: str) -> List[TagDetectionResult]:
        """
        走法质量检测 - 需要前后对比

        Args:
            fen_before: 走法前的局面FEN
            move: UCI格式走法 (如 "h2e2")

        Returns:
            List[TagDetectionResult]: 走法质量标签列表
        """
        board = self._fen_to_board(fen_before)
        is_red_turn = self._is_red_turn(fen_before)
        results = []

        # 解析走法
        (from_row, from_col), (to_row, to_col) = self._parse_uci(move)
        moving_piece = board[from_row][from_col]
        if not moving_piece:
            return results

        # 执行走法后的局面
        new_board = self._apply_move(board, move)

        # 1. 检测吃子走法
        results.extend(self._detect_move_capture(board, move, moving_piece, to_row, to_col))

        # 2. 检测将军走法
        results.extend(self._detect_move_check(new_board, move, moving_piece, is_red_turn))

        # 3. 检测失误走法
        results.extend(self._detect_move_blunder(board, new_board, move, moving_piece, is_red_turn))

        # 4. 检测防守走法
        results.extend(self._detect_move_defense(board, new_board, move, moving_piece, is_red_turn))

        # 5. 检测逃脱走法
        results.extend(self._detect_move_escape(board, new_board, move, moving_piece, is_red_turn))

        # 6. 检测位置改善
        results.extend(self._detect_move_improvement(board, new_board, move, moving_piece, from_row, from_col, to_row, to_col))

        return results

    def _detect_move_capture(self, board: List[List[str]], move: str,
                             moving_piece: str, to_row: int, to_col: int) -> List[TagDetectionResult]:
        """检测吃子走法"""
        results = []
        target_piece = board[to_row][to_col]

        if target_piece and self._is_red(target_piece) != self._is_red(moving_piece):
            tag = get_tag_by_name("move_is_capture")
            if tag:
                results.append(TagDetectionResult(
                    tag=tag,
                    detected=True,
                    confidence=1.0,
                    bind_pieces=[
                        self._bind_piece(moving_piece, to_row, to_col),
                        self._bind_piece(target_piece, to_row, to_col)
                    ],
                    metadata={
                        "move": move,
                        "captured_piece": target_piece,
                        "captured_value": self.PIECE_VALUES.get(target_piece.lower(), 0)
                    }
                ))

        return results

    def _detect_move_check(self, new_board: List[List[str]], move: str,
                           moving_piece: str, is_red_turn: bool) -> List[TagDetectionResult]:
        """检测将军走法"""
        results = []

        if self._is_in_check(new_board, not is_red_turn):
            tag = get_tag_by_name("move_gives_check")
            if tag:
                results.append(TagDetectionResult(
                    tag=tag,
                    detected=True,
                    confidence=1.0,
                    bind_pieces=[self._bind_piece(moving_piece, 0, 0)],  # 位置在new_board中
                    metadata={"move": move}
                ))

        return results

    def _detect_move_blunder(self, board: List[List[str]], new_board: List[List[str]],
                             move: str, moving_piece: str, is_red_turn: bool) -> List[TagDetectionResult]:
        """检测严重失误"""
        results = []

        # 检查走法后是否丢子（价值>=300）
        material_loss = self._calculate_material_loss(board, new_board, is_red_turn)

        # 检查走法后是否被将死
        is_checkmated = self._is_in_check(new_board, is_red_turn) and not self._has_legal_moves(new_board, is_red_turn)

        if material_loss >= 300 or is_checkmated:
            tag = get_tag_by_name("move_is_blunder")
            if tag:
                reason = "被将死" if is_checkmated else f"丢子{material_loss}分"
                results.append(TagDetectionResult(
                    tag=tag,
                    detected=True,
                    confidence=1.0,
                    bind_pieces=[self._bind_piece(moving_piece, 0, 0)],
                    metadata={
                        "move": move,
                        "material_loss": material_loss,
                        "is_checkmated": is_checkmated,
                        "reason": reason
                    }
                ))

        return results

    def _detect_move_defense(self, board: List[List[str]], new_board: List[List[str]],
                             move: str, moving_piece: str, is_red_turn: bool) -> List[TagDetectionResult]:
        """检测防守走法"""
        results = []

        # 找出走法前无根、走法后有根的己方棋子
        unprotected_before = self._get_unprotected_pieces(board, is_red_turn)
        unprotected_after = self._get_unprotected_pieces(new_board, is_red_turn)

        # 新获得保护的棋子
        newly_protected = unprotected_before - unprotected_after

        if newly_protected:
            tag = get_tag_by_name("move_defends_piece")
            if tag:
                bind_pieces = [self._bind_piece(moving_piece, 0, 0)]
                for piece_pos in newly_protected:
                    r, c = piece_pos
                    piece = new_board[r][c]
                    if piece:
                        bind_pieces.append(self._bind_piece(piece, r, c))

                results.append(TagDetectionResult(
                    tag=tag,
                    detected=True,
                    confidence=1.0,
                    bind_pieces=bind_pieces,
                    metadata={
                        "move": move,
                        "defended_pieces": list(newly_protected)
                    }
                ))

        return results

    def _detect_move_escape(self, board: List[List[str]], new_board: List[List[str]],
                            move: str, moving_piece: str, is_red_turn: bool) -> List[TagDetectionResult]:
        """检测逃脱走法"""
        results = []

        (from_row, from_col), (to_row, to_col) = self._parse_uci(move)

        # 检查走法前是否被攻击
        was_under_attack = self._is_piece_under_attack(board, from_row, from_col, is_red_turn)

        # 检查走法后是否安全
        is_now_safe = not self._is_piece_under_attack(new_board, to_row, to_col, is_red_turn)

        if was_under_attack and is_now_safe:
            tag = get_tag_by_name("move_escapes_threat")
            if tag:
                results.append(TagDetectionResult(
                    tag=tag,
                    detected=True,
                    confidence=1.0,
                    bind_pieces=[self._bind_piece(moving_piece, to_row, to_col)],
                    metadata={
                        "move": move,
                        "escaped_from": (from_row, from_col),
                        "escaped_to": (to_row, to_col)
                    }
                ))

        return results

    def _detect_move_improvement(self, board: List[List[str]], new_board: List[List[str]],
                                 move: str, moving_piece: str,
                                 from_row: int, from_col: int, to_row: int, to_col: int) -> List[TagDetectionResult]:
        """检测位置改善"""
        results = []

        # 计算活跃度变化（控制点数量）
        activity_before = len(self._get_attacks(board, from_row, from_col))
        activity_after = len(self._get_attacks(new_board, to_row, to_col))

        if activity_after > activity_before:
            tag = get_tag_by_name("move_improves_position")
            if tag:
                results.append(TagDetectionResult(
                    tag=tag,
                    detected=True,
                    confidence=1.0,
                    bind_pieces=[self._bind_piece(moving_piece, to_row, to_col)],
                    metadata={
                        "move": move,
                        "activity_before": activity_before,
                        "activity_after": activity_after,
                        "improvement": activity_after - activity_before
                    }
                ))

        return results

    # =========================================================================
    # 战略评估检测（Phase 2 新增）
    # =========================================================================

    def detect_strategic_tags(self, fen: str) -> List[TagDetectionResult]:
        """
        战略评估检测

        Args:
            fen: 局面FEN

        Returns:
            List[TagDetectionResult]: 战略标签列表
        """
        board = self._fen_to_board(fen)
        is_red_turn = self._is_red_turn(fen)
        results = []

        # 1. 检测控制开放线
        results.extend(self._detect_open_file_control(board))

        # 2. 检测子力活跃
        results.extend(self._detect_active_pieces(board, is_red_turn))

        # 3. 检测子力协同
        results.extend(self._detect_piece_coordination(board, is_red_turn))

        # 4. 检测将帅安全（正面）
        results.extend(self._detect_king_safety_good(board, is_red_turn))

        # 5. 检测空间优势
        results.extend(self._detect_space_advantage(board, is_red_turn))

        return results

    def _detect_open_file_control(self, board: List[List[str]]) -> List[TagDetectionResult]:
        """检测控制开放线"""
        results = []

        for col in range(9):
            # 检查该列是否有车控制
            red_rook_row = None
            black_rook_row = None

            for row in range(10):
                piece = board[row][col]
                if piece == 'R':
                    red_rook_row = row
                elif piece == 'r':
                    black_rook_row = row

            # 检查是否开放线（两车之间无其他子）
            if red_rook_row is not None and black_rook_row is not None:
                is_open = True
                for r in range(min(red_rook_row, black_rook_row) + 1, max(red_rook_row, black_rook_row)):
                    if board[r][col]:
                        is_open = False
                        break

                if is_open:
                    tag = get_tag_by_name("controls_open_file")
                    if tag:
                        results.append(TagDetectionResult(
                            tag=tag,
                            detected=True,
                            confidence=1.0,
                            bind_pieces=[self._bind_piece('R', red_rook_row, col)],
                            metadata={"file": col + 1}
                        ))

        return results

    def _detect_active_pieces(self, board: List[List[str]], is_red_turn: bool) -> List[TagDetectionResult]:
        """检测子力活跃"""
        results = []

        total_attacks = 0
        active_count = 0

        for r in range(10):
            for c in range(9):
                piece = board[r][c]
                if not piece or self._is_red(piece) != is_red_turn:
                    continue

                attacks = self._get_attacks(board, r, c)
                attack_count = len(attacks)
                total_attacks += attack_count

                # 活跃子：控制3个以上点
                if attack_count >= 3:
                    active_count += 1

        # 如果有2个以上活跃子，标记为子力活跃
        if active_count >= 2:
            tag = get_tag_by_name("has_active_pieces")
            if tag:
                results.append(TagDetectionResult(
                    tag=tag,
                    detected=True,
                    confidence=1.0,
                    bind_pieces=[],
                    metadata={
                        "active_count": active_count,
                        "total_attacks": total_attacks
                    }
                ))

        return results

    def _detect_piece_coordination(self, board: List[List[str]], is_red_turn: bool) -> List[TagDetectionResult]:
        """检测子力协同"""
        results = []

        # 统计每个位置被多少己方子攻击
        attack_counts: Dict[Tuple[int, int], List[str]] = {}

        for r in range(10):
            for c in range(9):
                piece = board[r][c]
                if not piece or self._is_red(piece) != is_red_turn:
                    continue

                attacks = self._get_attacks(board, r, c)
                for target in attacks:
                    if target not in attack_counts:
                        attack_counts[target] = []
                    attack_counts[target].append(self._bind_piece(piece, r, c))

        # 找出被2个以上子攻击的位置
        coordinated_positions = {pos: pieces for pos, pieces in attack_counts.items() if len(pieces) >= 2}

        if len(coordinated_positions) >= 1:
            tag = get_tag_by_name("piece_coordination")
            if tag:
                # 取第一个协同位置作为绑定
                first_pos = list(coordinated_positions.keys())[0]
                bind_pieces = coordinated_positions[first_pos]

                results.append(TagDetectionResult(
                    tag=tag,
                    detected=True,
                    confidence=1.0,
                    bind_pieces=bind_pieces,
                    metadata={
                        "coordinated_count": len(coordinated_positions),
                        "positions": [f"({c+1},{10-r})" for r, c in coordinated_positions.keys()]
                    }
                ))

        return results

    def _detect_king_safety_good(self, board: List[List[str]], is_red_turn: bool) -> List[TagDetectionResult]:
        """检测将帅安全（正面状态）"""
        results = []

        king_pos = self._find_king(board, is_red_turn)
        if not king_pos:
            return results

        king_r, king_c = king_pos

        # 检查周围防守子数量
        defenders_count = 0
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0:
                    continue
                nr, nc = king_r + dr, king_c + dc
                if 0 <= nr < 10 and 0 <= nc < 9:
                    piece = board[nr][nc]
                    if piece and self._is_red(piece) == is_red_turn:
                        defenders_count += 1

        # 检查是否有直接威胁
        is_under_threat = self._is_piece_under_attack(board, king_r, king_c, is_red_turn)

        # 周围有2个以上防守子且无直接威胁
        if defenders_count >= 2 and not is_under_threat:
            tag = get_tag_by_name("king_safety_good")
            if tag:
                king = 'K' if is_red_turn else 'k'
                results.append(TagDetectionResult(
                    tag=tag,
                    detected=True,
                    confidence=1.0,
                    bind_pieces=[self._bind_piece(king, king_r, king_c)],
                    metadata={
                        "defenders_count": defenders_count,
                        "under_threat": False
                    }
                ))

        return results

    def _detect_space_advantage(self, board: List[List[str]], is_red_turn: bool) -> List[TagDetectionResult]:
        """检测空间优势"""
        results = []

        # 计算己方控制的格子数
        red_control = set()
        black_control = set()

        for r in range(10):
            for c in range(9):
                piece = board[r][c]
                if not piece:
                    continue

                attacks = self._get_attacks(board, r, c)
                control_set = red_control if self._is_red(piece) else black_control
                control_set.update(attacks)

        my_control = red_control if is_red_turn else black_control
        opp_control = black_control if is_red_turn else red_control

        # 控制点数多10%以上算优势
        if len(my_control) > len(opp_control) * 1.1:
            tag = get_tag_by_name("has_space_advantage")
            if tag:
                results.append(TagDetectionResult(
                    tag=tag,
                    detected=True,
                    confidence=1.0,
                    bind_pieces=[],
                    metadata={
                        "my_control": len(my_control),
                        "opp_control": len(opp_control)
                    }
                ))

        return results

    # =========================================================================
    # 辅助方法
    # =========================================================================

    def _calculate_material_loss(self, board_before: List[List[str]],
                                  board_after: List[List[str]], is_red: bool) -> int:
        """计算走法后的子力损失"""
        def count_material(board: List[List[str]], is_red_side: bool) -> int:
            total = 0
            for r in range(10):
                for c in range(9):
                    piece = board[r][c]
                    if piece and self._is_red(piece) == is_red_side:
                        total += self.PIECE_VALUES.get(piece.lower(), 0)
            return total

        material_before = count_material(board_before, is_red)
        material_after = count_material(board_after, is_red)

        return max(0, material_before - material_after)

    def _get_unprotected_pieces(self, board: List[List[str]], is_red: bool) -> Set[Tuple[int, int]]:
        """获取无根棋子位置集合"""
        unprotected = set()

        for r in range(10):
            for c in range(9):
                piece = board[r][c]
                if piece and self._is_red(piece) == is_red:
                    if not self._is_protected(board, r, c, is_red):
                        unprotected.add((r, c))

        return unprotected

    def _is_piece_under_attack(self, board: List[List[str]], row: int, col: int, is_red: bool) -> bool:
        """检查某个位置是否被对方攻击"""
        for r in range(10):
            for c in range(9):
                piece = board[r][c]
                if piece and self._is_red(piece) != is_red:
                    attacks = self._get_attacks(board, r, c)
                    if (row, col) in attacks:
                        return True
        return False


def detect_tactical_tags(fen: str, mode: DetectionMode = DetectionMode.STATIC) -> Any:
    """
    便捷函数：检测战术标签
    
    Args:
        fen: 局面FEN
        mode: 检测模式
        
    Returns:
        检测结果
    """
    detector = TacticalDetector()
    
    if mode == DetectionMode.STATIC:
        return detector.detect_static(fen)
    elif mode == DetectionMode.DYNAMIC:
        return detector.detect_full(fen)
    else:
        return detector.detect_full(fen)


def generate_evidence_map(fen: str, include_dynamic: bool = True) -> Dict[str, Any]:
    """
    便捷函数：生成Evidence Map
    
    Args:
        fen: 局面FEN
        include_dynamic: 是否包含动态检测
        
    Returns:
        Evidence Map字典
    """
    detector = TacticalDetector()
    
    if include_dynamic:
        result = detector.detect_full(fen)
        return result.to_evidence_map()
    else:
        result = detector.detect_static(fen)
        return result.to_evidence_map()
