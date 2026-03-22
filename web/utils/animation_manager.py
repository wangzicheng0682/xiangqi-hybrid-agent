"""
动画管理器 - 商业级60fps流畅动画

职责: 贝塞尔曲线计算、动画生成、缓动函数

文档依据: JOINT_REFACTOR_ARCHITECTURE.md 动画系统

Phase 2完整实现:
- 贝塞尔曲线计算（三次贝塞尔）
- 走棋动画（60fps，300ms）
- 吃子动画（缩放+淡出，200ms）
- 选中动画（脉冲效果，1.5s）
- 缓动函数（ease-in-out-cubic）
"""

import math
from typing import List, Tuple, Callable


class BezierCurve:
    """
    贝塞尔曲线计算器

    计算三次贝塞尔曲线，用于平滑的走棋动画
    """

    @staticmethod
    def calculate_curve(from_pos: Tuple[int, int],
                    to_pos: Tuple[int, int],
                    num_frames: int = 18) -> List[Tuple[float, float]]:
        """
        计算三次贝塞尔曲线

        Args:
            from_pos: 起始位置 (row, col)
            to_pos: 目标位置 (row, col)
            num_frames: 动画帧数（默认18帧，60fps下300ms）

        Returns:
            路径点列表 [(x, y), ...]
        """
        # 控制点（贝塞尔曲线的形状控制）
        p0 = (float(from_pos[1]), float(from_pos[0]))  # 起始点 (col, row)
        p1 = ((from_pos[1] + to_pos[1]) / 2, (from_pos[0] + to_pos[0]) / 2)  # 控制点1
        p2 = ((from_pos[1] + to_pos[1]) / 2, (from_pos[0] + to_pos[0]) / 2)  # 控制点2
        p3 = (float(to_pos[1]), float(to_pos[0]))  # 终点 (col, row)

        path_points = []
        for i in range(num_frames + 1):
            t = i / num_frames

            # 三次贝塞尔曲线公式
            x = (1-t)**3 * p0[0] + 3*(1-t)**2 * t * p1[0] + 3*(1-t) * t**2 * p2[0] + t**3 * p3[0]
            y = (1-t)**3 * p0[1] + 3*(1-t)**2 * t * p1[1] + 3*(1-t) * t**2 * p2[1] + t**3 * p3[1]

            path_points.append((x, y))

        return path_points

    @staticmethod
    def calculate_arc_curve(from_pos: Tuple[int, int],
                        to_pos: Tuple[int, int],
                        arc_height: float = 0.1,
                        num_frames: int = 18) -> List[Tuple[float, float]]:
        """
        计算带弧度的贝塞尔曲线（用于马、炮等特殊走法）

        Args:
            from_pos: 起始位置
            to_pos: 目标位置
            arc_height: 弧度高度（相对于距离的百分比）
            num_frames: 动画帧数

        Returns:
            路径点列表
        """
        # 基础贝塞尔曲线
        base_curve = BezierCurve.calculate_curve(from_pos, to_pos, num_frames)

        # 添加弧度（垂直方向）
        distance = math.sqrt((to_pos[1] - from_pos[1])**2 + (to_pos[0] - from_pos[0])**2)
        max_arc = distance * arc_height

        path_points = []
        for i, (x, y) in enumerate(base_curve):
            # 使用正弦函数添加弧度
            progress = i / num_frames
            arc = math.sin(progress * math.pi) * max_arc

            # 判断是水平移动还是垂直移动
            if abs(to_pos[0] - from_pos[0]) > abs(to_pos[1] - from_pos[1]):
                # 水平移动为主，弧度在垂直方向
                path_points.append((x, y + arc))
            else:
                # 垂直移动为主，弧度在水平方向
                path_points.append((x + arc, y))

        return path_points


class EaseFunctions:
    """
    缓动函数集合

    用于动画的平滑过渡效果
    """

    @staticmethod
    def ease_in_out_cubic(progress: float) -> float:
        """
        缓入缓出 - 三次贝塞尔

        Args:
            progress: 进度 (0-1)

        Returns:
            缓动后的值 (0-1)
        """
        if progress < 0.5:
            return 4 * progress ** 3
        else:
            return 1 - pow(2 * progress - 2, 2)

    @staticmethod
    def ease_out_quad(progress: float) -> float:
        """
        缓出 - 二次贝塞尔

        Args:
            progress: 进度 (0-1)

        Returns:
            缓动后的值 (0-1)
        """
        return 1 - (1 - progress) * (1 - progress)

    @staticmethod
    def ease_in_out_sine(progress: float) -> float:
        """
        缓入缓出 - 正弦函数

        Args:
            progress: 进度 (0-1)

        Returns:
            缓动后的值 (0-1)
        """
        return -math.cos(progress * math.pi) / 2 + 0.5


