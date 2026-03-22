"""
控制面板组件 - 天天象棋级别

职责: 用户交互、模式切换、按钮操作

文档依据: JOINT_REFACTOR_ARCHITECTURE.md ControlsUI

Phase 2将完整实现以下功能:
- 模式切换（下棋谱/人机对战/复盘）
- 难度选择（1-10级）
- 走棋控制（上一步/下一步/跳转）
- 播放控制（暂停/继续/速度）
- 帮助按钮（规则说明/快捷键）

当前: 框架版本，提供基础Gradio组件
"""

from typing import Callable, Optional


class ControlsUI:
    """
    控制面板框架

    Phase 2将完整实现商业级交互组件
    当前版本提供基础Gradio组件
    """

    def __init__(self):
        self.on_new_game: Optional[Callable] = None
        self.on_next_move: Optional[Callable] = None
        self.on_prev_move: Optional[Callable] = None
        self.on_difficulty_change: Optional[Callable] = None

    def render(self) -> dict:
        """
        渲染控制面板

        Returns:
            Gradio组件字典
        """
        # Phase 2: 返回完整的Gradio组件
        # 当前返回空字典，由routes模块负责创建
        return {}

    def handle_new_game(self):
        """处理新对局按钮"""
        if self.on_new_game:
            return self.on_new_game()
        return "新对局功能开发中"

    def handle_next_move(self):
        """处理下一步按钮"""
        if self.on_next_move:
            return self.on_next_move()
        return "下一步功能开发中"

    def handle_prev_move(self):
        """处理上一步按钮"""
        if self.on_prev_move:
            return self.on_prev_move()
        return "上一步功能开发中"
