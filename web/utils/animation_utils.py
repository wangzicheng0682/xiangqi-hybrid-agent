"""
动画工具模块 - 商业级60fps流畅动画

用途：提供流畅的棋子移动、吃子、特效动画
"""

import time
import math
from typing import List, Tuple, Callable, Optional


def calculate_bezier_curve(from_pos: Tuple[int, int], to_pos: Tuple[int, int], num_frames: int = 18) -> List[Tuple[float, float]]:
    """
    计算贝塞尔曲线 - 60fps流畅移动

    Args:
        from_pos: 起始位置 (row, col)
        to_pos: 目标位置 (row, col)
        num_frames: 动画帧数（默认18帧，60fps下300ms）

    Returns:
        路径点列表
    """
    # 三次贝塞尔曲线
    p0 = (from_pos[0], from_pos[1])
    p1 = ((from_pos[0] + to_pos[0]) / 2, (from_pos[1] + to_pos[1]) / 2)
    p2 = to_pos

    path_points = []
    for i in range(num_frames + 1):
        t = i / num_frames
        # 三次贝塞尔曲线公式
        x = (1-t)**3 * p0[0] + 3*(1-t)**2 * t * p1[0] + 3*(1-t)*t**2 * p2[0]
        y = (1-t)**3 * p0[1] + 3*(1-t)**2 * t * p1[1] + 3*(1-t)*t**2 * p2[1]
        path_points.append((x, y))

    return path_points


def calculate_cubic_bezier(from_pos: Tuple[int, int], to_pos: Tuple[int, int],
                         control_points: List[Tuple[float, float]] = None,
                         num_frames: int = 18) -> List[Tuple[float, float]]:
    """
    计算三次贝塞尔曲线 - 更平滑的移动路径

    Args:
        from_pos: 起始位置
        to_pos: 目标位置
        control_points: 控制点列表（可选）
        num_frames: 动画帧数

    Returns:
        路径点列表
    """
    # 如果没有提供控制点，自动生成
    if control_points is None:
        p0 = (from_pos[0], from_pos[1])
        p2 = ((from_pos[0] + to_pos[0]) / 2, (from_pos[1] + to_pos[1]) / 2)
        p1 = p2
        p3 = to_pos
        control_points = [p1, p2]

    # 转换为numpy计算（更精确）
    p0 = from_pos
    p1 = control_points[0]
    p2 = control_points[1]
    p3 = to_pos

    path_points = []
    for i in range(num_frames + 1):
        t = i / num_frames
        # 三次贝塞尔曲线公式
        x = (1-t)**3 * p0[0] + 3*(1-t)**2 * t * p1[0] + 3*(1-t)*t**2 * p2[0] + t**3 * p3[0]
        y = (1-t)**3 * p0[1] + 3*(1-t)**2 * t * p1[1] + 3*(1-t)*t**2 * p2[1] + t**3 * p3[1]
        path_points.append((x, y))

    return path_points


def create_move_animation(piece_element, from_pos: Tuple[int, int],
                     to_pos: Tuple[int, int],
                     duration: float = 0.3,
                     callback: Optional[Callable] = None) -> str:
    """
    创建棋子移动动画（商业级60fps流畅度）

    Args:
        piece_element: 棋子DOM元素
        from_pos: 起始位置 (row, col)
        to_pos: 目标位置 (row, col)
        duration: 动画持续时间（秒）
        callback: 动画完成回调

    Returns:
        动画ID
    """
    # 动画配置
    fps = 60
    num_frames = int(duration * fps)
    path_points = calculate_bezier_curve(from_pos, to_pos, num_frames)

    # 运行动画
    animation_id = f"move_{id(piece_element)}"

    def animate():
        for i, (x, y) in enumerate(path_points):
            # 更新位置
            piece_element.update_x(x)
            piece_element.update_y(y)

            # 更新阴影
            shadow_offset = -6 + (i / num_frames) * 6
            piece_element.update_shadow(
                0,
                -6 + (i / num_frames) * 6,
                0.5 + (i / num_frames) * 0.5
            )

            # 等待下一帧（60fps = 16.67ms）
            time.sleep(1 / fps)

        # 动画完成回调
        if callback:
            callback()

    # 异步运行动画（在实际应用中）
    animate()

    return animation_id


def create_capture_animation(captured_element, duration: float = 0.2,
                        callback: Optional[Callable] = None):
    """
    创建吃子动画（缩放+淡出）

    Args:
        captured_element: 被吃棋子元素
        duration: 动画持续时间
        callback: 动画完成回调
    """
    # 动画配置
    fps = 60
    num_frames = int(duration * fps)

    animation_id = f"capture_{id(captured_element)}"

    def animate():
        for i in range(num_frames):
            # 缩小
            scale = 1.2 - (i / num_frames) * 0.2
            captured_element.update(scale=scale)

            # 淡出
            opacity = 1.0 - (i / num_frames)
            captured_element.update(opacity=opacity)

            time.sleep(1 / fps)

        if callback:
            callback()

    animate()
    return animation_id


def create_selected_animation(piece_element, duration: float = 1.5):
    """
    创建选中动画（脉冲效果）

    Args:
        piece_element: 棋子元素
        duration: 动画持续时间

    Returns:
        动画样式类名
    """
    return "piece-selected"


def create_check_alert_animation(check_element, duration: float = 0.5):
    """
    创建将军警报动画

    Args:
        check_element: 将军标记元素
        duration: 动画持续时间

    Returns:
        动画样式类名
    """
    return "check-alert"


def smooth_interpolation(current: float, target: float,
                         duration: float,
                         progress: float) -> float:
    """
    平滑插值函数 - 用于实时动画

    Args:
        current: 当前值
        target: 目标值
        duration: 总持续时间
        progress: 进度 (0-1)

    Returns:
        插值后的值
    """
    # 缓动函数
    t = progress
    if t <= 0.5:
        # 前半段：加速
        return current + (target - current) * (2 * t**2)
    else:
        # 后半段：减速
        return current + (target - current) * (1 - 2 * (1-t)**2)


def ease_in_out_cubic(progress: float) -> float:
    """
    缓动函数 - 三次贝塞尔缓动

    Args:
        progress: 进度 (0-1)

    Returns:
        缓动后的值 (0-1)
    """
    if progress < 0.5:
        return 4 * progress ** 3
    else:
        return 1 - pow(2 * progress - 2, 2)
