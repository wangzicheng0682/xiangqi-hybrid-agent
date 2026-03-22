"""
中国象棋引擎适配器
封装底层象棋引擎,提供统一接口
基于 cchess 库实现
"""
from typing import List, Optional, Literal
from dataclasses import dataclass, field
from enum import Enum


class GameResult(Enum):
    """游戏结果"""
    RED_WIN = "RED"
    BLACK_WIN = "BLACK"
    DRAW = "DRAW"
    ONGOING = "ONGOING"


@dataclass
class Board:
    """棋盘状态封装"""
    fen: str  # FEN格式棋盘表示
    move_history: List[str] = field(default_factory=list)  # 移动历史
    
    def copy(self) -> "Board":
        """深拷贝棋盘"""
        return Board(
            fen=self.fen,
            move_history=self.move_history.copy()
        )


class ChessEngineAdapter:
    """
    中国象棋引擎适配器
    基于 cchess 库实现
    """
    
    def __init__(self):
        """初始化引擎"""
        try:
            import cchess
            self.cchess = cchess
        except ImportError:
            raise ImportError(
                "cchess库未安装。请执行: pip install cchess"
            )
    
    def get_initial_board(self) -> Board:
        """获取初始棋盘"""
        # 使用 cchess 库的起始局面
        game = self.cchess.Game()
        return Board(fen=game.fen(), move_history=[])
    
    def legal_moves(self, board: Board) -> List[str]:
        """
        获取当前局面所有合法走法
        
        Args:
            board: 当前棋盘状态
            
        Returns:
            合法走法列表,格式如 ["e2e4", "b0c2", ...]
        """
        try:
            game = self.cchess.Game(board.fen)
            moves = []
            
            # 获取所有合法移动
            for move in game.legal_moves():
                # 转换为标准格式: 起点+终点 (如 "e2e4")
                from_sq = self.cchess.square_name(move.from_square)
                to_sq = self.cchess.square_name(move.to_square)
                moves.append(f"{from_sq}{to_sq}")
            
            return moves
        except Exception as e:
            # 如果FEN解析失败,返回空列表
            print(f"获取合法走法失败: {e}")
            return []
    
    def apply_move(self, board: Board, move: str) -> Board:
        """
        应用走法,返回新棋盘状态
        
        Args:
            board: 当前棋盘
            move: 走法字符串 (如 "e2e4")
            
        Returns:
            新棋盘状态
            
        Raises:
            ValueError: 走法不合法时抛出
        """
        try:
            game = self.cchess.Game(board.fen)
            
            # 解析走法
            if len(move) != 4:
                raise ValueError(f"走法格式错误: {move}, 应为4字符如'e2e4'")
            
            from_sq = self.cchess.parse_square(move[:2])
            to_sq = self.cchess.parse_square(move[2:4])
            
            # 在合法走法中查找匹配的move对象
            move_obj = None
            for legal_move in game.legal_moves():
                if legal_move.from_square == from_sq and legal_move.to_square == to_sq:
                    move_obj = legal_move
                    break
            
            if move_obj is None:
                legal_moves = [f"{self.cchess.square_name(m.from_square)}{self.cchess.square_name(m.to_square)}" 
                             for m in list(game.legal_moves())[:5]]
                raise ValueError(f"非法走法: {move}, 合法走法示例: {legal_moves}...")
            
            # 应用走法
            game.push(move_obj)
            
            # 构造新棋盘
            new_board = board.copy()
            new_board.fen = game.fen()
            new_board.move_history.append(move)
            
            return new_board
            
        except Exception as e:
            raise ValueError(f"应用走法失败: {move}, 错误: {e}")
    
    def is_terminal(self, board: Board) -> bool:
        """
        判断是否为终局状态
        
        Args:
            board: 棋盘状态
            
        Returns:
            是否终局
        """
        try:
            game = self.cchess.Game(board.fen)
            
            # 检查游戏是否结束
            if game.is_game_over():
                return True
            
            # 检查无子可走
            legal_moves_list = list(game.legal_moves())
            if not legal_moves_list:
                return True
            
            # 检查重复局面(简化版:连续60回合无吃子判和)
            if len(board.move_history) >= 120:
                return True
            
            return False
            
        except Exception:
            return True
    
    def get_winner(self, board: Board) -> GameResult:
        """
        获取游戏结果
        
        Args:
            board: 棋盘状态
            
        Returns:
            游戏结果枚举
        """
        if not self.is_terminal(board):
            return GameResult.ONGOING
        
        try:
            game = self.cchess.Game(board.fen)
            
            # 检查将军或困毙
            if game.is_checkmate():
                # 当前玩家被将死,对手获胜
                current_turn = game.turn
                if current_turn == self.cchess.RED:
                    return GameResult.BLACK_WIN
                else:
                    return GameResult.RED_WIN
            
            # 和棋情况
            if game.is_stalemate() or len(board.move_history) >= 120:
                return GameResult.DRAW
            
            # 其他终局情况视为和棋
            return GameResult.DRAW
            
        except Exception:
            return GameResult.DRAW
    
    def get_current_player(self, board: Board) -> Literal["RED", "BLACK"]:
        """
        获取当前行动方
        
        Args:
            board: 棋盘状态
            
        Returns:
            "RED" 或 "BLACK"
        """
        try:
            game = self.cchess.Game(board.fen)
            return "RED" if game.turn == self.cchess.RED else "BLACK"
        except Exception:
            # 默认红方先手
            return "RED" if len(board.move_history) % 2 == 0 else "BLACK"
    
    def get_board_display(self, board: Board) -> str:
        """
        获取棋盘的文本显示
        
        Args:
            board: 棋盘状态
            
        Returns:
            棋盘的ASCII表示
        """
        try:
            game = self.cchess.Game(board.fen)
            return str(game)
        except Exception as e:
            return f"无法显示棋盘: {e}"


# ============ 工厂函数 ============

def create_engine() -> ChessEngineAdapter:
    """
    工厂函数:创建引擎实例
    便于后续替换引擎实现
    """
    return ChessEngineAdapter()

