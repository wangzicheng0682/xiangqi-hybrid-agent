"""
对弈模式 API 测试

覆盖:
  - AI 走棋 /api/ai-move 和 /api/game/ai-move（双路由）
  - 三种难度（字符串 + 数字）
  - 前端兼容格式（board + red_to_move）
  - 返回格式验证
  - 边界情况
"""

import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

INITIAL_FEN = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"

INITIAL_BOARD = [
    ['r', 'n', 'b', 'a', 'k', 'a', 'b', 'n', 'r'],
    ['', '', '', '', '', '', '', '', ''],
    ['', 'c', '', '', '', '', '', 'c', ''],
    ['p', '', 'p', '', 'p', '', 'p', '', 'p'],
    ['', '', '', '', '', '', '', '', ''],
    ['', '', '', '', '', '', '', '', ''],
    ['P', '', 'P', '', 'P', '', 'P', '', 'P'],
    ['', 'C', '', '', '', '', '', 'C', ''],
    ['', '', '', '', '', '', '', '', ''],
    ['R', 'N', 'B', 'A', 'K', 'A', 'B', 'N', 'R'],
]


class TestAIMoveEndpoint:
    """AI 走棋 API 测试"""

    def test_ai_move_basic(self):
        """基本 AI 走棋（FEN格式）"""
        resp = client.post("/api/game/ai-move", json={
            "fen": INITIAL_FEN,
            "difficulty": "easy",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["move"]
        assert len(data["move"]) == 4
        assert data["fen"]
        assert "board" in data

    def test_ai_move_board_format(self):
        """前端board格式"""
        resp = client.post("/api/ai-move", json={
            "board": INITIAL_BOARD,
            "red_to_move": True,
            "difficulty": 10,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["move"]
        assert len(data["board"]) == 10
        assert 0 <= data["from_row"] <= 9
        assert 0 <= data["from_col"] <= 8

    def test_ai_move_medium(self):
        """中等难度"""
        resp = client.post("/api/ai-move", json={
            "fen": INITIAL_FEN,
            "difficulty": "medium",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["move"]

    def test_ai_move_hard(self):
        """困难难度"""
        resp = client.post("/api/ai-move", json={
            "fen": INITIAL_FEN,
            "difficulty": "hard",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["move"]

    def test_ai_move_numeric_difficulty(self):
        """数字难度"""
        resp = client.post("/api/ai-move", json={
            "fen": INITIAL_FEN,
            "difficulty": 4,
        })
        assert resp.status_code == 200

    def test_ai_move_black_turn(self):
        """黑方走棋"""
        black_fen = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR b - - 0 1"
        resp = client.post("/api/ai-move", json={
            "fen": black_fen,
            "difficulty": "easy",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["move"]

    def test_ai_move_midgame(self):
        """中局局面"""
        midgame_fen = "r1bakab1r/9/1cn4c1/p1p1p1p1p/9/2P6/P3P1P1P/1C2C1N2/9/RNBAKAB1R w - - 0 5"
        resp = client.post("/api/ai-move", json={
            "fen": midgame_fen,
            "difficulty": "easy",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["move"]

    def test_ai_move_response_format(self):
        """返回格式完整性"""
        resp = client.post("/api/ai-move", json={
            "fen": INITIAL_FEN,
            "difficulty": "easy",
        })
        data = resp.json()
        for key in ["move", "from_row", "from_col", "to_row", "to_col",
                     "board", "fen", "score", "explanation", "in_check", "game_over"]:
            assert key in data, f"缺少字段: {key}"

    def test_ai_move_default_difficulty(self):
        """默认难度"""
        resp = client.post("/api/ai-move", json={
            "fen": INITIAL_FEN,
        })
        assert resp.status_code == 200
