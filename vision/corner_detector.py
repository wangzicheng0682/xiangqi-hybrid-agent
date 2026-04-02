"""
Corner Detector - 外框角点检测

用于测量新图的外框4个角点坐标
支持两种模式：
1. 手动输入（用户用工具查看像素坐标后输入）
2. 自动检测（基于图像处理，需要拍摄质量好的图片）
"""

from typing import Tuple, Optional
from dataclasses import dataclass
from PIL import Image
import numpy as np


@dataclass
class CornerResult:
    """角点检测结果"""
    tl: Tuple[int, int]
    tr: Tuple[int, int]
    bl: Tuple[int, int]
    br: Tuple[int, int]
    confidence: float


def detect_corners_manual(image_path: str) -> Optional[CornerResult]:
    """
    手动模式：用户通过外部工具（如 pixspy.com）查看像素坐标
    这里只提供读取图片的接口，具体坐标由用户输入
    """
    try:
        img = Image.open(image_path)
        return CornerResult(
            tl=(0, 0),
            tr=(img.width, 0),
            bl=(0, img.height),
            br=(img.width, img.height),
            confidence=0.0,
        )
    except Exception as e:
        print(f"无法打开图片: {e}")
        return None


def detect_corners_auto(image: Image.Image) -> Optional[CornerResult]:
    """
    自动检测模式：基于图像处理检测外框角点
    适用于：棋盘格线清晰、背景干净、拍摄角度正
    """
    try:
        import cv2
        img_array = np.array(image)
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array

        # 边缘检测
        edges = cv2.Canny(gray, 50, 150)

        # 霍夫变换检测直线
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, 100,
                                minLineLength=200, maxLineGap=20)

        if lines is None or len(lines) < 4:
            return None

        # 找最外围的4条线，然后计算交点
        # 简化版：找边缘像素点做透视变换

        # 找棋盘轮廓
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return None

        # 找最大轮廓（假设是棋盘）
        max_contour = max(contours, key=cv2.contourArea)
        if cv2.contourArea(max_contour) < 10000:
            return None

        # 找最小外接矩形
        rect = cv2.minAreaRect(max_contour)
        box = cv2.boxPoints(rect)
        box = np.int0(box)

        # 按位置排序四个角点（左上、右上、右下、左下）
        box = sorted(box, key=lambda p: (p[0], p[1]))
        if box[0][1] > box[1][1]:
            box[0], box[1] = box[1], box[0]
        if box[2][1] < box[3][1]:
            box[2], box[3] = box[3], box[2]

        # 重新按矩形顺序排列
        box = sorted(box, key=lambda p: p[0] + p[1])
        tl = box[0]
        br = box[3]

        # 找另两个角
        candidates = [box[1], box[2]]
        if candidates[0][0] < candidates[1][0]:
            tr, bl = candidates[0], candidates[1]
        else:
            tr, bl = candidates[1], candidates[0]

        return CornerResult(
            tl=(int(tl[0]), int(tl[1])),
            tr=(int(tr[0]), int(tr[1])),
            bl=(int(bl[0]), int(bl[1])),
            br=(int(br[0]), int(br[1])),
            confidence=0.8,
        )

    except ImportError:
        print("需要安装 OpenCV: pip install opencv-python")
        return None
    except Exception as e:
        print(f"角点检测失败: {e}")
        return None


def load_image_and_detect_corners(image_path: str,
                                   auto_detect: bool = False) -> Optional[CornerResult]:
    """加载图片并检测角点"""
    try:
        img = Image.open(image_path)
        if auto_detect:
            return detect_corners_auto(img)
        else:
            return detect_corners_manual(image_path)
    except Exception as e:
        print(f"加载图片失败: {e}")
        return None


def estimate_corners_from_image_size(width: int, height: int,
                                     margin: float = 0.02) -> Tuple:
    """
    根据图片尺寸估算外框角点（假设棋盘占满画面，四周留白比例相同）
    margin: 四周留白占图片尺寸的比例
    """
    margin_x = int(width * margin)
    margin_y = int(height * margin)

    return (
        (margin_x, margin_y),           # tl
        (width - margin_x, margin_y),  # tr
        (margin_x, height - margin_y),  # bl
        (width - margin_x, height - margin_y),  # br
    )