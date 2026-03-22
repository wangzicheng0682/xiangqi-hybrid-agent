"""
Mock RAG 实现

Reference:
  - PRD: Sprint 2 / 任务1 - 棋书PDF向量化
  - TECH: 向量数据库与RAG / BooksRAG
"""

from core.engine.base import BaseRAG, RAGResult
from typing import List


class MockRAG(BaseRAG):
    """
    Mock棋书检索实现

    Sprint 2.0: 先用mock数据验证接口设计
    Sprint 2.1: 将连接真实向量数据库(FAISS/Chroma)
    """

    def retrieve(self, query: str, top_k: int = 3) -> List[RAGResult]:
        """
        Mock检索：返回预设的经典文献引用

        实际实现时将：
        - 将query转为向量
        - 在向量库中检索相似片段
        - 返回top_k个最相关结果
        """
        # Mock: 根据查询关键词返回相关引用
        results = []

        if "炮" in query or "开局" in query:
            results.append(RAGResult(
                book_name="橘中秘",
                content="当头炮势如破竹，直攻中宫，最为凶猛。",
                relevance=0.95
            ))

        if "马" in query or "布局" in query:
            results.append(RAGResult(
                book_name="梅花谱",
                content="屏风马稳健守势，可攻可守，为后手第一着法。",
                relevance=0.90
            ))

        if "中局" in query or "战术" in query:
            results.append(RAGResult(
                book_name="象棋中局战法",
                content="中局宜审势度形，或攻或守，随机应变。",
                relevance=0.85
            ))

        # 如果没有匹配，返回通用建议
        if not results:
            results.append(RAGResult(
                book_name="象棋攻防妙法",
                content="棋之为艺，贵在审时度势，知己知彼。",
                relevance=0.70
            ))

        return results[:top_k]


__all__ = ['MockRAG']
