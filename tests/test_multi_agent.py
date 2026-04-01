"""
多Agent系统测试用例

覆盖范围：
1. 自适应决策逻辑（should_use_multi_agent）
2. 专家配置正确性
3. 异常处理和降级逻辑
4. 阶段检测（PhaseDetector）
5. 张力检测（detect_tensions）
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestAdaptiveDecision:
    """测试自适应决策逻辑"""

    def test_force_multi_with_depth_request(self):
        """用户要求深度分析 → 多Agent"""
        from core.llm.experts.base_expert import should_use_multi_agent

        result = should_use_multi_agent(
            tensions=[],
            phase_name="开局",
            user_request="深度分析这个局面"
        )
        assert result is True

    def test_force_multi_with_detailed_request(self):
        """用户要求详细分析 → 多Agent"""
        from core.llm.experts.base_expert import should_use_multi_agent

        result = should_use_multi_agent(
            tensions=[],
            phase_name="开局",
            user_request="请详细讲解"
        )
        assert result is True

    def test_simple_opening_no_tension_single_agent(self):
        """开局无张力 → 单Agent"""
        from core.llm.experts.base_expert import should_use_multi_agent

        result = should_use_multi_agent(
            tensions=[],
            phase_name="开局",
            user_request="这步棋怎么样"
        )
        assert result is False

    def test_critical_priority_multi_agent(self):
        """CRITICAL张力 → 多Agent"""
        from core.llm.experts.base_expert import should_use_multi_agent

        result = should_use_multi_agent(
            tensions=[{"priority": "CRITICAL", "tension_type": "HIDDEN_IMBALANCE"}],
            phase_name="中局",
            user_request="这步棋怎么样"
        )
        assert result is True

    def test_three_or_more_tensions_multi_agent(self):
        """张力数量>=3 → 多Agent"""
        from core.llm.experts.base_expert import should_use_multi_agent

        result = should_use_multi_agent(
            tensions=[
                {"priority": "HIGH", "tension_type": "A"},
                {"priority": "MEDIUM", "tension_type": "B"},
                {"priority": "LOW", "tension_type": "C"},
            ],
            phase_name="中局",
            user_request="这步棋怎么样"
        )
        assert result is True

    def test_two_tensions_single_agent(self):
        """张力<=2 → 单Agent"""
        from core.llm.experts.base_expert import should_use_multi_agent

        result = should_use_multi_agent(
            tensions=[
                {"priority": "HIGH", "tension_type": "A"},
                {"priority": "MEDIUM", "tension_type": "B"},
            ],
            phase_name="中局",
            user_request="这步棋怎么样"
        )
        assert result is False


class TestExpertConfig:
    """测试专家配置"""

    def test_tactics_expert_has_correct_tools(self):
        """战术专家配置了正确的工具"""
        from core.llm.experts.tactics_expert import TacticsExpert, TACTICS_TOOLS

        tool_names = [t["function"]["name"] for t in TACTICS_TOOLS]
        assert "get_piece_attacks" in tool_names
        assert "get_piece_defenders" in tool_names
        assert "get_threats_to_piece" in tool_names
        assert "get_piece_relations" in tool_names
        assert "analyze_move" in tool_names
        assert "get_forcing_sequence" in tool_names

    def test_strategy_expert_has_correct_tools(self):
        """战略专家配置了正确的工具"""
        from core.llm.experts.strategy_expert import StrategyExpert, STRATEGY_TOOLS

        tool_names = [t["function"]["name"] for t in STRATEGY_TOOLS]
        assert "analyze_position_strategy" in tool_names
        assert "compare_moves" in tool_names
        assert "get_piece_attacks" in tool_names
        assert "get_piece_relations" in tool_names

    def test_engine_expert_has_correct_tools(self):
        """引擎专家配置了正确的工具"""
        from core.llm.experts.engine_expert import EngineExpert, ENGINE_TOOLS

        tool_names = [t["function"]["name"] for t in ENGINE_TOOLS]
        assert "engine_deep_analysis" in tool_names
        assert "engine_alternatives" in tool_names
        assert "analyze_move" in tool_names
        assert "compare_moves" in tool_names

    def test_expert_config_max_tokens(self):
        """专家配置了足够的max_tokens"""
        from core.llm.experts.tactics_expert import TacticsExpert
        from core.llm.experts.strategy_expert import StrategyExpert
        from core.llm.experts.engine_expert import EngineExpert

        assert TacticsExpert.CONFIG.max_tokens >= 1024
        assert StrategyExpert.CONFIG.max_tokens >= 1024
        assert EngineExpert.CONFIG.max_tokens >= 1024

    def test_expert_config_max_rounds(self):
        """专家配置了合理的max_rounds"""
        from core.llm.experts.tactics_expert import TacticsExpert
        from core.llm.experts.strategy_expert import StrategyExpert
        from core.llm.experts.engine_expert import EngineExpert

        assert TacticsExpert.CONFIG.max_rounds >= 3
        assert StrategyExpert.CONFIG.max_rounds >= 2
        assert EngineExpert.CONFIG.max_rounds >= 2


class TestPhaseDetector:
    """测试阶段检测"""

    def test_opening_detection(self):
        """开局判断"""
        from core.llm.thinking_templates import PhaseDetector

        fen = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"
        phase = PhaseDetector.detect(fen, move_count=5)

        assert phase.phase_name == "开局"
        assert phase.total_pieces == 32

    def test_endgame_detection(self):
        """残局判断"""
        from core.llm.thinking_templates import PhaseDetector

        # 只剩将和一个兵
        fen = "k9/4a4/9/9/9/9/9/9/9/4K4 w - - 0 1"
        phase = PhaseDetector.detect(fen, move_count=60)

        assert phase.phase_name == "残局"
        assert phase.total_pieces <= 14

    def test_middlegame_detection(self):
        """中局判断"""
        from core.llm.thinking_templates import PhaseDetector

        # 中局棋子数
        fen = "r1r3rk1/4a1c2/p1n1p1p1p/1p1n1p3/P1R1P4/2N1B4/3N1C3/3A1R3/4AK2R b - - 0 20"
        phase = PhaseDetector.detect(fen, move_count=20)

        assert phase.phase_name == "中局"


class TestExpertResult:
    """测试 ExpertResult 数据类"""

    def test_expert_result_creation(self):
        """正确创建 ExpertResult"""
        from core.llm.experts.base_expert import ExpertResult

        result = ExpertResult(
            expert_name="tactics",
            finding="红方占优",
            details="红方子力活跃...",
            tool_calls=[{"name": "get_piece_attacks", "round": 0}],
            success=True,
            error=None
        )

        assert result.expert_name == "tactics"
        assert result.finding == "红方占优"
        assert result.success is True
        assert result.error is None
        assert len(result.tool_calls) == 1

    def test_expert_result_failure(self):
        """失败的 ExpertResult"""
        from core.llm.experts.base_expert import ExpertResult

        result = ExpertResult(
            expert_name="tactics",
            finding="分析失败",
            details="",
            success=False,
            error="API超时"
        )

        assert result.success is False
        assert result.error == "API超时"


class TestOrchestratorExceptionHandling:
    """测试 Orchestrator 异常处理"""

    def test_single_expert_failure_returns_fallback_result(self):
        """单个专家失败时返回降级结果"""
        from core.llm.multi_agent_orchestrator import MultiAgentOrchestrator
        from core.llm.experts.base_expert import ExpertResult

        # Mock 战术专家失败
        with patch("core.llm.multi_agent_orchestrator.TacticsExpert") as MockTactics:
            with patch("core.llm.multi_agent_orchestrator.StrategyExpert") as MockStrategy:
                with patch("core.llm.multi_agent_orchestrator.EngineExpert") as MockEngine:
                    with patch("core.llm.multi_agent_orchestrator.Synthesizer") as MockSynth:

                        # 模拟失败
                        MockTactics.return_value.analyze.side_effect = Exception("Network error")
                        MockTactics.return_value.analyze.return_value = ExpertResult(
                            expert_name="tactics",
                            finding="执行失败",
                            details="",
                            success=False,
                            error="Network error"
                        )

                        # 其他专家成功
                        MockStrategy.return_value.analyze.return_value = ExpertResult(
                            expert_name="strategy",
                            finding="红方主动",
                            details="...",
                            success=True
                        )
                        MockEngine.return_value.analyze.return_value = ExpertResult(
                            expert_name="engine",
                            finding="评估+50cp",
                            details="...",
                            success=True
                        )

                        # 合成器返回结果
                        MockSynth.return_value.synthesize.return_value = "综合讲解：红方占优"

                        orchestrator = MultiAgentOrchestrator()
                        orchestrator.tactics_expert = MockTactics.return_value
                        orchestrator.strategy_expert = MockStrategy.return_value
                        orchestrator.engine_expert = MockEngine.return_value
                        orchestrator.synthesizer = MockSynth.return_value

                        def noop(*args, **kwargs): pass

                        result = orchestrator.analyze_multi(
                            fen="rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1",
                            question="这步棋怎么样",
                            on_thinking=noop
                        )

                        # 战术失败但其他成功，合成器仍然输出结果
                        assert result == "综合讲解：红方占优"


class TestBoardLayout:
    """测试棋盘布局生成"""

    def test_generate_board_layout(self):
        """正确解析FEN生成棋盘布局"""
        from core.llm.experts.tactics_expert import TacticsExpert

        expert = TacticsExpert()
        fen = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"
        layout = expert._generate_board_layout(fen)

        assert "红方棋子" in layout
        assert "黑方棋子" in layout
        assert "红帅" in layout
        assert "黑将" in layout

    def test_generate_board_layout_with_pieces(self):
        """验证具体棋子位置"""
        from core.llm.experts.tactics_expert import TacticsExpert

        expert = TacticsExpert()
        # 简单局面：只剩将和帅
        fen = "4k4/9/9/9/9/9/9/9/9/4K4 w - - 0 1"
        layout = expert._generate_board_layout(fen)

        assert "红帅" in layout
        assert "黑将" in layout


class TestSharedContext:
    """测试共享上下文构建"""

    def test_build_context_with_phase_info(self):
        """phase_info 被正确注入上下文"""
        from core.llm.experts.tactics_expert import TacticsExpert
        from core.llm.thinking_templates import PhaseInfo, GamePhase

        expert = TacticsExpert()
        phase_info = PhaseInfo(
            phase=GamePhase.MIDDLEGAME,
            phase_name="中局",
            move_count=25,
            total_pieces=20
        )

        context = expert._build_shared_context(
            fen="rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1",
            tag_summary=["is_check: 红方正在将军"],
            primary_tension={"tension_type": "CHECK", "priority": "CRITICAL", "question": "如何应对将军"},
            phase_info=phase_info,
            question="这步棋怎么样"
        )

        assert "中局" in context
        assert "回合数≈25" in context
        assert "剩余棋子≈20" in context

    def test_build_context_with_tension(self):
        """张力信息被正确注入"""
        from core.llm.experts.tactics_expert import TacticsExpert

        expert = TacticsExpert()
        context = expert._build_shared_context(
            fen="rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1",
            tag_summary=[],
            primary_tension={
                "tension_type": "HIDDEN_IMBALANCE",
                "priority": "HIGH",
                "question": "子力兑换时机",
                "hypothesis": "红方子力占优"
            },
            phase_info=None,
            question="这步棋怎么样"
        )

        assert "HIDDEN_IMBALANCE" in context
        assert "子力兑换时机" in context


class TestSynthesizerPrompt:
    """测试合成器 System Prompt"""

    def test_synthesizer_has_conflict_resolution_rules(self):
        """合成器定义了冲突解决规则"""
        from core.llm.multi_agent_orchestrator import SYNTHESIZER_SYSTEM_PROMPT

        assert "战术发现优先" in SYNTHESIZER_SYSTEM_PROMPT
        assert "引擎评估 vs 战术发现" in SYNTHESIZER_SYSTEM_PROMPT
        assert "对手处境" in SYNTHESIZER_SYSTEM_PROMPT  # 必须分析对手

    def test_synthesizer_output_format(self):
        """合成器定义了输出格式"""
        from core.llm.multi_agent_orchestrator import SYNTHESIZER_SYSTEM_PROMPT

        assert "【综合评估】" in SYNTHESIZER_SYSTEM_PROMPT
        assert "【共识分析】" in SYNTHESIZER_SYSTEM_PROMPT
        assert "【分歧解读】" in SYNTHESIZER_SYSTEM_PROMPT
        assert "【教练建议】" in SYNTHESIZER_SYSTEM_PROMPT


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
