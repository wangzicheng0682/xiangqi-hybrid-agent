"""
棋子绑定工具
处理棋子坐标、类型、颜色的标准化绑定
"""

from dataclasses import dataclass
from typing import Tuple, Optional


@dataclass(frozen=True)
class PieceBinding:
    """
    棋子绑定对象
    
    格式: 颜色-兵种-坐标
    示例: 红车-(5,8), 黑将-(5,1), 红马-(7,7)
    """
    color: str          # "红" 或 "黑"
    piece_type: str     # 兵种: 帅/将/仕/士/相/象/马/车/炮/兵/卒
    x: int              # 列坐标 1-9
    y: int              # 行坐标 1-10
    
    def __post_init__(self):
        # 验证坐标范围
        if not (1 <= self.x <= 9):
            raise ValueError(f"列坐标x必须在1-9之间，当前: {self.x}")
        if not (1 <= self.y <= 10):
            raise ValueError(f"行坐标y必须在1-10之间，当前: {self.y}")
        # 验证颜色
        if self.color not in ("红", "黑"):
            raise ValueError(f"颜色必须是'红'或'黑'，当前: {self.color}")
    
    @property
    def coordinate(self) -> Tuple[int, int]:
        """获取坐标元组"""
        return (self.x, self.y)
    
    def to_string(self) -> str:
        """
        转换为标准字符串格式
        示例: "红车-(5,8)"
        """
        return f"{self.color}{self.piece_type}-({self.x},{self.y})"
    
    def __str__(self) -> str:
        return self.to_string()
    
    def __repr__(self) -> str:
        return f"PieceBinding({self.to_string()})"


class PieceBindingFactory:
    """棋子绑定工厂类"""
    
    # 兵种映射表（统一命名）
    PIECE_TYPE_MAP = {
        # 红方
        'K': '帅', 'A': '仕', 'B': '相', 'N': '马', 'R': '车', 'C': '炮', 'P': '兵',
        'k': '帅', 'a': '仕', 'b': '相', 'n': '马', 'r': '车', 'c': '炮', 'p': '兵',
        # 黑方
        'k_black': '将', 'a_black': '士', 'b_black': '象', 
        'n_black': '马', 'r_black': '车', 'c_black': '炮', 'p_black': '卒',
    }
    
    @classmethod
    def from_fen_piece(cls, piece_char: str, x: int, y: int) -> PieceBinding:
        """
        从FEN棋子字符创建绑定
        
        Args:
            piece_char: FEN中的棋子字符（如 'R', 'n', 'C'）
            x: 列坐标 1-9
            y: 行坐标 1-10
            
        Returns:
            PieceBinding: 棋子绑定对象
        """
        piece_char = piece_char.upper()
        
        # 判断颜色
        if piece_char.isupper():
            color = "红"
        else:
            color = "黑"
            piece_char = piece_char.upper()
        
        # 映射兵种
        piece_type_map = {
            'K': '帅' if color == "红" else "将",
            'A': '仕' if color == "红" else "士",
            'B': '相' if color == "红" else "象",
            'N': '马',
            'R': '车',
            'C': '炮',
            'P': '兵' if color == "红" else "卒",
        }
        
        piece_type = piece_type_map.get(piece_char, "未知")
        
        return PieceBinding(color=color, piece_type=piece_type, x=x, y=y)
    
    @classmethod
    def from_string(cls, binding_str: str) -> PieceBinding:
        """
        从字符串解析绑定
        
        Args:
            binding_str: 格式如 "红车-(5,8)"
            
        Returns:
            PieceBinding: 棋子绑定对象
        """
        # 解析格式: 红车-(5,8)
        import re
        pattern = r'([红黑])([帅将仕士相象马车炮兵卒])-\((\d+),(\d+)\)'
        match = re.match(pattern, binding_str)
        
        if not match:
            raise ValueError(f"无法解析棋子绑定字符串: {binding_str}")
        
        color = match.group(1)
        piece_type = match.group(2)
        x = int(match.group(3))
        y = int(match.group(4))
        
        return PieceBinding(color=color, piece_type=piece_type, x=x, y=y)
    
    @classmethod
    def create(cls, color: str, piece_type: str, x: int, y: int) -> PieceBinding:
        """
        直接创建绑定
        
        Args:
            color: "红" 或 "黑"
            piece_type: 兵种名称
            x: 列坐标 1-9
            y: 行坐标 1-10
            
        Returns:
            PieceBinding: 棋子绑定对象
        """
        return PieceBinding(color=color, piece_type=piece_type, x=x, y=y)


def format_bind_pieces(pieces: list) -> list:
    """
    格式化棋子绑定列表
    
    Args:
        pieces: PieceBinding对象列表或字符串列表
        
    Returns:
        list: 标准化字符串列表
    """
    result = []
    for piece in pieces:
        if isinstance(piece, PieceBinding):
            result.append(piece.to_string())
        elif isinstance(piece, str):
            result.append(piece)
        else:
            result.append(str(piece))
    return result


# =============================================================================
# 坐标转换工具
# =============================================================================

def fen_index_to_coord(index: int) -> Tuple[int, int]:
    """
    将FEN字符串中的索引转换为象棋坐标
    
    FEN格式: 从第10行到第1行，每行从第1列到第9列
    
    Args:
        index: FEN中的字符索引
        
    Returns:
        Tuple[int, int]: (x, y) 坐标，x为1-9列，y为1-10行
    """
    # FEN中每行以/分隔，数字表示连续空位
    # 这里简化处理，假设已经解析为棋盘数组
    # 实际使用时需要结合具体FEN解析逻辑
    row = index // 9
    col = index % 9
    # 转换：FEN第0行对应y=10，第9行对应y=1
    y = 10 - row
    x = col + 1
    return (x, y)


def coord_to_fen_index(x: int, y: int) -> int:
    """
    将象棋坐标转换为FEN索引
    
    Args:
        x: 列 1-9
        y: 行 1-10
        
    Returns:
        int: FEN字符串中的大致索引位置
    """
    row = 10 - y
    col = x - 1
    return row * 9 + col


def uci_to_coord(uci: str) -> Tuple[Tuple[int, int], Tuple[int, int]]:
    """
    将UCI格式转换为坐标
    
    UCI格式: 如 "h2e2"（中国象棋UCI使用a-i表示列，0-9表示行）
    
    Args:
        uci: UCI走法字符串，如 "h2e2"
        
    Returns:
        Tuple[Tuple[int, int], Tuple[int, int]]: ((from_x, from_y), (to_x, to_y))
    """
    files = 'abcdefghi'
    
    if len(uci) < 4:
        raise ValueError(f"UCI格式错误: {uci}")
    
    from_file = uci[0].lower()
    from_rank = uci[1]
    to_file = uci[2].lower()
    to_rank = uci[3]
    
    from_x = files.index(from_file) + 1
    from_y = int(from_rank)
    to_x = files.index(to_file) + 1
    to_y = int(to_rank)
    
    return ((from_x, from_y), (to_x, to_y))


def coord_to_uci(from_coord: Tuple[int, int], to_coord: Tuple[int, int]) -> str:
    """
    将坐标转换为UCI格式
    
    Args:
        from_coord: (x, y) 起始坐标
        to_coord: (x, y) 目标坐标
        
    Returns:
        str: UCI格式字符串，如 "h2e2"
    """
    files = 'abcdefghi'
    
    from_x, from_y = from_coord
    to_x, to_y = to_coord
    
    uci = f"{files[from_x - 1]}{from_y}{files[to_x - 1]}{to_y}"
    return uci
