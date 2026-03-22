"""
Xiangqi Hybrid Agent - Interactive Board Component

Features:
- 交互式棋盘（点击走棋）
- 走法规则检测
- 棋子可视化

Reference:
  - PRD: 3.1 下棋谱模式、3.2 人机对战模式
"""

from typing import List, Tuple, Optional, Dict, Set
from dataclasses import dataclass
from enum import Enum
import copy


class PieceType(Enum):
    KING = "k"
    ADVISOR = "a"
    ELEPHANT = "e"
    ROOK = "r"
    CANNON = "c"
    KNIGHT = "n"
    PAWN = "p"


PIECE_NAMES = {
    "K": "帅", "k": "将",
    "A": "仕", "a": "士",
    "E": "相", "e": "象",
    "R": "车", "r": "车",
    "C": "炮", "c": "炮",
    "N": "马", "n": "马",
    "P": "兵", "p": "卒",
}

INITIAL_BOARD = [
    ["r", "n", "e", "a", "k", "a", "e", "n", "r"],
    ["", "", "", "", "", "", "", "", ""],
    ["", "c", "", "", "", "", "", "c", ""],
    ["p", "", "p", "", "p", "", "p", "", "p"],
    ["", "", "", "", "", "", "", "", ""],
    ["", "", "", "", "", "", "", "", ""],
    ["P", "", "P", "", "P", "", "P", "", "P"],
    ["", "C", "", "", "", "", "", "C", ""],
    ["", "", "", "", "", "", "", "", ""],
    ["R", "N", "E", "A", "K", "A", "E", "N", "R"],
]


@dataclass
class Move:
    from_pos: Tuple[int, int]
    to_pos: Tuple[int, int]
    piece: str
    captured: str = ""
    
    def to_iccs(self) -> str:
        fc = chr(ord('A') + self.from_pos[1])
        fr = str(self.from_pos[0])
        tc = chr(ord('A') + self.to_pos[1])
        tr = str(self.to_pos[0])
        return f"{fc}{fr}-{tc}{tr}"
    
    def to_chinese(self) -> str:
        piece_name = PIECE_NAMES.get(self.piece, self.piece)
        return f"{piece_name}"


