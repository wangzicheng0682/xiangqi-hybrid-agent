---
name: 追踪系统
type: reference
version: 1.0
date: 2026-04-01
owner: AI（自动维护）
changelog:
  - v1.0 (2026-04-01): 初始版本，基于 OpenTelemetry
---

# 追踪系统（OpenTelemetry）

## 概述

基于 OpenTelemetry（OTEL）标准协议的多Agent追踪系统，用于实时观测和调试多Agent执行链路。

**设计原则**：与现有 `debug_logger.py` 完全共存——debug_logger 负责文件持久化，OTEL 负责结构化实时追踪。

---

## 核心概念

### Trace 和 Span

**Trace**：一次完整请求的执行链路（如：用户点击"深度分析" → 系统返回讲解）

**Span**：Trace 中的每个独立操作节点（如：战术专家分析、LLM调用、工具执行）

```
orchestrator.analyze_multi
│
├── tactics_expert.analyze
│       ├── llm.call  [60ms]
│       │       ├── input_tokens=500
│       │       └── output_tokens=120
│       └── tool_call.get_piece_attacks  [15ms]
│
├── strategy_expert.analyze
│       └── llm.call  [55ms]
│
├── engine_expert.analyze
│       └── llm.call  [65ms]
│
└── synthesizer.synthesize
        └── llm.call  [30ms]
```

---

## 架构

```
┌─────────────────────────────────────────────────────┐
│                    追踪数据源                         │
│  Orchestrator ── Span ── Expert ── Tool            │
└─────────────────────┬─────────────────────────────┘
                      │ OpenTelemetry SDK
                      ▼
┌─────────────────────────────────────────────────────┐
│              ConsoleSpanExporter（本地开发）          │
│  ── 控制台实时打印 Span 树（无需任何外部服务）        │
│                                                     │
│  可选 OTLP 导出：                                   │
│  ── Langfuse Cloud（免费账号）                      │
│  ── Langfuse 自托管（Docker）                        │
│  ── Jaeger / Grafana Tempo 等 OTEL兼容后端         │
└─────────────────────────────────────────────────────┘
```

---

## 使用方式

### 零配置使用（本地开发）

```python
# 首次调用时自动初始化，自动输出到控制台
from core.llm.tracing import get_tracer

tracer = get_tracer()

with tracer.start_as_current_span("my.operation") as span:
    span.set_attribute("key", "value")
    # 业务逻辑...
```

**效果**：运行深度分析，控制台实时输出：

```
{
  "name": "orchestrator.analyze_multi",
  "context": {...},
  "start_time": "...",
  "end_time": "...",
  "attributes": {
    "fen.hash": "a3f2b8c1...",
    "phase": "中局",
    "tension_count": 2
  },
  "children": [
    {
      "name": "tactics_expert.analyze",
      "attributes": {"agent.name": "tactics"},
      "children": [
        {"name": "llm.call", "attributes": {"llm.model": "glm-5", "llm.duration_ms": 1500}},
        {"name": "tool_call.get_piece_attacks", "attributes": {"tool.name": "get_piece_attacks"}}
      ]
    },
    ...
  ]
}
```

### 接入 Langfuse（云服务）

**Step 1**：注册 Langfuse Cloud（免费账号）https://cloud.langfuse.com

**Step 2**：设置环境变量

```bash
# .env
LANGFUSE_PUBLIC_KEY=pk-xxx
LANGFUSE_SECRET_KEY=sk-xxx
LANGFUSE_HOST=https://cloud.langfuse.com
```

**Step 3**：自动生效，无需修改代码

```python
# 无需任何改动，tracing.py 自动检测环境变量
from core.llm.tracing import get_tracer
tracer = get_tracer()  # → 自动启用 Langfuse
```

### 自托管 Langfuse（Docker）

```bash
# docker-compose.yml
services:
  langfuse:
    image: langfuse/langfuse:latest
    environment:
      - DATABASE_URL=postgresql://...
      - SECRET_KEY=your-secret-key
    ports:
      - "3000:3000"
```

```bash
# .env
LANGFUSE_PUBLIC_KEY=pk-xxx
LANGFUSE_SECRET_KEY=sk-xxx
LANGFUSE_HOST=http://localhost:3000
OTLP_ENDPOINT=http://localhost:4317
```

### 接入 Jaeger / Grafana Tempo

```bash
# .env
OTLP_ENDPOINT=http://localhost:4317
```

```bash
# Jaeger
docker run -p 16686:16686 -p 4317:4317 jaegertracing/all-in-one
```

