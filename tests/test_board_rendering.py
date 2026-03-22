"""
Tests for board rendering.

Reference:
  - PRD: Sprint 1 / 验收门禁
  - TECH: FEN解析与棋盘生成
"""

import pytest
from PIL import Image
from core.render.board_renderer import render_board, render_board_to_file
import tempfile
import os


class TestBoardRendering:
    """Test board rendering functionality."""

    def test_render_initial_position(self):
        """Test rendering initial position."""
        fen = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"
        img = render_board(fen)

        assert isinstance(img, Image.Image)
        assert img.size == (540, 600)  # Default size

    def test_render_with_custom_size(self):
        """Test rendering with custom dimensions."""
        fen = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"
        img = render_board(fen, width=800, height=900)

        assert img.size == (800, 900)

    def test_render_to_file(self):
        """Test rendering board to file."""
        fen = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"

        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            output_path = tmp.name

        try:
            returned_path = render_board_to_file(fen, output_path)

            assert returned_path == output_path
            assert os.path.exists(output_path)
            assert os.path.getsize(output_path) > 0

            img = Image.open(output_path)
            assert isinstance(img, Image.Image)
            img.close()
        finally:
            if os.path.exists(output_path):
                try:
                    os.unlink(output_path)
                except PermissionError:
                    pass

    def test_render_with_pieces(self):
        """Test that board with pieces renders without error."""
        fen = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"
        img = render_board(fen)

        # Should not raise any exceptions
        assert img is not None

    def test_render_different_positions(self):
        """Test rendering multiple different positions."""
        fens = [
            "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1",
            "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR b - - 1 2",
        ]

        for fen in fens:
            img = render_board(fen)
            assert isinstance(img, Image.Image)
