"""
Template Data Structure for Xiangqi Board Recognition
中国象棋棋盘模板数据 - 一次性测量，永久复用

列(col): 从棋盘最右侧一列开始，从右往左数，编号 0~8
行(row): 从棋盘最上方一行（黑方底线）开始，从上往下数，编号 0~9
格点坐标: (x, y) 像素坐标
"""

from dataclasses import dataclass
from typing import List, Tuple
import json
import os


@dataclass
class BoardBox:
    """带留白的外框4个角点"""
    tl: Tuple[int, int]  # 左上
    tr: Tuple[int, int]  # 右上
    bl: Tuple[int, int]  # 左下
    br: Tuple[int, int]  # 右下

    def to_dict(self):
        return {
            "tl": list(self.tl),
            "tr": list(self.tr),
            "bl": list(self.bl),
            "br": list(self.br),
        }

    @classmethod
    def from_dict(cls, d):
        return cls(
            tl=tuple(d["tl"]),
            tr=tuple(d["tr"]),
            bl=tuple(d["bl"]),
            br=tuple(d["br"]),
        )


@dataclass
class ChessTemplate:
    """
    象棋棋盘模板
    grid[col][row] = (x, y) 像素坐标
    col: 0~8 (从右到左)
    row: 0~9 (从上到下)
    """
    name: str
    total_width: int   # 外框宽度
    total_height: int  # 外框高度
    box: BoardBox       # 外框4个角点
    grid: List[List[Tuple[int, int]]]  # 90个格点坐标 [col][row]
    scale_ref: float = 1.0  # 参考缩放比例（用于说明）

    def to_dict(self):
        return {
            "name": self.name,
            "total_width": self.total_width,
            "total_height": self.total_height,
            "box": self.box.to_dict(),
            "grid": [[list(p) for p in row] for row in self.grid],
            "scale_ref": self.scale_ref,
        }

    @classmethod
    def from_dict(cls, d):
        grid = [[tuple(p) for p in row] for row in d["grid"]]
        return cls(
            name=d["name"],
            total_width=d["total_width"],
            total_height=d["total_height"],
            box=BoardBox.from_dict(d["box"]),
            grid=grid,
            scale_ref=d.get("scale_ref", 1.0),
        )

    def get_grid_point(self, col: int, row: int) -> Tuple[int, int]:
        """获取指定格点的像素坐标"""
        return self.grid[col][row]


def load_template(path: str) -> ChessTemplate:
    """从JSON文件加载模板"""
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return ChessTemplate.from_dict(data)


def save_template(template: ChessTemplate, path: str):
    """保存模板到JSON文件"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(template.to_dict(), f, ensure_ascii=False, indent=2)


def distance_sq(x1: float, y1: float, x2: float, y2: float) -> float:
    """计算距离的平方（不开根号，速度更快）"""
    dx = x1 - x2
    dy = y1 - y2
    return dx * dx + dy * dy


def find_nearest_grid_point(x: float, y: float, template: ChessTemplate) -> Tuple[int, int]:
    """
    找距离最近的格点，返回 (col, row)
    核心比对：遍历90个格点，找距离最近的
    """
    min_dist = float('inf')
    target_col = 0
    target_row = 0

    for col in range(9):
        for row in range(10):
            gx, gy = template.grid[col][row]
            dist = distance_sq(x, y, gx, gy)
            if dist < min_dist:
                min_dist = dist
                target_col = col
                target_row = row

    return target_col, target_row


# 棋子映射: YOLO类别 -> FEN字符
YOLO_TO_FEN = {
    # 红方 (大写)
    "r_shuai": "K",
    "r_shi": "A",
    "r_xiang": "B",
    "r_che": "R",
    "r_ma": "N",
    "r_pao": "C",
    "r_bing": "P",
    # 黑方 (小写)
    "b_jiang": "k",
    "b_shi": "a",
    "b_xiang": "b",
    "b_che": "r",
    "b_ma": "n",
    "b_pao": "c",
    "b_zu": "p",
}


# 反向映射（FEN字符 -> YOLO类别）
FEN_TO_YOLO = {v: k for k, v in YOLO_TO_FEN.items()}