"""可靠性架构重构回归测试。"""

from unittest.mock import MagicMock, patch

from core.llm.analysis_policy import choose_analysis_policy
from core.llm.agent_tools import AgentTools
from core.llm.contracts import AnalysisPolicyDecision, AnalysisStatus, ExpertFailureType
from core.llm.experts.base_expert import ExpertResult
from core.llm.multi_agent_orchestrator import MultiAgentOrchestrator, Synthesizer
from core.llm.reliable_client import ReliableLLMClient
from core.llm.thinking_templates import PhaseDetector


class DummyResponse:
    def __init__(self, status_code, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self):
        return self._payload


def test_reliable_client_retries_429_then_success():
    client = ReliableLLMClient(
        api_key="test-key",
        base_url="https://example.com",
        model="glm-5",
        max_retries=2,
        backoff_base=0,
    )

    responses = [
        DummyResponse(429, text="rate limited"),
        DummyResponse(200, payload={
            "choices": [{
                "message": {"content": "ok", "reasoning_content": "", "tool_calls": []},
                "finish_reason": "stop",
            }],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1},
        }),
    ]

    mock_session = MagicMock()
    mock_session.post.side_effect = responses

    with patch("core.llm.reliable_client.requests.Session", return_value=mock_session):
        with patch("core.llm.reliable_client.time.sleep"):
            result = client.complete(messages=[{"role": "user", "content": "hello"}])

    assert result.success is True
    assert result.content == "ok"
    assert result.retry_count == 1
    assert result.status == AnalysisStatus.DEGRADED


def test_reliable_client_fails_after_retries():
    client = ReliableLLMClient(
        api_key="test-key",
        base_url="https://example.com",
        model="glm-5",
        max_retries=1,
        backoff_base=0,
    )

    mock_session = MagicMock()
    mock_session.post.side_effect = [DummyResponse(503, text="down"), DummyResponse(503, text="down")]

    with patch("core.llm.reliable_client.requests.Session", return_value=mock_session):
        with patch("core.llm.reliable_client.time.sleep"):
            result = client.complete(messages=[{"role": "user", "content": "hello"}])

    assert result.success is False
    assert result.error_type == ExpertFailureType.API_HTTP
    assert result.retry_count == 1


def test_choose_analysis_policy_for_engine_question():
    decision = choose_analysis_policy(
        question="这步棋引擎评分和候选怎么理解？",
        tensions=[],
        phase_name="中局",
        engine_eval={"best": "h2e2"},
    )

    assert decision.selected_experts == ["engine", "strategy"]
    assert decision.parallelism >= 1


def test_choose_analysis_policy_for_opening_defaults_to_plan_and_eval():
    decision = choose_analysis_policy(
        question="现在开局应该怎么下",
        tensions=[],
        phase_name="开局",
        engine_eval={},
    )

    assert decision.selected_experts == ["strategy", "engine"]


def test_choose_analysis_policy_for_very_early_opening_prefers_single_strategy():
    decision = choose_analysis_policy(
        question="现在开局应该怎么下",
        tensions=[],
        phase_name="开局",
        engine_eval={},
        move_count=2,
    )

    assert decision.selected_experts == ["strategy"]
    assert decision.reason == "opening_low_cost_strategy_first"


def test_synthesizer_returns_degraded_text_when_insufficient_experts():
    synth = Synthesizer(api_key="test-key")
    synth.llm_client = MagicMock()

    result = synth.synthesize(
        tactics_result=ExpertResult(expert_name="tactics", finding="可用结论", details="...", success=True),
        strategy_result=ExpertResult(
            expert_name="strategy",
            finding="分析失败",
            details="",
            success=False,
            error="429",
            status=AnalysisStatus.FAILED,
            failure_type=ExpertFailureType.API_RATE_LIMIT,
        ),
        engine_result=ExpertResult(
            expert_name="engine",
            finding="策略裁剪未执行",
            details="",
            success=False,
            error="policy",
            status=AnalysisStatus.SKIPPED,
            failure_type=ExpertFailureType.POLICY_SKIPPED,
        ),
        user_question="请综合分析",
    )

    assert "降级分析" in result
    assert "缺失专家" in result
    synth.llm_client.stream_complete.assert_not_called()