class XiangqiRules:
    @staticmethod
    def is_red(piece: str) -> bool:
        return piece.isupper()
    
    @staticmethod
    def is_black(piece: str) -> bool:
        return piece.islower()
    
    @staticmethod
    def get_legal_moves(board: List[List[str]], row: int, col: int, red_to_move: bool) -> List[Tuple[int, int]]:
        piece = board[row][col]
        if not piece:
            return []
        
        is_red = XiangqiRules.is_red(piece)
        if is_red != red_to_move:
            return []
        
        piece_type = piece.lower()
        legal_moves = []
        
        if piece_type == 'k':
            legal_moves = XiangqiRules._king_moves(board, row, col, is_red)
        elif piece_type == 'a':
            legal_moves = XiangqiRules._advisor_moves(board, row, col, is_red)
        elif piece_type == 'e':
            legal_moves = XiangqiRules._elephant_moves(board, row, col, is_red)
        elif piece_type == 'r':
            legal_moves = XiangqiRules._rook_moves(board, row, col, is_red)
        elif piece_type == 'c':
            legal_moves = XiangqiRules._cannon_moves(board, row, col, is_red)
        elif piece_type == 'n':
            legal_moves = XiangqiRules._knight_moves(board, row, col, is_red)
        elif piece_type == 'p':
            legal_moves = XiangqiRules._pawn_moves(board, row, col, is_red)
        
        legal_moves = [m for m in legal_moves if XiangqiRules._is_valid_target(board, m[0], m[1], is_red)]
        
        return legal_moves
    
    @staticmethod
    def _is_valid_target(board: List[List[str]], row: int, col: int, is_red: bool) -> bool:
        if not (0 <= row < 10 and 0 <= col < 9):
            return False
        target = board[row][col]
        if not target:
            return True
        return XiangqiRules.is_red(target) != is_red
    
    @staticmethod
    def _king_moves(board: List[List[str]], row: int, col: int, is_red: bool) -> List[Tuple[int, int]]:
        moves = []
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
        
        min_row, max_row = (7, 9) if is_red else (0, 2)
        min_col, max_col = 3, 5
        
        for dr, dc in directions:
            nr, nc = row + dr, col + dc
            if min_row <= nr <= max_row and min_col <= nc <= max_col:
                moves.append((nr, nc))
        
        enemy_king_col = col
        for r in range(10):
            if r == row:
                continue
            piece = board[r][enemy_king_col]
            if piece and piece.lower() == 'k':
                blocked = False
                start, end = min(r, row) + 1, max(r, row)
                for check_r in range(start, end):
                    if board[check_r][enemy_king_col]:
                        blocked = True
                        break
                if not blocked:
                    moves.append((r, enemy_king_col))
        
        return moves
    
    @staticmethod
    def _advisor_moves(board: List[List[str]], row: int, col: int, is_red: bool) -> List[Tuple[int, int]]:
        moves = []
        directions = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
        
        min_row, max_row = (7, 9) if is_red else (0, 2)
        min_col, max_col = 3, 5
        
        for dr, dc in directions:
            nr, nc = row + dr, col + dc
            if min_row <= nr <= max_row and min_col <= nc <= max_col:
                moves.append((nr, nc))
        
        return moves
    
    @staticmethod
    def _elephant_moves(board: List[List[str]], row: int, col: int, is_red: bool) -> List[Tuple[int, int]]:
        moves = []
        directions = [(2, 2), (2, -2), (-2, 2), (-2, -2)]
        blocks = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
        
        min_row, max_row = (5, 9) if is_red else (0, 4)
        
        for i, (dr, dc) in enumerate(directions):
            nr, nc = row + dr, col + dc
            br, bc = row + blocks[i][0], col + blocks[i][1]
            
            if min_row <= nr <= max_row and 0 <= nc < 9:
                if not board[br][bc]:
                    moves.append((nr, nc))
        
        return moves
    
    @staticmethod
    def _rook_moves(board: List[List[str]], row: int, col: int, is_red: bool) -> List[Tuple[int, int]]:
        moves = []
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
        
        for dr, dc in directions:
            nr, nc = row + dr, col + dc
            while 0 <= nr < 10 and 0 <= nc < 9:
                if board[nr][nc]:
                    moves.append((nr, nc))
                    break
                moves.append((nr, nc))
                nr += dr
                nc += dc
        
        return moves
    
    @staticmethod
    def _cannon_moves(board: List[List[str]], row: int, col: int, is_red: bool) -> List[Tuple[int, int]]:
        moves = []
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
        
        for dr, dc in directions:
            nr, nc = row + dr, col + dc
            jumped = False
            
            while 0 <= nr < 10 and 0 <= nc < 9:
                if board[nr][nc]:
                    if jumped:
                        moves.append((nr, nc))
                        break
                    else:
                        jumped = True
                else:
                    if not jumped:
                        moves.append((nr, nc))
                
                nr += dr
                nc += dc
        
        return moves
    
    @staticmethod
    def _knight_moves(board: List[List[str]], row: int, col: int, is_red: bool) -> List[Tuple[int, int]]:
        moves = []
        knight_moves = [
            ((-2, -1), (-1, 0)),
            ((-2, 1), (-1, 0)),
            ((2, -1), (1, 0)),
            ((2, 1), (1, 0)),
            ((-1, -2), (0, -1)),
            ((-1, 2), (0, 1)),
            ((1, -2), (0, -1)),
            ((1, 2), (0, 1)),
        ]
        
        for (dr, dc), (br, bc) in knight_moves:
            nr, nc = row + dr, col + dc
            block_r, block_c = row + br, col + bc
            
            if 0 <= nr < 10 and 0 <= nc < 9:
                if not board[block_r][block_c]:
                    moves.append((nr, nc))
        
        return moves
    
    @staticmethod
    def _pawn_moves(board: List[List[str]], row: int, col: int, is_red: bool) -> List[Tuple[int, int]]:
        moves = []
        
        forward = -1 if is_red else 1
        crossed_river = (row <= 4) if is_red else (row >= 5)
        
        nr = row + forward
        if 0 <= nr < 10:
            moves.append((nr, col))
        
        if crossed_river:
            for dc in [-1, 1]:
                nc = col + dc
                if 0 <= nc < 9:
                    moves.append((row, nc))
        
        return moves


