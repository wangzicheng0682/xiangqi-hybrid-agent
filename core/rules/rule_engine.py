"""
规则引擎 - 基于Pikafish引擎真值

职责: 获取合法走法，不做任何自研规则计算

设计原则:
- 引擎真值是唯一可信来源
- 不自行计算攻击/防御关系
- 不生成语义标签
"""

from typing import List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

# 延迟导入，避免循环依赖
_pikafish_engine = None


def _get_engine():
    """获取引擎实例（单例模式）"""
    global _pikafish_engine
    if _pikafish_engine is None:
        from core.engine.pikafish_engine import PikafishEngine
        _pikafish_engine = PikafishEngine()
        _pikafish_engine.start()
    return _pikafish_engine


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
        engine = _get_engine()
        
        # 使用perft 1获取所有合法走法
        # perft会输出所有走法及其数量
        import subprocess
        
        engine_path = engine.engine_path
        process = subprocess.Popen(
            [str(engine_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        
        try:
            # 初始化
            process.stdin.write("uci\n")
            process.stdin.flush()
            
            # 等待uciok
            while True:
                line = process.stdout.readline()
                if "uciok" in line:
                    break
            
            # 设置位置
            process.stdin.write(f"position fen {fen}\n")
            process.stdin.flush()
            
            # 使用perft 1获取走法
            process.stdin.write("perft 1\n")
            process.stdin.flush()
            
            moves = []
            node_count = 0
            
            # 读取所有走法
            while True:
                line = process.stdout.readline().strip()
                if not line:
                    continue
                
                # 解析走法行 (格式: "h2e2: 123")
                if ":" in line:
                    parts = line.split(":")
                    uci = parts[0].strip()
                    count = int(parts[1].strip()) if len(parts) > 1 else 0
                    
                    from_sq, to_sq = RuleEngine._uci_to_squares(uci)
                    iccs = RuleEngine._uci_to_iccs(uci)
                    
                    moves.append(LegalMove(
                        from_square=from_sq,
                        to_square=to_sq,
                        uci=uci,
                        iccs=iccs
                    ))
                
                # 解析总行数
                elif line.isdigit():
                    node_count = int(line)
                    break
            
            # 检查是否被将军（通过分析局面）
            process.stdin.write("d\n")
            process.stdin.flush()
            
            is_check = False
            is_checkmate = False
            
            # 读取局面信息
            for _ in range(20):  # 最多读取20行
                line = process.stdout.readline()
                if "Checkers:" in line:
                    is_check = True
                if "Checkmate" in line or len(moves) == 0 and is_check:
                    is_checkmate = True
                if not line.strip():
                    break
            
            side_to_move = RuleEngine._parse_side_to_move(fen)
            
            return LegalMovesResult(
                fen=fen,
                side_to_move=side_to_move,
                moves=moves,
                count=len(moves),
                is_check=is_check,
                is_checkmate=is_checkmate,
                is_stalemate=(len(moves) == 0 and not is_check)
            )
            
        finally:
            process.stdin.write("quit\n")
            process.stdin.flush()
            process.wait(timeout=5)
    
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
