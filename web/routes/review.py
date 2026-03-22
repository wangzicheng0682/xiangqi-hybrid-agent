"""
复盘模式路由

职责: 复盘模式的Gradio路由和事件处理

文档依据: JOINT_REFACTOR_ARCHITECTURE.md 路由层
"""

import gradio as gr
from typing import Tuple, Optional
from web.modes.review_mode import ReviewMode
from web.components.charts import ChartsUI


class ReviewRoute:
    """
    复盘模式路由

    处理复盘模式的所有Gradio交互
    """

    def __init__(self, agent, review_mode: ReviewMode):
        self.agent = agent
        self.review_mode = review_mode
        self.charts_ui = ChartsUI()

    def handle_analyze_game(self, moves_str: str, red_player: str,
                          black_player: str, result: str) -> Tuple[Optional[str], str, dict]:
        """
        处理分析对局按钮

        Args:
            moves_str: 走法字符串
            red_player: 红方名称
            black_player: 黑方名称
            result: 对局结果

        Returns:
            (图表图片路径, 报告Markdown, 分析状态)
        """
        # 解析走法
        moves = moves_str.strip().split() if moves_str.strip() else []

        if not moves:
            return None, "请输入走法记录", {"scores": [], "moves": []}

        # 加载对局
        game = self.review_mode.load_game(
            red_player=red_player,
            black_player=black_player,
            result=result,
            moves=moves
        )

        # 分析对局
        analysis = self.review_mode.analyze_full_game()

        # 生成胜率曲线
        scores = analysis.get('scores', [])
        turning_points = analysis.get('turning_points', [])
        blunders = self.review_mode.find_blunders(scores)

        chart_path = self.review_mode.generate_eval_curve(scores, turning_points, blunders)

        # 生成报告
        report = self.review_mode.generate_report()

        return chart_path, report, analysis

    def handle_generate_report(self, moves_str: str, red_player: str,
                           black_player: str, result: str) -> Tuple[Optional[str], str, dict]:
        """
        处理生成报告按钮

        Args:
            moves_str: 走法字符串
            red_player: 红方名称
            black_player: 黑方名称
            result: 对局结果

        Returns:
            (图表图片路径, 报告Markdown, 分析状态)
        """
        # 与handle_analyze_game相同，暂时复用
        return self.handle_analyze_game(moves_str, red_player, black_player, result)
