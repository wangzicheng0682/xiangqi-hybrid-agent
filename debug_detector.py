"""系统性调试检测器问题"""
import sys
sys.path.insert(0, 'd:/xiangqi-hybrid-agent')

from core.rules.tactical_detector import TacticalDetector

detector = TacticalDetector()

# 测试GP002
fen = "4k4/4R4/9/9/9/9/9/9/9/9/4K4 b - - 0 1"
print("="*60)
print("测试GP002: 红车将死黑将")
print("="*60)

board = detector._fen_to_board(fen)
print("棋盘:")
for i, row in enumerate(board):
    pieces = [p if p else '.' for p in row]
    print(f"Row {i}: {' '.join(pieces)}")

print()

# 检查黑将位置
king_pos = detector._find_king(board, False)
print(f"黑将位置: {king_pos}")

# 检查红车位置
for r in range(10):
    for c in range(9):
        if board[r][c] == 'R':
            print(f"红车位置: ({r}, {c})")
            attacks = detector._get_attacks(board, r, c)
            print(f"红车攻击范围: {attacks}")
            if king_pos in attacks:
                print("✓ 黑将在红车攻击范围内")

# 检查黑方是否被将军
is_in_check = detector._is_in_check(board, False)
print(f"黑方被将军: {is_in_check}")

# 检查黑方是否有合法走法
has_legal = detector._has_legal_moves(board, False)
print(f"黑方有合法走法: {has_legal}")

# 完整检测
result = detector.detect_static(fen)
print("\n检测到的标签:")
for t in result.get_detected_tags():
    print(f"  - {t.tag.name}: {t.bind_pieces}")

print("\n" + "="*60)

# 测试GP003
fen = "4k4/9/9/9/9/9/9/9/9/3K4 b - - 0 1"
print("测试GP003: 困毙")
print("="*60)

board = detector._fen_to_board(fen)
print("棋盘:")
for i, row in enumerate(board):
    pieces = [p if p else '.' for p in row]
    print(f"Row {i}: {' '.join(pieces)}")

print()

# 检查黑将位置
king_pos = detector._find_king(board, False)
print(f"黑将位置: {king_pos}")

# 检查黑方是否被将军
is_in_check = detector._is_in_check(board, False)
print(f"黑方被将军: {is_in_check}")

# 检查黑方是否有合法走法
has_legal = detector._has_legal_moves(board, False)
print(f"黑方有合法走法: {has_legal}")

# 检查黑将的合法走法
if king_pos:
    moves = detector.rules_engine.get_legal_moves(board, king_pos[0], king_pos[1])
    print(f"黑将合法走法: {moves}")

# 完整检测
result = detector.detect_static(fen)
print("\n检测到的标签:")
for t in result.get_detected_tags():
    print(f"  - {t.tag.name}: {t.bind_pieces}")
