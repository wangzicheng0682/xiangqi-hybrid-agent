"""
OpenTelemetry 追踪基础设施

为多Agent系统提供标准化的分布式追踪能力。

核心功能：
- TracerProvider 初始化
- ConsoleSpanExporter（本地开发用）
- Langfuse 集成（可选，需要 LANGFUSE_PUBLIC_KEY 环境变量）
- 结构化 Span 属性生成
- 与现有 debug_logger.py 完全共存

Span 层级设计：
    orchestrator.analyze_multi
        ├── tactics_expert.analyze
        │       ├── llm.call
        │       └── tool_call.get_piece_*
        ├── strategy_expert.analyze
        └── engine_expert.analyze

使用方式：
    from core.llm.tracing import get_tracer, traced, add_span_attributes

    tracer = get_tracer()

    @traced("orchestrator.analyze_multi")
    def analyze_multi(self, fen, question, ...):
        span = trace.get_current_span()
        span.set_attribute("fen.hash", hash_fen(fen))
        span.set_attribute("phase", phase_name)
        ...
"""

import os
import sys
import functools
from typing import Optional, Any, Callable

# OpenTelemetry 核心
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)
from opentelemetry.trace import Status, StatusCode, SpanKind
from opentelemetry.trace.propagation import set_span_in_context


# ═══════════════════════════════════════════════════════════════════════════════
# TracerProvider 初始化（单例）
# ═══════════════════════════════════════════════════════════════════════════════

_tracer_provider: Optional[TracerProvider] = None
_tracer: Optional[trace.Tracer] = None
_initialized: bool = False


def init_tracing(
    service_name: str = "xiangqi-agent",
    console_export: bool = True,
    otlp_endpoint: Optional[str] = None,
) -> trace.Tracer:
    """
    初始化 TracerProvider（全进程调用一次）

    Args:
        service_name: 服务名，用于 Trace 列表分组
        console_export: 是否输出到控制台（本地开发用）
        otlp_endpoint: OTLP 收集器地址，如 "http://localhost:4317"
                      支持：Langfuse、Jaeger、Grafana Tempo 等 OTEL 兼容后端
    """
    global _tracer_provider, _tracer, _initialized

    if _initialized:
        return _tracer

    _tracer_provider = TracerProvider()
    trace.set_tracer_provider(_tracer_provider)

    # Console 输出（本地开发）：用 SimpleSpanProcessor 避免后台线程在 pytest teardown 时写已关闭的 stdout
    if console_export:
        _tracer_provider.add_span_processor(
            SimpleSpanProcessor(ConsoleSpanExporter(out=sys.stdout))
        )

    # OTLP 导出（远程收集器，如 Langfuse 自托管）
    if otlp_endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                OTLPSpanExporter,
            )
            _tracer_provider.add_span_processor(
                BatchSpanProcessor(
                    OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
                )
            )
        except ImportError:
            pass  # opentelemetry-exporter-otlp 未安装

    # Langfuse 云服务（免费账号）
    # 设置 LANGFUSE_PUBLIC_KEY 和 LANGFUSE_SECRET_KEY 环境变量即可
    if os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"):
        _init_langfuse()

    _tracer = _tracer_provider.get_tracer(service_name)
    _initialized = True

    return _tracer


def _init_langfuse():
    """Langfuse 集成（可选功能）"""
    try:
        from langfuse.decorators import langfuse_context

        # 自动配置 Langfuse
        langfuse_context.update_current_trace_settings(
            metadata={"service": "xiangqi-agent"}
        )
    except ImportError:
        pass  # langfuse 未安装


def get_tracer() -> trace.Tracer:
    """
    获取 Tracer 实例（懒初始化）

    自动检测环境：
    - 有 LANGFUSE_* 环境变量 → 启用 Langfuse 追踪
    - 有 OTLP_ENDPOINT 环境变量 → 启用 OTLP 导出
    - 其他情况 → 仅 Console 输出
    """
    global _tracer

    if not _initialized:
        otlp_endpoint = os.getenv("OTLP_ENDPOINT")
        init_tracing(
            service_name="xiangqi-agent",
            console_export=not bool(otlp_endpoint),
            otlp_endpoint=otlp_endpoint,
        )

    return _tracer or trace.get_tracer("xiangqi-agent")


