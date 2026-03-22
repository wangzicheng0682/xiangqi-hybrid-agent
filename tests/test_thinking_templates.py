"""
思维链模板测试

测试内容:
1. 阶段检测器 (PhaseDetector)
2. 开局分析器 (OpeningAnalyzer)
3. 思维模板构建器 (ThinkingTemplateBuilder)
4. 集成测试
"""

import pytest
from core.llm.thinking_templates import (
    GamePhase,
    PhaseInfo,
    PhaseDetector,
    OpeningAnalyzer,
    ThinkingTemplateBuilder,
    ThinkingTemplate,
    get_phase_aware_prompt,
    detect_phase,
    analyze_opening,
    get_opening_summary,
)


class TestPhaseDetector:
    """阶段检测器测试"""

    # 标准开局FEN（32子，完整棋盘）
    INITIAL_FEN = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"

    # 中局FEN（棋子减少）
    MIDDLEGAME_FEN = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 20"

    # 残局FEN（棋子少于14）
    ENDGAME_FEN = "4k4/9/9/9/9/9/9/9/9/4K4 w - - 0 50"

    def test_detect_opening(self):
        """测试开局检测"""
        phase_info = PhaseDetector.detect(self.INITIAL_FEN, move_count=5)

        assert phase_info.phase == GamePhase.OPENING
        assert phase_info.phase_name == "开局"
        assert phase_info.total_pieces == 32
        assert phase_info.is_opening() is True
        assert phase_info.is_middlegame() is False
        assert phase_info.is_endgame() is False

    def test_detect_opening_boundary(self):
        """测试开局边界条件（15回合）"""
        phase_info = PhaseDetector.detect(self.INITIAL_FEN, move_count=15)

        # 15回合且棋子>=26，应该是开局
        assert phase_info.phase == GamePhase.OPENING

    def test_detect_middlegame(self):
        """测试中局检测"""
        # 回合数超过15，棋子数在15-27之间
        phase_info = PhaseDetector.detect(self.MIDDLEGAME_FEN, move_count=20)

        assert phase_info.phase == GamePhase.MIDDLEGAME
        assert phase_info.phase_name == "中局"
        assert phase_info.is_middlegame() is True

    def test_detect_endgame(self):
        """测试残局检测"""
        phase_info = PhaseDetector.detect(self.ENDGAME_FEN, move_count=50)

        assert phase_info.phase == GamePhase.ENDGAME
        assert phase_info.phase_name == "残局"
        assert phase_info.total_pieces == 2  # 只有两个帅
        assert phase_info.is_endgame() is True

    def test_count_pieces(self):
        """测试棋子计数"""
        # 完整棋盘32子
        assert PhaseDetector._count_pieces(self.INITIAL_FEN) == 32

        # 只有双帅
        assert PhaseDetector._count_pieces(self.ENDGAME_FEN) == 2

    def test_convenience_function(self):
        """测试便捷函数"""
        phase_info = detect_phase(self.INITIAL_FEN, 5)
        assert phase_info.phase == GamePhase.OPENING


class TestOpeningAnalyzer:
    """开局分析器测试"""

    # 初始局面FEN
    INITIAL_FEN = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"

    # 中炮开局FEN（走了炮二平五）
    CENTER_CANNON_FEN = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"

    def test_analyze_returns_structure(self):
        """测试分析返回正确的结构"""
        result = OpeningAnalyzer.analyze(self.INITIAL_FEN, move_count=1)

        assert "phase" in result
        assert "move_count" in result
        assert "development" in result
        assert "center_control" in result
        assert "piece_activity" in result
        assert "initiative" in result

    def test_development_analysis(self):
        """测试出子效率分析"""
        result = OpeningAnalyzer.analyze(self.INITIAL_FEN, move_count=1)
        dev = result["development"]

        assert "red_developed" in dev
        assert "black_developed" in dev
        assert "advantage" in dev
        assert "difference" in dev

    def test_center_control_analysis(self):
        """测试中心控制分析"""
        result = OpeningAnalyzer.analyze(self.INITIAL_FEN, move_count=1)
        center = result["center_control"]

        assert "red_center_pieces" in center
        assert "black_center_pieces" in center
        assert "center_control" in center

    def test_piece_activity_analysis(self):
        """测试子力活跃度分析"""
        result = OpeningAnalyzer.analyze(self.INITIAL_FEN, move_count=1)
        activity = result["piece_activity"]

        assert "red_horses" in activity
        assert "black_horses" in activity
        assert "red_cannons" in activity
        assert "black_cannons" in activity
        assert "red_chariots" in activity
        assert "black_chariots" in activity

    def test_generate_summary(self):
        """测试生成摘要"""
        result = OpeningAnalyzer.analyze(self.INITIAL_FEN, move_count=1)
        summary = OpeningAnalyzer.generate_summary(result)

        assert "出子效率" in summary
        assert "中心控制" in summary
        assert "子力活跃" in summary
        assert "先手判断" in summary

    def test_convenience_functions(self):
        """测试便捷函数"""
        analysis = analyze_opening(self.INITIAL_FEN, 1)
        assert "phase" in analysis

        summary = get_opening_summary(self.INITIAL_FEN, 1)
        assert "出子效率" in summary


