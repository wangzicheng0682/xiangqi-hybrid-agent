"""调试将军检测问题"""
import sys
sys.path.insert(0, 'd:/xiangqi-hybrid-agent')

from core.rules.tactical_detector import TacticalDetector

# 测试GP001的FEN
fen = '4k4/9/9/9/9/9/9/9/4R4/4K4 w - - 0 1'
detector = TacticalDetector()
board = detector._fen_to_board(fen)

print('棋盘布局:')
for i, row in enumerate(board):
    pieces = [p if p else '.' for p in row]
    print(f'Row {9-i}: {" ".join(pieces)}')

print()
print('黑将位置:', detector._find_king(board, False))
print('红帅位置:', detector._find_king(board, True))
print('红方走棋:', detector._is_red_turn(fen))

# 检查红车位置
for r in range(10):
    for c in range(9):
        if board[r][c] == 'R':
            print(f'\n红车位置: row={r}, col={c}')
            attacks = detector._get_attacks(board, r, c)
            print(f'红车攻击范围: {attacks}')
            
            # 检查黑将是否在攻击范围内
            king_pos = detector._find_king(board, False)
            if king_pos:
                print(f'黑将位置: {king_pos}')
                print(f'黑将在红车攻击范围内: {king_pos in attacks}')

# 测试将军检测
print('\n--- 将军检测 ---')
is_red_turn = detector._is_red_turn(fen)
is_in_check = detector._is_in_check(board, is_red_turn)
print(f'is_red_turn: {is_red_turn}')
print(f'is_in_check(红方被将军): {is_in_check}')

# 问题：将军检测应该检测当前走棋方是否被将军
# 但GP001是红方走棋，红车将军黑将，应该检测黑方是否被将军
# 而不是检测红方是否被将军！

print('\n--- 正确的将军检测逻辑 ---')
# 应该检测对方是否被将军
is_opponent_in_check = detector._is_in_check(board, not is_red_turn)
print(f'黑方被将军: {is_opponent_in_check}')
