"""
Tests for FEN validation.

Reference:
  - PRD: Sprint 1 / 验收门禁
  - TECH: FEN解析与棋盘生成
"""

import pytest
from core.utils.fen_validator import validate_fen, is_legal_fen


class TestFENValidation:
    """Test FEN string validation."""

    def test_valid_initial_position(self):
        """Test valid initial position FEN."""
        fen = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"
        is_valid, msg = validate_fen(fen)
        assert is_valid is True
        assert msg == "Valid FEN"

    def test_valid_midgame_position(self):
        """Test valid midgame position."""
        fen = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"
        is_valid, msg = validate_fen(fen)
        assert is_valid is True

    def test_empty_fen(self):
        """Test empty FEN string."""
        is_valid, msg = validate_fen("")
        assert is_valid is False
        assert "empty" in msg.lower()

    def test_missing_turn_field(self):
        """Test FEN without turn field."""
        fen = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR"
        is_valid, msg = validate_fen(fen)
        assert is_valid is False
        assert "turn" in msg.lower()

    def test_invalid_turn(self):
        """Test FEN with invalid turn character."""
        fen = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR x - - 0 1"
        is_valid, msg = validate_fen(fen)
        assert is_valid is False
        assert "turn" in msg.lower()

    def test_wrong_number_of_ranks(self):
        """Test FEN with wrong number of ranks."""
        fen = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"
        is_valid, msg = validate_fen(fen)
        assert is_valid is False
        assert "10 ranks" in msg

    def test_invalid_piece_character(self):
        """Test FEN with invalid piece character."""
        fen = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNX w - - 0 1"
        is_valid, msg = validate_fen(fen)
        assert is_valid is False
        assert "Invalid character" in msg

    def test_is_legal_fen_helper(self):
        """Test is_legal_fen helper function."""
        valid_fen = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"
        invalid_fen = "invalid"

        assert is_legal_fen(valid_fen) is True
        assert is_legal_fen(invalid_fen) is False

    def test_rank_with_wrong_file_count(self):
        """Test rank that doesn't have exactly 9 files."""
        fen = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1/1C5C1/9/RNBAKABNR w - - 0 1"
        is_valid, msg = validate_fen(fen)
        assert is_valid is False
        assert "9 files" in msg
