"""
Mock Engine 实现

Reference:
  - PRD: Sprint 2 / 任务2 - LangGraph状态机
  - TECH: Pikafish UCI封装 / 战术精确性
"""

from .base import BaseEngine, EngineResult
from typing import List


class MockEngine(BaseEngine):
    """
    Mock引擎实现

    Sprint 2.0: 先用mock数据验证接口设计
    Sprint 2.1: 将替换为真实Pikafish UCI调用
    """

    def analyze(self, fen: str, depth: int = 20) -> EngineResult:
        """
        Mock分析：返回预设的常见开局着法

        实际实现时将通过UCI协议与Pikafish通信：
        - uci: 初始化引擎
        - isready: 确认就绪
        - position fen {fen}: 设置局面
        - go depth {depth}: 发起搜索
        """
        # Mock: 根据FEN返回常见开局着法
        if "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9" in fen:
            # 初始局面：当头炮
            return EngineResult(
                bestmove="炮二平五",
                score=0.3,
                depth=depth,
                pv=["炮二平五", "马8进7", "马二进三", "车9平8"]
            )
        elif "w" in fen:
            # 红方走棋
            return EngineResult(
                bestmove="车一进一",
                score=0.1,
                depth=depth,
                pv=["车一进一"]
            )
        else:
            # 黑方走棋
            return EngineResult(
                bestmove="车9进1",
                score=-0.1,
                depth=depth,
                pv=["车9进1"]
            )


__all__ = ['MockEngine']
