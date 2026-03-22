"""设计正确的将死局面 - 最终版本"""
import sys
sys.path.insert(0, 'd:/xiangqi-hybrid-agent')

from core.rules.tactical_detector import TacticalDetector

detector = TacticalDetector()

# 设计原则：
# 黑将在(0, 3)
# 黑将的逃跑格：(0, 4), (1, 3)
# (0, 2)是九宫格边界，不能走

# GP051: 卧槽马 - 已经正确
# 黑将在(0, 3)，红车在(1, 4)将军，红马在(2, 2)控制(1, 3)和(0, 4)
fen_051 = "3k5/4R4/2N5/9/9/9/9/9/9/4K4 b - - 0 1"

# GP052: 白脸将 - 利用将帅不能对面规则
# 黑将在(0, 4)，红车在(0, 3)将军，红车在(0, 5)保护
# 黑将移动到(0, 3)后被红车(0, 5)攻击
# 黑将移动到(0, 5)后被红车(0, 3)攻击
# 黑将移动到(1, 4)后需要被攻击
# 解决：用红马控制(1, 4)
# 马要攻击(1, 4)，需要在(3, 3)或(3, 5)或(2, 2)或(2, 6)
fen_052 = "3RkR3/9/2N5/9/9/9/9/9/9/4K4 b - - 0 1"

# GP053: 重炮杀
# 黑将在(0, 3)，红炮在(0, 5)将军（以红炮(0, 4)为炮架）
# 黑将移动到(0, 4)后吃掉红炮(0, 4)，需要保护
# 黑将移动到(1, 3)后需要被攻击
# 解决：用红车保护红炮(0, 4)，用红马在(3, 2)控制(1, 3)
fen_053 = "3kC1C2/3R5/9/2N5/9/9/9/9/9/4K4 b - - 0 1"

# GP054: 海底捞月 - 车深入敌方底线将死
# 黑将在(0, 3)，红车在(0, 4)将军，红车在(0, 5)保护
# 黑将移动到(0, 4)后被红车(0, 5)攻击
# 黑将移动到(1, 3)后需要被攻击
# 解决：用红马在(3, 2)控制(1, 3)
fen_054 = "3kRR3/9/9/2N5/9/9/9/9/9/4K4 b - - 0 1"

# GP055: 侧面虎 - 车与将同行，横向将死
# 黑将在(0, 3)，红车在(1, 3)将军，红车在(2, 3)保护
# 黑将移动到(0, 4)后需要被攻击
# 黑将移动到(1, 3)后被红车(2, 3)攻击
# 解决：用红车封锁(0, 4)，用红马控制(1, 3)
fen_055 = "3kR5/3R5/3R5/2N5/9/9/9/9/9/4K4 b - - 0 1"

# GP056: 双车错 - 双车交替将军将死
# 黑将在(0, 3)，红车在(0, 4)将军，红车在(0, 5)保护
# 黑将移动到(0, 4)后被红车(0, 5)攻击
# 黑将移动到(1, 3)后需要被攻击
# 解决：用红马在(3, 2)控制(1, 3)
fen_056 = "3kRR3/9/9/2N5/9/9/9/9/9/4K4 b - - 0 1"

# GP050: 马后炮 - 马控制逃跑格，炮将军
# 黑将在(0, 3)，红炮在(0, 5)将军（以红炮(0, 4)为炮架）
# 黑将移动到(0, 4)后吃掉红炮(0, 4)，需要保护
# 黑将移动到(1, 3)后需要被攻击
# 解决：用红车保护红炮(0, 4)，用红马在(3, 2)控制(1, 3)
fen_050 = "3kC1C2/3R5/9/2N5/9/9/9/9/9/4K4 b - - 0 1"

test_cases = [
    ("GP050", "马后炮", fen_050),
    ("GP051", "卧槽马", fen_051),
    ("GP052", "白脸将", fen_052),
    ("GP053", "重炮杀", fen_053),
    ("GP054", "海底捞月", fen_054),
    ("GP055", "侧面虎", fen_055),
    ("GP056", "双车错", fen_056),
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
