"""
规则引擎正确性测试

覆盖：
- 自将过滤（走后不能让己方帅/将被攻击）
- 将帅照面过滤（走后不能将帅同列无遮挡）
- 被将军时必须应将
- RuleEngine 与 XiangqiRulesEngine 一致性
"""

import pytest
from core.rules.xiangqi_rules import XiangqiRulesEngine as Rules
from core.rules.rule_engine import RuleEngine


# ═══════════════════════════════════════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════════════════════════════════════

def make_board():
    """创建空棋盘"""
    return [['' for _ in range(9)] for _ in range(10)]


def place(board, row, col, piece):
    board[row][col] = piece
    return board


def legal_uci(board, row, col):
    """返回某位置棋子的合法走法 UCI 列表"""
    moves = Rules.get_legal_moves(board, row, col)
    return {f"{'abcdefghi'[col]}{9 - row}{'abcdefghi'[c]}{9 - r}" for r, c in moves}


# ═══════════════════════════════════════════════════════════════════════════════
# 1. 自将过滤
# ═══════════════════════════════════════════════════════════════════════════════

class TestSelfCheckFiltering:
    """走后不能让自己帅/将被攻击"""

    def test_pinned_rook_cannot_move_laterally(self):
        """被牵制的车不能横向移动（会暴露帅）"""
        board = make_board()
        place(board, 9, 4, 'K')  # 红帅 e0
        place(board, 0, 4, 'k')  # 黑将 e9
        place(board, 5, 4, 'R')  # 红车 e4 — 挡在黑车和红帅之间
        place(board, 1, 4, 'r')  # 黑车 e8

        moves = Rules.get_legal_moves(board, 5, 4)
        # 红车只能沿 e 列移动，不能横向
        for r, c in moves:
            assert c == 4, f"红车不应该横向移动到({r},{c})，会暴露帅"

    def test_pinned_knight_cannot_move(self):
        """被牵制的马完全不能移动（所有日字走法都会暴露帅）"""
        board = make_board()
        place(board, 9, 4, 'K')  # 红帅 e0
        place(board, 0, 4, 'k')  # 黑将 e9
        place(board, 7, 4, 'N')  # 红马 e2 — 挡在e列
        place(board, 1, 4, 'r')  # 黑车 e8

        moves = Rules.get_legal_moves(board, 7, 4)
        # 马的所有走法都离开 e 列，全部送将
        assert len(moves) == 0, f"被牵制的马不应有任何合法走法，实际={moves}"

    def test_king_cannot_move_into_check(self):
        """帅不能走到被攻击的位置"""
        board = make_board()
        place(board, 9, 4, 'K')  # 红帅 e0
        place(board, 0, 4, 'k')  # 黑将 e9
        place(board, 9, 0, 'r')  # 黑车 a0 — 控制第0行

        moves = Rules.get_legal_moves(board, 9, 4)
        # 红帅不能走到 d0 或 f0（被黑车 a0 控制）; 只能上移到 e1(row8)
        for r, c in moves:
            assert r != 9 or c == 4, f"帅不应走到({r},{c})，row9被黑车控制"

    def test_must_escape_check(self):
        """被将军时，只有解将的走法是合法的"""
        board = make_board()
        place(board, 9, 4, 'K')  # 红帅 e0
        place(board, 0, 4, 'k')  # 黑将 e9
        place(board, 5, 4, 'P')  # 红兵 e4 — 遮挡照面
        place(board, 9, 0, 'r')  # 黑车 a0 — 将军红帅

        # 红帅被将军，只能跑到 e1（有兵遮挡不会照面）
        king_moves = Rules.get_legal_moves(board, 9, 4)
        assert len(king_moves) > 0, "被将军时应有解将着法"
        # 所有解将着法走完后帅不应仍被攻击
        for r, c in king_moves:
            new_board = [row[:] for row in board]
            new_board[r][c] = 'K'
            new_board[9][4] = ''
            assert not Rules._is_square_attacked(new_board, r, c, False), \
                f"解将着法({r},{c})走完后帅仍被攻击"
            assert not Rules._kings_face_each_other(new_board), \
                f"解将着法({r},{c})走完后将帅照面"


# ═══════════════════════════════════════════════════════════════════════════════
# 2. 将帅照面过滤
# ═══════════════════════════════════════════════════════════════════════════════

