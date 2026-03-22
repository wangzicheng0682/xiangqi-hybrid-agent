"""
棋盘HTML渲染 - 天天象棋级别

职责: 生成商业级棋盘HTML（楚河汉界、九宫格、3D棋子）

文档依据: JOINT_REFACTOR_ARCHITECTURE.md BoardUI

Phase 2完整实现:
- 棋盘渲染（楚河汉界、九宫格）
- 棋子渲染（3D立体效果）
- 宣纸纹理背景
- 鎏金边框
"""

from typing import List, Tuple, Optional
from web.state.board_state import PIECE_NAMES


# 中国风配色方案
CHINESE_COLORS = {
    'primary_red': '#C41E3A',      # 朱红
    'primary_black': '#1A1A1A',     # 墨黑
    'gold': '#D4AF37',              # 鎏金
    'jade': '#00A86B',               # 翠绿
    'paper': '#F5F5DC',             # 宣纸白
    'red_piece': '#E63946',
    'black_piece': '#2C3E50',
    'border': '#B8860B',
}


class BoardHTMLRenderer:
    """
    棋盘HTML渲染器

    生成商业级棋盘HTML，包含：
    - 宣纸纹理背景
    - 楚河汉界
    - 九宫格（虚线）
    - 3D立体棋子
    - 鎏金边框
    """

    def __init__(self):
        self.board_width = 540  # 9 * 60
        self.board_height = 600  # 10 * 60
        self.cell_width = 60
        self.cell_height = 60

    def render(self, board: List[List[str]],
              selected_pos: Optional[Tuple[int, int]] = None,
              valid_moves: List[Tuple[int, int]] = None,
              last_move: Optional[Tuple[Tuple[int, int], Tuple[int, int]]] = None) -> str:
        """
        渲染完整棋盘HTML

        Args:
            board: 棋盘二维数组
            selected_pos: 选中的位置
            valid_moves: 合法走法列表
            last_move: 最后一步走法 ((from_row, from_col), (to_row, to_col))

        Returns:
            HTML字符串
        """
        html_parts = [
            self._build_container(),
            self._build_background(),
            self._build_grid(),
            self._build_river(),
            self._build_palaces(),
            self._build_pieces(board, selected_pos),
            self._build_valid_moves(valid_moves),
            self._build_last_move_highlight(last_move),
            self._build_close_container(),
            self._build_styles()
        ]

        return "\n".join(html_parts)

    def _build_container(self) -> str:
        """构建棋盘容器"""
        return f"""
        <div class="chess-container" style="
            position: relative;
            width: {self.board_width}px;
            height: {self.board_height}px;
            background: radial-gradient(circle at 30% 20%, {CHINESE_COLORS['paper']} 0%, #E8E4D9 100%);
            border: 4px solid {CHINESE_COLORS['border']};
            border-radius: 8px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.2), inset 0 1px 0 rgba(0,0,0,0.1);
            overflow: hidden;
        ">
        """

    def _build_background(self) -> str:
        """构建宣纸纹理背景"""
        return """
        <div class="board-background" style="
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: radial-gradient(circle at 30% 20%, #F5F5DC 0%, #E8E4D9 100%);
            pointer-events: none;
        "></div>
        """

    def _build_grid(self) -> str:
        """构建网格线"""
        grid_lines = []

        # 横线（10行）
        for i in range(10):
            y = i * self.cell_height
            grid_lines.append(f"""
            <div class="grid-line h-line" style="
                position: absolute;
                top: {y}px;
                left: 0;
                right: 0;
                height: 2px;
                background: {CHINESE_COLORS['border']};
            "></div>
            """)

        # 竖线（9列）
        for i in range(9):
            x = i * self.cell_width
            grid_lines.append(f"""
            <div class="grid-line v-line" style="
                position: absolute;
                left: {x}px;
                top: 0;
                bottom: 0;
                width: 2px;
                background: {CHINESE_COLORS['border']};
            "></div>
            """)

        return "\n".join(grid_lines)

    def _build_river(self) -> str:
        """构建楚河汉界"""
        river_y = 4.5 * self.cell_height
        return f"""
        <div class="river" style="
            position: absolute;
            top: {river_y}px;
            left: 0;
            right: 0;
            height: {self.cell_height}px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-family: '楷体', 'STKaiti', 'KaiTi', serif;
            font-size: 24px;
            font-weight: bold;
            color: #2C3E50;
            background: linear-gradient(90deg, transparent 0%, {CHINESE_COLORS['gold']} 50%, transparent 100%);
            border-top: 2px solid {CHINESE_COLORS['border']};
            border-bottom: 2px solid {CHINESE_COLORS['border']};
            letter-spacing: 4rem;
            pointer-events: none;
        ">
            <span style="margin-right: 2rem;">楚河</span>
            <span style="margin-left: 2rem;">汉界</span>
        </div>
        """

    def _build_palaces(self) -> str:
        """构建九宫格（虚线）"""
        # 顶部九宫（红方）
        top_palace_x = 3 * self.cell_width
        top_palace_y = 0
        top_palace_width = 2 * self.cell_width
        top_palace_height = 3 * self.cell_height

        # 底部九宫（黑方）
        bottom_palace_x = 3 * self.cell_width
        bottom_palace_y = 7 * self.cell_height

        # 顶部九宫格
        top_palace = f"""
        <div class="palace palace-top" style="
            position: absolute;
            left: {top_palace_x}px;
            top: {top_palace_y}px;
            width: {top_palace_width}px;
            height: {top_palace_height}px;
            border: 2px dashed {CHINESE_COLORS['gold']};
            opacity: 0.3;
            pointer-events: none;
        ">
            <div class="palace-diagonal-1" style="
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: linear-gradient(to bottom right, transparent calc(50% - 1px), {CHINESE_COLORS['gold']} 50%, transparent calc(50% + 1px));
            "></div>
            <div class="palace-diagonal-2" style="
                position: absolute;
                top: 0;
                right: 0;
                width: 100%;
                height: 100%;
                background: linear-gradient(to bottom left, transparent calc(50% - 1px), {CHINESE_COLORS['gold']} 50%, transparent calc(50% + 1px));
            "></div>
        </div>
        """

        # 底部九宫格
        bottom_palace = f"""
        <div class="palace palace-bottom" style="
            position: absolute;
            left: {bottom_palace_x}px;
            top: {bottom_palace_y}px;
            width: {top_palace_width}px;
            height: {top_palace_height}px;
            border: 2px dashed {CHINESE_COLORS['gold']};
            opacity: 0.3;
            pointer-events: none;
        ">
            <div class="palace-diagonal-1" style="
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: linear-gradient(to bottom right, transparent calc(50% - 1px), {CHINESE_COLORS['gold']} 50%, transparent calc(50% + 1px));
            "></div>
            <div class="palace-diagonal-2" style="
                position: absolute;
                top: 0;
                right: 0;
                width: 100%;
                height: 100%;
                background: linear-gradient(to bottom left, transparent calc(50% - 1px), {CHINESE_COLORS['gold']} 50%, transparent calc(50% + 1px));
            "></div>
        </div>
        """

        return top_palace + bottom_palace

    def _build_pieces(self, board: List[List[str]],
                    selected_pos: Optional[Tuple[int, int]]) -> str:
        """构建棋子（3D立体效果）"""
        pieces = []

        for row in range(10):
            for col in range(9):
                piece = board[row][col]
                if piece:
                    piece_html = self._build_piece(piece, row, col, selected_pos)
                    pieces.append(piece_html)

        return "\n".join(pieces)

    def _build_piece(self, piece: str, row: int, col: int,
                    selected_pos: Optional[Tuple[int, int]]) -> str:
        """
        构建单个棋子（3D立体效果）

        3D立体效果:
        - 径向渐变（白→米黄→米白）
        - 多层阴影（制造深度）
        - 悬停浮起效果
        - 选中脉冲效果
        """
        is_red = piece.isupper()
        piece_name = PIECE_NAMES.get(piece, piece)
        piece_color = CHINESE_COLORS['red_piece'] if is_red else CHINESE_COLORS['black_piece']

        x = col * self.cell_width + self.cell_width // 2
        y = row * self.cell_height + self.cell_height // 2

        is_selected = selected_pos and selected_pos == (row, col)

        selected_class = " selected" if is_selected else ""

        return f"""
        <div class="chess-piece{selected_class}"
             data-row="{row}"
             data-col="{col}"
             data-piece="{piece}"
             style="
                position: absolute;
                left: {x - 25}px;
                top: {y - 25}px;
                width: 50px;
                height: 50px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-family: '楷体', 'STKaiti', 'KaiTi', serif;
                font-weight: bold;
                font-size: 28px;
                cursor: pointer;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                background: radial-gradient(circle at 30% 30%, #FFFFFF 0%, #F5F5DC 50%, #E8E4D0 100%);
                box-shadow:
                    0 6px 12px rgba(0, 0, 0, 0.3),
                    0 3px 6px rgba(0, 0, 0, 0.2),
                    inset 0 2px 4px rgba(255, 255, 255, 0.3),
                    inset 0 1px 2px rgba(0, 0, 0, 0.1);
                border: 3px solid {piece_color};
                color: {piece_color};
                text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.3);
                z-index: 10;
                {self._build_selected_style(is_selected)}
             ">{piece_name}</div>
        """

    def _build_selected_style(self, is_selected: bool) -> str:
        """构建选中样式"""
        if not is_selected:
            return ""

        return f"""
            transform: scale(1.15);
            box-shadow:
                0 0 20px {CHINESE_COLORS['gold']},
                0 0 40px rgba(212, 175, 55, 0.3),
                inset 0 4px 8px rgba(212, 175, 55, 0.4);
            animation: pulse-gold 1.5s infinite;
        """

    def _build_valid_moves(self, valid_moves: List[Tuple[int, int]]) -> str:
        """
        构建可走位置高亮

        视觉效果:
        - 绿色圆点（翠绿）
        - 脉冲动画
        """
        if not valid_moves:
            return ""

        dots = []
        for row, col in valid_moves:
            x = col * self.cell_width + self.cell_width // 2
            y = row * self.cell_height + self.cell_height // 2

            dots.append(f"""
            <div class="valid-move"
                 style="
                    position: absolute;
                    left: {x - 10}px;
                    top: {y - 10}px;
                    width: 20px;
                    height: 20px;
                    border-radius: 50%;
                    background: radial-gradient(circle, {CHINESE_COLORS['jade']} 0%, transparent 70%);
                    animation: pulse-jade 1.5s infinite;
                    z-index: 5;
                    pointer-events: none;
                 "></div>
            """)

        return "\n".join(dots)

    def _build_last_move_highlight(self, last_move: Optional[Tuple[Tuple[int, int], Tuple[int, int]]]) -> str:
        """
        构建最后走法高亮

        视觉效果:
        - 淡淡绿色高亮
        - 从起始位置到目标位置的箭头
        """
        if not last_move:
            return ""

        (from_row, from_col), (to_row, to_col) = last_move

        from_x = from_col * self.cell_width + self.cell_width // 2
        from_y = from_row * self.cell_height + self.cell_height // 2
        to_x = to_col * self.cell_width + self.cell_width // 2
        to_y = to_row * self.cell_height + self.cell_height // 2

        # 起始位置高亮
        from_highlight = f"""
        <div class="last-move-from" style="
            position: absolute;
            left: {from_x - 30}px;
            top: {from_y - 30}px;
            width: 60px;
            height: 60px;
            border-radius: 50%;
            background: rgba(0, 174, 107, 0.1);
            animation: flash-last-move 0.5s ease-out;
            pointer-events: none;
            z-index: 3;
        "></div>
        """

        # 目标位置高亮
        to_highlight = f"""
        <div class="last-move-to" style="
            position: absolute;
            left: {to_x - 30}px;
            top: {to_y - 30}px;
            width: 60px;
            height: 60px;
            border-radius: 50%;
            background: rgba(0, 174, 107, 0.1);
            animation: flash-last-move 0.5s ease-out;
            pointer-events: none;
            z-index: 3;
        "></div>
        """

        return from_highlight + to_highlight

    def _build_close_container(self) -> str:
        """构建容器闭合标签"""
        return "</div>"

    def _build_styles(self) -> str:
        """构建CSS样式"""
        return """
        <style>
        /* 选中脉冲动画 */
        @keyframes pulse-gold {
            0%, 100% {
                box-shadow:
                    0 0 20px #D4AF37,
                    0 0 40px rgba(212, 175, 55, 0.3),
                    inset 0 4px 8px rgba(212, 175, 55, 0.4);
            }
            50% {
                box-shadow:
                    0 0 30px #D4AF37,
                    0 0 60px rgba(212, 175, 55, 0.5),
                    inset 0 6px 12px rgba(212, 175, 55, 0.6);
            }
        }

        /* 翠绿脉冲动画 */
        @keyframes pulse-jade {
            0%, 100% {
                opacity: 0.3;
            }
            50% {
                opacity: 0.7;
            }
        }

        /* 最后走法闪烁动画 */
        @keyframes flash-last-move {
            0% {
                background: rgba(0, 174, 107, 0.3);
            }
            100% {
                background: rgba(0, 174, 107, 0.1);
            }
        }

        /* 棋子悬停效果 */
        .chess-piece:hover {
            transform: translateY(-8px) scale(1.1);
            box-shadow:
                0 12px 20px rgba(0, 0, 0, 0.4),
                0 6px 10px rgba(212, 175, 55, 0.3),
                inset 0 3px 6px rgba(255, 255, 255, 0.4);
        }

        /* 棋子选中效果 */
        .chess-piece.selected {
            cursor: default;
        }
        </style>
        """


def render_chessboard_html(board: List[List[str]],
                         selected_pos: Optional[Tuple[int, int]] = None,
                         valid_moves: List[Tuple[int, int]] = None,
                         last_move: Optional[Tuple[Tuple[int, int], Tuple[int, int]]] = None) -> str:
    """
    渲染棋盘HTML（便捷函数）

    Args:
        board: 棋盘二维数组
        selected_pos: 选中的位置
        valid_moves: 合法走法列表
        last_move: 最后一步走法

    Returns:
        HTML字符串
    """
    renderer = BoardHTMLRenderer()
    return renderer.render(board, selected_pos, valid_moves, last_move)
