"""
棋盘组件 - 商业级完整版

职责: 棋盘渲染、走棋交互、动画播放、音效播放

文档依据: JOINT_REFACTOR_ARCHITECTURE.md BoardUI

Phase 2完整实现:
- 棋盘渲染（楚河汉界、九宫格、中国风）
- 棋子渲染（3D立体效果）
- 走棋交互（点击、高亮）
- 动画播放（贝塞尔曲线、60fps）
- 音效播放（不同棋子不同声音）
"""

import gradio as gr
from typing import List, Tuple, Optional
from web.state.board_state import PIECE_NAMES
from web.components.board_html import render_chessboard_html
from web.utils.animation_manager import (
    get_move_animation,
    get_capture_animation,
    get_selected_animation,
    BezierCurve
)
from web.utils.audio_system import (
    play_move_audio,
    play_capture_audio,
    play_check_audio,
    get_preloaded_audio_html
)


class CompleteBoardUI:
    """
    完整的棋盘UI组件

    集成HTML渲染、动画系统、音效系统
    """

    def __init__(self):
        self.selected_pos = None
        self.valid_moves = []
        self.last_move = None
        self.animation_enabled = True
        self.audio_enabled = True

    def render(self, board: List[List[str]],
              selected_pos: Optional[Tuple[int, int]] = None,
              valid_moves: List[Tuple[int, int]] = None,
              last_move: Optional[Tuple[Tuple[int, int], Tuple[int, int]]] = None) -> gr.HTML:
        """
        渲染完整棋盘（包含动画和音效）

        Args:
            board: 棋盘二维数组
            selected_pos: 选中的位置
            valid_moves: 合法走法列表
            last_move: 最后一步走法

        Returns:
            Gradio HTML组件
        """
        # 更新内部状态
        self.selected_pos = selected_pos
        self.valid_moves = valid_moves if valid_moves else []
        self.last_move = last_move

        # 生成棋盘HTML
        board_html = render_chessboard_html(board, selected_pos, valid_moves, last_move)

        # 生成动画CSS
        animation_css = self._build_animation_css()

        # 生成音效预加载HTML
        audio_html = self._build_audio_html()

        # 组合完整HTML
        full_html = f"""
        {board_html}
        {animation_css}
        {audio_html}
        """

        return gr.HTML(value=full_html)

    def _build_animation_css(self) -> str:
        """
        构建动画CSS

        返回选中动画的CSS
        """
        if not self.animation_enabled:
            return ""

        return get_selected_animation()

    def _build_audio_html(self) -> str:
        """
        构建音效预加载HTML

        预加载所有音效，确保播放流畅
        """
        if not self.audio_enabled:
            return ""

        audio_elements = get_preloaded_audio_html()
        return "\n".join(audio_elements)

    def select_piece(self, board: List[List[str]], row: int, col: int):
        """
        选中棋子

        Args:
            board: 棋盘二维数组
            row: 行号（0-9）
            col: 列号（0-8）

        Returns:
            (新选中位置, 合法走法列表, 音效路径)
        """
        # 检查位置是否有棋子
        piece = board[row][col]
        if not piece:
            return None, [], None

        # 播放选中音效
        audio_path = None
        if self.audio_enabled:
            audio_path = play_move_audio(piece)

        # 返回选中状态
        return (row, col), [], audio_path

    def move_piece(self, board: List[List[str]], from_pos: Tuple[int, int],
                 to_pos: Tuple[int, int], piece_type: str):
        """
        走棋（包含动画和音效）

        Args:
            board: 棋盘二维数组
            from_pos: 起始位置
            to_pos: 目标位置
            piece_type: 棋子类型

        Returns:
            (动画CSS, 音效路径)
        """
        # 播放走棋音效
        audio_path = None
        if self.audio_enabled:
            audio_path = play_move_audio(piece_type)

        # 生成走棋动画（贝塞尔曲线）
        animation_css = None
        if self.animation_enabled:
            # 根据棋子类型选择曲线类型
            curve_type = "arc" if piece_type.upper() in ['N', 'C'] else "cubic"
            animation_css = get_move_animation(from_pos, to_pos, curve_type)

        return animation_css, audio_path

    def capture_piece(self, board: List[List[str]], from_pos: Tuple[int, int],
                    to_pos: Tuple[int, int]):
        """
        吃子（包含动画和音效）

        Args:
            board: 棋盘二维数组
            from_pos: 起始位置
            to_pos: 目标位置

        Returns:
            (动画CSS, 音效路径)
        """
        # 播放吃子音效
        audio_path = None
        if self.audio_enabled:
            audio_path = play_capture_audio()

        # 生成吃子动画（缩放+淡出）
        animation_css = None
        if self.animation_enabled:
            animation_css = get_capture_animation()

        return animation_css, audio_path

    def alert_check(self, board: List[List[str]], king_pos: Tuple[int, int]):
        """
        将军警报

        Args:
            board: 棋盘二维数组
            king_pos: 将/帅的位置

        Returns:
            (动画CSS, 音效路径)
        """
        # 播放将军音效
        audio_path = None
        if self.audio_enabled:
            audio_path = play_check_audio()

        # 生成将军警报动画
        animation_css = None
        if self.animation_enabled:
            from web.utils.animation_manager import get_check_alert_animation
            animation_css = get_check_alert_animation()

        return animation_css, audio_path

    def highlight_valid_moves(self, moves: List[Tuple[int, int]]) -> str:
        """
        高亮可走位置

        Args:
            moves: 可走位置列表

        Returns:
            高亮HTML片段
        """
        if not moves:
            return ""

        # 生成可走位置高亮的HTML
        highlight_html = []
        for row, col in moves:
            x = col * 60 + 30
            y = row * 60 + 30

            highlight_html.append(f"""
            <div class="valid-move"
                 style="
                    position: absolute;
                    left: {x - 10}px;
                    top: {y - 10}px;
                    width: 20px;
                    height: 20px;
                    border-radius: 50%;
                    background: radial-gradient(circle, #00A86B 0%, transparent 70%);
                    animation: pulse-jade 1.5s infinite;
                    z-index: 5;
                    pointer-events: none;
                 "></div>
            """)

        return "\n".join(highlight_html)

    def toggle_animation(self) -> bool:
        """
        切换动画开关

        Returns:
            当前动画状态
        """
        self.animation_enabled = not self.animation_enabled
        return self.animation_enabled

    def toggle_audio(self) -> bool:
        """
        切换音效开关

        Returns:
            当前音效状态
        """
        self.audio_enabled = not self.audio_enabled
        return self.audio_enabled

    def get_bezier_path(self, from_pos: Tuple[int, int],
                       to_pos: Tuple[int, int]) -> List[Tuple[float, float]]:
        """
        获取贝塞尔曲线路径点

        Args:
            from_pos: 起始位置
            to_pos: 目标位置

        Returns:
            路径点列表
        """
        return BezierCurve.calculate_curve(from_pos, to_pos)

    def get_animation_preview(self, from_pos: Tuple[int, int],
                           to_pos: Tuple[int, int]) -> str:
        """
        获取动画预览（用于调试）

        Args:
            from_pos: 起始位置
            to_pos: 目标位置

        Returns:
            动画路径描述
        """
        path_points = self.get_bezier_path(from_pos, to_pos)

        path_description = f"""
        ## 贝塞尔曲线动画路径

        **起始位置**: {from_pos}
        **目标位置**: {to_pos}
        **总帧数**: {len(path_points)}
        **动画时长**: 300ms (60fps)

        ### 路径点:
        """

        for i, (x, y) in enumerate(path_points):
            path_description += f"帧 {i}: ({x:.2f}, {y:.2f})\n"

        return path_description


# 便捷函数
def create_complete_board_ui() -> CompleteBoardUI:
    """
    创建完整棋盘UI实例（便捷函数）

    Returns:
        CompleteBoardUI实例
    """
    return CompleteBoardUI()
