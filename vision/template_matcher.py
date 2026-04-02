"""
Template Matcher - 模板比对法棋盘识别核心
核心逻辑：一次模板测量，永久复用；新图仅做「缩放 + 距离比对」

流程:
1. 加载模板
2. 测量新图外框4个角
3. 计算缩放比例
4. 把棋子坐标缩放到模板坐标系
5. 比对格点，确定棋子位置
"""

import math
from typing import Optional, List, Tuple, Dict, Any
from dataclasses import dataclass

from .template_data import (
    ChessTemplate, BoardBox, load_template,
    find_nearest_grid_point, distance_sq,
    YOLO_TO_FEN
)


@dataclass
class DetectedPiece:
    """检测到的棋子"""
    x: float        # 原始像素坐标
    y: float
    category: str    # YOLO类别，如 "r_pao"
    confidence: float
    col: Optional[int] = None   # 匹配到的列 (0~8)
    row: Optional[int] = None   # 匹配到的行 (0~9)
    fen_char: Optional[str] = None  # FEN字符


@dataclass
class ScaleInfo:
    """缩放信息"""
    scale_x: float
    scale_y: float
    offset_x: float
    offset_y: float


class TemplateMatcher:
    """
    模板比对法棋盘识别器
    核心：加载模板 → 测量新图外框 → 计算缩放 → 缩放棋子坐标 → 比对格点
    """

    def __init__(self, template_path: str = None, template: ChessTemplate = None):
        if template:
            self.template = template
        elif template_path:
            self.template = load_template(template_path)
        else:
            self.template = None

        self.scale_info: Optional[ScaleInfo] = None

    def load_template(self, path: str):
        """加载模板"""
        self.template = load_template(path)

    def measure_new_board(self, new_box: BoardBox):
        """
        测量新图外框4个角，计算缩放信息
        new_box: 新图的外框4个角点
        """
        if not self.template:
            raise ValueError("模板未加载")

        # 计算新图的尺寸
        new_width = max(new_box.tr[0], new_box.br[0]) - min(new_box.tl[0], new_box.bl[0])
        new_height = max(new_box.bl[1], new_box.br[1]) - min(new_box.tl[1], new_box.tr[1])

        # 计算模板的尺寸
        t_width = self.template.total_width
        t_height = self.template.total_height

        # 计算缩放比例
        scale_x = t_width / new_width if new_width > 0 else 1.0
        scale_y = t_height / new_height if new_height > 0 else 1.0

        # 计算偏移量（模板左上角 - 新图左上角缩放后）
        self.scale_info = ScaleInfo(
            scale_x=scale_x,
            scale_y=scale_y,
            offset_x=self.template.box.tl[0] - new_box.tl[0] * scale_x,
            offset_y=self.template.box.tl[1] - new_box.tl[1] * scale_y,
        )

    def transform_piece_coords(self, x: float, y: float) -> Tuple[float, float]:
        """
        把棋子坐标从新图坐标系转换到模板坐标系
        三步走：
        1. 转相对坐标
        2. 按比例缩放
        3. 转模板绝对坐标
        """
        if not self.scale_info:
            raise ValueError("请先调用 measure_new_board")

        # 1. 转相对坐标
        si = self.scale_info
        x_rel = x - self._get_new_box_tl_x()
        y_rel = y - self._get_new_box_tl_y()

        # 2. 按比例缩放
        x_template_rel = x_rel * si.scale_x
        y_template_rel = y_rel * si.scale_y

        # 3. 转模板绝对坐标
        x_final = x_template_rel + si.offset_x + self._get_new_box_tl_x() * si.scale_x
        y_final = y_template_rel + si.offset_y + self._get_new_box_tl_y() * si.scale_y

        return x_final, y_final

    def _get_new_box_tl_x(self) -> float:
        if not hasattr(self, '_new_box_tl'):
            return 0
        return self._new_box_tl[0]

    def _get_new_box_tl_y(self) -> float:
        if not hasattr(self, '_new_box_tl'):
            return 0
        return self._new_box_tl[1]

    def match_pieces(self, pieces: List[DetectedPiece], new_box: BoardBox,
                     confidence_threshold: float = 0.7) -> List[DetectedPiece]:
        """
        把检测到的棋子匹配到格点上
        pieces: YOLO检测到的棋子列表
        new_box: 新图外框4个角点
        confidence_threshold: 置信度阈值
        """
        # 1. 测量新图外框，计算缩放
        self._new_box_tl = new_box.tl
        self.measure_new_board(new_box)

        matched = []

        for piece in pieces:
            # 过滤低置信度
            if piece.confidence < confidence_threshold:
                continue

            # 2. 把棋子坐标缩放到模板坐标系
            x_final, y_final = self.transform_piece_coords(piece.x, piece.y)

            # 3. 比对格点
            col, row = find_nearest_grid_point(x_final, y_final, self.template)

            # 4. 填充结果
            piece.col = col
            piece.row = row
            piece.fen_char = YOLO_TO_FEN.get(piece.category)

            matched.append(piece)

        return matched

    def build_board_matrix(self, pieces: List[DetectedPiece]) -> List[List[str]]:
        """
        构建9×10空棋盘矩阵，填入棋子
        返回: board[9][10]，空位为"." 或数字（留空时用）
        """
        # 初始化空棋盘
        board = [["" for _ in range(10)] for _ in range(9)]

        # 填入棋子 (col从右到左编号, row从上到下编号)
        for piece in pieces:
            if piece.col is not None and piece.row is not None and piece.fen_char:
                board[piece.col][piece.row] = piece.fen_char

        return board

    def board_to_fen(self, board: List[List[str]], side_to_move: str = "w") -> str:
        """
        把棋盘矩阵转换为FEN字符串
        col顺序: 从第8列到第0列（对应FEN从左到右）
        row顺序: 从第0行到第9行（对应FEN从上到下）
        """
        fen_rows = []
        for row in range(10):
            row_chars = []
            col = 8  # 从右往左
            while col >= 0:
                piece = board[col][row]
                if piece:
                    row_chars.append(piece)
                    col -= 1
                else:
                    empty = 0
                    while col >= 0 and not board[col][row]:
                        empty += 1
                        col -= 1
                    row_chars.append(str(empty))
            fen_rows.append("".join(row_chars))

        fen = "/".join(fen_rows)
        fen += f" {side_to_move} - - 0 1"
        return fen


def simple_match(x: float, y: float, template: ChessTemplate) -> Tuple[int, int]:
    """
    简单匹配：给定坐标，直接找最近的格点
    用于已知棋子在新图坐标，直接匹配到模板格点
    """
    return find_nearest_grid_point(x, y, template)


# 缩放比例计算工具
def compute_scale(new_box: BoardBox, template: ChessTemplate) -> ScaleInfo:
    """计算新图到模板的缩放比例"""
    new_width = max(new_box.tr[0], new_box.br[0]) - min(new_box.tl[0], new_box.bl[0])
    new_height = max(new_box.bl[1], new_box.br[1]) - min(new_box.tl[1], new_box.tr[1])

    t_width = template.total_width
    t_height = template.total_height

    scale_x = t_width / new_width if new_width > 0 else 1.0
    scale_y = t_height / new_height if new_height > 0 else 1.0

    return ScaleInfo(
        scale_x=scale_x,
        scale_y=scale_y,
        offset_x=template.box.tl[0],
        offset_y=template.box.tl[1],
    )