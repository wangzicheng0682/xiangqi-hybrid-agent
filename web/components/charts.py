"""
图表组件 - 天天象棋级别

职责: 显示胜率曲线、热力图

文档依据: JOINT_REFACTOR_ARCHITECTURE.md 图表组件

Phase 2将完整实现以下功能:
- 胜率曲线图（动态更新）
- 转折点标记
- 劣着标记
- 实时热力图

当前: 框架版本，使用PIL绘制简单图表
"""

from typing import List, Tuple
from PIL import Image, ImageDraw


class ChartsUI:
    """
    图表组件框架

    Phase 2将完整实现商业级图表
    当前版本使用PIL绘制简单图表
    """

    def __init__(self):
        self.scores = []

    def render_eval_curve(self,
                        scores: List[float],
                        turning_points: List[int] = None,
                        blunders: List[int] = None) -> str:
        """
        渲染胜率曲线图

        Args:
            scores: 评分历史
            turning_points: 转折点索引
            blunders: 劣着索引

        Returns:
            图片路径
        """
        import tempfile

        if not scores:
            return None

        # 创建空白图片
        width, height = 800, 400
        img = Image.new('RGB', (width, height), '#FFFFFF')
        draw = ImageDraw.Draw(img)

        # 绘制坐标轴
        padding = 40
        plot_width = width - 2 * padding
        plot_height = height - 2 * padding

        draw.line([(padding, padding), (padding, height - padding)], fill='#000000', width=2)
        draw.line([(padding, height - padding), (width - padding, height - padding)], fill='#000000', width=2)

        # 计算Y轴范围
        min_score = min(scores)
        max_score = max(scores)
        score_range = max_score - min_score if max_score > min_score else 1

        # 绘制曲线
        points = []
        for i, score in enumerate(scores):
            x = padding + (i / (len(scores) - 1)) * plot_width if len(scores) > 1 else padding
            y = height - padding - ((score - min_score) / score_range) * plot_height
            points.append((x, y))

        # 绘制折线
        if len(points) > 1:
            draw.line(points, fill='#C41E3A', width=2)

        # 标记转折点
        if turning_points:
            for i in turning_points:
                if 0 <= i < len(points):
                    x, y = points[i]
                    draw.ellipse([(x - 5, y - 5), (x + 5, y + 5)], fill='#D4AF37')

        # 标记劣着
        if blunders:
            for i in blunders:
                if 0 <= i < len(points):
                    x, y = points[i]
                    draw.ellipse([(x - 5, y - 5), (x + 5, y + 5)], fill='#E63946')

        # 保存图片
        temp_path = tempfile.mktemp(suffix='.png')
        img.save(temp_path)
        return temp_path

    def set_scores(self, scores: List[float]) -> None:
        """
        设置评分历史

        Args:
            scores: 评分列表
        """
        self.scores = scores
