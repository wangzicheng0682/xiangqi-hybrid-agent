"""
Mock KG 实现

Reference:
  - PRD: Sprint 2 / 任务2 - LangGraph状态机
  - TECH: Neo4j与图谱构建 / GraphRAG
"""

from core.engine.base import BaseKG, KGResult
from typing import Optional


class MockKG(BaseKG):
    """
    Mock知识图谱实现

    Sprint 2.0: 先用mock数据验证接口设计
    Sprint 2.1: 将连接真实Neo4j数据库
    """

    def query(self, fen: str) -> Optional[KGResult]:
        """
        Mock查询：返回预设的开局统计信息

        实际实现时将通过Cypher查询Neo4j：
        - 查询当前局面节点
        - 统计历史胜率
        - 获取开局类型
        """
        # Mock: 初始局面统计
        if "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9" in fen:
            return KGResult(
                win_rate=55.0,
                opening_name="当头炮开局",
                statistics="此局面历史上红方胜率约55%，黑方常见应对为马8进7"
            )
        elif "w" in fen:
            # 红方走棋
            return KGResult(
                win_rate=52.0,
                opening_name="中局",
                statistics="红方历史胜率约52%"
            )
        else:
            # 黑方走棋
            return KGResult(
                win_rate=48.0,
                opening_name="中局",
                statistics="黑方历史胜率约52%"
            )


__all__ = ['MockKG']
