"""
统一接口抽象层 - 基础类型定义

Reference:
  - PRD: Sprint 2 / 架构设计 / Tool-first原则
  - TECH: 系统工作流程 / 多工具协同
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class EngineResult:
    """引擎分析结果"""
    bestmove: str  # 最佳着法（中文表示）
    score: float    # 局面评估分数
    depth: int      # 搜索深度
    pv: List[str]   # 主要变例 (Principal Variation)


@dataclass
class KGResult:
    """知识图谱检索结果"""
    win_rate: Optional[float]  # 历史胜率
    opening_name: Optional[str]  # 开局名称
    statistics: str  # 统计信息描述


@dataclass
class RAGResult:
    """棋书检索结果"""
    book_name: str   # 书名
    content: str     # 引用内容
    relevance: float # 相关性分数


class BaseEngine(ABC):
    """引擎抽象基类"""

    @abstractmethod
    def analyze(self, fen: str, depth: int = 20) -> EngineResult:
        """
        分析局面

        Args:
            fen: FEN串
            depth: 搜索深度

        Returns:
            EngineResult: 引擎分析结果
        """
        pass


class BaseKG(ABC):
    """知识图谱抽象基类"""

    @abstractmethod
    def query(self, fen: str) -> Optional[KGResult]:
        """
        查询知识图谱

        Args:
            fen: FEN串

        Returns:
            KGResult: 知识图谱检索结果，无数据返回None
        """
        pass


class BaseRAG(ABC):
    """棋书检索抽象基类"""

    @abstractmethod
    def retrieve(self, query: str, top_k: int = 3) -> List[RAGResult]:
        """
        检索棋书内容

        Args:
            query: 查询文本
            top_k: 返回结果数量

        Returns:
            List[RAGResult]: 检索结果列表
        """
        pass
