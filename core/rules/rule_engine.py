"""
规则引擎 - 基于Pikafish引擎真值

职责: 获取合法走法，不做任何自研规则计算

设计原则:
- 引擎真值是唯一可信来源
- 不自行计算攻击/防御关系
- 不生成语义标签
"""

from typing import List, Tuple
from dataclasses import dataclass

from core.rules.xiangqi_rules import XiangqiRulesEngine

@dataclass
class LegalMove:
    """单个合法走法"""
    from_square: str      # 起始位置（如 "h2"）
    to_square: str        # 目标位置（如 "e2"）
    uci: str              # UCI格式（如 "h2e2"）
    iccs: str             # ICCS格式（如 "H2-E2"）


@dataclass
class LegalMovesResult:
    """合法走法结果"""
    fen: str                          # 输入FEN
    side_to_move: str                 # 轮到哪方（"red"/"black"）
    moves: List[LegalMove]            # 合法走法列表
    count: int                        # 合法走法数量
    is_check: bool                    # 是否被将军
    is_checkmate: bool                # 是否被将死
    is_stalemate: bool                # 是否逼和


class RuleEngine:
    """
    规则引擎 - 基于Pikafish引擎
    
    不自行计算规则，完全依赖引擎输出
    """
    
    @staticmethod
    def _uci_to_iccs(uci: str) -> str:
        """UCI格式转ICCS格式"""
        if len(uci) < 4:
            return uci
        files = 'abcdefghi'
        ranks = '0123456789'
        from_file = files[ord(uci[0]) - ord('a')].upper()
        from_rank = uci[1]
        to_file = files[ord(uci[2]) - ord('a')].upper()
        to_rank = uci[3]
        return f"{from_file}{from_rank}-{to_file}{to_rank}"
    
    @staticmethod
    def _uci_to_squares(uci: str) -> Tuple[str, str]:
        """UCI格式转起始/目标位置"""
        if len(uci) < 4:
            return uci[:2], uci[2:4] if len(uci) >= 4 else uci[2:]
        return uci[:2], uci[2:4]

    @staticmethod
    def _coords_to_square(row: int, col: int) -> str:
        """内部坐标转UCI格点。"""
        return f"{'abcdefghi'[col]}{9 - row}"

    @staticmethod
    def _coords_to_uci(from_row: int, from_col: int, to_row: int, to_col: int) -> str:
        """内部坐标转UCI走法。"""
        return (
            f"{RuleEngine._coords_to_square(from_row, from_col)}"
            f"{RuleEngine._coords_to_square(to_row, to_col)}"
        )

    @staticmethod
    def _fen_to_board(fen: str) -> List[List[str]]:
        """FEN转棋盘二维数组。"""
        board_part = fen.split()[0]
        rows = board_part.split('/')
        board: List[List[str]] = []

        for row_text in rows:
            row: List[str] = []
            for char in row_text:
                if char.isdigit():
                    row.extend([''] * int(char))
                else:
                    row.append(char)
            if len(row) != 9:
                raise ValueError(f"非法FEN行: {row_text}")
            board.append(row)

        if len(board) != 10:
            raise ValueError(f"非法FEN: {fen}")

        return board
    
    @staticmethod
    def _parse_side_to_move(fen: str) -> str:
        """从FEN解析当前行棋方"""
        parts = fen.split()
        if len(parts) >= 2:
            return "red" if parts[1] == 'w' else "black"
        return "red"
    
    @staticmethod
    def get_legal_moves(fen: str) -> LegalMovesResult:
        """
        获取当前局面的所有合法走法
        
        基于Pikafish引擎，不自行计算
        
        Args:
            fen: 当前局面FEN字符串
            
        Returns:
            LegalMovesResult: 合法走法结果
        """
        board = RuleEngine._fen_to_board(fen)
        side_to_move = RuleEngine._parse_side_to_move(fen)
        is_red_turn = side_to_move == "red"

        moves: List[LegalMove] = []
        for row in range(10):
            for col in range(9):
                piece = board[row][col]
                if not piece:
                    continue
                if XiangqiRulesEngine.is_red(piece) != is_red_turn:
                    continue

                for to_row, to_col in XiangqiRulesEngine.get_legal_moves(board, row, col):
                    uci = RuleEngine._coords_to_uci(row, col, to_row, to_col)
                    from_sq, to_sq = RuleEngine._uci_to_squares(uci)
                    moves.append(LegalMove(
                        from_square=from_sq,
                        to_square=to_sq,
                        uci=uci,
                        iccs=RuleEngine._uci_to_iccs(uci),
                    ))

        king_pos = XiangqiRulesEngine._find_king(board, is_red_turn)
        is_check = False
        if king_pos is not None:
            is_check = XiangqiRulesEngine._is_in_check(
                board,
                king_pos[0],
                king_pos[1],
                is_attacking_red=not is_red_turn,
            )

        return LegalMovesResult(
            fen=fen,
            side_to_move=side_to_move,
            moves=moves,
            count=len(moves),
            is_check=is_check,
            is_checkmate=(len(moves) == 0 and is_check),
            is_stalemate=(len(moves) == 0 and not is_check),
        )
    
    @staticmethod
    def is_legal_move(fen: str, move: str) -> bool:
        """
        判断指定走法是否合法
        
        Args:
            fen: 当前局面FEN字符串
            move: 走法（UCI格式，如 "h2e2"）
            
        Returns:
            bool: 是否合法
        """
        result = RuleEngine.get_legal_moves(fen)
        return any(m.uci == move for m in result.moves)


# 便捷函数
def get_legal_moves(fen: str) -> LegalMovesResult:
    """获取合法走法（便捷函数）"""
    return RuleEngine.get_legal_moves(fen)


def is_legal_move(fen: str, move: str) -> bool:
    """判断走法是否合法（便捷函数）"""
    return RuleEngine.is_legal_move(fen, move)
