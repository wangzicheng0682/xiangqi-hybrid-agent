"""调试GP002问题"""
import sys
sys.path.insert(0, 'd:/xiangqi-hybrid-agent')

from core.rules.tactical_detector import TacticalDetector

# GP002的FEN
fen = '3k5/4R4/9/9/9/9/9/9/9/4K4 w - - 0 1'
detector = TacticalDetector()
board = detector._fen_to_board(fen)

print('棋盘布局:')
for i, row in enumerate(board):
    pieces = [p if p else '.' for p in row]
    print(f'Row {i}: {" ".join(pieces)}')

print()
print('红帅位置:', detector._find_king(board, True))
print('黑将位置:', detector._find_king(board, False))
print('红方走棋:', detector._is_red_turn(fen))

# 检查红车的攻击范围
for r in range(10):
    for c in range(9):
        if board[r][c] == 'R':
            print(f'\n红车位置: ({r}, {c})')
            attacks = detector._get_attacks(board, r, c)
            print(f'红车攻击范围: {attacks}')
            
            # 检查黑将是否在攻击范围内
            king_pos = detector._find_king(board, False)
            if king_pos:
                print(f'黑将位置: {king_pos}')
                print(f'黑将在红车攻击范围内: {king_pos in attacks}')

# 检查将军检测
print('\n--- 将军检测 ---')
is_red_turn = detector._is_red_turn(fen)
print(f'is_red_turn: {is_red_turn}')

# 问题：检测器检测的是当前走棋方是否被将军
# GP002是红方走棋，# 红车将军黑将
# 所以应该检测黑方是否被将军，而不是红方！

is_red_in_check = detector._is_in_check(board, True)
is_black_in_check = detector._is_in_check(board, False)
print(f'红方被将军: {is_red_in_check}')
print(f'黑方被将军: {is_black_in_check}')

# 检查是否有合法走法
has_red_legal = detector._has_legal_moves(board, True)
has_black_legal = detector._has_legal_moves(board, False)
print(f'红方有合法走法: {has_red_legal}')
print(f'黑方有合法走法: {has_black_legal}')

# 完整检测结果
result = detector.detect_static(fen)
print('\n检测到的标签:')
for t in result.get_detected_tags():
    print(f'  - {t.tag.name}: {t.bind_pieces}')