class AnimationGenerator:
    """
    动画生成器

    生成各种类型的CSS动画代码
    """

    def __init__(self):
        self.animation_counter = 0

    def generate_move_animation(self, from_pos: Tuple[int, int],
                             to_pos: Tuple[int, int],
                             duration: float = 0.3,
                             curve_type: str = "cubic") -> str:
        """
        生成走棋动画（贝塞尔曲线）

        Args:
            from_pos: 起始位置 (row, col)
            to_pos: 目标位置 (row, col)
            duration: 动画持续时间（秒）
            curve_type: 曲线类型（cubic/arc）

        Returns:
            CSS动画代码
        """
        # 计算曲线路径
        if curve_type == "arc":
            path_points = BezierCurve.calculate_arc_curve(from_pos, to_pos)
        else:
            path_points = BezierCurve.calculate_curve(from_pos, to_pos)

        # 生成动画keyframes
        animation_id = f"move-animation-{self.animation_counter}"
        self.animation_counter += 1

        keyframes = []
        for i, (x, y) in enumerate(path_points):
            progress = i / len(path_points)
            # 使用缓动函数
            eased_progress = EaseFunctions.ease_in_out_cubic(progress)

            keyframes.append(f"""
            {progress * 100:.1f}% {{
                transform: translate({x * 60}px, {y * 60}px);
                box-shadow:
                    0 {-6 + eased_progress * 6}px {6 - eased_progress * 6}px 12px rgba(0, 0, 0, {0.3 + eased_progress * 0.2}),
                    inset 0 1px 3px rgba(255, 255, 255, {0.3 + eased_progress * 0.1});
            }}
            """)

        # 组装完整的CSS
        css = f"""
        <style>
        @keyframes {animation_id} {{
            {''.join(keyframes)}
        }}

        .piece-moving {{
            animation: {animation_id} {duration}s cubic-bezier(0.4, 0, 0.2, 1) forwards;
        }}
        </style>
        """

        return css

    def generate_capture_animation(self, duration: float = 0.2) -> str:
        """
        生成吃子动画（缩放+淡出）

        Args:
            duration: 动画持续时间（秒）

        Returns:
            CSS动画代码
        """
        animation_id = f"capture-animation-{self.animation_counter}"
        self.animation_counter += 1

        css = f"""
        <style>
        @keyframes {animation_id} {{
            0% {{
                transform: scale(1);
                opacity: 1;
            }}
            50% {{
                transform: scale(1.2);
                opacity: 0.8;
            }}
            100% {{
                transform: scale(0);
                opacity: 0;
            }}
        }}

        .piece-captured {{
            animation: {animation_id} {duration}s ease-out forwards;
        }}
        </style>
        """

        return css

    def generate_selected_animation(self, duration: float = 1.5) -> str:
        """
        生成选中动画（脉冲效果）

        Args:
            duration: 动画持续时间（秒）

        Returns:
            CSS动画代码
        """
        animation_id = f"selected-animation-{self.animation_counter}"
        self.animation_counter += 1

        css = f"""
        <style>
        @keyframes {animation_id} {{
            0%, 100% {{
                box-shadow:
                    0 0 20px #D4AF37,
                    0 0 40px rgba(212, 175, 55, 0.3),
                    inset 0 4px 8px rgba(212, 175, 55, 0.4);
            }}
            50% {{
                box-shadow:
                    0 0 30px #D4AF37,
                    0 0 60px rgba(212, 175, 55, 0.5),
                    inset 0 6px 12px rgba(212, 175, 55, 0.6);
            }}
        }}

        .piece-selected {{
            animation: {animation_id} {duration}s infinite;
        }}
        </style>
        """

        return css

    def generate_check_alert_animation(self, duration: float = 1.0) -> str:
        """
        生成将军警报动画

        Args:
            duration: 动画持续时间（秒）

        Returns:
            CSS动画代码
        """
        animation_id = f"check-alert-{self.animation_counter}"
        self.animation_counter += 1

        css = f"""
        <style>
        @keyframes {animation_id} {{
            0%, 100% {{
                border: 4px solid #E63946;
            }}
            50% {{
                border: 4px solid #E63946;
                box-shadow: 0 0 10px rgba(230, 57, 70, 0.5);
            }}
        }}

        .piece-in-check {{
            animation: {animation_id} {duration}s infinite;
        }}
        </style>
        """

        return css

    def generate_threat_animation(self, duration: float = 0.8) -> str:
        """
        生成威胁提示动画（用于提示将军或危险局面）

        Args:
            duration: 动画持续时间（秒）

        Returns:
            CSS动画代码
        """
        animation_id = f"threat-animation-{self.animation_counter}"
        self.animation_counter += 1

        css = f"""
        <style>
        @keyframes {animation_id} {{
            0%, 100% {{
                background: rgba(230, 57, 70, 0.1);
            }}
            50% {{
                background: rgba(230, 57, 70, 0.3);
            }}
        }}

        .position-in-threat {{
            animation: {animation_id} {duration}s infinite;
        }}
        </style>
        """

        return css


# 全局动画生成器实例
animation_generator = AnimationGenerator()


def get_move_animation(from_pos: Tuple[int, int],
                     to_pos: Tuple[int, int],
                     curve_type: str = "cubic") -> str:
    """
    获取走棋动画（便捷函数）

    Args:
        from_pos: 起始位置
        to_pos: 目标位置
        curve_type: 曲线类型

    Returns:
        CSS动画代码
    """
    return animation_generator.generate_move_animation(from_pos, to_pos, 0.3, curve_type)


def get_capture_animation() -> str:
    """
    获取吃子动画（便捷函数）

    Returns:
        CSS动画代码
    """
    return animation_generator.generate_capture_animation(0.2)


def get_selected_animation() -> str:
    """
    获取选中动画（便捷函数）

    Returns:
        CSS动画代码
    """
    return animation_generator.generate_selected_animation(1.5)


def get_check_alert_animation() -> str:
    """
    获取将军警报动画（便捷函数）

    Returns:
        CSS动画代码
    """
    return animation_generator.generate_check_alert_animation(1.0)
