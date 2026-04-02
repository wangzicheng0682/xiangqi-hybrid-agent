"""
象棋规则引擎 - 完整版

职责: 实现所有象棋走法规则、合法走法生成、将军检测

文档依据: JOINT_REFACTOR_ARCHITECTURE.md 规则引擎

Phase 3完整实现:
- 所有棋子走法规则（将/士/象/车/马/炮/卒）
- 合法走法生成（包含将军检测）
- 九宫格边界
- 楚河汉界限制
"""

from typing import List, Tuple


class XiangqiRulesEngine:
    """
    象棋规则引擎

    完整实现所有象棋规则
    """

    @staticmethod
    def is_red(piece: str) -> bool:
        """判断棋子是否为红方"""
        return piece.isupper() if piece else False

    @staticmethod
    def is_black(piece: str) -> bool:
        """判断棋子是否为黑方"""
        return piece.islower() if piece else False

    @staticmethod
    def is_in_palace(row: int, col: int, is_red: bool) -> bool:
        """
        判断位置是否在九宫格内

        Args:
            row: 行号
            col: 列号
            is_red: 是否红方

        Returns:
            是否在九宫格内
        """
        if is_red:
            # 红方九宫：行7-9，列3-5
            return 7 <= row <= 9 and 3 <= col <= 5
        else:
            # 黑方九宫：行0-2，列3-5
            return 0 <= row <= 2 and 3 <= col <= 5

    @staticmethod
    def get_legal_moves(board: List[List[str]], row: int, col: int) -> List[Tuple[int, int]]:
        """
        获取合法走法

        Args:
            board: 棋盘二维数组
            row: 棋子行号
            col: 棋子列号

        Returns:
            合法走法列表 [(row, col), ...]
        """
        piece = board[row][col]
        if not piece:
            return []

        is_red = XiangqiRulesEngine.is_red(piece)
        piece_type = piece.lower()

        # 根据棋子类型调用对应的走法生成函数
        if piece_type == 'k':
            moves = XiangqiRulesEngine._king_moves(board, row, col, is_red)
        elif piece_type == 'a':
            moves = XiangqiRulesEngine._advisor_moves(board, row, col, is_red)
        elif piece_type == 'b':
            moves = XiangqiRulesEngine._elephant_moves(board, row, col, is_red)
        elif piece_type == 'r':
            moves = XiangqiRulesEngine._rook_moves(board, row, col)
        elif piece_type == 'c':
            moves = XiangqiRulesEngine._cannon_moves(board, row, col)
        elif piece_type == 'n':
            moves = XiangqiRulesEngine._knight_moves(board, row, col, is_red)
        elif piece_type == 'p':
            moves = XiangqiRulesEngine._pawn_moves(board, row, col, is_red)
        else:
            moves = []

        # 过滤掉会让自己被将军的走法
        valid_moves = []
        for nr, nc in moves:
            if XiangqiRulesEngine._is_valid_move(board, row, col, nr, nc, is_red):
                valid_moves.append((nr, nc))

        return valid_moves

    # -----------------------------------------------------------------
    # 底层原始走法 — 仅依赖棋子步法规则，不含将军过滤，用于攻击检测
    # -----------------------------------------------------------------

    @staticmethod
    def _get_raw_moves(board: List[List[str]], row: int, col: int) -> List[Tuple[int, int]]:
        """获取棋子原始走法（不过滤自将），供攻击检测使用。"""
        piece = board[row][col]
        if not piece:
            return []
        is_red = XiangqiRulesEngine.is_red(piece)
        piece_type = piece.lower()
        if piece_type == 'k':
            return XiangqiRulesEngine._king_moves(board, row, col, is_red)
        elif piece_type == 'a':
            return XiangqiRulesEngine._advisor_moves(board, row, col, is_red)
        elif piece_type == 'b':
            return XiangqiRulesEngine._elephant_moves(board, row, col, is_red)
        elif piece_type == 'r':
            return XiangqiRulesEngine._rook_moves(board, row, col)
        elif piece_type == 'c':
            return XiangqiRulesEngine._cannon_moves(board, row, col)
        elif piece_type == 'n':
            return XiangqiRulesEngine._knight_moves(board, row, col, is_red)
        elif piece_type == 'p':
            return XiangqiRulesEngine._pawn_moves(board, row, col, is_red)
        return []

    @staticmethod
    def _is_square_attacked(board: List[List[str]], row: int, col: int,
                            by_red: bool) -> bool:
        """判断某个格子是否被指定方的某棋子攻击到（基于原始走法，无递归）。"""
        for r in range(10):
            for c in range(9):
                piece = board[r][c]
                if piece and XiangqiRulesEngine.is_red(piece) == by_red:
                    if (row, col) in XiangqiRulesEngine._get_raw_moves(board, r, c):
                        return True
        return False

    @staticmethod
    def _kings_face_each_other(board: List[List[str]]) -> bool:
        """检查将帅是否照面（同列无遮挡）。"""
        red_king = XiangqiRulesEngine._find_king(board, True)
        black_king = XiangqiRulesEngine._find_king(board, False)
        if not red_king or not black_king:
            return False
        if red_king[1] != black_king[1]:
            return False
        min_row = min(red_king[0], black_king[0])
        max_row = max(red_king[0], black_king[0])
        for r in range(min_row + 1, max_row):
            if board[r][red_king[1]]:
                return False
        return True

    # -----------------------------------------------------------------
    # 走法合法性验证 — 模拟走棋，检查自将与照面
    # -----------------------------------------------------------------

    @staticmethod
    def _is_valid_move(board: List[List[str]], from_row: int, from_col: int,
                       to_row: int, to_col: int, is_red: bool) -> bool:
        """
        验证走法是否合法：走后不能自将，不能将帅照面。

        使用 _is_square_attacked（基于 _get_raw_moves）检测，无递归风险。
        """
        target = board[to_row][to_col]
        if target and XiangqiRulesEngine.is_red(target) == is_red:
            return False

        # 模拟走棋
        new_board = [row[:] for row in board]
        new_board[to_row][to_col] = new_board[from_row][from_col]
        new_board[from_row][from_col] = ''

        # 走后己方帅/将不能被对方攻击
        king_pos = XiangqiRulesEngine._find_king(new_board, is_red)
        if king_pos is None:
            return False
        if XiangqiRulesEngine._is_square_attacked(new_board, king_pos[0], king_pos[1], not is_red):
            return False

        # 走后不能将帅照面
        if XiangqiRulesEngine._kings_face_each_other(new_board):
            return False

        return True

    @staticmethod
    def _find_king(board: List[List[str]], is_red: bool) -> Tuple[int, int]:
        """
        查找将/帅位置

        Args:
            board: 棋盘
            is_red: 是否红方

        Returns:
            将/帅的位置 (row, col)，如果找不到返回None
        """
        king = 'K' if is_red else 'k'
        for r in range(10):
            for c in range(9):
                if board[r][c] == king:
                    return (r, c)
        return None

    @staticmethod
    def _is_in_check(board: List[List[str]], king_row: int, king_col: int,
                    is_attacking_red: bool) -> bool:
        """
        检查将/帅是否被将军

        委派到 _is_square_attacked（基于原始走法、无递归）。
        """
        return XiangqiRulesEngine._is_square_attacked(board, king_row, king_col, is_attacking_red)

    @staticmethod
    def _king_moves(board: List[List[str]], row: int, col: int, is_red: bool) -> List[Tuple[int, int]]:
        """将/帅走法规则"""
        moves = []

        # 在九宫格内上下左右移动
        for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nr, nc = row + dr, col + dc

            if XiangqiRulesEngine.is_in_palace(nr, nc, is_red):
                target = board[nr][nc]
                if not target or XiangqiRulesEngine.is_red(target) != is_red:
                    moves.append((nr, nc))

        return moves

    @staticmethod
    def _advisor_moves(board: List[List[str]], row: int, col: int, is_red: bool) -> List[Tuple[int, int]]:
        """仕/士走法规则（斜线移动，只能在九宫格内）"""
        moves = []

        # 斜线移动
        for dr, dc in [(1, 1), (1, -1), (-1, 1), (-1, -1)]:
            nr, nc = row + dr, col + dc

            if XiangqiRulesEngine.is_in_palace(nr, nc, is_red):
                target = board[nr][nc]
                if not target or XiangqiRulesEngine.is_red(target) != is_red:
                    moves.append((nr, nc))

        return moves

    @staticmethod
    def _elephant_moves(board: List[List[str]], row: int, col: int, is_red: bool) -> List[Tuple[int, int]]:
        """相/象走法规则（走田字，不能过河）"""
        moves = []

        # 走田字（2格斜线）
        for dr, dc in [(2, 2), (2, -2), (-2, 2), (-2, -2)]:
            nr, nc = row + dr, col + dc
            mr, mc = row + dr // 2, col + dc // 2

            # 检查是否在棋盘内
            if 0 <= nr < 10 and 0 <= nc < 9:
                # 检查象眼位置是否有棋子（蹩象）
                if board[mr][mc]:
                    continue

                # 检查是否过河
                if is_red and nr < 5:
                    continue  # 红相不能过河到黑方区域
                if not is_red and nr > 4:
                    continue  # 黑象不能过河到红方区域

                target = board[nr][nc]
                if not target or XiangqiRulesEngine.is_red(target) != is_red:
                    moves.append((nr, nc))

        return moves

    @staticmethod
    def _rook_moves(board: List[List[str]], row: int, col: int) -> List[Tuple[int, int]]:
        """车走法规则（直线移动，不限格数）"""
        moves = []

        # 四个方向：上下左右
        for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nr, nc = row + dr, col + dc

            # 沿着这个方向移动直到遇到棋子或边界
            while 0 <= nr < 10 and 0 <= nc < 9:
                target = board[nr][nc]

                if not target:
                    # 空位，可以走
                    moves.append((nr, nc))
                elif XiangqiRulesEngine.is_red(target) != XiangqiRulesEngine.is_red(board[row][col]):
                    # 敌方棋子，可以吃，但不能继续
                    moves.append((nr, nc))
                    break
                else:
                    # 己方棋子，不能继续
                    break

                nr += dr
                nc += dc

        return moves

    @staticmethod
    def _cannon_moves(board: List[List[str]], row: int, col: int) -> List[Tuple[int, int]]:
        """炮走法规则（移动时不限格数，吃子时需要炮架）"""
        moves = []
        is_red = XiangqiRulesEngine.is_red(board[row][col])

        # 四个方向：上下左右
        for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nr, nc = row + dr, col + dc

            # 标记是否遇到过炮架
            has_jumped = False

            # 沿着这个方向移动
            while 0 <= nr < 10 and 0 <= nc < 9:
                target = board[nr][nc]

                if not target and not has_jumped:
                    # 空位且未跳过，可以移动
                    moves.append((nr, nc))
                elif target:
                    if not has_jumped:
                        # 第一个棋子，设为炮架
                        has_jumped = True
                    elif XiangqiRulesEngine.is_red(target) != is_red:
                        # 炮架后的敌方棋子，可以吃
                        moves.append((nr, nc))
                        break
                    else:
                        # 炮架后的己方棋子，不能继续
                        break

                nr += dr
                nc += dc

        return moves

    @staticmethod
    def _knight_moves(board: List[List[str]], row: int, col: int, is_red: bool) -> List[Tuple[int, int]]:
        """马走法规则（日字走法，有蹩马）"""
        moves = []

        # 马的8个走法位置
        knight_moves = [
            (2, 1, 1, 0),  # 右下
            (2, -1, 1, 0),  # 右上
            (-2, 1, -1, 0),  # 左下
            (-2, -1, -1, 0),  # 左上
            (1, 2, 0, 1),  # 下右
            (1, -2, 0, -1),  # 上右
            (-1, 2, 0, 1),  # 下左
            (-1, -2, 0, -1),  # 上左
        ]

        for dr, dc, block_r, block_c in knight_moves:
            nr, nc = row + dr, col + dc
            mr, mc = row + block_r, col + block_c

            # 检查是否在棋盘内
            if 0 <= nr < 10 and 0 <= nc < 9:
                # 检查蹩马（马腿位置是否有棋子）
                if 0 <= mr < 10 and 0 <= mc < 9 and not board[mr][mc]:
                    target = board[nr][nc]
                    if not target or XiangqiRulesEngine.is_red(target) != is_red:
                        moves.append((nr, nc))

        return moves

    @staticmethod
    def _pawn_moves(board: List[List[str]], row: int, col: int, is_red: bool) -> List[Tuple[int, int]]:
        """兵/卒走法规则（只能向前，过河后可横向）"""
        moves = []

        # 兵/卒只能向前走1格
        if is_red:
            # 红兵向前（row减小）
            if row > 0:
                target = board[row - 1][col]
                if not target or XiangqiRulesEngine.is_black(target):
                    moves.append((row - 1, col))

            # 过河后（row <= 4）可以横向移动
            if row <= 4:
                for dc in [-1, 1]:
                    if 0 <= col + dc < 9:
                        target = board[row][col + dc]
                        if not target or XiangqiRulesEngine.is_black(target):
                            moves.append((row, col + dc))
        else:
            # 黑卒向前（row增大）
            if row < 9:
                target = board[row + 1][col]
                if not target or XiangqiRulesEngine.is_red(target):
                    moves.append((row + 1, col))

            # 过河后（row >= 5）可以横向移动
            if row >= 5:
                for dc in [-1, 1]:
                    if 0 <= col + dc < 9:
                        target = board[row][col + dc]
                        if not target or XiangqiRulesEngine.is_red(target):
                            moves.append((row, col + dc))

        return moves


# 便捷函数
def get_legal_moves(board: List[List[str]], row: int, col: int) -> List[Tuple[int, int]]:
    """
    获取合法走法（便捷函数）

    Args:
        board: 棋盘二维数组
        row: 棋子行号
        col: 棋子列号

    Returns:
        合法走法列表
    """
    return XiangqiRulesEngine.get_legal_moves(board, row, col)


def is_in_check(board: List[List[str]], is_red: bool) -> bool:
    """
    检查是否被将军（便捷函数）

    Args:
        board: 棋盘二维数组
        is_red: 是否红方走棋

    Returns:
        是否被将军
    """
    king_pos = XiangqiRulesEngine._find_king(board, is_red)
    if not king_pos:
        return False

    return XiangqiRulesEngine._is_in_check(board, king_pos[0], king_pos[1], not is_red)
