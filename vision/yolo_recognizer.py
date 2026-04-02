"""
YOLO Direct Recognizer - 基于 YOLO 模型的棋盘直接识别

流程：
    1. YOLO 检测棋子位置和类别（同时检测 board 边框）
    2. 用 board bbox 确定棋盘区域（无 board 时用图片边距估算）
    3. 将棋子像素坐标映射到 (col, row) 格点
    4. 生成 FEN 字符串

col 规则: 0=最右列, 8=最左列 (从右往左数)
row 规则: 0=最上行(黑方底线), 9=最下行(红方底线)

使用:
    from vision.yolo_recognizer import YoloDirectRecognizer
    recognizer = YoloDirectRecognizer()
    result = recognizer.recognize_image(pil_image)
    print(result.fen)
"""

import os
from dataclasses import dataclass, field
from typing import Optional, List, Tuple
from pathlib import Path

from .template_data import YOLO_TO_FEN

# 模型路径（相对工作目录）
_DEFAULT_MODEL = str(Path(__file__).parent / "xiangqi-detect-model" / "weights" / "best.pt")

# 全局缓存，避免重复加载
_model_cache = {}


@dataclass
class PieceDetection:
    cls: str
    x: int
    y: int
    conf: float
    col: Optional[int] = None
    row: Optional[int] = None
    fen_char: Optional[str] = None


@dataclass
class YoloRecognitionResult:
    fen: str = ""
    pieces_count: int = 0
    confidence: float = 0.0
    description: str = ""
    pieces: List[PieceDetection] = field(default_factory=list)
    verified: bool = False
    board_detected: bool = False    # YOLO 是否检测到 board 类
    annotated_image_b64: str = ""   # YOLO 标注图（base64 PNG）


def _get_model(model_path: str):
    """懒加载并缓存 YOLO 模型"""
    if model_path not in _model_cache:
        from ultralytics import YOLO
        _model_cache[model_path] = YOLO(model_path)
    return _model_cache[model_path]


def _build_fen(board_grid: List[List[str]], side_to_move: str = "w") -> str:
    """board_grid[col][row] -> FEN 字符串"""
    fen_rows = []
    for row in range(10):
        empty = 0
        row_str = ""
        for col in range(8, -1, -1):   # col=8(左)→0(右)，对应FEN从左到右
            c = board_grid[col][row]
            if c == ".":
                empty += 1
            else:
                if empty:
                    row_str += str(empty)
                    empty = 0
                row_str += c
        if empty:
            row_str += str(empty)
        fen_rows.append(row_str)
    return "/".join(fen_rows) + f" {side_to_move} - - 0 1"


def _verify_fen(fen: str) -> bool:
    """简单验证 FEN 格式"""
    try:
        board_part = fen.split()[0]
        rows = board_part.split("/")
        if len(rows) != 10:
            return False
        for row in rows:
            total = sum(int(c) if c.isdigit() else 1 for c in row)
            if total != 9:
                return False
        return True
    except Exception:
        return False


