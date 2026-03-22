"""修复GP050"""
import sys
sys.path.insert(0, 'd:/xiangqi-hybrid-agent')

from core.rules.tactical_detector import TacticalDetector

detector = TacticalDetector()

# GP050: 马后炮
# 炮需要炮架才能攻击
# 黑将在(0, 3)，红炮在(0, 5)将军，红炮(0, 4)作为炮架
# 磋炮架问题：黑将可以吃掉红炮(0, 4)
# 解决：用红车在(1, 4)保护红炮(0, 4)
# 红马在(3, 2)控制(1, 3)
# 黑将移动到(0, 4)后吃掉红炮(0, 4)，被红车(1, 4)攻击
# 黑将移动到(1, 3)后被红马攻击
fen_050 = "3kC1C2/4R4/9/2N5/9/9/9/9/9/4K4 b - - 0 1"

print("="*60)
print("GP050: 马后炮")
print(f"FEN: {fen_050}")
print("="*60)

board = detector._fen_to_board(fen_050)

# 检查黑将位置
black_king = detector._find_king(board, False)
print(f"黑将位置: {black_king}")

# 检查黑方是否被将军
is_check = detector._is_in_check(board, False)
print(f"黑方被将军: {is_check}")

# 检查黑方是否有合法走法
has_legal = detector._has_legal_moves(board, False)
print(f"黑方有合法走法: {has_legal}")

# 检查黑将的合法走法
if black_king:
    moves = detector.rules_engine.get_legal_moves(board, black_king[0], black_king[1])
    print(f"黑将合法走法: {moves}")
    
    # 检查每个走法后是否被将军
    for move in moves:
        new_board = [row[:] for row in board]
        new_board[move[0]][move[1]] = new_board[black_king[0]][black_king[1]]
        new_board[black_king[0]][black_king[1]] = ''
        is_check_after = detector._is_in_check(new_board, False)
        print(f"  移动到 {move} 后是否被将军: {is_check_after}")

# 检测结果
result = detector.detect_static(fen_050)
detected_tags = [t.tag.name for t in result.get_detected_tags()]
print(f"检测到的标签: {detected_tags}")

# 预期
expected = ["is_check", "is_checkmate"]
missing = [t for t in expected if t not in detected_tags]
if missing:
    print(f"❌ 缺少标签: {missing}")
else:
    print(f"✅ 标签检测正确")

