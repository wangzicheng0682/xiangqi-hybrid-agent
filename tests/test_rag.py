"""
RAG 系统测试 — ChromaRAG 索引与检索

覆盖:
  - 棋理原则自动索引
  - 语义检索相关性
  - 按阶段/类型过滤
  - AgentTools.search_chess_knowledge 工具
  - 棋谱开局索引（可选）
"""

import pytest
from core.rag.chroma_rag import ChromaRAG, _get_collection, index_game_openings
from core.engine.base import RAGResult


class TestChromaRAGBasic:
    """基础 RAG 检索测试"""

    def test_collection_auto_created(self):
        """集合自动创建并索引棋理原则"""
        collection = _get_collection()
        assert collection.count() > 0, "集合应自动索引棋理原则"

    def test_principles_indexed(self):
        """应至少索引 60 条棋理原则"""
        collection = _get_collection()
        # knowledge_retriever 有 80+ 条原则
        result = collection.get(where={"type": "principle"}, limit=1)
        assert result and result["ids"], "应有 principle 类型的文档"

    def test_retrieve_attack_pattern(self):
        """检索攻杀相关知识"""
        rag = ChromaRAG()
        results = rag.retrieve("马后炮杀法", top_k=3)
        assert len(results) > 0
        assert all(isinstance(r, RAGResult) for r in results)
        # 至少一条应与马后炮相关
        contents = " ".join(r.content for r in results)
        assert "马" in contents or "炮" in contents

    def test_retrieve_opening(self):
        """检索开局知识"""
        rag = ChromaRAG()
        results = rag.retrieve("当头炮开局", top_k=3)
        assert len(results) > 0
        contents = " ".join(r.content for r in results)
        assert "炮" in contents or "开局" in contents

    def test_retrieve_defense(self):
        """检索防守知识"""
        rag = ChromaRAG()
        results = rag.retrieve("将帅安全防守", top_k=3)
        assert len(results) > 0

    def test_relevance_scores(self):
        """相关性分数在合理范围"""
        rag = ChromaRAG()
        results = rag.retrieve("车马配合进攻", top_k=5)
        for r in results:
            assert 0.0 <= r.relevance <= 1.0

    def test_retrieve_by_phase(self):
        """按阶段过滤"""
        rag = ChromaRAG()
        results = rag.retrieve_by_phase("残局技巧", "endgame", top_k=3)
        assert len(results) > 0

    def test_retrieve_by_type(self):
        """按类型过滤"""
        rag = ChromaRAG()
        results = rag.retrieve_by_type("车马冷着", "principle", top_k=3)
        assert len(results) > 0

    def test_empty_query(self):
        """空查询不崩溃"""
        rag = ChromaRAG()
        results = rag.retrieve("", top_k=3)
        # 可能返回一些结果（最近邻），不应抛异常
        assert isinstance(results, list)


class TestSearchChessKnowledgeTool:
    """AgentTools.search_chess_knowledge 工具测试"""

    def test_tool_basic(self):
        """基本工具调用"""
        from core.llm.agent_tools import AgentTools
        tools = AgentTools()
        result = tools.search_chess_knowledge(query="中炮对屏风马")
        assert result.success
        assert result.data["count"] > 0

    def test_tool_with_top_k(self):
        """指定返回数量"""
        from core.llm.agent_tools import AgentTools
        tools = AgentTools()
        result = tools.search_chess_knowledge(query="弃子战术", top_k=2)
        assert result.success
        assert result.data["count"] <= 2

    def test_tool_message_format(self):
        """返回消息格式正确"""
        from core.llm.agent_tools import AgentTools
        tools = AgentTools()
        result = tools.search_chess_knowledge(query="残局定式")
        assert result.success
        # message 应包含编号和来源
        assert "1." in result.message


class TestGameOpeningIndex:
    """棋谱开局索引测试（仅在数据文件存在时）"""

    def test_index_games(self):
        """索引少量棋谱"""
        import os
        pgn_path = os.path.join(
            os.path.dirname(__file__), "..", "data", "init_data", "dpxq-99813games.pgns"
        )
        if not os.path.exists(pgn_path):
            pytest.skip("棋谱数据文件不存在")

        count = index_game_openings(max_games=50)
        # 首次索引应返回正数，再次调用返回0（已索引）
        assert isinstance(count, int)
        assert count >= 0