class YoloDirectRecognizer:
    """
    用训练好的 YOLO 模型直接识别象棋棋盘，无需预标定模板。
    """

    def __init__(self, model_path: str = None, conf_threshold: float = 0.07):
        self.model_path = model_path or _DEFAULT_MODEL
        self.conf_threshold = conf_threshold

    def recognize_image(
        self,
        image,   # PIL.Image 或 numpy array
        side_to_move: str = "w",
    ) -> YoloRecognitionResult:
        """
        识别棋盘图片，返回 FEN 和详细信息。

        参数:
            image        : PIL.Image (或 numpy array)
            side_to_move : 'w' 红方走 / 'b' 黑方走

        返回:
            YoloRecognitionResult
        """
        import numpy as np

        # 加载模型
        model = _get_model(self.model_path)

        # PIL → numpy
        if hasattr(image, "convert"):
            img_arr = np.array(image.convert("RGB"))
        else:
            img_arr = np.array(image)

        # YOLO 推理
        results = model(img_arr, verbose=False, conf=self.conf_threshold)
        boxes = results[0].boxes
        names = model.names

        # 生成 YOLO 标注图（BGR → RGB → base64 PNG）
        annotated_b64 = ""
        try:
            import base64, io as _io
            ann_bgr = results[0].plot(line_width=2, font_size=12)
            from PIL import Image as _PILImage
            ann_rgb = _PILImage.fromarray(ann_bgr[..., ::-1])   # BGR→RGB
            buf = _io.BytesIO()
            ann_rgb.save(buf, format="WEBP", quality=75)
            annotated_b64 = base64.b64encode(buf.getvalue()).decode()
        except Exception:
            pass

        # ------- 1. 提取 board bbox -------
        board_xyxy = None
        pieces_raw: List[PieceDetection] = []

        for b in boxes:
            cls_name = names[int(b.cls[0])]
            cx, cy = (int(v) for v in b.xywh[0].tolist()[:2])
            conf = float(b.conf[0])
            if cls_name == "board":
                bx1, by1, bx2, by2 = (int(v) for v in b.xyxy[0].tolist())
                if board_xyxy is None or conf > 0.5:
                    board_xyxy = (bx1, by1, bx2, by2)
            else:
                pieces_raw.append(PieceDetection(cls=cls_name, x=cx, y=cy, conf=conf))

        board_detected = board_xyxy is not None

        # 没拿到 board 类时用图像边缘估算
        if board_xyxy is None:
            h, w = img_arr.shape[:2]
            margin = max(10, int(min(w, h) * 0.03))
            board_xyxy = (margin, margin, w - margin, h - margin)

        bx1, by1, bx2, by2 = board_xyxy
        bw = bx2 - bx1
        bh = by2 - by1

        if bw <= 0 or bh <= 0:
            return YoloRecognitionResult(
                description="棋盘区域无效，请确保图片包含完整棋盘"
            )

        # ------- 2. 棋子坐标 → (col, row) -------
        board_grid = [["." for _ in range(10)] for _ in range(9)]
        matched: List[PieceDetection] = []

        for p in pieces_raw:
            fen_char = YOLO_TO_FEN.get(p.cls)
            if not fen_char:
                continue
            rel_x = p.x - bx1
            rel_y = p.y - by1
            # col: 0=最右, 8=最左（从右往左数）
            col = max(0, min(8, round(8 * (1.0 - rel_x / bw))))
            # row: 0=最上(黑方底线), 9=最下(红方底线)
            row = max(0, min(9, round(9 * rel_y / bh)))
            p.col = col
            p.row = row
            p.fen_char = fen_char
            board_grid[col][row] = fen_char
            matched.append(p)

        # ------- 3. 生成 FEN -------
        fen = _build_fen(board_grid, side_to_move)
        verified = _verify_fen(fen)
        pieces_count = len(matched)

        # 计算平均置信度
        avg_conf = (
            sum(p.conf for p in matched) / len(matched)
            if matched else 0.0
        )

        piece_names_cn = {
            "r_shuai": "红帅", "r_shi": "红仕", "r_xiang": "红相",
            "r_che": "红车", "r_ma": "红马", "r_pao": "红炮", "r_bing": "红兵",
            "b_jiang": "黑将", "b_shi": "黑士", "b_xiang": "黑象",
            "b_che": "黑车", "b_ma": "黑马", "b_pao": "黑炮", "b_zu": "黑卒",
        }
        piece_desc = "、".join(
            piece_names_cn.get(p.cls, p.cls) for p in matched[:5]
        )
        extra = f"等{pieces_count}枚棋子" if pieces_count > 5 else f"共{pieces_count}枚棋子"
        desc = f"识别到{piece_desc}{extra}" if matched else "未检测到棋子"
        if board_detected:
            desc = "（棋盘已定位）" + desc

        return YoloRecognitionResult(
            fen=fen,
            pieces_count=pieces_count,
            confidence=round(avg_conf, 3),
            description=desc,
            pieces=matched,
            verified=verified,
            board_detected=board_detected,
            annotated_image_b64=annotated_b64,
        )
