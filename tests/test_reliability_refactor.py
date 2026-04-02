"""可靠性架构重构回归测试。"""

from unittest.mock import MagicMock, patch

from core.llm.analysis_policy import choose_analysis_policy
from core.llm.contracts import AnalysisPolicyDecision, AnalysisStatus, ExpertFailureType
from core.llm.experts.base_expert import ExpertResult
from core.llm.multi_agent_orchestrator import MultiAgentOrchestrator, Synthesizer
from core.llm.reliable_client import ReliableLLMClient


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
