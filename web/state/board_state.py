"""
棋盘状态管理

职责: 管理棋盘、走法、游戏状态

文档依据: JOINT_REFACTOR_ARCHITECTURE.md 棋盘组件
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Union


PIECE_NAMES = {
    'K': '帅', 'k': '将', 'A': '仕', 'a': '士',
    'B': '相', 'b': '象', 'R': '车', 'r': '車',
    'C': '炮', 'c': '砲', 'N': '马', 'n': '馬',
    'P': '兵', 'p': '卒',
}

INITIAL_BOARD = [
    ['r', 'n', 'b', 'a', 'k', 'a', 'b', 'n', 'r'],
    ['', '', '', '', '', '', '', '', ''],
    ['', 'c', '', '', '', '', '', 'c', ''],
    ['p', '', 'p', '', 'p', '', 'p', '', 'p'],
    ['', '', '', '', '', '', '', '', ''],
    ['', '', '', '', '', '', '', '', ''],
    ['P', '', 'P', '', 'P', '', 'P', '', 'P'],
    ['', 'C', '', '', '', '', '', 'C', ''],
    ['', '', '', '', '', '', '', '', ''],
    ['R', 'N', 'B', 'A', 'K', 'A', 'B', 'N', 'R'],
]


@dataclass
class BoardState:
    """
    棋盘状态

    字段:
        board: 棋盘二维数组（10行9列）
        red_to_move: 是否红方走棋
        selected_pos: 选中的位置（行, 列）
        legal_moves: 合法走法列表
        move_history: 走法历史（中文描述）
        iccs_moves: ICCS格式走法历史
        last_move_info: 最后一步走法信息
        game_over: 游戏是否结束
        winner: 胜者（红方/黑方/None）
    """
    board: List[List[str]] = field(default_factory=lambda: [row[:] for row in INITIAL_BOARD])
    red_to_move: bool = True
    selected_pos: Optional[Tuple[int, int]] = None
    legal_moves: List[Tuple[int, int]] = field(default_factory=list)
    move_history: List[str] = field(default_factory=list)
    iccs_moves: List[str] = field(default_factory=list)
    last_move_info: Optional[Dict] = None
    game_over: bool = False
    winner: Optional[str] = None

    def reset(self) -> None:
        """重置棋盘到初始状态"""
        self.board = [row[:] for row in INITIAL_BOARD]
        self.red_to_move = True
        self.selected_pos = None
        self.legal_moves = []
        self.move_history = []
        self.iccs_moves = []
        self.last_move_info = None
        self.game_over = False
        self.winner = None

    def select_piece(self, row: int, col: int):
        """
        选中棋子

        Args:
            row: 行号（0-9）
            col: 列号（0-8）

        Returns:
            合法走法列表，如果位置没有棋子返回None
        """
        piece = self.board[row][col]
        if not piece:
            return None

        # 检查是否是当前方的棋子
        is_red_piece = piece.isupper()
        if is_red_piece != self.red_to_move:
            return None

        self.selected_pos = (row, col)
        # TODO: 调用规则引擎生成合法走法
        self.legal_moves = []

        return self.legal_moves

    def deselect_piece(self) -> None:
        """取消选中"""
        self.selected_pos = None
        self.legal_moves = []

    def make_move(self, from_row: int, from_col: int,
                 to_row: int, to_col: int):
        """
        走棋

        Args:
            from_row: 起始行号
            from_col: 起始列号
            to_row: 目标行号
            to_col: 目标列号

        Returns:
            走棋描述，如果走法不合法返回None
        """
        # 检查坐标是否在范围内
        if not (0 <= from_row < 10 and 0 <= from_col < 9 and
                0 <= to_row < 10 and 0 <= to_col < 9):
            return None

        # 检查走法是否在合法列表中
        if (to_row, to_col) not in self.legal_moves:
            return None

        # 执行走棋
        piece = self.board[from_row][from_col]
        captured = self.board[to_row][to_col]

        self.board[from_row][from_col] = ''
        self.board[to_row][to_col] = piece

        # 记录走法
        piece_name = PIECE_NAMES.get(piece, piece)
        move_desc = f"{'红' if self.red_to_move else '黑'}{piece_name}: {from_col}{from_row} → {to_col}{to_row}"
        self.move_history.append(move_desc)

        # 记录ICCS走法
        iccs_move = f"{chr(ord('a') + from_col)}{from_row}{chr(ord('a') + to_col)}{to_row}"
        self.iccs_moves.append(iccs_move)

        # 记录最后一步走法信息
        self.last_move_info = {
            "from_pos": (from_row, from_col),
            "to_pos": (to_row, to_col),
            "piece": piece,
            "captured": captured,
            "notation": iccs_move
        }

        # 检查是否将死
        if captured and captured.lower() == 'k':
            self.game_over = True
            self.winner = "红方" if self.red_to_move else "黑方"
        else:
            # 切换走棋方
            self.red_to_move = not self.red_to_move

        # 清除选中状态
        self.selected_pos = None
        self.legal_moves = []

        return move_desc

    def get_move_history(self) -> str:
        """
        获取走法历史字符串

        Returns:
            格式化的走法历史
        """
        return "\n".join(self.move_history)

    def is_game_over(self) -> bool:
        """游戏是否结束"""
        return self.game_over

    def get_winner(self):
        """获取胜者"""
        return self.winner

    def get_fen(self) -> str:
        """
        获取当前局面FEN

        Returns:
            FEN字符串
        """
        # TODO: 实现完整的FEN生成逻辑
        # 这里返回简化版FEN
        fen = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR"
        if self.red_to_move:
            fen += " w - - 0 1"
        else:
            fen += " b - - 0 1"
        return fen