class TestKingsFaceToFace:
    """走后不能将帅同列无遮挡"""

    def test_detection_no_obstruction(self):
        """同列无遮挡 → 照面"""
        board = make_board()
        place(board, 9, 4, 'K')
        place(board, 0, 4, 'k')
        assert Rules._kings_face_each_other(board) is True

    def test_detection_with_obstruction(self):
        """同列有遮挡 → 不照面"""
        board = make_board()
        place(board, 9, 4, 'K')
        place(board, 0, 4, 'k')
        place(board, 5, 4, 'P')
        assert Rules._kings_face_each_other(board) is False

    def test_detection_different_column(self):
        """不同列 → 不照面"""
        board = make_board()
        place(board, 9, 4, 'K')
        place(board, 0, 3, 'k')
        assert Rules._kings_face_each_other(board) is False

    def test_piece_cannot_expose_face_to_face(self):
        """挡在将帅之间的棋子不能移走导致照面"""
        board = make_board()
        place(board, 9, 4, 'K')  # 红帅 e0
        place(board, 0, 4, 'k')  # 黑将 e9
        place(board, 5, 4, 'P')  # 红兵 e4 — 唯一遮挡

        moves = Rules.get_legal_moves(board, 5, 4)
        # 红兵不能横向移动（假设已过河）；
        # 但即使向前走(e5)也可以，因为 e5 仍在 e 列挡住
        for r, c in moves:
            new_board = [row[:] for row in board]
            new_board[r][c] = 'P'
            new_board[5][4] = ''
            assert not Rules._kings_face_each_other(new_board), \
                f"走到({r},{c})后将帅照面，该走法不应合法"

    def test_king_cannot_step_into_face_to_face(self):
        """帅不能走到与将照面的位置"""
        board = make_board()
        place(board, 9, 3, 'K')  # 红帅 d0
        place(board, 0, 4, 'k')  # 黑将 e9

        king_moves = Rules.get_legal_moves(board, 9, 3)
        # 帅走到 e0(9,4) 会与 e9 黑将照面（同列无遮挡）
        face_positions = [(9, 4)]
        for pos in face_positions:
            assert pos not in king_moves, f"帅不应走到{pos}，会照面"


# ═══════════════════════════════════════════════════════════════════════════════
# 3. RuleEngine 合法走法一致性
# ═══════════════════════════════════════════════════════════════════════════════

class TestRuleEngineConsistency:
    """RuleEngine.get_legal_moves(fen) 与 XiangqiRulesEngine 一致"""

    def test_initial_position_move_count(self):
        """初始局面应有合理数量的合法走法"""
        fen = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"
        result = RuleEngine.get_legal_moves(fen)
        # 初始局面红方约 44 合法走法
        assert result.count > 30, f"初始局面合法走法数={result.count}，太少"
        assert result.count < 60, f"初始局面合法走法数={result.count}，太多"
        assert result.side_to_move == "red"

    def test_checkmate_position(self):
        """被将死局面不应有合法走法"""
        # 黑将被红双车将死
        fen = "3kR4/4R4/9/9/9/9/9/9/9/4K4 b - - 0 1"
        result = RuleEngine.get_legal_moves(fen)
        assert result.count == 0, f"将死局面不应有合法走法，实际={result.count}"
        assert result.is_check is True
        assert result.is_checkmate is True

    def test_stalemate_position(self):
        """困毙局面：不被将但无合法走法"""
        # 黑将在角落被红方封死，但未被将军
        fen = "k8/2R6/1R7/9/9/9/9/9/9/4K4 b - - 0 1"
        result = RuleEngine.get_legal_moves(fen)
        assert result.count == 0
        assert result.is_check is False
        assert result.is_stalemate is True

    def test_all_moves_are_legal(self):
        """RuleEngine 返回的每个走法都应通过 is_legal_move 验证"""
        fen = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"
        result = RuleEngine.get_legal_moves(fen)
        for move in result.moves:
            assert RuleEngine.is_legal_move(fen, move.uci), \
                f"is_legal_move 不承认 get_legal_moves 返回的走法: {move.uci}"


# ═══════════════════════════════════════════════════════════════════════════════
# 4. 攻击范围 vs 合法走法分离
# ═══════════════════════════════════════════════════════════════════════════════

class TestAttackVsLegal:
    """攻击范围不应受自将过滤影响"""

    def test_pinned_piece_still_attacks(self):
        """被牵制的车不能移动，但仍然威胁横向格子"""
        board = make_board()
        place(board, 9, 4, 'K')  # 红帅 e0
        place(board, 0, 4, 'k')  # 黑将 e9
        place(board, 5, 4, 'R')  # 红车 e4 — 被牵制
        place(board, 1, 4, 'r')  # 黑车 e8

        # 合法走法：只能沿 e 列
        legal = Rules.get_legal_moves(board, 5, 4)
        legal_cols = {c for r, c in legal}
        assert legal_cols == {4}

        # 原始攻击范围：包括横向
        raw = Rules._get_raw_moves(board, 5, 4)
        raw_cols = {c for r, c in raw}
        assert len(raw_cols) > 1, "原始攻击范围应包括横向格子"

    def test_raw_moves_includes_self_check(self):
        """_get_raw_moves 不过滤自将"""
        board = make_board()
        place(board, 9, 4, 'K')
        place(board, 0, 4, 'k')
        place(board, 7, 4, 'N')  # 红马 e2 被牵制
        place(board, 1, 4, 'r')  # 黑车 e8

        legal = Rules.get_legal_moves(board, 7, 4)
        raw = Rules._get_raw_moves(board, 7, 4)
        assert len(legal) == 0, "被牵制的马无合法走法"
        assert len(raw) > 0, "原始走法应包含马的日字走法"