def test_synthesizer_strips_step_noise_from_expert_details():
    synth = Synthesizer(api_key="test-key")

    block = synth._format_expert_block(
        "战术专家",
        ExpertResult(
            expert_name="tactics",
            finding="红方先手压力更大",
            details="[STEP: 扫描战术机会]\n## 1 扫描战术机会\n【局面扫描】\n红方可先手施压\n- 黑方中路薄弱",
            success=True,
        ),
    )

    assert "详情摘要：红方可先手施压 黑方中路薄弱" in block
    assert "[STEP:" not in block
    assert "## 1" not in block


def test_synthesizer_cleans_final_output_before_validation():
    synth = Synthesizer(api_key="test-key")
    synth.llm_client = MagicMock()
    synth.llm_client.stream_complete.return_value = MagicMock(
        success=True,
        error_message="",
        content=(
            "## 1 对齐三方断言\n"
            "[STEP: 识别三位专家的共识断言]\n"
            "【综合评估】红方优势明确。\n\n"
            "【证据基础】战术与引擎都支持红方先手。\n\n"
            "【对手处境】黑方需要先稳住中路。\n\n"
            "【共识分析】红方可继续扩张。\n\n"
            "【分歧解读】分歧主要在兑现路径。\n\n"
            "【教练建议】先稳步扩张，再考虑强制手。"
        ),
    )

    result = synth.synthesize(
        tactics_result=ExpertResult(expert_name="tactics", finding="红方优势", details="...", success=True),
        strategy_result=ExpertResult(expert_name="strategy", finding="红方空间更好", details="...", success=True),
        engine_result=ExpertResult(expert_name="engine", finding="引擎支持红方", details="...", success=True),
        user_question="这步为什么红方更舒服？",
    )

    assert "[STEP:" not in result
    assert "## 1" not in result
    assert "【综合评估】" in result
    assert "【教练建议】" in result


def test_fallback_synthesis_does_not_hardcode_double_cannon_story_for_opening():
    synth = Synthesizer(api_key="test-key")

    result = synth._build_fallback_synthesis(
        tactics_result=ExpertResult(expert_name="tactics", finding="当前仍在开局主线窗口", details="...", success=True),
        strategy_result=ExpertResult(expert_name="strategy", finding="应优先完成出子顺序", details="...", success=True),
        engine_result=ExpertResult(expert_name="engine", finding="不要轻易脱离熟悉定式", details="...", success=True),
        user_question="现在开局应该怎么下，是否还在中炮对屏风马主线里？",
    )

    assert "重炮阵型" not in result
    assert "开局主线" in result or "定式" in result


def test_analyze_position_strategy_ignores_cannon_battery_as_opening_focus():
    tools = AgentTools()
    static_result = MagicMock()

    class FakeTag:
        def __init__(self, name):
            self.name = name

    class FakeDetectedTag:
        def __init__(self, name):
            self.detected = True
            self.tag = FakeTag(name)

    static_result.tags = [
        FakeDetectedTag("phase_opening"),
        FakeDetectedTag("cannon_battery"),
        FakeDetectedTag("has_active_pieces"),
    ]

    with patch.object(tools.detector, "detect_static", return_value=static_result):
        result = tools.analyze_position_strategy(
            "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"
        )

    assert result.success is True
    assert "重炮阵型" not in result.data["key_features"]
    assert any("定式" in item or "主流" in item for item in result.data["suggested_plans"])


def test_orchestrator_uses_policy_selected_experts_only():
    orchestrator = MultiAgentOrchestrator(api_key="test-key")
    orchestrator.tactics_expert = MagicMock()
    orchestrator.strategy_expert = MagicMock()
    orchestrator.engine_expert = MagicMock()
    orchestrator.synthesizer = MagicMock()

    orchestrator.strategy_expert.analyze.return_value = ExpertResult(
        expert_name="strategy", finding="战略结论", details="...", success=True
    )
    orchestrator.engine_expert.analyze.return_value = ExpertResult(
        expert_name="engine", finding="引擎结论", details="...", success=True
    )
    orchestrator.synthesizer.synthesize.return_value = "综合结果"

    policy = AnalysisPolicyDecision(
        mode="multi",
        selected_experts=["strategy", "engine"],
        parallelism=1,
        reason="test-policy",
    )

    with patch("core.llm.multi_agent_orchestrator.choose_analysis_policy", return_value=policy):
        result = orchestrator.analyze_multi(
            fen="rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1",
            question="整体怎么看",
            evidence_map={"facts_rules": []},
            tag_summary=[],
            move_count=10,
            engine_eval={"best": "h2e2"},
        )

    assert result == "综合结果"
    orchestrator.tactics_expert.analyze.assert_not_called()
    assert orchestrator.strategy_expert.analyze.called
    assert orchestrator.engine_expert.analyze.called

    synth_kwargs = orchestrator.synthesizer.synthesize.call_args.kwargs
    assert synth_kwargs["tactics_result"].status == AnalysisStatus.SKIPPED


