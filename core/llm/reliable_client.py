"""统一的高可靠 LLM 调用客户端。"""

import json
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

import requests

from core.llm.contracts import AnalysisStatus, DegradationLevel, ExpertFailureType


RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


@dataclass
class ReliableLLMResponse:
    content: str = ""
    reasoning_content: str = ""
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    finish_reason: str = "stop"
    success: bool = True
    status: str = AnalysisStatus.SUCCESS
    error_type: Optional[str] = None
    error_message: str = ""
    retry_count: int = 0
    degraded: bool = False
    degradation_level: str = DegradationLevel.NONE
    metadata: Dict[str, Any] = field(default_factory=dict)


class ReliableLLMClient:
    _semaphore_lock = threading.Lock()
    _request_semaphore = None
    _failure_lock = threading.Lock()
    _consecutive_failures = 0

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        timeout: int = 120,
        max_retries: int = 2,
        backoff_base: float = 1.0,
    ):
        self.api_key = api_key or os.getenv("ALIYUN_API_KEY")
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self._ensure_semaphore()

    @classmethod
    def _ensure_semaphore(cls) -> None:
        with cls._semaphore_lock:
            target = max(1, int(os.getenv("LLM_MAX_PARALLEL_REQUESTS", "4")))
            if cls._request_semaphore is None or getattr(cls._request_semaphore, "_initial_value", None) != target:
                semaphore = threading.BoundedSemaphore(target)
                semaphore._initial_value = target  # type: ignore[attr-defined]
                cls._request_semaphore = semaphore

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _classify_error(self, status_code: Optional[int], exception: Optional[Exception]) -> str:
        if status_code == 429:
            return ExpertFailureType.API_RATE_LIMIT
        if status_code is not None:
            return ExpertFailureType.API_HTTP
        if exception is not None:
            return ExpertFailureType.REQUEST_EXCEPTION
        return ExpertFailureType.UNKNOWN

    def _should_retry(self, status_code: Optional[int], exception: Optional[Exception], attempt: int) -> bool:
        if attempt >= self.max_retries:
            return False
        if status_code in RETRYABLE_STATUS_CODES:
            return True
        if exception is not None:
            return True
        return False

    def _register_success(self) -> None:
        with self._failure_lock:
            self._consecutive_failures = 0

    @classmethod
    def _register_failure(cls) -> None:
        with cls._failure_lock:
            cls._consecutive_failures += 1

    @classmethod
    def _circuit_open(cls) -> bool:
        threshold = max(3, int(os.getenv("LLM_CIRCUIT_BREAKER_THRESHOLD", "12")))
        with cls._failure_lock:
            return cls._consecutive_failures >= threshold

    def _build_payload(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]],
        temperature: float,
        max_tokens: int,
        thinking_enabled: bool,
        stream: bool,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }
        if thinking_enabled:
            payload["thinking"] = {"type": "enabled"}
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        return payload

    def complete(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        thinking_enabled: bool = False,
    ) -> ReliableLLMResponse:
        if not self.api_key:
            return ReliableLLMResponse(
                success=False,
                status=AnalysisStatus.FAILED,
                error_type=ExpertFailureType.REQUEST_EXCEPTION,
                error_message="API Key未配置",
                finish_reason="error",
            )

        if self._circuit_open():
            return ReliableLLMResponse(
                success=False,
                status=AnalysisStatus.FAILED,
                error_type=ExpertFailureType.REQUEST_EXCEPTION,
                error_message="LLM circuit breaker open",
                finish_reason="error",
                degraded=True,
                degradation_level=DegradationLevel.SERIALIZED,
            )

        payload = self._build_payload(messages, tools, temperature, max_tokens, thinking_enabled, stream=False)
        last_status = None
        last_exception: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            status_code = None
            last_exception = None
            try:
                with self._request_semaphore:
                    session = requests.Session()
                    session.trust_env = False
                    response = session.post(
                        f"{self.base_url}/chat/completions",
                        headers=self._headers(),
                        json=payload,
                        timeout=self.timeout,
                    )
                status_code = response.status_code
                last_status = status_code
                if status_code == 200:
                    result = response.json()
                    choice = result.get("choices", [{}])[0]
                    message = choice.get("message", {})
                    self._register_success()
                    return ReliableLLMResponse(
                        content=message.get("content", ""),
                        reasoning_content=message.get("reasoning_content", ""),
                        tool_calls=message.get("tool_calls", []),
                        finish_reason=choice.get("finish_reason", "stop"),
                        success=True,
                        status=AnalysisStatus.DEGRADED if attempt > 0 else AnalysisStatus.SUCCESS,
                        retry_count=attempt,
                        degraded=attempt > 0,
                        degradation_level=DegradationLevel.RETRIED if attempt > 0 else DegradationLevel.NONE,
                        metadata={"usage": result.get("usage", {}), "status_code": status_code},
                    )
                if not self._should_retry(status_code, None, attempt):
                    self._register_failure()
                    return ReliableLLMResponse(
                        success=False,
                        status=AnalysisStatus.FAILED,
                        error_type=self._classify_error(status_code, None),
                        error_message=f"API错误: {status_code}",
                        finish_reason="error",
                        retry_count=attempt,
                        degraded=attempt > 0,
                        degradation_level=DegradationLevel.RETRIED if attempt > 0 else DegradationLevel.NONE,
                        metadata={"status_code": status_code, "response_text": response.text[:500]},
                    )
            except Exception as exc:  # requests 的异常类型在测试里不稳定，统一兜底
                last_exception = exc
                if not self._should_retry(None, exc, attempt):
                    self._register_failure()
                    return ReliableLLMResponse(
                        success=False,
                        status=AnalysisStatus.FAILED,
                        error_type=self._classify_error(None, exc),
                        error_message=f"请求失败: {str(exc)}",
                        finish_reason="error",
                        retry_count=attempt,
                        degraded=attempt > 0,
                        degradation_level=DegradationLevel.RETRIED if attempt > 0 else DegradationLevel.NONE,
                    )

            sleep_s = self.backoff_base * (2 ** attempt)
            time.sleep(sleep_s)

        self._register_failure()
        return ReliableLLMResponse(
            success=False,
            status=AnalysisStatus.FAILED,
            error_type=self._classify_error(last_status, last_exception),
            error_message="请求失败: 超出最大重试次数",
            finish_reason="error",
            retry_count=self.max_retries,
            degraded=True,
            degradation_level=DegradationLevel.RETRIED,
        )

    def stream_complete(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        thinking_enabled: bool = False,
        on_chunk: Optional[Callable[[str], None]] = None,
        on_reasoning_chunk: Optional[Callable[[str], None]] = None,
    ) -> ReliableLLMResponse:
        if not self.api_key:
            return ReliableLLMResponse(
                success=False,
                status=AnalysisStatus.FAILED,
                error_type=ExpertFailureType.REQUEST_EXCEPTION,
                error_message="API Key未配置",
                finish_reason="error",
            )

        payload = self._build_payload(messages, tools, temperature, max_tokens, thinking_enabled, stream=True)

        for attempt in range(self.max_retries + 1):
            try:
                request_started_at = time.time()
                with self._request_semaphore:
                    session = requests.Session()
                    session.trust_env = False
                    response = session.post(
                        f"{self.base_url}/chat/completions",
                        headers=self._headers(),
                        json=payload,
                        stream=True,
                        timeout=self.timeout,
                    )

                if response.status_code != 200:
                    if self._should_retry(response.status_code, None, attempt):
                        time.sleep(self.backoff_base * (2 ** attempt))
                        continue
                    self._register_failure()
                    return ReliableLLMResponse(
                        success=False,
                        status=AnalysisStatus.FAILED,
                        error_type=self._classify_error(response.status_code, None),
                        error_message=f"API错误: {response.status_code}",
                        finish_reason="error",
                        retry_count=attempt,
                        degraded=attempt > 0,
                        degradation_level=DegradationLevel.RETRIED if attempt > 0 else DegradationLevel.NONE,
                    )

                full_content: List[str] = []
                reasoning_parts: List[str] = []
                tool_calls_data: Dict[str, Dict[str, str]] = {}
                finish_reason = "stop"
                first_content_chunk_at: Optional[float] = None
                first_reasoning_chunk_at: Optional[float] = None
                chunk_count = 0

                response.encoding = "utf-8"
                for line in response.iter_lines(chunk_size=1, decode_unicode=True):
                    if not line:
                        continue
                    decoded = line
                    if not decoded.startswith("data: "):
                        continue
                    data_str = decoded[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    choices = data.get("choices", [])
                    if not choices:
                        continue
                    delta = choices[0].get("delta", {})
                    finish_reason = choices[0].get("finish_reason") or finish_reason

                    content_chunk = delta.get("content", "")
                    if content_chunk:
                        chunk_count += 1
                        if first_content_chunk_at is None:
                            first_content_chunk_at = time.time()
                        full_content.append(content_chunk)
                        if on_chunk:
                            on_chunk(content_chunk)

                    reasoning_chunk = delta.get("reasoning_content", "")
                    if reasoning_chunk:
                        if first_reasoning_chunk_at is None:
                            first_reasoning_chunk_at = time.time()
                        reasoning_parts.append(reasoning_chunk)
                        if on_reasoning_chunk:
                            on_reasoning_chunk(reasoning_chunk)

                    for tc_chunk in delta.get("tool_calls", []):
                        tc_id = tc_chunk.get("id") or f"index_{tc_chunk.get('index', 0)}"
                        if tc_id not in tool_calls_data:
                            tool_calls_data[tc_id] = {"id": tc_id, "name": "", "arguments": ""}
                        func = tc_chunk.get("function", {})
                        if func.get("name"):
                            tool_calls_data[tc_id]["name"] = func["name"]
                        if func.get("arguments"):
                            tool_calls_data[tc_id]["arguments"] += func["arguments"]

                tool_calls: List[Dict[str, Any]] = []
                for tc_id, tc_data in tool_calls_data.items():
                    tool_calls.append({
                        "id": tc_id,
                        "type": "function",
                        "function": {
                            "name": tc_data["name"],
                            "arguments": tc_data["arguments"],
                        },
                    })

                self._register_success()
                return ReliableLLMResponse(
                    content="".join(full_content),
                    reasoning_content="".join(reasoning_parts),
                    tool_calls=tool_calls,
                    finish_reason=finish_reason,
                    success=True,
                    status=AnalysisStatus.DEGRADED if attempt > 0 else AnalysisStatus.SUCCESS,
                    retry_count=attempt,
                    degraded=attempt > 0,
                    degradation_level=DegradationLevel.RETRIED if attempt > 0 else DegradationLevel.NONE,
                    metadata={
                        "chunk_count": chunk_count,
                        "first_content_chunk_ms": (
                            int((first_content_chunk_at - request_started_at) * 1000)
                            if first_content_chunk_at is not None
                            else None
                        ),
                        "first_reasoning_chunk_ms": (
                            int((first_reasoning_chunk_at - request_started_at) * 1000)
                            if first_reasoning_chunk_at is not None
                            else None
                        ),
                    },
                )
            except Exception as exc:
                if self._should_retry(None, exc, attempt):
                    time.sleep(self.backoff_base * (2 ** attempt))
                    continue
                self._register_failure()
                return ReliableLLMResponse(
                    success=False,
                    status=AnalysisStatus.FAILED,
                    error_type=self._classify_error(None, exc),
                    error_message=f"请求失败: {str(exc)}",
                    finish_reason="error",
                    retry_count=attempt,
                    degraded=attempt > 0,
                    degradation_level=DegradationLevel.RETRIED if attempt > 0 else DegradationLevel.NONE,
                )

        self._register_failure()
        return ReliableLLMResponse(
            success=False,
            status=AnalysisStatus.FAILED,
            error_type=ExpertFailureType.REQUEST_EXCEPTION,
            error_message="请求失败: 超出最大重试次数",
            finish_reason="error",
            retry_count=self.max_retries,
            degraded=True,
            degradation_level=DegradationLevel.RETRIED,
        )
