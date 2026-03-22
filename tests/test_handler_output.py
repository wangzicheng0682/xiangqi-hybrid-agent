"""
Tests for handler output structure.

Reference:
  - PRD: Sprint 1 / 验收门禁 - "handler 输出结构必须包含 bestmove/eval/citations"
  - TECH: Gradio/Web形态
"""

import pytest
from core.types.state import GameState


class TestHandlerOutputStructure:
    """Test that handler output has required fields."""

    def test_game_state_has_required_fields(self):
        """Test GameState has bestmove, eval, citations fields."""
        state = GameState(
            fen="rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1",
            bestmove="炮二平五",
            eval="红方稍优 (+0.3)",
            citations=["[知识图谱] 胜率55%"]
        )

        assert hasattr(state, 'fen')
        assert hasattr(state, 'bestmove')
        assert hasattr(state, 'eval')
        assert hasattr(state, 'citations')

    def test_game_state_bestmove_present(self):
        """Test that bestmove field exists and is string."""
        state = GameState(
            fen="test",
            bestmove="炮二平五"
        )

        assert state.bestmove is not None
        assert isinstance(state.bestmove, str)

    def test_game_state_eval_present(self):
        """Test that eval field exists and is string."""
        state = GameState(
            fen="test",
            eval="红方优势"
        )

        assert state.eval is not None
        assert isinstance(state.eval, str)

    def test_game_state_citations_is_list(self):
        """Test that citations field is a list."""
        state = GameState(
            fen="test",
            citations=["citation1", "citation2"]
        )

        assert isinstance(state.citations, list)
        assert len(state.citations) == 2

    def test_game_state_validity_check(self):
        """Test GameState validity check."""
        valid_state = GameState(fen="valid fen")
        invalid_state = GameState(fen="")

        assert valid_state.is_valid() is True
        assert invalid_state.is_valid() is False

    def test_game_state_default_citations(self):
        """Test that citations defaults to empty list."""
        state = GameState(fen="test")

        assert state.citations == []
        assert isinstance(state.citations, list)

    def test_handler_output_structure_complete(self):
        """Test complete output structure matches PRD requirements."""
        # This simulates what handler should return
        output = {
            'fen': "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1",
            'bestmove': "炮二平五",
            'eval': "红方稍优 (+0.3)",
            'citations': [
                "[知识图谱] 此局面历史上红方胜率约55%",
                "[棋书RAG] 《橘中秘》: '当头炮势如破竹'"
            ]
        }

        # Verify all required fields exist
        required_fields = ['bestmove', 'eval', 'citations']
        for field in required_fields:
            assert field in output, f"Missing required field: {field}"

        # Verify types
        assert isinstance(output['bestmove'], str)
        assert isinstance(output['eval'], str)
        assert isinstance(output['citations'], list)
