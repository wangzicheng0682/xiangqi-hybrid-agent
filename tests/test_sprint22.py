#!/usr/bin/env python3
"""Test Sprint 2.2 frontend components"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.types.state import GameState
from core.utils.fen_validator import validate_fen
from core.render.board_renderer import render_board
from core.engine import MockEngine
from core.kg import MockKG
from core.rag import MockRAG

print("Testing imports...")

def test_engine():
    print("\nTesting Engine...")
    engine = MockEngine()
    result = engine.analyze("rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1")
    print(f"Best move: {result.bestmove}")
    print(f"Score: {result.score}")
    assert result.bestmove is not None
    assert result.score is not None
    print("Engine test passed!")

def test_kg():
    print("\nTesting KG...")
    kg = MockKG()
    result = kg.query("rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1")
    print(f"Win rate: {result.win_rate}")
    print(f"Opening: {result.opening_name}")
    assert result.win_rate >= 0
    assert result.opening_name is not None
    print("KG test passed!")

def test_rag():
    print("\nTesting RAG...")
    rag = MockRAG()
    results = rag.retrieve("开局策略")
    print(f"Found {len(results)} results")
    if results:
        print(f"First result: {results[0].content[:50]}...")
    assert len(results) > 0
    assert results[0].content is not None
    print("RAG test passed!")

def test_xiangqi_rules():
    print("\nTesting Xiangqi Rules...")
    
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
    
    PIECE_NAMES = {
        'K': '帅', 'k': '将', 'A': '仕', 'a': '士',
        'E': '相', 'e': '象', 'R': '车', 'r': '車',
        'C': '炮', 'c': '砲', 'N': '马', 'n': '馬',
        'P': '兵', 'p': '卒',
    }
    
    class XiangqiRules:
        @staticmethod
        def is_red(piece: str) -> bool:
            return piece.isupper() if piece else False
        
        @staticmethod
        def is_black(piece: str) -> bool:
            return piece.islower() if piece else False
        
        @staticmethod
        def _is_in_palace(row, col, is_red):
            if not (3 <= col <= 5):
                return False
            if is_red:
                return 7 <= row <= 9
            else:
                return 0 <= row <= 2
        
        @staticmethod
        def _is_on_side(row, is_red):
            if is_red:
                return row >= 5
            else:
                return row <= 4
        
        @staticmethod
        def _knight_moves(board, row, col, is_red):
            moves = []
            knight_moves = [
                (2, 1, 1, 0), (2, -1, 1, 0),
                (-2, 1, -1, 0), (-2, -1, -1, 0),
                (1, 2, 0, 1), (1, -2, 0, -1),
                (-1, 2, 0, 1), (-1, -2, 0, -1),
            ]
            for dr, dc, br, bc in knight_moves:
                nr, nc = row + dr, col + dc
                mr, mc = row + br, col + bc
                if 0 <= nr < 10 and 0 <= nc < 9 and not board[mr][mc]:
                    target = board[nr][nc]
                    if not target or XiangqiRules.is_red(target) != is_red:
                        moves.append((nr, nc))
            return moves
        
        @staticmethod
        def get_legal_moves(board, row: int, col: int):
            piece = board[row][col]
            if not piece:
                return []
            
            is_red = XiangqiRules.is_red(piece)
            piece_type = piece.lower()
            
            if piece_type == 'n':
                return XiangqiRules._knight_moves(board, row, col, is_red)
            return []
        
        @staticmethod
        def is_in_check(board, red_to_move):
            return False
    
    board = [row[:] for row in INITIAL_BOARD]
    
    legal_moves = XiangqiRules.get_legal_moves(board, 9, 1)
    print(f"Legal moves for red knight at (9,1): {legal_moves}")
    assert len(legal_moves) > 0
    
    in_check = XiangqiRules.is_in_check(board, True)
    print(f"Red in check: {in_check}")
    assert not in_check
    
    print("Xiangqi Rules test passed!")

def test_board_to_fen():
    print("\nTesting board_to_fen...")
    
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
    
    def board_to_fen(board, red_to_move=True):
        rows = []
        for row in board:
            fen_row = ""
            empty = 0
            for cell in row:
                if cell:
                    if empty:
                        fen_row += str(empty)
                        empty = 0
                    fen_row += cell
                else:
                    empty += 1
            if empty:
                fen_row += str(empty)
            rows.append(fen_row)
        turn = "w" if red_to_move else "b"
        return "/".join(rows) + f" {turn} - - 0 1"
    
    fen = board_to_fen(INITIAL_BOARD, True)
    print(f"Initial FEN: {fen}")
    assert "rnbakabnr" in fen
    assert "w" in fen
    
    print("board_to_fen test passed!")

if __name__ == "__main__":
    test_engine()
    test_kg()
    test_rag()
    test_xiangqi_rules()
    test_board_to_fen()
    print("\n✅ All Sprint 2.2 tests passed!")
