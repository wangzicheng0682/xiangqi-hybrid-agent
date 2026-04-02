"""
FEN Builder - 根据匹配结果生成FEN字符串

FEN格式说明（中国象棋）:
- 棋盘部分：9列×10行，用/分隔
- 列顺序：从第8列到第0列（对应FEN从左到右）
- 行顺序：从第0行到第9行（对应FEN从上到下）
- 连续空格用数字表示（1-9）
- 红方棋子：大写字母（K帅 A仕 B相 R车 N马 C炮 P兵）
- 黑方棋子：小写字母（k将 a士 b象 r车 n马 c炮 p卒）
- 结尾：side_to_move（w红方/b黑方）+ castle + ep + halfmove + fullmove
"""

from typing import List, Optional
from .template_data import YOLO_TO_FEN


def build_fen_from_pieces(pieces: List, side_to_move: str = "w") -> str:
    """
    根据检测到的棋子列表生成FEN字符串

    pieces: 每个元素需要包含 col, row, fen_char 属性
    """
    # 初始化9×10空棋盘
    board = [["." for _ in range(10)] for _ in range(9)]

    # 填入棋子
    for piece in pieces:
        if hasattr(piece, 'col') and hasattr(piece, 'fen_char'):
            if piece.col is not None and piece.fen_char:
                board[piece.col][piece.row] = piece.fen_char

    # 转换为FEN行
    fen_rows = []
    for row in range(10):
        # 从col=8到col=0（FEN从左到右）
        row_chars = []
        col = 8
        while col >= 0:
            p = board[col][row]
            if p == ".":
                # 数连续空格
                empty = 0
                while col >= 0 and board[col][row] == ".":
                    empty += 1
                    col -= 1
                row_chars.append(str(empty))
            else:
                row_chars.append(p)
                col -= 1
        fen_rows.append("".join(row_chars))

    fen = "/".join(fen_rows)
    fen += f" {side_to_move} - - 0 1"
    return fen


def verify_fen(fen: str) -> bool:
    """验证FEN格式是否正确"""
    try:
        parts = fen.strip().split()
        if len(parts) < 4:
            return False

        board_part = parts[0]
        rows = board_part.split("/")

        if len(rows) != 10:
            return False

        total = 0
        for row in rows:
            row_sum = 0
            for c in row:
                if c.isdigit():
                    row_sum += int(c)
                elif c.isalpha() and c in "rnbakabnrcpRNBAKABNRCP":
                    row_sum += 1
                else:
                    return False
            total += row_sum

        # 象棋棋盘最多90个格点（9×10），验证总格点正确即可
        if total != 90:
            return False

        return True

    except Exception:
        return False


def count_pieces(fen: str) -> int:
    """统计FEN中的棋子数量"""
    if not fen:
        return 0
    board = fen.split()[0] if ' ' in fen else fen
    count = 0
    for c in board:
        if c.isalpha() and c in "rnbakabnrcpRNBAKABNRCP":
            count += 1
    return count


def fen_to_board_matrix(fen: str) -> List[List[str]]:
    """
    把FEN字符串转换为棋盘矩阵
    返回: board[col][row]，col 0~8，row 0~9
    """
    board = [["." for _ in range(10)] for _ in range(9)]

    if not fen:
        return board

    parts = fen.strip().split()
    rows = parts[0].split("/")

    for row_idx, row_str in enumerate(rows):
        if row_idx >= 10:
            break

        col_idx = 0
        for c in row_str:
            if c.isdigit():
                col_idx += int(c)
            elif c.isalpha():
                board[col_idx][row_idx] = c
                col_idx += 1

    return board


# FEN 棋子映射（用于展示）
FEN_PIECE_NAMES = {
    "K": "红帅", "A": "红仕", "B": "红相", "R": "红车",
    "N": "红马", "C": "红炮", "P": "红兵",
    "k": "黑将", "a": "黑士", "b": "黑象", "r": "黑车",
    "n": "黑马", "c": "黑炮", "p": "黑卒",
}


def piece_name(fen_char: str) -> str:
    """获取棋子名称"""
    return FEN_PIECE_NAMES.get(fen_char, fen_char)