def test_orchestrator_uses_opening_fast_path_before_forced_multi():
    orchestrator = MultiAgentOrchestrator(api_key="test-key")
    orchestrator.tactics_expert = MagicMock()
    orchestrator.strategy_expert = MagicMock()
    orchestrator.engine_expert = MagicMock()
    orchestrator.synthesizer = MagicMock()

    events = []

    def collect(event_type, message):
        events.append((event_type, message))

    result = orchestrator.analyze(
        fen="rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1",
        question="分析刚才走的棋 h2e2，这步棋走得怎么样？",
        move="h2e2",
        move_history=["h2e2"],
        engine_eval={"cp": 36, "best": "h9g7"},
        on_thinking=collect,
        force_multi=True,
    )

    assert "【开局判断】" in result
    assert any(event_type == "dispatch_info" for event_type, _ in events)
    assert any(event_type == "expert_start" and '"strategy"' in payload for event_type, payload in events)
    assert any(event_type == "expert_start" and '"engine"' in payload for event_type, payload in events)
    orchestrator.tactics_expert.analyze.assert_not_called()
    orchestrator.strategy_expert.analyze.assert_not_called()
    orchestrator.engine_expert.analyze.assert_not_called()


def test_orchestrator_uses_opening_fast_path_for_clear_fen_only_opening():
    orchestrator = MultiAgentOrchestrator(api_key="test-key")
    orchestrator.tactics_expert = MagicMock()
    orchestrator.strategy_expert = MagicMock()
    orchestrator.engine_expert = MagicMock()

    result = orchestrator.analyze(
        fen="rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1",
        question="现在开局应该怎么下？",
        move_history=[],
        engine_eval={"cp": 12, "best": "h2e2"},
        on_thinking=lambda *_: None,
        force_multi=False,
    )

    assert "【开局判断】" in result
    orchestrator.tactics_expert.analyze.assert_not_called()
    orchestrator.strategy_expert.analyze.assert_not_called()
    orchestrator.engine_expert.analyze.assert_not_called()


def test_orchestrator_prefers_multi_path_when_streaming_is_enabled():
    orchestrator = MultiAgentOrchestrator(api_key="test-key")
    orchestrator.analyze_multi = MagicMock(return_value="综合结果")
    orchestrator.analyze_single = MagicMock(return_value="单链路结果")

    result = orchestrator.analyze(
        fen="2bakab2/4n4/4c4/p1p1p1p1p/2n6/2P1C1P2/P3P3P/2N1B4/4A4/2BAK1N2 w - - 0 1",
        question="这步为什么难下，应该先看什么矛盾？",
        move_history=[],
        evidence_map={"facts_rules": []},
        engine_eval={"cp": 0, "best": None},
        on_thinking=lambda *_: None,
        force_multi=False,
    )

    assert result == "综合结果"
    orchestrator.analyze_multi.assert_called_once()
    orchestrator.analyze_single.assert_not_called()


def test_phase_detector_without_history_does_not_overcall_middlegame_as_opening():
    phase = PhaseDetector.detect(
        "2bakab2/4n4/4c4/p1p1p1p1p/2n6/2P1C1P2/P3P3P/2N1B4/4A4/2BAK1N2 w - - 0 1",
        move_count=0,
        move_count_source="fen",
    )

    assert phase.phase_name == "中局"


def test_phase_detector_uses_stricter_rule_for_fen_only_move_count():
    phase = PhaseDetector.detect(
        "r1bakab1r/4n4/1cn1c1p1p/p1p1p3P/6P2/2P1C1N2/P3P4/1C4C2/4A4/RNBAKAB1R b - - 0 1",
        move_count=0,
        move_count_source="fen",
    )

    assert phase.phase_name == "中局"


def test_orchestrator_infers_move_count_from_fen_metadata():
    orchestrator = MultiAgentOrchestrator(api_key="test-key")

    inferred = orchestrator._infer_move_count(
        "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 8",
        move_count=0,
        move_history=[],
    )

    assert inferred == 8
