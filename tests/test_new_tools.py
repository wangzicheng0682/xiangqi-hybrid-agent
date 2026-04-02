"""
测试新增工具：simulate_move, query_chess_principles

以及 Evidence Map 结构化管线的正确性。
"""

import pytest
from core.llm.agent_tools import AgentTools, ToolResult


@pytest.fixture
def tools():
    return AgentTools()


# =============================================================================
# simulate_move 工具测试
# =============================================================================

class TestSimulateMove:
    """测试走法模拟工具"""

    def test_simulate_capture_move(self, tools):
        """模拟吃子走法，应检测到子力变化"""
        # 红车在(5,2)，黑马在(5,5)，红车吃黑马
        fen = "4k4/9/9/9/4n4/4R4/9/9/9/4K4 w - - 0 1"
        result = tools.simulate_move(fen, "e4e5")  # 红车上吃黑马
        assert result.success
        assert result.data["captured"] is not None
        assert result.data["captured"]["piece"] is not None

    def test_simulate_check_move(self, tools):
        """模拟将军走法"""
        fen = "4k4/9/9/9/9/9/9/4R4/9/4K4 w - - 0 1"
        result = tools.simulate_move(fen, "e2e8")  # 红车到e8将军
        assert result.success
        # 应该检测到将军
        assert result.data["gives_check"] is True

    def test_simulate_invalid_move(self, tools):
        """无效走法应返回失败"""
        fen = "4k4/9/9/9/9/9/9/9/9/4K4 w - - 0 1"
        result = tools.simulate_move(fen, "a0a1")  # 不存在的走法
        # 在空位起步应该报错
        assert not result.success or result.data.get("captured") is None

    def test_simulate_tag_diff(self, tools):
        """走棋前后标签差异应正确反映"""
        # 初始局面
        fen = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"
        candidates = tools.get_move_candidates(fen)
        assert candidates.success

        result = tools.simulate_move(fen, candidate_id=candidates.data["candidates"][0]["candidate_id"])
        assert result.success
        assert "fen_after" in result.data
        assert isinstance(result.data["tags_before"], list)
        assert isinstance(result.data["tags_after"], list)

    def test_simulate_returns_fen_after(self, tools):
        """走棋后应返回新FEN"""
        fen = "4k4/9/9/9/9/4R4/9/9/9/4K4 w - - 0 1"
        result = tools.simulate_move(fen, "e4e9")
        assert result.success
        assert result.data["fen_after"]
        # 新FEN应表示黑方走棋
        assert " b " in result.data["fen_after"]

    def test_simulate_move_with_candidate_id(self, tools):
        """simulate_move 应支持 candidate_id 协议"""
        fen = "4k4/9/9/9/4n4/4R4/9/9/9/4K4 w - - 0 1"
        candidates = tools.get_move_candidates(fen)
        assert candidates.success
        capture_candidate = next(
            candidate for candidate in candidates.data["candidates"]
            if candidate["move"] == "e4e5"
        )

        result = tools.simulate_move(fen, candidate_id=capture_candidate["candidate_id"])
        assert result.success
        assert result.data["candidate_id"] == capture_candidate["candidate_id"]
        assert result.data["move"] == "e4e5"
        assert result.data["captured"] is not None


