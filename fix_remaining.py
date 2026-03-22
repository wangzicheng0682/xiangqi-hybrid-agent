"""修复剩余的将死局面"""
import sys
sys.path.insert(0, 'd:/xiangqi-hybrid-agent')

from core.rules.tactical_detector import TacticalDetector

detector = TacticalDetector()

# 问题分析：
# GP050和GP053：黑将移动到(0, 4)后吃掉红炮，不被将军
# GP055：黑将移动到(0, 4)后不被将军

# 解决方案：
# 用红车在(0, 5)位置，这样黑将吃掉红炮(0, 4)后，红车(0, 5)可以攻击(0, 4)

# GP050: 马后炮
# 黑将在(0, 3)，红炮在(0, 4)直接将军，红车在(0, 5)保护红炮
# 红马在(3, 2)控制(1, 3)
# 黑将移动到(0, 4)后吃掉红炮，被红车(0, 5)攻击
# 黑将移动到(1, 3)后被红马攻击
fen_050 = "3kCR3/9/9/2N5/9/9/9/9/9/4K4 b - - 0 1"

# GP053: 重炮杀
# 黑将在(0, 3)，红炮在(0, 4)将军，红炮在(0, 5)作为炮架
# 等等，这样红炮(0, 4)不能攻击黑将(0, 3)，因为中间没有炮架
# 正确的重炮杀：红炮在(0, 5)将军，红炮(0, 4)作为炮架
# 但这样炮架在炮和目标之间，炮在(0, 5)，炮架在(0, 4)，目标在(0, 3)
# 黑将移动到(0, 4)后吃掉红炮(0, 4)，需要保护
# 解决：用红车在(0, 6)保护红炮(0, 4)
# 但这样红车(0, 6)不能保护红炮(0, 4)，因为中间有红炮(0, 5)
# 
# 重新设计：用红车在(1, 4)保护红炮(0, 4)
# 黑将在(0, 3)，红炮在(0, 5)将军，红炮(0, 4)作为炮架
# 红车在(1, 4)保护红炮(0, 4)
# 红马在(3, 2)控制(1, 3)
# 黑将移动到(0, 4)后吃掉红炮(0, 4)，被红车(1, 4)攻击
# 黑将移动到(1, 3)后被红马攻击
fen_053 = "3kC1C2/4R4/9/2N5/9/9/9/9/9/4K4 b - - 0 1"

# GP055: 侧面虎
# 黑将在(0, 3)，红车在(1, 3)将军，红车在(2, 3)保护
# 黑将移动到(0, 4)后需要被攻击
# 黑将移动到(1, 3)后被红车(2, 3)攻击
# 解决：用红车在(0, 5)攻击(0, 4)
fen_055 = "3kR1R2/3R5/3R5/9/9/9/9/9/9/4K4 b - - 0 1"

test_cases = [
    ("GP050", "马后炮", fen_050),
    ("GP053", "重炮杀", fen_053),
    ("GP055", "侧面虎", fen_055),
]

all_passed = True
for case_id, name, fen in test_cases:
    print("="*60)
    print(f"{case_id}: {name}")
    print(f"FEN: {fen}")
    print("="*60)
    
    board = detector._fen_to_board(fen)
    
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
    result = detector.detect_static(fen)
    detected_tags = [t.tag.name for t in result.get_detected_tags()]
    print(f"检测到的标签: {detected_tags}")
    
    # 预期
    expected = ["is_check", "is_checkmate"]
    missing = [t for t in expected if t not in detected_tags]
    if missing:
        print(f"❌ 缺少标签: {missing}")
        all_passed = False
    else:
        print(f"✅ 标签检测正确")
    
    print()

if all_passed:
    print("\n" + "="*60)
    print("所有将死局面设计正确！")
    print("="*60)
