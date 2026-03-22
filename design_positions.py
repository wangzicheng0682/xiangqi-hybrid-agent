"""设计正确的困毙局面"""
import sys
sys.path.insert(0, 'd:/xiangqi-hybrid-agent')

from core.rules.tactical_detector import TacticalDetector

detector = TacticalDetector()

# 困毙局面：黑将在(0, 3)，红车在(1, 4)，红帅在(9, 4)
# 黑将不被将军（红车不在(0, 3)的同一行或同一列）
# 黑将移动到(0, 4)后，被红帅攻击（将帅不能对面）
# 黑将移动到(1, 3)后，被红车攻击
fen_stalemate = "3k5/4R4/9/9/9/9/9/9/9/4K4 b - - 0 1"

# 将死局面：黑将在(0, 3)，红车在(0, 4)将军，红车在(1, 3)封锁下路
# 黑将可以移动到(0, 2)：九宫格边界
# 黑将可以移动到(1, 3)：被红车攻击
# 黑将可以移动到(0, 4)：吃掉红车，但被另一个红车保护
fen_checkmate = "3kRR2/3R5/9/9/9/9/9/9/9/4K4 b - - 0 1"

for name, fen in [("困毙", fen_stalemate), ("将死", fen_checkmate)]:
    print("="*60)
    print(f"测试: {name}")
    print(f"FEN: {fen}")
    print("="*60)
    
    board = detector._fen_to_board(fen)
    print("棋盘:")
    for i, row in enumerate(board):
        pieces = [p if p else '.' for p in row]
        print(f"Row {i}: {' '.join(pieces)}")
    
    # 检查黑将位置
    king_pos = detector._find_king(board, False)
    print(f"\n黑将位置: {king_pos}")
    
    # 检查红帅位置
    red_king_pos = detector._find_king(board, True)
    print(f"红帅位置: {red_king_pos}")
    
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
        
        # 检查每个走法后是否被将军
        for move in moves:
            new_board = [row[:] for row in board]
            new_board[move[0]][move[1]] = new_board[king_pos[0]][king_pos[1]]
            new_board[king_pos[0]][king_pos[1]] = ''
            is_check_after = detector._is_in_check(new_board, False)
            print(f"  移动到 {move} 后是否被将军: {is_check_after}")
    
    # 完整检测
    result = detector.detect_static(fen)
    print("\n检测到的标签:")
    for t in result.get_detected_tags():
        print(f"  - {t.tag.name}: {t.bind_pieces}")
    
    print()
