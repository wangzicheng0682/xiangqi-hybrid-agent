"""
走法列表组件 - 天天象棋级别

职责: 显示走法历史、支持导航

文档依据: JOINT_REFACTOR_ARCHITECTURE.md 走法列表

Phase 2将完整实现以下功能:
- 走法列表展示（带编号）
- 当前走法高亮
- 点击跳转到指定走法

当前: 框架版本，使用Textbox显示
"""

from typing import List


class MoveListUI:
    """
    走法列表框架

    Phase 2将完整实现商业级HTML/CSS渲染
    当前版本使用Textbox显示
    """

    def __init__(self):
        self.moves = []
        self.current_move = 0

    def render(self, moves: List[str], current_move: int = 0) -> str:
        """
        渲染走法列表

        Args:
            moves: 走法列表
            current_move: 当前走法索引

        Returns:
            格式化的走法列表字符串
        """
        if not moves:
            return "暂无走法"

        formatted_moves = []
        for i, move in enumerate(moves):
            prefix = "▶ " if i == current_move else "  "
            formatted_moves.append(f"{prefix} {i+1}. {move}")

        return "\n".join(formatted_moves)

    def set_moves(self, moves: List[str]) -> None:
        """
        设置走法列表

        Args:
            moves: 走法列表
        """
        self.moves = moves

    def set_current_move(self, index: int) -> None:
        """
        设置当前走法

        Args:
            index: 走法索引
        """
        self.current_move = index