---

## API 参考

### `core/llm/tracing.py`

#### `init_tracing(...)`

初始化 TracerProvider（全进程调用一次）。

```python
from core.llm.tracing import init_tracing

init_tracing(
    service_name="xiangqi-agent",
    console_export=True,        # 控制台输出（默认开启）
    otlp_endpoint=None,         # OTLP 收集器地址（可选）
)
```

#### `get_tracer()`

获取 Tracer 实例（懒初始化，自动检测环境）。

```python
tracer = get_tracer()
```

#### `@traced(span_name, attributes)`

将函数包装为 Span 的装饰器。

```python
from core.llm.tracing import traced

@traced("my.operation", attributes={"key": "value"})
def my_function():
    ...
```

#### `add_span_attributes(**kwargs)`

为当前 Span 添加属性的上下文管理器。

```python
from core.llm.tracing import add_span_attributes

with add_span_attributes(fen_hash="xxx", phase="中局"):
    expert.analyze(...)
```

---

## Span 名称和属性常量

```python
from core.llm.tracing import SpanNames, SpanAttributes

# Span 名称
SpanNames.ORCHESTRATOR_ANALYZE       # 协调器入口
SpanNames.ORCHESTRATOR_ANALYZE_MULTI # 多Agent分析
SpanNames.TACTICS_EXPERT_ANALYZE     # 战术专家
SpanNames.STRATEGY_EXPERT_ANALYZE    # 战略专家
SpanNames.ENGINE_EXPERT_ANALYZE       # 引擎专家
SpanNames.SYNTHESIZER_SYNTHESIZE     # 合成器
SpanNames.LLM_CALL                    # LLM调用
SpanNames.TOOL_CALL                   # 工具调用

# Span 属性
SpanAttributes.AGENT_NAME           # agent.name
SpanAttributes.AGENT_TYPE             # agent.type
SpanAttributes.FEN_HASH              # fen.hash（完整FEN的短哈希）
SpanAttributes.PHASE                 # phase（开局/中局/残局）
SpanAttributes.MOVE_COUNT            # move_count
SpanAttributes.TENSION_COUNT          # tension_count
SpanAttributes.TENSION_TYPE          # tension.type
SpanAttributes.LLM_MODEL              # llm.model
SpanAttributes.LLM_INPUT_TOKENS      # llm.input_tokens
SpanAttributes.LLM_OUTPUT_TOKENS      # llm.output_tokens
SpanAttributes.LLM_DURATION_MS        # llm.duration_ms
SpanAttributes.TOOL_NAME             # tool.name
SpanAttributes.TOOL_SUCCESS          # tool.success
SpanAttributes.TOOL_DURATION_MS      # tool.duration_ms
SpanAttributes.EXPERT_SUCCESS         # expert.success
SpanAttributes.EXPERT_FINDING         # expert.finding（截断100字）
SpanAttributes.ERROR                 # error
SpanAttributes.ERROR_MESSAGE          # error.message
```

---

## 与 debug_logger 的关系

| 维度 | debug_logger | tracing |
|------|-------------|---------|
| **用途** | 文件持久化日志 | 结构化实时追踪 |
| **输出** | JSON/TXT 文件 | Console + OTLP |
| **实时性** | 事后查看 | 实时查看 |
| **查询** | grep | Dashboard |
| **延迟分析** | 需人工 | 自动生成时间线 |
| **外部依赖** | 无 | 可选（Langfuse等） |
| **是否共存** | ✅ | ✅ |

**两者完全独立，同时工作，互不干扰。**

---

## 追踪层级

```
Level 1: Orchestrator 入口
  └── Level 2: 每个 Expert 执行
        └── Level 3: LLM 调用
              └── Level 4: 工具调用
```

**延迟计算**：每个层级自动记录 `duration_ms`，可在 Dashboard 中直观看到瓶颈。

---

## 生产环境建议

| 环境 | 建议 | 理由 |
|------|------|------|
| 本地开发 | ConsoleExporter | 无需配置，实时可见 |
| 测试环境 | ConsoleExporter | 方便调试 |
| 预发布 | Langfuse Cloud（免费账号） | 无需运维 |
| 生产环境 | Langfuse 自托管 | 数据自主可控 |

---

## 性能影响

- **OTEL SDK 开销**：< 1ms/span（批量处理）
- **Console 输出**：几乎可忽略（批量写入）
- **OTLP 导出**：异步批量，不阻塞主线程
