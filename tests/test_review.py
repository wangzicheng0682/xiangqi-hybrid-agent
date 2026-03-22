"""
复盘报告生成模块测试

文档依据: PRD.md 3.3.3 复盘报告内容
"""

import pytest
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestTurningPointDetection:
    """测试转折点识别"""
    
    def test_identify_single_turning_point(self):
        """测试识别单个转折点"""
        from core.review import identify_turning_points
        
        scores = [0, 0, 0, 500, 500, 500]
        turning_points = identify_turning_points(scores, threshold=300)
        
        assert len(turning_points) == 1
        assert turning_points[0].move_number == 3
        assert turning_points[0].score_change == 500
    
    def test_identify_multiple_turning_points(self):
        """测试识别多个转折点"""
        from core.review import identify_turning_points
        
        scores = [0, 400, 400, -300, -300, 600]
        turning_points = identify_turning_points(scores, threshold=300)
        
        assert len(turning_points) == 3
    
    def test_no_turning_points(self):
        """测试无转折点情况"""
        from core.review import identify_turning_points
        
        scores = [0, 50, -30, 80, -20, 100]
        turning_points = identify_turning_points(scores, threshold=300)
        
        assert len(turning_points) == 0


class TestBlunderDetection:
    """测试劣着识别"""
    
    def test_identify_red_blunder(self):
        """测试识别红方劣着"""
        from core.review import identify_blunders
        
        scores = [0, -400, -400, -400]
        blunders = identify_blunders(scores, threshold=200)
        
        assert 1 in blunders
    
    def test_identify_black_blunder(self):
        """测试识别黑方劣着"""
        from core.review import identify_blunders
        
        scores = [0, 0, 400, 400]
        blunders = identify_blunders(scores, threshold=200)
        
        assert 2 in blunders
    
    def test_no_blunders(self):
        """测试无劣着情况"""
        from core.review import identify_blunders
        
        scores = [0, 50, -30, 80, -20]
        blunders = identify_blunders(scores, threshold=200)
        
        assert len(blunders) == 0


class TestScoreToWinrate:
    """测试评分转胜率"""
    
    def test_even_position(self):
        """测试均势"""
        from core.review import score_to_winrate
        
        winrate = score_to_winrate(0)
        assert 45 <= winrate <= 55
    
    def test_red_advantage(self):
        """测试红方优势 - 500分约55%胜率"""
        from core.review import score_to_winrate
        
        winrate = score_to_winrate(500)
        assert winrate > 52  # 红方优势
    
    def test_black_advantage(self):
        """测试黑方优势 - -500分约45%胜率"""
        from core.review import score_to_winrate
        
        winrate = score_to_winrate(-500)
        assert winrate < 48  # 黑方优势
    
    def test_large_advantage(self):
        """测试大优 - 1000分约60%胜率"""
        from core.review import score_to_winrate
        
        winrate = score_to_winrate(1000)
        assert winrate > 55  # 大优


class TestGameFlowAnalysis:
    """测试对局走势分析"""
    
    def test_opening_phase(self):
        """测试开局阶段"""
        from core.review import analyze_game_flow
        
        scores = [0] * 5
        result = analyze_game_flow(scores)
        
        assert result["phase"] == "开局"
    
    def test_middlegame_phase(self):
        """测试中局阶段"""
        from core.review import analyze_game_flow
        
        scores = [0] * 25
        result = analyze_game_flow(scores)
        
        assert result["phase"] == "中局"
    
    def test_endgame_phase(self):
        """测试残局阶段"""
        from core.review import analyze_game_flow
        
        scores = [0] * 50
        result = analyze_game_flow(scores)
        
        assert result["phase"] == "残局"
    
    def test_advantage_analysis(self):
        """测试优势分析"""
        from core.review import analyze_game_flow
        
        scores = [0, 100, 200, 300, 400]
        result = analyze_game_flow(scores)
        
        assert "红方" in result["advantage"]


class TestReportGeneration:
    """测试报告生成"""
    
    def test_generate_report(self):
        """测试生成完整报告"""
        from core.review import (
            GameRecord, generate_review_report, format_report_markdown
        )
        
        game = GameRecord(
            red_player="测试红方",
            black_player="测试黑方",
            result="1-0"
        )
        
        scores = [0, 100, 200, -300, -200, 500]
        
        report = generate_review_report(game, scores)
        
        assert report.overview is not None
        assert report.result_summary is not None
        assert len(report.score_history) == len(scores)
    
    def test_format_markdown(self):
        """测试Markdown格式化"""
        from core.review import (
            GameRecord, generate_review_report, format_report_markdown
        )
        
        game = GameRecord(
            red_player="红方",
            black_player="黑方",
            result="1-0"
        )
        
        scores = [0, 100, 200, -300, 500]
        report = generate_review_report(game, scores)
        markdown = format_report_markdown(report)
        
        assert "# 📊 复盘报告" in markdown
        assert "红方" in markdown


class TestChartGeneration:
    """测试图表生成"""
    
    def test_generate_simple_chart(self):
        """测试简单图表生成"""
        from core.review import generate_score_chart
        
        scores = [0, 100, 200, -100, 300]
        
        chart = generate_score_chart(scores)
        
        assert chart is not None
        assert chart.size[0] > 0
        assert chart.size[1] > 0
    
    def test_generate_chart_with_markers(self):
        """测试带标记的图表生成"""
        from core.review import generate_score_chart
        
        scores = [0, 100, -400, 200, 500]
        turning_points = [2, 4]
        blunders = [2]
        
        chart = generate_score_chart(
            scores, 
            turning_points=turning_points,
            blunders=blunders
        )
        
        assert chart is not None
    
    def test_generate_score_data(self):
        """测试图表数据生成"""
        from core.review import generate_score_data
        
        scores = [0, 100, 200, -100]
        data = generate_score_data(scores)
        
        assert "labels" in data
        assert "datasets" in data
        assert len(data["labels"]) == len(scores)
