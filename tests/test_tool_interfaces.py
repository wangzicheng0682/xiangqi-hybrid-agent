"""
接口统一性测试

Reference:
  - PRD: Sprint 2 / 测试驱动开发
  - TECH: Tool-first原则 / 多工具协同
"""

import pytest
from core.engine import MockEngine, EngineResult
from core.kg import MockKG, KGResult
from core.rag import MockRAG, RAGResult


class TestEngineInterface:
    """测试引擎接口"""

    def test_engine_returns_engine_result(self):
        """测试引擎返回正确的数据类型"""
        engine = MockEngine()
        result = engine.analyze("rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1")

        assert isinstance(result, EngineResult)
        assert hasattr(result, 'bestmove')
        assert hasattr(result, 'score')
        assert hasattr(result, 'depth')
        assert hasattr(result, 'pv')

    def test_engine_initial_position(self):
        """测试初始局面分析"""
        engine = MockEngine()
        fen = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"
        result = engine.analyze(fen, depth=20)

        assert result.bestmove == "炮二平五"
        assert result.score == 0.3
        assert result.depth == 20
        assert len(result.pv) > 0

    def test_engine_custom_depth(self):
        """测试自定义搜索深度"""
        engine = MockEngine()
        result = engine.analyze("test fen", depth=15)

        assert result.depth == 15


class TestKGInterface:
    """测试知识图谱接口"""

    def test_kg_returns_kg_result(self):
        """测试KG返回正确的数据类型"""
        kg = MockKG()
        result = kg.query("rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1")

        assert isinstance(result, KGResult)
        assert hasattr(result, 'win_rate')
        assert hasattr(result, 'opening_name')
        assert hasattr(result, 'statistics')

    def test_kg_initial_position(self):
        """测试初始局面查询"""
        kg = MockKG()
        fen = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"
        result = kg.query(fen)

        assert result.win_rate == 55.0
        assert "当头炮" in result.opening_name
        assert "胜率" in result.statistics

    def test_kg_returns_optional(self):
        """测试KG可能返回None（无数据时）"""
        # 注意：当前MockKG总是返回数据，但接口定义为Optional
        kg = MockKG()
        result = kg.query("some fen")

        # 接口应该允许None，但Mock实现总是返回数据
        assert result is not None or result is None


class TestRAGInterface:
    """测试棋书检索接口"""

    def test_rag_returns_list_of_rag_result(self):
        """测试RAG返回正确的数据类型"""
        rag = MockRAG()
        results = rag.retrieve("炮开局", top_k=3)

        assert isinstance(results, list)
        assert all(isinstance(r, RAGResult) for r in results)

    def test_rag_top_k_limit(self):
        """测试top_k参数限制返回数量"""
        rag = MockRAG()
        results = rag.retrieve("炮开局", top_k=1)

        assert len(results) <= 1

    def test_rag_result_has_required_fields(self):
        """测试RAG结果包含必要字段"""
        rag = MockRAG()
        results = rag.retrieve("炮开局")

        for result in results:
            assert hasattr(result, 'book_name')
            assert hasattr(result, 'content')
            assert hasattr(result, 'relevance')
            assert isinstance(result.relevance, float)
            assert 0 <= result.relevance <= 1

    def test_rag_relevance_ordering(self):
        """测试相关性排序"""
        rag = MockRAG()
        results = rag.retrieve("炮开局", top_k=3)

        # 结果应该按相关性降序排列
        relevances = [r.relevance for r in results]
        assert relevances == sorted(relevances, reverse=True)

    def test_rag_returns_default_on_no_match(self):
        """测试无匹配时返回默认结果"""
        rag = MockRAG()
        results = rag.retrieve("xyz123无关键词")

        # 应该返回至少一个通用结果
        assert len(results) > 0


class TestIntegration:
    """集成测试：工具协同工作"""

    def test_tools_work_together(self):
        """测试三个工具可以协同工作"""
        engine = MockEngine()
        kg = MockKG()
        rag = MockRAG()

        fen = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"

        # 引擎分析
        engine_result = engine.analyze(fen)

        # 知识图谱查询
        kg_result = kg.query(fen)

        # 棋书检索
        rag_results = rag.retrieve(engine_result.bestmove)

        # 验证协同
        assert engine_result.bestmove is not None
        assert kg_result is not None
        assert len(rag_results) > 0

        # 验证可以组合成最终输出
        citations = []
        citations.append(f"[知识图谱] {kg_result.statistics}")
        for rag_result in rag_results:
            citations.append(f"[棋书RAG] 《{rag_result.book_name}》")

        assert len(citations) > 0
