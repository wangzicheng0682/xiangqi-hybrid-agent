"""
中国象棋棋盘状态类
负责状态表示、序列化、哈希等功能
不包含走子合法性判断(由engine_adapter负责)
"""
from typing import List, Dict, Optional
from dataclasses import dataclass, field
import hashlib
import json


@dataclass
class Board:
    """
    中国象棋棋盘状态
    
    Attributes:
        fen: FEN格式棋盘表示
        move_history: 走法历史列表
        metadata: 额外元数据(如时间戳、对弈ID等)
    """
    fen: str
    move_history: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
    
    @classmethod
    def create_initial(cls) -> "Board":
        """
        创建标准开局棋盘
        
        Returns:
            初始化的棋盘对象
        """
        initial_fen = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"
        return cls(fen=initial_fen, move_history=[], metadata={})
    
    def copy(self) -> "Board":
        """
        深拷贝棋盘状态
        
        Returns:
            新的棋盘对象
        """
        return Board(
            fen=self.fen,
            move_history=self.move_history.copy(),
            metadata=self.metadata.copy()
        )
    
    def to_text(self, include_history: bool = True) -> str:
        """
        转换为LLM可读的文本表示
        
        Args:
            include_history: 是否包含走法历史
            
        Returns:
            格式化的文本描述
        """
        text_parts = []
        
        # 1. 棋盘可视化
        text_parts.append("=== 当前棋盘 ===")
        text_parts.append(self._render_board())
        
        # 2. FEN表示
        text_parts.append(f"\nFEN: {self.fen}")
        
        # 3. 当前行动方
        current_player = self._get_current_player()
        text_parts.append(f"当前行动方: {current_player}")
        
        # 4. 走法历史(可选)
        if include_history and self.move_history:
            text_parts.append(f"\n走法历史 (共{len(self.move_history)}步):")
            history_str = " -> ".join(self.move_history[-10:])  # 最近10步
            if len(self.move_history) > 10:
                history_str = "... -> " + history_str
            text_parts.append(history_str)
        
        # 5. 回合数
        half_moves = len(self.move_history)
        full_moves = (half_moves // 2) + 1
        text_parts.append(f"\n回合数: {full_moves} (半回合: {half_moves})")
        
        return "\n".join(text_parts)
    
    def get_state_hash(self) -> str:
        """
        生成稳定的状态哈希值
        用于经验池检索和去重
        
        策略:
        - 仅基于FEN的棋子位置部分(忽略移动计数器)
        - 确保相同局面产生相同哈希
        
        Returns:
            16进制哈希字符串
        """
        # 解析FEN,只保留棋子位置和行动方
        fen_parts = self.fen.split()
        canonical_fen = " ".join(fen_parts[:2])  # 位置 + 行动方
        
        # SHA256哈希
        hash_obj = hashlib.sha256(canonical_fen.encode('utf-8'))
        return hash_obj.hexdigest()
    
    def to_dict(self) -> Dict:
        """
        序列化为字典(用于存储)
        
        Returns:
            包含所有状态信息的字典
        """
        return {
            "fen": self.fen,
            "move_history": self.move_history,
            "metadata": self.metadata,
            "state_hash": self.get_state_hash()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Board":
        """
        从字典反序列化
        
        Args:
            data: 序列化的字典
            
        Returns:
            Board对象
        """
        return cls(
            fen=data["fen"],
            move_history=data.get("move_history", []),
            metadata=data.get("metadata", {})
        )
    
    def to_json(self) -> str:
        """JSON序列化"""
        return json.dumps(self.to_dict(), ensure_ascii=False)
    
    @classmethod
    def from_json(cls, json_str: str) -> "Board":
        """JSON反序列化"""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    # ============ 内部辅助方法 ============
    
    def _render_board(self) -> str:
        """
        渲染棋盘为ASCII艺术字
        
        Returns:
            可视化的棋盘字符串
        """
        # 解析FEN中的棋子位置部分
        fen_parts = self.fen.split()
        position = fen_parts[0]
        
        # 棋子符号映射(中文)
        piece_map = {
            'r': '車', 'n': '馬', 'b': '象', 'a': '士', 'k': '將',
            'c': '砲', 'p': '卒',
            'R': '俥', 'N': '傌', 'B': '相', 'A': '仕', 'K': '帥',
            'C': '炮', 'P': '兵'
        }
        
        lines = []
        lines.append("  ０１２３４５６７８")
        lines.append("  ─────────────────")
        
        rows = position.split('/')
        for rank_idx, row in enumerate(rows):
            rank_num = rank_idx
            rank_display = f"{rank_num}│"
            
            col = 0
            for char in row:
                if char.isdigit():
                    # 数字表示空格
                    empty_count = int(char)
                    rank_display += "  " * empty_count
                    col += empty_count
                else:
                    # 棋子
                    piece = piece_map.get(char, char)
                    rank_display += piece + " "
                    col += 1
            
            lines.append(rank_display)
            
            # 在第4行和第5行之间绘制楚河汉界
            if rank_idx == 4:
                lines.append("  ═════════════════")
        
        return "\n".join(lines)
    
    def _get_current_player(self) -> str:
        """
        从FEN中解析当前行动方
        
        Returns:
            "红方" 或 "黑方"
        """
        fen_parts = self.fen.split()
        if len(fen_parts) < 2:
            # 默认红方先手
            return "红方"
        
        turn = fen_parts[1]
        return "红方" if turn == 'w' else "黑方"
    
    def get_move_count(self) -> int:
        """获取当前走法总数"""
        return len(self.move_history)
    
    def get_last_move(self) -> Optional[str]:
        """获取最后一步走法"""
        return self.move_history[-1] if self.move_history else None
    
    def __repr__(self) -> str:
        """简洁的字符串表示"""
        return f"Board(moves={len(self.move_history)}, hash={self.get_state_hash()[:8]}...)"
    
    def __eq__(self, other) -> bool:
        """基于状态哈希判断相等性"""
        if not isinstance(other, Board):
            return False
        return self.get_state_hash() == other.get_state_hash()
    
    def __hash__(self) -> int:
        """支持作为字典键"""
        return int(self.get_state_hash()[:16], 16)


# ============ 辅助函数 ============

def create_board_from_fen(fen: str) -> Board:
    """
    从FEN字符串创建棋盘
    
    Args:
        fen: FEN格式字符串
        
    Returns:
        Board对象
    """
    return Board(fen=fen, move_history=[], metadata={})


def create_initial_board() -> Board:
    """
    快捷函数: 创建初始棋盘
    
    Returns:
        初始化的Board对象
    """
    return Board.create_initial()