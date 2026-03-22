"""设计正确的GP001局面"""
import sys
sys.path.insert(0, 'd:/xiangqi-hybrid-agent')

from core.rules.tactical_detector import TacticalDetector

detector = TacticalDetector()

# GP001的FEN：红帅被将军，但有合法走法
# 红帅在(8, 4)（九宫格内），黑车在(8, 3)将军（横向攻击）
# 红帅可以移动到(8, 5), (9, 4)或(7, 4)躲避将军
# 黑将在(0, 3)（不同列，避免将帅对面）
fen = "3k5/9/9/9/9/9/9/9/3rK3/9 w - - 0 1"
print("="*60)
print("测试GP001: 黑车将军红帅")
print(f"FEN: {fen}")
print("="*60)

board = detector._fen_to_board(fen)
print("棋盘:")
for i, row in enumerate(board):
    pieces = [p if p else '.' for p in row]
    print(f"Row {i}: {' '.join(pieces)}")

# 检查红帅位置
king_pos = detector._find_king(board, True)
print(f"\n红帅位置: {king_pos}")

# 检查黑将位置
black_king_pos = detector._find_king(board, False)
print(f"黑将位置: {black_king_pos}")

# 检查红方是否被将军
is_in_check = detector._is_in_check(board, True)
print(f"红方被将军: {is_in_check}")

# 检查红方是否有合法走法
has_legal = detector._has_legal_moves(board, True)
print(f"红方有合法走法: {has_legal}")

# 检查红帅的合法走法
if king_pos:
    moves = detector.rules_engine.get_legal_moves(board, king_pos[0], king_pos[1])
    print(f"红帅合法走法: {moves}")
    
    # 检查每个走法后是否被将军
    for move in moves:
        new_board = [row[:] for row in board]
        new_board[move[0]][move[1]] = new_board[king_pos[0]][king_pos[1]]
        new_board[king_pos[0]][king_pos[1]] = ''
        is_check_after = detector._is_in_check(new_board, True)
        print(f"  移动到 {move} 后是否被将军: {is_check_after}")

# 完整检测
result = detector.detect_static(fen)
print("\n检测到的标签:")
for t in result.get_detected_tags():
    print(f"  - {t.tag.name}: {t.bind_pieces}")