class InteractiveBoard:
    def __init__(self):
        self.board = [row[:] for row in INITIAL_BOARD]
        self.red_to_move = True
        self.selected_pos: Optional[Tuple[int, int]] = None
        self.legal_moves: List[Tuple[int, int]] = []
        self.move_history: List[Move] = []
        self.game_over = False
        self.winner: Optional[str] = None
    
    def reset(self):
        self.board = [row[:] for row in INITIAL_BOARD]
        self.red_to_move = True
        self.selected_pos = None
        self.legal_moves = []
        self.move_history = []
        self.game_over = False
        self.winner = None
    
    def select(self, row: int, col: int) -> Tuple[bool, str]:
        if self.game_over:
            return False, "游戏已结束"
        
        piece = self.board[row][col]
        
        if self.selected_pos:
            if (row, col) in self.legal_moves:
                return self._make_move(row, col)
            elif piece and XiangqiRules.is_red(piece) == self.red_to_move:
                self.selected_pos = (row, col)
                self.legal_moves = XiangqiRules.get_legal_moves(self.board, row, col, self.red_to_move)
                return True, f"选中 {PIECE_NAMES.get(piece, piece)}"
            else:
                self.selected_pos = None
                self.legal_moves = []
                return False, "取消选择"
        else:
            if piece and XiangqiRules.is_red(piece) == self.red_to_move:
                self.selected_pos = (row, col)
                self.legal_moves = XiangqiRules.get_legal_moves(self.board, row, col, self.red_to_move)
                return True, f"选中 {PIECE_NAMES.get(piece, piece)}"
            return False, "请选择己方棋子"
    
    def _make_move(self, to_row: int, to_col: int) -> Tuple[bool, str]:
        from_row, from_col = self.selected_pos
        piece = self.board[from_row][from_col]
        captured = self.board[to_row][to_col]
        
        move = Move(
            from_pos=(from_row, from_col),
            to_pos=(to_row, to_col),
            piece=piece,
            captured=captured
        )
        
        self.board[to_row][to_col] = piece
        self.board[from_row][from_col] = ""
        
        self.move_history.append(move)
        self.selected_pos = None
        self.legal_moves = []
        self.red_to_move = not self.red_to_move
        
        if captured and captured.lower() == 'k':
            self.game_over = True
            self.winner = "红方" if XiangqiRules.is_red(piece) else "黑方"
            return True, f"将死！{self.winner}获胜！"
        
        turn = "红方" if self.red_to_move else "黑方"
        return True, f"{move.to_iccs()} - {turn}走棋"
    
    def get_board_state(self) -> Dict:
        return {
            "board": [row[:] for row in self.board],
            "red_to_move": self.red_to_move,
            "selected": self.selected_pos,
            "legal_moves": self.legal_moves,
            "move_count": len(self.move_history),
            "game_over": self.game_over,
            "winner": self.winner,
        }
    
    def to_fen(self) -> str:
        rows = []
        for row in self.board:
            fen_row = ""
            empty = 0
            for cell in row:
                if cell:
                    if empty:
                        fen_row += str(empty)
                        empty = 0
                    fen_row += cell
                else:
                    empty += 1
            if empty:
                fen_row += str(empty)
            rows.append(fen_row)
        
        turn = "w" if self.red_to_move else "b"
        move_num = len(self.move_history) // 2 + 1
        
        return f"{'/'.join(rows)} {turn} - - 0 {move_num}"
    
    def from_fen(self, fen: str):
        parts = fen.split()
        board_str = parts[0]
        
        self.board = [[""] * 9 for _ in range(10)]
        for r, row_str in enumerate(board_str.split('/')):
            c = 0
            for ch in row_str:
                if ch.isdigit():
                    c += int(ch)
                else:
                    self.board[r][c] = ch
                    c += 1
        
        if len(parts) > 1:
            self.red_to_move = parts[1] == 'w'
        
        self.selected_pos = None
        self.legal_moves = []
        self.move_history = []
        self.game_over = False
        self.winner = None
