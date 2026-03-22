"""验证并修复GP050-GP056的FEN"""
import sys
sys.path.insert(0, 'd:/xiangqi-hybrid-agent')

from core.rules.tactical_detector import TacticalDetector

detector = TacticalDetector()

# 九宫格规则：
# 红方九宫格：行 7-9，列 3-5
# 黑方九宫格：行 0-2，列 3-5

test_cases = [
    ("GP050", "马后炮", "3k5/4P4/9/4n4/9/9/9/9/9/3K5 b - - 0 1"),
    ("GP051", "卧槽马", "3k5/9/9/9/9/9/9/3N5/9/4K4 b - - 0 1"),
    ("GP052", "白脸将", "4k4/9/9/9/9/9/9/9/9/3RK4 b - - 0 1"),
    ("GP053", "重炮杀", "3k5/9/9/9/9/9/9/9/4CC3/4K4 b - - 0 1"),
    ("GP054", "海底捞月", "3kR4/9/9/9/9/9/9/9/9/4K4 b - - 0 1"),
    ("GP055", "侧面虎", "3k5/3R5/9/9/9/9/9/9/9/4K4 b - - 0 1"),
    ("GP056", "双车错", "3k5/3R4R/9/9/9/9/9/9/9/4K4 b - - 0 1"),
    ("GP100", "红黑视角", "4K4/9/9/9/9/9/9/9/4r4/4k4 b - - 0 1"),
]

for case_id, name, fen in test_cases:
    print("="*60)
    print(f"{case_id}: {name}")
    print(f"FEN: {fen}")
    print("="*60)
    
    board = detector._fen_to_board(fen)
    
    # 检查黑将位置
    black_king = detector._find_king(board, False)
    print(f"黑将位置: {black_king}")
    if black_king:
        in_palace = (0 <= black_king[0] <= 2) and (3 <= black_king[1] <= 5)
        print(f"黑将在九宫格内: {in_palace}")
    
    # 检查红帅位置
    red_king = detector._find_king(board, True)
    print(f"红帅位置: {red_king}")
    if red_king:
        in_palace = (7 <= red_king[0] <= 9) and (3 <= red_king[1] <= 5)
        print(f"红帅在九宫格内: {in_palace}")
    
    # 检查黑方是否被将军
    is_check = detector._is_in_check(board, False)
    print(f"黑方被将军: {is_check}")
    
    # 检查黑方是否有合法走法
    has_legal = detector._has_legal_moves(board, False)
    print(f"黑方有合法走法: {has_legal}")
    
    # 检测结果
    result = detector.detect_static(fen)
    detected_tags = [t.tag.name for t in result.get_detected_tags()]
    print(f"检测到的标签: {detected_tags}")
    
    # 预期
    expected = ["is_check", "is_checkmate"]
    missing = [t for t in expected if t not in detected_tags]
    if missing:
        print(f"❌ 缺少标签: {missing}")
    else:
        print(f"✅ 标签检测正确")
    
    print()
