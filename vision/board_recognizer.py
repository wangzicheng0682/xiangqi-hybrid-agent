"""
Board Recognizer - 棋盘识别整合器

整合模板比对法的所有组件，提供简洁的API:
    from core.vision.board_recognizer import BoardRecognizer

    recognizer = BoardRecognizer(template_path="templates/my_board.json")
    result = recognizer.recognize(image_path="photo.jpg",
                                  yolo_results=[...],
                                  new_board_corners=...)
    print(result.fen)
"""

from typing import List, Optional, Tuple, Dict, Any
from dataclasses import dataclass
from pathlib import Path

from .template_data import ChessTemplate, BoardBox, load_template, YOLO_TO_FEN
from .template_matcher import TemplateMatcher, DetectedPiece, ScaleInfo
from .fen_builder import build_fen_from_pieces, verify_fen, count_pieces


@dataclass
class RecognitionResult:
    """识别结果"""
    fen: str
    pieces_count: int
    confidence: float
    description: str
    pieces: List[DetectedPiece]  # 每个棋子的匹配结果
    verified: bool  # 是否通过验证

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fen": self.fen,
            "pieces_count": self.pieces_count,
            "confidence": self.confidence,
            "description": self.description,
            "verified": self.verified,
        }


class BoardRecognizer:
    """
    棋盘识别器
    使用模板比对法：一次测量，永久复用
    """

    def __init__(self, template_path: str = None, template: ChessTemplate = None):
        self.matcher = TemplateMatcher(template=template)
        if template_path:
            self.matcher.load_template(template_path)

        self.last_result: Optional[RecognitionResult] = None

    def recognize(self,
                  image_path: str = None,
                  yolo_results: List[Dict] = None,
                  new_board_corners: BoardBox = None,
                  side_to_move: str = "w",
                  confidence_threshold: float = 0.7) -> Optional[RecognitionResult]:
        """
        识别棋盘图片，生成FEN

        参数:
            image_path: 棋盘图片路径（用于自动检测外框）
            yolo_results: YOLO检测结果列表，格式：
                [{"x": 500, "y": 300, "category": "r_pao", "confidence": 0.95}, ...]
            new_board_corners: 新图的外框4个角点
            side_to_move: 红方走棋"w" / 黑方走棋"b"
            confidence_threshold: 置信度阈值

        返回:
            RecognitionResult: 包含FEN和详细信息
        """
        if not self.matcher.template:
            raise ValueError("模板未加载，请先加载模板")

        if not new_board_corners:
            # 尝试自动检测
            if image_path:
                from .corner_detector import load_image_and_detect_corners, estimate_corners_from_image_size
                from PIL import Image

                img = Image.open(image_path)
                corners = estimate_corners_from_image_size(img.width, img.height)
                new_board_corners = BoardBox(
                    tl=corners[0], tr=corners[1],
                    bl=corners[2], br=corners[3]
                )
            else:
                raise ValueError("需要提供 new_board_corners 或 image_path")

        if not yolo_results:
            # 无检测结果，返回空FEN
            return RecognitionResult(
                fen="",
                pieces_count=0,
                confidence=0.0,
                description="无棋子检测结果",
                pieces=[],
                verified=False,
            )

        # 转换为DetectedPiece列表
        pieces = []
        for r in yolo_results:
            piece = DetectedPiece(
                x=r.get("x", 0),
                y=r.get("y", 0),
                category=r.get("category", r.get("class", "")),
                confidence=r.get("confidence", r.get("conf", 0.0)),
            )
            pieces.append(piece)

        # 匹配棋子到格点
        matched_pieces = self.matcher.match_pieces(
            pieces, new_board_corners, confidence_threshold
        )

        # 生成FEN
        fen = build_fen_from_pieces(matched_pieces, side_to_move)
        pieces_count = count_pieces(fen)
        verified = verify_fen(fen) and 16 <= pieces_count <= 32

        # 计算置信度
        if matched_pieces:
            avg_conf = sum(p.confidence for p in matched_pieces) / len(matched_pieces)
            conf_score = avg_conf * (1.0 if verified else 0.7)
        else:
            conf_score = 0.0

        result = RecognitionResult(
            fen=fen,
            pieces_count=pieces_count,
            confidence=conf_score,
            description=f"检测到{pieces_count}个棋子" + (" [OK]" if verified else " [FAIL]"),
            pieces=matched_pieces,
            verified=verified,
        )

        self.last_result = result
        return result

    def recognize_from_yolo(self,
                            yolo_output: List[Dict],
                            new_box: BoardBox,
                            side_to_move: str = "w",
                            confidence_threshold: float = 0.7) -> Optional[RecognitionResult]:
        """
        直接从YOLO输出识别（不读取图片文件）
        yolo_output: YOLO模型输出，格式同recognize的yolo_results
        """
        return self.recognize(
            yolo_results=yolo_output,
            new_board_corners=new_box,
            side_to_move=side_to_move,
            confidence_threshold=confidence_threshold,
        )

    @staticmethod
    def create_with_yolo_integration(yolo_model_path: str = None,
                                     template_path: str = None) -> 'BoardRecognizer':
        """
        创建集成了YOLO的识别器
        注意: YOLO模型需要单独加载
        """
        recognizer = BoardRecognizer(template_path=template_path)

        # 预留YOLO集成接口
        # TODO: 集成YOLO模型
        recognizer.yolo_model = None

        return recognizer


# 便捷函数
def recognize_board(image_path: str,
                    yolo_results: List[Dict],
                    new_box: BoardBox,
                    template_path: str,
                    side_to_move: str = "w") -> Optional[str]:
    """
    一行命令识别棋盘图片

    示例:
        corners = BoardBox(tl=(100,100), tr=(1100,100),
                          bl=(100,1200), br=(1100,1200))
        pieces = [{"x":500,"y":400,"category":"r_che","confidence":0.95}, ...]
        fen = recognize_board("photo.jpg", pieces, corners, "templates/my_board.json")
    """
    recognizer = BoardRecognizer(template_path=template_path)
    result = recognizer.recognize(
        image_path=image_path,
        yolo_results=yolo_results,
        new_board_corners=new_box,
        side_to_move=side_to_move,
    )
    return result.fen if result else None


# 调试/验证工具
def debug_match(piece_x: float, piece_y: float,
                template_path: str,
                new_box: BoardBox) -> Tuple[int, int]:
    """
    调试工具：手动验证某个坐标的匹配结果
    用于测试模板是否正确
    """
    from .template_matcher import compute_scale

    template = load_template(template_path)
    scale = compute_scale(new_box, template)

    # 缩放坐标
    new_tl_x = new_box.tl[0]
    new_tl_y = new_box.tl[1]

    x_rel = piece_x - new_tl_x
    y_rel = piece_y - new_tl_y

    x_final = x_rel * scale.scale_x + template.box.tl[0]
    y_final = y_rel * scale.scale_y + template.box.tl[1]

    # 找最近格点
    from .template_data import find_nearest_grid_point
    col, row = find_nearest_grid_point(x_final, y_final, template)

    return col, row