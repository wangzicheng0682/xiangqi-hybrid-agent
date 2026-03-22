"""
中国象棋记谱法转换模块
支持内部坐标表示(如"b0c2") <-> 中文记谱法(如"马二进三")
"""
from typing import Optional, Tuple, Dict
import re


class NotationConverter:
    """中国象棋记谱法转换器"""
    
    # 棋子中文名称映射
    PIECE_NAMES = {
        'r': '车', 'n': '马', 'b': '象', 'a': '士', 'k': '将',
        'c': '炮', 'p': '卒',
        'R': '车', 'N': '马', 'B': '相', 'A': '仕', 'K': '帅',
        'C': '炮', 'P': '兵'
    }
    
    # 数字中文映射
    NUM_TO_CHINESE = {
        0: '一', 1: '二', 2: '三', 3: '四', 4: '五',
        5: '六', 6: '七', 7: '八', 8: '九'
    }
    
    CHINESE_TO_NUM = {v: k for k, v in NUM_TO_CHINESE.items()}
    
    # 动作中文
    ACTION_NAMES = {
        'advance': '进',  # 前进
        'retreat': '退',  # 后退
        'horizontal': '平'  # 平移
    }
    
    def __init__(self):
        """初始化转换器"""
        pass
    
    def coord_to_chinese(self, move: str, fen: str) -> str:
        """
        坐标转中文记谱
        
        Args:
            move: 坐标表示,如"b0c2"
            fen: 当前棋盘FEN(用于确定棋子类型)
            
        Returns:
            中文记谱,如"马二进三"
        """
        if len(move) != 4:
            return move
        
        from_sq = move[:2]
        to_sq = move[2:4]
        
        # 解析坐标
        from_file, from_rank = self._parse_square(from_sq)
        to_file, to_rank = self._parse_square(to_sq)
        
        if from_file is None or to_file is None:
            return move
        
        # 获取棋子类型
        piece = self._get_piece_at(fen, from_file, from_rank)
        if not piece:
            return move
        
        # 判断红黑方
        is_red = piece.isupper()
        
        # 棋子名称
        piece_name = self.PIECE_NAMES.get(piece.lower(), '?')
        
        # 起始位置(从红方视角)
        if is_red:
            start_pos = 8 - from_file  # 红方从右往左数
        else:
            start_pos = from_file  # 黑方从左往右数
        
        start_chinese = self.NUM_TO_CHINESE.get(start_pos, '?')
        
        # 判断动作类型和目标
        if from_file == to_file:
            # 直线移动
            if is_red:
                if to_rank > from_rank:
                    action = '进'
                    distance = to_rank - from_rank
                else:
                    action = '退'
                    distance = from_rank - to_rank
            else:
                if to_rank < from_rank:
                    action = '进'
                    distance = from_rank - to_rank
                else:
                    action = '退'
                    distance = to_rank - from_rank
            
            target = self.NUM_TO_CHINESE.get(distance, str(distance))
        else:
            # 横向移动
            action = '平'
            if is_red:
                target_pos = 8 - to_file
            else:
                target_pos = to_file
            target = self.NUM_TO_CHINESE.get(target_pos, '?')
        
        return f"{piece_name}{start_chinese}{action}{target}"
    
    def chinese_to_coord(self, chinese_move: str, fen: str, legal_moves: list) -> Optional[str]:
        """
        中文记谱转坐标
        
        Args:
            chinese_move: 中文记谱,如"马二进三"
            fen: 当前棋盘FEN
            legal_moves: 合法走法列表(用于消歧)
            
        Returns:
            坐标表示,如"b0c2",失败返回None
        """
        # 移除空格
        chinese_move = chinese_move.strip()
        
        if len(chinese_move) < 4:
            return None
        
        # 解析中文记谱
        parsed = self._parse_chinese_move(chinese_move)
        if not parsed:
            return None
        
        piece_name, start_pos, action, target = parsed
        
        # 在合法走法中匹配
        for move in legal_moves:
            if self._match_chinese_move(move, fen, piece_name, start_pos, action, target):
                return move
        
        return None
    
    def format_move_list(self, moves: list, fen: str) -> str:
        """
        格式化走法列表(用于给LLM展示)
        
        Args:
            moves: 坐标走法列表
            fen: 当前棋盘FEN
            
        Returns:
            格式化的字符串
        """
        formatted = []
        for idx, move in enumerate(moves, 1):
            chinese = self.coord_to_chinese(move, fen)
            formatted.append(f"{idx}. {move} ({chinese})")
        
        return "\n".join(formatted)
    
    # ============ 内部辅助方法 ============
    
    def _parse_square(self, square: str) -> Tuple[Optional[int], Optional[int]]:
        """
        解析坐标字符串
        
        Args:
            square: 如"b0"
            
        Returns:
            (file, rank) 如(1, 0)
        """
        if len(square) != 2:
            return None, None
        
        file_char = square[0]
        rank_char = square[1]
        
        # 文件: a-i -> 0-8
        if 'a' <= file_char <= 'i':
            file = ord(file_char) - ord('a')
        else:
            return None, None
        
        # 等级: 0-9
        if rank_char.isdigit():
            rank = int(rank_char)
        else:
            return None, None
        
        return file, rank
    
    def _get_piece_at(self, fen: str, file: int, rank: int) -> Optional[str]:
        """
        获取指定位置的棋子
        
        Args:
            fen: FEN字符串
            file: 列(0-8)
            rank: 行(0-9)
            
        Returns:
            棋子符号,如'R','n',无棋子返回None
        """
        position = fen.split()[0]
        rows = position.split('/')
        
        if rank >= len(rows):
            return None
        
        row = rows[rank]
        col = 0
        
        for char in row:
            if char.isdigit():
                col += int(char)
            else:
                if col == file:
                    return char
                col += 1
        
        return None
    
    def _parse_chinese_move(self, chinese_move: str) -> Optional[Tuple[str, str, str, str]]:
        """
        解析中文记谱
        
        Args:
            chinese_move: 如"马二进三"
            
        Returns:
            (棋子名, 起始位置, 动作, 目标) 或 None
        """
        # 模式: 棋子名 + 起始位置 + 动作 + 目标
        pattern = r'^(车|马|相|象|士|仕|将|帅|炮|兵|卒)(一|二|三|四|五|六|七|八|九|前|后|中)(进|退|平)(一|二|三|四|五|六|七|八|九|\d+)$'
        
        match = re.match(pattern, chinese_move)
        if not match:
            return None
        
        return match.groups()
    
    def _match_chinese_move(self, move: str, fen: str, 
                           piece_name: str, start_pos: str, 
                           action: str, target: str) -> bool:
        """
        检查坐标走法是否匹配中文记谱
        
        Args:
            move: 坐标走法
            fen: FEN字符串
            piece_name: 棋子名
            start_pos: 起始位置
            action: 动作
            target: 目标
            
        Returns:
            是否匹配
        """
        from_sq = move[:2]
        to_sq = move[2:4]
        
        from_file, from_rank = self._parse_square(from_sq)
        to_file, to_rank = self._parse_square(to_sq)
        
        if from_file is None:
            return False
        
        # 检查棋子类型
        piece = self._get_piece_at(fen, from_file, from_rank)
        if not piece:
            return False
        
        piece_chinese = self.PIECE_NAMES.get(piece.lower(), '')
        if piece_chinese != piece_name:
            return False
        
        is_red = piece.isupper()
        
        # 检查起始位置
        if start_pos in self.CHINESE_TO_NUM:
            expected_file = self.CHINESE_TO_NUM[start_pos]
            if is_red:
                expected_file = 8 - expected_file
            if from_file != expected_file:
                return False
        
        # 检查动作和目标
        if action == '平':
            if from_file == to_file:
                return False
            if target in self.CHINESE_TO_NUM:
                expected_file = self.CHINESE_TO_NUM[target]
                if is_red:
                    expected_file = 8 - expected_file
                return to_file == expected_file
        
        elif action == '进':
            if from_file != to_file:
                return False
            
            if target in self.CHINESE_TO_NUM:
                distance = self.CHINESE_TO_NUM[target]
                if is_red:
                    return to_rank == from_rank + distance
                else:
                    return to_rank == from_rank - distance
        
        elif action == '退':
            if from_file != to_file:
                return False
            
            if target in self.CHINESE_TO_NUM:
                distance = self.CHINESE_TO_NUM[target]
                if is_red:
                    return to_rank == from_rank - distance
                else:
                    return to_rank == from_rank + distance
        
        return True
    
    def _make_square(self, file: int, rank: int) -> str:
        """
        生成坐标字符串
        
        Args:
            file: 列(0-8)
            rank: 行(0-9)
            
        Returns:
            坐标字符串,如"b0"
        """
        file_char = chr(ord('a') + file)
        return f"{file_char}{rank}"


# ============ 便捷函数 ============

_converter = NotationConverter()


def coord_to_chinese(move: str, fen: str) -> str:
    """
    坐标转中文记谱(便捷函数)
    
    Args:
        move: 坐标表示
        fen: FEN字符串
        
    Returns:
        中文记谱
    """
    return _converter.coord_to_chinese(move, fen)


def chinese_to_coord(chinese_move: str, fen: str, legal_moves: list) -> Optional[str]:
    """
    中文记谱转坐标(便捷函数)
    
    Args:
        chinese_move: 中文记谱
        fen: FEN字符串
        legal_moves: 合法走法列表
        
    Returns:
        坐标表示或None
    """
    return _converter.chinese_to_coord(chinese_move, fen, legal_moves)


def format_move_list(moves: list, fen: str) -> str:
    """
    格式化走法列表(便捷函数)
    
    Args:
        moves: 坐标走法列表
        fen: FEN字符串
        
    Returns:
        格式化字符串
    """
    return _converter.format_move_list(moves, fen)


def create_notation_converter() -> NotationConverter:
    """
    工厂函数: 创建转换器实例
    
    Returns:
        NotationConverter对象
    """
    return NotationConverter()