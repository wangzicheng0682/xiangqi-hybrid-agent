"""
棋盘组件 - 天天象棋级别

职责: 棋盘渲染、走棋交互、动画展示

文档依据: JOINT_REFACTOR_ARCHITECTURE.md BoardUI

Phase 2将完整实现以下功能:
- 棋盘渲染（楚河汉界、九宫格）
- 棋子渲染（3D立体效果）
- 走棋交互（点击、拖拽）
- 动画效果（贝塞尔曲线移动）
- 视觉反馈（高亮、脉冲）

当前: 框架版本，使用PIL渲染棋盘图片
"""

from PIL import Image, ImageDraw, ImageFont
from typing import List, Tuple, Optional
from web.state.board_state import PIECE_NAMES, INITIAL_BOARD


CELL_SIZE = 60
BOARD_WIDTH = CELL_SIZE * 9
BOARD_HEIGHT = CELL_SIZE * 10


class BoardUI:
    """
    棋盘组件框架

    Phase 2将完整实现商业级HTML/CSS渲染
    当前版本使用PIL渲染图片
    """

    def __init__(self):
        self.selected_piece = None
        self.valid_moves = []

    def render(self, board: List[List[str]],
              selected_pos: Optional[Tuple[int, int]] = None,
              valid_moves: List[Tuple[int, int]] = None) -> str:
        """
        渲染棋盘

        Args:
            board: 棋盘二维数组
            selected_pos: 选中的位置
            valid_moves: 合法走法列表

        Returns:
            棋盘图片路径
        """
        return render_board_image(board, selected_pos, valid_moves)

    def highlight_valid_moves(self, moves: List[Tuple[int, int]]) -> None:
        """
        高亮可走位置

        Args:
            moves: 可走位置列表
        """
        self.valid_moves = moves

    def animate_move(self, from_pos: Tuple[int, int],
                   to_pos: Tuple[int, int],
                   piece_type: str) -> None:
        """
        走棋动画（贝塞尔曲线）

        Args:
            from_pos: 起始位置
            to_pos: 目标位置
            piece_type: 棋子类型
        """
        # Phase 2: 实现贝塞尔曲线动画
        pass


def render_board_image(board: List[List[str]],
                    selected_pos: Optional[Tuple[int, int]] = None,
                    valid_moves: List[Tuple[int, int]] = None) -> str:
    """
    渲染棋盘图片（PIL版本）

    Args:
        board: 棋盘二维数组
        selected_pos: 选中的位置
        valid_moves: 合法走法列表

    Returns:
        图片路径
    """
    import tempfile

    # 创建空白图片
    img = Image.new('RGB', (BOARD_WIDTH, BOARD_HEIGHT), '#F5F5DC')
    draw = ImageDraw.Draw(img)

    # 绘制网格线
    for i in range(10):
        y = i * CELL_SIZE
        draw.line([(0, y), (BOARD_WIDTH, y)], fill='#B8860B', width=2)

    for i in range(9):
        x = i * CELL_SIZE
        draw.line([(x, 0), (x, BOARD_HEIGHT)], fill='#B8860B', width=2)

    # 绘制楚河汉界
    river_y = 4.5 * CELL_SIZE
    draw.line([(0, river_y), (BOARD_WIDTH, river_y)], fill='#D4AF37', width=3)
    # 添加楚河汉界文字（简化处理，不绘制文字）

    # 绘制棋子
    for row in range(10):
        for col in range(9):
            piece = board[row][col]
            if piece:
                x = col * CELL_SIZE + CELL_SIZE // 2
                y = row * CELL_SIZE + CELL_SIZE // 2

                # 棋子背景
                piece_color = '#E63946' if piece.isupper() else '#2C3E50'
                draw.ellipse(
                    [(x - 25, y - 25), (x + 25, y + 25)],
                    fill='#FFFFFF',
                    outline=piece_color,
                    width=3
                )

                # 棋子文字
                try:
                    # 尝试使用中文字体，如果失败则使用默认字体
                    font = ImageFont.truetype("simhei.ttf", 30)
                except:
                    font = ImageFont.load_default()

                piece_name = PIECE_NAMES.get(piece, piece)
                text_bbox = draw.textbbox((0, 0), piece_name, font=font)
                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]
                draw.text(
                    (x - text_width // 2, y - text_height // 2),
                    piece_name,
                    fill=piece_color,
                    font=font
                )

    # 高亮选中的棋子
    if selected_pos:
        row, col = selected_pos
        x = col * CELL_SIZE + CELL_SIZE // 2
        y = row * CELL_SIZE + CELL_SIZE // 2
        draw.ellipse(
            [(x - 30, y - 30), (x + 30, y + 30)],
            outline='#D4AF37',
            width=4
        )

    # 高亮合法走法
    if valid_moves:
        for row, col in valid_moves:
            x = col * CELL_SIZE + CELL_SIZE // 2
            y = row * CELL_SIZE + CELL_SIZE // 2
            draw.ellipse(
                [(x - 10, y - 10), (x + 10, y + 10)],
                fill='#00A86B',
                outline='#00A86B'
            )

    # 保存图片
    temp_path = tempfile.mktemp(suffix='.png')
    img.save(temp_path)
    return temp_path
