"""检查马的攻击范围"""
import sys
sys.path.insert(0, 'd:/xiangqi-hybrid-agent')

from core.rules.tactical_detector import TacticalDetector

detector = TacticalDetector()

# 马要攻击(1, 3)，需要马在哪些位置？
# 马走日字：先走一步直线，再走一步斜线
# 马在(r, c)的攻击范围：
# (r-2, c-1), (r-2, c+1), (r-1, c-2), (r-1, c+2)
# (r+1, c-2), (r+1, c+2), (r+2, c-1), (r+2, c+1)

# 要攻击(1, 3)，马需要在：
# (1+2, 3-1) = (3, 2)
# (1+2, 3+1) = (3, 4)
# (1+1, 3-2) = (2, 1)
# (1+1, 3+2) = (2, 5)
# (1-1, 3-2) = (0, 1)
# (1-1, 3+2) = (0, 5)
# (1-2, 3-1) = (-1, 2) - 越界
# (1-2, 3+1) = (-1, 4) - 越界

# 所以马需要在(3, 2), (3, 4), (2, 1), (2, 5), (0, 1), (0, 5)

# 验证：马在(3, 2)的攻击范围
board = [['' for _ in range(9)] for _ in range(10)]
board[3][2] = 'N'
attacks = detector._get_attacks(board, 3, 2)
print(f"马在(3, 2)的攻击范围: {attacks}")
print(f"是否包含(1, 3): {(1, 3) in attacks}")

# 验证：马在(2, 2)的攻击范围
board = [['' for _ in range(9)] for _ in range(10)]
board[2][2] = 'N'
attacks = detector._get_attacks(board, 2, 2)
print(f"马在(2, 2)的攻击范围: {attacks}")
print(f"是否包含(1, 3): {(1, 3) in attacks}")

# 验证：马在(2, 4)的攻击范围
board = [['' for _ in range(9)] for _ in range(10)]
board[2][4] = 'N'
attacks = detector._get_attacks(board, 2, 4)
print(f"马在(2, 4)的攻击范围: {attacks}")
print(f"是否包含(1, 3): {(1, 3) in attacks}")
