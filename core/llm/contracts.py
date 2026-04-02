"""LLM 分析链路的结构化状态与错误码。"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class AnalysisStatus:
    SUCCESS = "success"
    DEGRADED = "degraded"
    PARTIAL = "partial"
    FAILED = "failed"
    SKIPPED = "skipped"


class ExpertFailureType:
    API_RATE_LIMIT = "api_rate_limit"
    API_HTTP = "api_http"
    REQUEST_EXCEPTION = "request_exception"
    TOOL_TIMEOUT = "tool_timeout"
    TOOL_ERROR = "tool_error"
    INVALID_RESPONSE = "invalid_response"
    POLICY_SKIPPED = "policy_skipped"
    UNKNOWN = "unknown"


class DegradationLevel:
    NONE = "none"
    RETRIED = "retried"
    SERIALIZED = "serialized"
    PARTIAL_EXPERTS = "partial_experts"
    SINGLE_EXPERT = "single_expert"
    SYNTHESIS_BYPASSED = "synthesis_bypassed"


@dataclass
class ReliabilityInfo:
    status: str = AnalysisStatus.SUCCESS
    error_type: Optional[str] = None
    error_message: str = ""
    retry_count: int = 0
    degraded: bool = False
    degradation_level: str = DegradationLevel.NONE
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AnalysisPolicyDecision:
    mode: str
    selected_experts: List[str]
    parallelism: int
    reason: str
    degradation_level: str = DegradationLevel.NONE