class TestThinkingTemplateBuilder:
    """思维模板构建器测试"""

    def test_get_opening_template(self):
        """测试获取开局模板"""
        template = ThinkingTemplateBuilder.get_template(GamePhase.OPENING)

        assert isinstance(template, ThinkingTemplate)
        assert template.phase_name == "开局"
        assert len(template.principles) == 5
        assert len(template.questions) > 0
        # 检查原则包含关键内容
        principles_str = "".join(template.principles)
        assert "出子" in principles_str or "大子" in principles_str

    def test_get_middlegame_template(self):
        """测试获取中局模板"""
        template = ThinkingTemplateBuilder.get_template(GamePhase.MIDDLEGAME)

        assert template.phase_name == "中局"
        assert len(template.principles) == 5
        assert "战术" in template.principles[0]

    def test_get_endgame_template(self):
        """测试获取残局模板"""
        template = ThinkingTemplateBuilder.get_template(GamePhase.ENDGAME)

        assert template.phase_name == "残局"
        assert len(template.principles) == 5
        assert "兵" in template.principles[0]

    def test_template_has_priority_tools(self):
        """测试模板有推荐工具"""
        for phase in [GamePhase.OPENING, GamePhase.MIDDLEGAME, GamePhase.ENDGAME]:
            template = ThinkingTemplateBuilder.get_template(phase)
            assert len(template.priority_tools) > 0


class TestGetPhaseAwarePrompt:
    """阶段感知Prompt测试"""

    INITIAL_FEN = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"

    def test_returns_tuple(self):
        """测试返回元组"""
        result = get_phase_aware_prompt(self.INITIAL_FEN, move_count=5)

        assert len(result) == 3
        prompt, phase_info, phase_analysis = result

        assert isinstance(prompt, str)
        assert isinstance(phase_info, PhaseInfo)
        assert isinstance(phase_analysis, dict)

    def test_opening_prompt_contains_analysis(self):
        """测试开局Prompt包含分析数据"""
        prompt, phase_info, phase_analysis = get_phase_aware_prompt(
            self.INITIAL_FEN, move_count=5
        )

        assert phase_info.is_opening()
        assert "开局" in prompt
        assert "出子效率" in prompt or "出子" in prompt
        assert len(phase_analysis) > 0

    def test_with_base_prompt(self):
        """测试带基础Prompt"""
        base = "你是象棋教练。"
        prompt, _, _ = get_phase_aware_prompt(
            self.INITIAL_FEN, move_count=5, base_prompt=base
        )

        assert "你是象棋教练" in prompt
        assert "开局" in prompt

    def test_non_opening_no_extra_analysis(self):
        """测试非开局阶段没有额外分析"""
        endgame_fen = "4k4/9/9/9/9/9/9/9/9/4K4 w - - 0 50"
        prompt, phase_info, phase_analysis = get_phase_aware_prompt(
            endgame_fen, move_count=50
        )

        assert phase_info.is_endgame()
        # 非开局阶段，phase_analysis应该为空
        assert phase_analysis == {}


class TestIntegration:
    """集成测试"""

    def test_full_workflow(self):
        """测试完整工作流"""
        fen = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"

        # 1. 检测阶段
        phase_info = detect_phase(fen, move_count=3)
        assert phase_info.is_opening()

        # 2. 执行开局分析
        analysis = analyze_opening(fen, move_count=3)
        assert "development" in analysis

        # 3. 获取摘要
        summary = get_opening_summary(fen, move_count=3)
        assert len(summary) > 0

        # 4. 获取阶段感知Prompt
        prompt, _, _ = get_phase_aware_prompt(fen, move_count=3)
        assert "开局" in prompt


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