class TestMoveCandidateProtocol:
    """测试 candidate_id 受约束协议"""

    def test_get_move_candidates_returns_stable_ids(self, tools):
        """候选列表应返回稳定 candidate_id"""
        fen = "4k4/9/9/9/4n4/4R4/9/9/9/4K4 w - - 0 1"

        first = tools.get_move_candidates(fen)
        second = tools.get_move_candidates(fen)

        assert first.success
        assert second.success
        assert first.data["candidates"] == second.data["candidates"]
        assert first.data["count"] > 0
        assert first.data["candidates"][0]["candidate_id"].startswith("cand_")

    def test_analyze_move_with_candidate_id(self, tools):
        """analyze_move 应优先解析 candidate_id"""
        fen = "4k4/9/9/9/4n4/4R4/9/9/9/4K4 w - - 0 1"
        candidates = tools.get_move_candidates(fen)
        capture_candidate = next(
            candidate for candidate in candidates.data["candidates"]
            if candidate["move"] == "e4e5"
        )

        result = tools.analyze_move(fen, candidate_id=capture_candidate["candidate_id"])

        assert result.success
        assert result.data["candidate_id"] == capture_candidate["candidate_id"]
        assert result.data["resolved_move"] == "e4e5"
        assert result.data["quality"] in {"excellent", "good", "ok", "blunder"}

    def test_compare_moves_with_candidate_ids(self, tools):
        """compare_moves 应支持 candidate_ids 列表"""
        fen = "4k4/9/9/9/4n4/4R4/9/9/9/R3K4 w - - 0 1"
        candidates = tools.get_move_candidates(fen)
        selected = [
            candidate["candidate_id"]
            for candidate in candidates.data["candidates"]
            if candidate["move"] in {"e4e5", "a0a1"}
        ]

        result = tools.compare_moves(fen, candidate_ids=selected)

        assert result.success
        assert result.data["candidate_ids"] == selected
        assert len(result.data["comparisons"]) == len(selected)
        assert result.data["best"] in {comparison["move"] for comparison in result.data["comparisons"]}

    def test_get_forcing_sequence_with_candidate_id(self, tools):
        """get_forcing_sequence 应支持 candidate_id"""
        fen = "4k4/9/9/9/9/9/9/4R4/9/4K4 w - - 0 1"
        candidates = tools.get_move_candidates(fen)
        checking_candidate = candidates.data["candidates"][0]

        result = tools.get_forcing_sequence(fen, candidate_id=checking_candidate["candidate_id"], depth=2)

        assert result.success
        assert isinstance(result.data["sequence"], list)
        assert result.data["depth_analyzed"] >= 1

    def test_invalid_candidate_id_returns_failure(self, tools):
        """非法 candidate_id 应显式失败"""
        fen = "4k4/9/9/9/9/9/9/4R4/9/4K4 w - - 0 1"

        result = tools.analyze_move(fen, candidate_id="cand_999")

        assert not result.success
        assert "candidate_id" in result.message


# =============================================================================
# query_chess_principles 工具测试
# =============================================================================

class TestQueryChessPrinciples:
    """测试棋理知识检索工具"""

    def test_query_with_tension_type(self, tools):
        """根据张力类型查询应返回原则"""
        fen = "4k4/9/9/9/9/9/9/9/9/4K4 w - - 0 1"
        result = tools.query_chess_principles(fen, tension_type="material_vs_initiative")
        assert result.success
        assert result.data["count"] > 0
        assert len(result.data["principles"]) > 0

    def test_query_general_principles(self, tools):
        """不指定张力类型应返回通用原则"""
        fen = "4k4/9/9/9/9/9/9/9/9/4K4 w - - 0 1"
        result = tools.query_chess_principles(fen)
        assert result.success
        assert result.data["count"] > 0

    def test_query_hidden_imbalance(self, tools):
        """查询hidden_imbalance张力的原则"""
        fen = "4k4/9/9/9/9/9/9/9/9/4K4 w - - 0 1"
        result = tools.query_chess_principles(fen, tension_type="hidden_imbalance")
        assert result.success
        assert result.data["count"] > 0

    def test_query_sleeping_piece(self, tools):
        """查询sleeping_piece张力的原则"""
        fen = "4k4/9/9/9/9/9/9/9/9/4K4 w - - 0 1"
        result = tools.query_chess_principles(fen, tension_type="sleeping_piece")
        assert result.success
        assert any("炮" in p.get("content", "") or "车" in p.get("content", "") or "棋子" in p.get("content", "")
                    for p in result.data["principles"])

    def test_query_unknown_tension(self, tools):
        """未知张力类型应返回通用原则"""
        fen = "4k4/9/9/9/9/9/9/9/9/4K4 w - - 0 1"
        result = tools.query_chess_principles(fen, tension_type="nonexistent_type")
        assert result.success
        # 至少有通用原则
        assert result.data["count"] > 0


# =============================================================================
# Evidence Map 结构化管线测试
# =============================================================================

