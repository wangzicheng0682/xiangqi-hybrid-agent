"""
PGN模式路由

职责: PGN模式的Gradio路由和事件处理

文档依据: JOINT_REFACTOR_ARCHITECTURE.md 路由层
"""

import gradio as gr
from typing import Tuple, List
from web.modes.pgn_mode import PGNMode
from web.components.board import BoardUI, render_board_image


class PGNRoute:
    """
    PGN模式路由

    处理PGN模式的所有Gradio交互
    """

    def __init__(self, agent, pgn_mode: PGNMode):
        self.agent = agent
        self.pgn_mode = pgn_mode
        self.board_ui = BoardUI()

    def handle_file_upload(self, file_obj) -> Tuple[str, str, str]:
        """
        处理PGN文件上传

        Args:
            file_obj: 上传的文件对象

        Returns:
            (对局列表, 棋盘图片, 状态消息)
        """
        if not file_obj:
            return "请选择PGN文件", render_board_image([]), "等待加载"

        file_path = file_obj.name
        games, error = self.pgn_mode.load_pgn(file_path)

        if error:
            return "", render_board_image([]), f"错误: {error}"

        # 显示对局列表
        game_list = self._format_game_list(games)
        board_img = render_board_image([])

        return game_list, board_img, f"已加载 {len(games)} 局对局"

    def handle_next_move(self) -> Tuple[int, str, str]:
        """
        处理下一步按钮

        Returns:
            (当前走法索引, 棋盘图片, 状态消息)
        """
        move_index, error = self.pgn_mode.next_move()

        if error:
            return move_index, render_board_image([]), error

        # 获取当前局面
        fen = self.pgn_mode.get_current_position()
        # TODO: 从FEN渲染棋盘

        return move_index, render_board_image([]), f"当前: 第{move_index+1}着"

    def handle_prev_move(self) -> Tuple[int, str, str]:
        """
        处理上一步按钮

        Returns:
            (当前走法索引, 棋盘图片, 状态消息)
        """
        move_index, error = self.pgn_mode.prev_move()

        if error:
            return move_index, render_board_image([]), error

        # 获取当前局面
        fen = self.pgn_mode.get_current_position()
        # TODO: 从FEN渲染棋盘

        return move_index, render_board_image([]), f"当前: 第{move_index+1}着"

    def handle_jump_to_move(self, move_number: int) -> Tuple[int, str, str]:
        """
        处理跳转到指定走法

        Args:
            move_number: 走法序号

        Returns:
            (当前走法索引, 棋盘图片, 状态消息)
        """
        move_index, error = self.pgn_mode.go_to_move(move_number - 1)

        if error:
            return move_index, render_board_image([]), error

        # 获取当前局面
        fen = self.pgn_mode.get_current_position()
        # TODO: 从FEN渲染棋盘

        return move_index, render_board_image([]), f"跳转到第{move_number}着"

    def _format_game_list(self, games: List[dict]) -> str:
        """
        格式化对局列表

        Args:
            games: 对局列表

        Returns:
            格式化的对局列表字符串
        """
        if not games:
            return "暂无对局"

        lines = ["## 对局列表\n"]
        for i, game in enumerate(games, 1):
            metadata = game.get("metadata", {})
            lines.append(f"**对局 {i}**: {metadata.get('event', '未知')}")

        return "\n".join(lines)
