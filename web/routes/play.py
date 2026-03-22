"""
人机对战模式路由

职责: 人机对战模式的Gradio路由和事件处理

文档依据: JOINT_REFACTOR_ARCHITECTURE.md 路由层
"""

import gradio as gr
from typing import Tuple
from web.modes.play_mode import PlayMode
from web.state.board_state import INITIAL_BOARD
from web.components.board import BoardUI, render_board_image
from web.components.analysis import AnalysisUI


class PlayRoute:
    """
    人机对战模式路由

    处理人机对战模式的所有Gradio交互
    """

    def __init__(self, agent, play_mode: PlayMode):
        self.agent = agent
        self.play_mode = play_mode
        self.board_ui = BoardUI()
        self.analysis_ui = AnalysisUI()

    def handle_new_game(self) -> Tuple[str, str]:
        """
        处理新对局按钮

        Returns:
            (游戏状态, 棋盘图片)
        """
        state = self.play_mode.new_game()
        board_img = render_board_image(state.board)
        return "新对局开始，红方先行", board_img

    def handle_board_click(self, click_data: dict, state) -> Tuple[dict, str, str]:
        """
        处理棋盘点击

        Args:
            click_data: 点击数据
            state: 游戏状态

        Returns:
            (新状态, 状态消息, 棋盘图片)
        """
        if not click_data:
            return state, "无效点击", render_board_image(state.board)

        # Phase 3: 实现完整的点击处理逻辑
        # 当前返回占位符
        return state, "点击处理开发中", render_board_image(state.board)

    def handle_analyze(self, state) -> str:
        """
        处理分析按钮

        Args:
            state: 游戏状态

        Returns:
            分析结果Markdown
        """
        result = self.play_mode.analyze_position()

        if not result:
            return "无法分析当前局面"

        return self.analysis_ui.render(
            engine_result=result.get('engine_result'),
            kg_result=result.get('kg_result'),
            rag_results=result.get('rag_results', [])
        )

    def handle_difficulty_change(self, difficulty: int) -> str:
        """
        处理难度变化

        Args:
            difficulty: 难度等级

        Returns:
            状态消息
        """
        self.play_mode.set_difficulty(difficulty)
        return f"难度已设置为 {difficulty} 级"

    def handle_set_ai_mode(self, mode: str) -> str:
        """
        处理AI模式切换

        Args:
            mode: AI模式（analysis/battle）

        Returns:
            状态消息
        """
        # TODO: 实现AI模式切换逻辑
        if mode == "analysis":
            return "📊 分析模式：引擎提供分析建议，不自动走棋"
        else:
            return "⚔️ 对战模式：引擎作为对手自动回应"