class TestStructuredEvidenceMap:
    """测试结构化Evidence Map构建"""

    def test_build_evidence_map_basic(self):
        """基本Evidence Map构建"""
        from core.llm.multi_agent_orchestrator import MultiAgentOrchestrator
        from core.llm.thinking_templates import PhaseDetector

        orch = MultiAgentOrchestrator.__new__(MultiAgentOrchestrator)
        fen = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"
        phase_info = PhaseDetector.detect(fen, 0)

        evidence_map = {
            "facts_rules": [
                {"tag": "phase_opening", "confidence": 1.0, "bind_pieces": [], "description": "开局阶段"},
            ]
        }

        result = orch._build_structured_evidence_map(
            fen=fen,
            evidence_map=evidence_map,
            phase_info=phase_info,
        )

        assert result["phase"] == "开局"
        assert len(result["tags"]) == 1
        assert result["tags"][0]["name"] == "phase_opening"
        assert result["piece_count"]["red"] > 0
        assert result["piece_count"]["black"] > 0

    def test_build_evidence_map_with_engine(self):
        """包含引擎评估的Evidence Map"""
        from core.llm.multi_agent_orchestrator import MultiAgentOrchestrator
        from core.llm.thinking_templates import PhaseDetector

        orch = MultiAgentOrchestrator.__new__(MultiAgentOrchestrator)
        fen = "4k4/9/9/9/4n4/4R4/9/9/9/4K4 w - - 0 1"
        phase_info = PhaseDetector.detect(fen, 30)

        engine_eval = {"cp": 150, "best": "e4e5", "pv": ["e4e5", "d9e9"]}

        result = orch._build_structured_evidence_map(
            fen=fen,
            engine_eval=engine_eval,
            phase_info=phase_info,
        )

        assert result["engine"]["cp"] == 150
        assert result["engine"]["best"] == "e4e5"

    def test_build_evidence_map_with_tensions(self):
        """包含张力的Evidence Map"""
        from core.llm.multi_agent_orchestrator import MultiAgentOrchestrator
        from core.llm.thinking_templates import PhaseDetector

        orch = MultiAgentOrchestrator.__new__(MultiAgentOrchestrator)
        fen = "4k4/9/9/9/9/9/9/9/9/4K4 w - - 0 1"
        phase_info = PhaseDetector.detect(fen, 60)

        tensions = [
            {"tension_type": "hidden_imbalance", "priority": "HIGH", "description": "评估异常"}
        ]

        result = orch._build_structured_evidence_map(
            fen=fen,
            phase_info=phase_info,
            tensions=tensions,
        )

        assert len(result["tensions"]) == 1
        assert result["tensions"][0]["type"] == "hidden_imbalance"

    def test_piece_count_accuracy(self):
        """子力统计应准确"""
        from core.llm.multi_agent_orchestrator import MultiAgentOrchestrator
        from core.llm.thinking_templates import PhaseDetector

        orch = MultiAgentOrchestrator.__new__(MultiAgentOrchestrator)
        # 红方: K, R = 2子, 黑方: k = 1子
        fen = "4k4/9/9/9/9/9/9/4R4/9/4K4 w - - 0 1"
        phase_info = PhaseDetector.detect(fen, 50)

        result = orch._build_structured_evidence_map(fen=fen, phase_info=phase_info)

        assert result["piece_count"]["red"] == 2
        assert result["piece_count"]["black"] == 1


# =============================================================================
# 专家上下文构建测试
# =============================================================================

class TestExpertContextBuilding:
    """测试专家上下文构建"""

    def test_shared_context_with_evidence_map(self):
        """带Evidence Map的上下文应包含结构化标签"""
        from core.llm.experts.base_expert import BaseExpert

        expert = BaseExpert.__new__(BaseExpert)
        expert.PIECE_NAMES = BaseExpert.PIECE_NAMES

        evidence_map = {
            "tags": [
                {"name": "is_check", "bind_pieces": ["红车-(5,2)", "黑将-(4,0)"], "description": "将军"},
            ],
            "engine": {"cp": 200, "best": "e2e9"},
            "piece_count": {"red": 5, "black": 3},
        }

        context = expert._build_shared_context(
            fen="4k4/9/9/9/9/9/9/4R4/9/4K4 w - - 0 1",
            tag_summary=[],
            primary_tension={},
            phase_info=None,
            question="分析这个局面",
            evidence_map=evidence_map,
        )

        assert "Evidence Map" in context
        assert "is_check" in context
        assert "红车-(5,2)" in context
        assert "评估分: 200cp" in context
        assert "红方5子" in context

    def test_shared_context_backward_compatible(self):
        """无Evidence Map时应回退到tag_summary"""
        from core.llm.experts.base_expert import BaseExpert

        expert = BaseExpert.__new__(BaseExpert)
        expert.PIECE_NAMES = BaseExpert.PIECE_NAMES

        context = expert._build_shared_context(
            fen="4k4/9/9/9/9/9/9/9/9/4K4 w - - 0 1",
            tag_summary=["is_check: 红车将军黑将"],
            primary_tension={},
            phase_info=None,
            question="分析这个局面",
        )

        assert "局面事实" in context
        assert "is_check" in context


# =============================================================================
# Engine Pool 测试
# =============================================================================

class TestEnginePool:
    """测试引擎连接池"""

    def test_singleton(self):
        """连接池应为单例"""
        from core.engine.pool import EnginePool
        pool1 = EnginePool.get_pool()
        pool2 = EnginePool.get_pool()
        assert pool1 is pool2