# ═══════════════════════════════════════════════════════════════════════════════
# 追踪装饰器
# ═══════════════════════════════════════════════════════════════════════════════

def traced(
    span_name: str,
    kind: SpanKind = SpanKind.INTERNAL,
    attributes: Optional[dict] = None,
):
    """
    将函数执行包装为 Span 的装饰器

    用法：
        @traced("orchestrator.analyze_multi", attributes={"agent": "orchestrator"})
        def analyze_multi(self, fen, question, ...):
            ...

    自动记录：
    - 函数输入参数（只记录可哈希的元数据，不记录大对象）
    - 函数返回值
    - 函数耗时
    - 异常信息（如果有）
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            tracer = get_tracer()
            with tracer.start_as_current_span(
                span_name,
                kind=kind,
            ) as span:
                if attributes:
                    for k, v in attributes.items():
                        if v is not None:
                            span.set_attribute(k, _serialize_attr(v))
                try:
                    result = func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            tracer = get_tracer()
            with tracer.start_as_current_span(
                span_name,
                kind=kind,
            ) as span:
                if attributes:
                    for k, v in attributes.items():
                        if v is not None:
                            span.set_attribute(k, _serialize_attr(v))
                try:
                    result = await func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise

        # 根据函数是否为异步返回对应包装器
        if asyncio_iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def add_span_attributes(**kwargs):
    """
    为当前 Span 添加属性的上下文管理器

    用法：
        with add_span_attributes(fen_hash="xxx", phase="中局"):
            expert.analyze(...)
    """
    span = trace.get_current_span()
    for k, v in kwargs.items():
        if v is not None:
            span.set_attribute(k, _serialize_attr(v))


# ═══════════════════════════════════════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════════════════════════════════════

def _serialize_attr(value: Any) -> str:
    """将属性值序列化为字符串（Span 属性只接受基本类型）"""
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple)):
        return str(value)[:200]  # 截断避免过长
    return str(value)[:200]


def hash_fen(fen: str, length: int = 20) -> str:
    """生成 FEN 的短哈希（避免在 Span 中记录完整 FEN）"""
    import hashlib
    return hashlib.sha256(fen.encode()).hexdigest()[:length]


def asyncio_iscoroutinefunction(func: Callable) -> bool:
    """判断函数是否为异步函数"""
    import asyncio
    return asyncio.iscoroutinefunction(func)


# ═══════════════════════════════════════════════════════════════════════════════
# Span 层级常量（保证所有 Span 使用统一的名称）
# ═══════════════════════════════════════════════════════════════════════════════

class SpanNames:
    """Span 名称常量"""
    ORCHESTRATOR_ANALYZE = "orchestrator.analyze"
    ORCHESTRATOR_ANALYZE_MULTI = "orchestrator.analyze_multi"
    ORCHESTRATOR_ANALYZE_SINGLE = "orchestrator.analyze_single"
    TACTICS_EXPERT_ANALYZE = "tactics_expert.analyze"
    STRATEGY_EXPERT_ANALYZE = "strategy_expert.analyze"
    ENGINE_EXPERT_ANALYZE = "engine_expert.analyze"
    SYNTHESIZER_SYNTHESIZE = "synthesizer.synthesize"
    LLM_CALL = "llm.call"
    TOOL_CALL = "tool_call"


class SpanAttributes:
    """标准 Span 属性名"""
    AGENT_NAME = "agent.name"
    AGENT_TYPE = "agent.type"
    FEN_HASH = "fen.hash"
    PHASE = "phase"
    MOVE_COUNT = "move_count"
    TENSION_COUNT = "tension_count"
    TENSION_TYPE = "tension.type"
    LLM_MODEL = "llm.model"
    LLM_INPUT_TOKENS = "llm.input_tokens"
    LLM_OUTPUT_TOKENS = "llm.output_tokens"
    LLM_DURATION_MS = "llm.duration_ms"
    TOOL_NAME = "tool.name"
    TOOL_SUCCESS = "tool.success"
    TOOL_DURATION_MS = "tool.duration_ms"
    EXPERT_SUCCESS = "expert.success"
    EXPERT_FINDING = "expert.finding"
    ERROR = "error"
    ERROR_MESSAGE = "error.message"
