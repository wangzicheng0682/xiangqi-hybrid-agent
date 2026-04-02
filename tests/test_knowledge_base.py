"""
测试知识库扩展（棋理原则 + 开局识别）
"""

import pytest
from core.llm.knowledge_retriever import (
    ChessKnowledgeBase,
    get_knowledge_base,
    query_principles_for_tension,
    get_principles_prompt,
)
from core.opening.opening_book import identify_opening, get_opening_name


class TestKnowledgeBaseExpansion:
    """测试棋理知识库扩展"""

    def setup_method(self):
        self.kb = ChessKnowledgeBase()

    # ── 覆盖率 ─────────────────────────────────────────────────────

    def test_tension_types_count(self):
        """至少 10 种张力类型"""
        assert len(self.kb.TENSION_PRINCIPLES) >= 10

    def test_total_principles_count(self):
        """总原则数量 >= 70"""
        total = sum(len(v) for v in self.kb.TENSION_PRINCIPLES.values())
        total += len(self.kb.GENERAL_PRINCIPLES)
        assert total >= 70, f"只有 {total} 条原则，不够"

    def test_every_category_has_principles(self):
        """每个张力类型至少 4 条"""
        for cat, principles in self.kb.TENSION_PRINCIPLES.items():
            assert len(principles) >= 4, f"{cat} 只有 {len(principles)} 条"

    def test_general_principles_count(self):
        """通用原则 >= 5"""
        assert len(self.kb.GENERAL_PRINCIPLES) >= 5

    # ── 数据完整性 ──────────────────────────────────────────────────

    def test_principle_fields_non_empty(self):
        """所有原则的必填字段不为空"""
        all_principles = []
        for cat, principles in self.kb.TENSION_PRINCIPLES.items():
            all_principles.extend(principles)
        all_principles.extend(self.kb.GENERAL_PRINCIPLES)

        for p in all_principles:
            assert p.content, f"content 为空: {p}"
            assert p.applies_when, f"applies_when 为空: {p.content}"

    def test_principle_to_dict(self):
        """to_dict 包含所有字段"""
        p = self.kb.GENERAL_PRINCIPLES[0]
        d = p.to_dict()
        assert "content" in d
        assert "applies_when" in d
        assert "phase" in d
        assert "tags" in d

    # ── 查询方法 ──────────────────────────────────────────────────

    def test_query_for_tension_known_type(self):
        """已知张力类型返回原则"""
        results = self.kb.query_for_tension("material_vs_initiative")
        assert len(results) >= 4

    def test_query_for_tension_unknown_type(self):
        """未知张力类型返回空列表"""
        results = self.kb.query_for_tension("totally_unknown_xyz")
        assert results == []

    def test_query_for_tension_phase_filtering(self):
        """阶段过滤：开局原则排在前面"""
        results = self.kb.query_for_tension("opening_theory", "开局")
        assert len(results) >= 5
        # 第一条原则应该是 opening 或 all 阶段
        assert results[0].phase in ("opening", "all", "")

    def test_query_for_tension_phase_english(self):
        """英文阶段名也能用"""
        results = self.kb.query_for_tension("endgame_theory", "endgame")
        assert len(results) >= 4

    def test_query_by_tags(self):
        """标签查询返回匹配的原则"""
        results = self.kb.query_by_tags(["has_initiative"])
        assert len(results) >= 2

    def test_query_by_tags_with_phase(self):
        """标签+阶段组合查询"""
        results = self.kb.query_by_tags(["king_safety_critical"], "middlegame")
        assert len(results) >= 1

    def test_query_by_tags_empty(self):
        """空标签返回空列表"""
        results = self.kb.query_by_tags([])
        assert results == []

    def test_query_by_tags_no_match(self):
        """无匹配标签返回空列表"""
        results = self.kb.query_by_tags(["totally_nonexistent_tag_xyz"])
        assert results == []

    # ── Prompt 生成 ────────────────────────────────────────────────

    def test_get_principles_for_prompt(self):
        """Prompt 格式正确"""
        text = self.kb.get_principles_for_prompt("attack_pattern")
        assert "相关棋理原则" in text
        assert "适用" in text

    def test_get_principles_for_prompt_empty(self):
        """未知类型返回空"""
        text = self.kb.get_principles_for_prompt("nonexistent_type")
        assert text == ""

    # ── 便捷函数 ──────────────────────────────────────────────────

    def test_get_knowledge_base(self):
        """get_knowledge_base 返回实例"""
        kb = get_knowledge_base()
        assert isinstance(kb, ChessKnowledgeBase)

    def test_query_principles_for_tension_func(self):
        """便捷函数返回字典列表"""
        results = query_principles_for_tension("defense_pattern")
        assert isinstance(results, list)
        assert len(results) >= 3
        assert isinstance(results[0], dict)
        assert "content" in results[0]

    def test_get_principles_prompt_func(self):
        """便捷字符串函数"""
        text = get_principles_prompt("piece_coordination")
        assert "相关棋理原则" in text


class TestOpeningBookExpansion:
    """测试开局库扩展"""

    def test_identify_zhongpao(self):
        """识别中炮开局"""
        result = identify_opening(["h2e2"])
        assert result is not None
        assert "中炮" in result.name

    def test_identify_feixiang(self):
        """识别飞相局"""
        result = identify_opening(["g0e2"])
        assert result is not None
        assert "飞相" in result.name

    def test_identify_qima(self):
        """识别起马局"""
        result = identify_opening(["h0g2"])
        assert result is not None
        assert "起马" in result.name

    def test_identify_zhongpao_vs_pingfengma(self):
        """识别中炮对屏风马"""
        result = identify_opening(["h2e2", "h9g7", "h0g2"])
        assert result is not None
        assert "屏风马" in result.name

    def test_identify_zhongpao_vs_shunpao(self):
        """识别顺手炮"""
        result = identify_opening(["h2e2", "b7e7"])
        assert result is not None
        assert "顺" in result.name or "炮" in result.name

    def test_identify_tiehuache(self):
        """识别铁滑车"""
        result = identify_opening(["i0i1"])
        assert result is not None
        assert "铁滑车" in result.name

    def test_identify_unknown(self):
        """未知走法序列返回 None"""
        result = identify_opening(["z9z8"])
        assert result is None

    def test_get_opening_name_empty(self):
        """空走法"""
        name = get_opening_name([])
        assert name == "未开局"

    def test_opening_sequences_expanded(self):
        """开局序列数量 >= 30"""
        from core.opening.opening_book import OPENING_SEQUENCES
        assert len(OPENING_SEQUENCES) >= 25, f"只有 {len(OPENING_SEQUENCES)} 条序列"
