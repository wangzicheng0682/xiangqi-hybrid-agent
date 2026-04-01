# OpenTelemetry 追踪系统交接文档

**日期**：2026-04-01
**维护者**：Claude Code
**状态**：已完成并验证

---

## 做了什么

### 调研阶段

调研了 GitHub 上成熟的多Agent调试系统：
- LangGraph 内置 Checkpoint + LangSmith
- AutoGen + OpenTelemetry
- CrewAI + Wandb Weave / Phoenix
- AgentPrism 可视化组件
- Langfuse / Arize Phoenix 开源平台

**结论**：OpenTelemetry 是行业标准，Langfuse 是最佳可视化终端（开源免费可自托管）。

### 实现阶段

**新增文件**：

| 文件 | 说明 |
|------|------|
| `core/llm/tracing.py` | OTEL 初始化 + TracerProvider + Span 常量 + 装饰器 |
| `docs/reference/tracing.md` | 完整技术文档 |

**修改文件**：

| 文件 | 改动 |
|------|------|
| `core/llm/multi_agent_orchestrator.py` | 导入 tracing 模块；analyze/analyze_multi/expert调用/合成器全部加 Span |
| `core/llm/experts/base_expert.py` | LLM调用 Span + 工具执行 Span |
| `tests/test_multi_agent.py` | 新增 23 个测试（自适应决策、专家配置、阶段检测、异常处理） |
| `docs/STATE.md` | 更新状态记录 |

### 验证结果

控制台输出完整 Span 树，同一 trace_id，父子关系正确：
```
orchestrator.analyze (根Span)
  ├── tactics_expert.analyze
  │     ├── llm.call
  │     └── tool_call
  ├── strategy_expert.analyze
  ├── engine_expert.analyze
  └── synthesizer.synthesize
```

---

## 技术架构

```
Span 层级：
Level 1: orchestrator.analyze（根Span）
  └── Level 2: orchestrator.analyze_multi
        ├── Level 3: tactics_expert.analyze
        │     ├── Level 4: llm.call（attributes: model, tokens, duration_ms）
        │     └── Level 4: tool_call（attributes: tool_name, success, error）
        ├── Level 3: strategy_expert.analyze
        └── Level 3: engine_expert.analyze
              └── Level 3: synthesizer.synthesize

导出目标：
  ├── ConsoleSpanExporter（本地开发，零配置）
  ├── Langfuse Cloud（设置环境变量即可）
  ├── Jaeger / Grafana Tempo（设置 OTLP_ENDPOINT）
```

---

## 怎么用

### 本地开发（零配置）

```bash
python -m uvicorn api.main:app --host 0.0.0.0 --port 8002
# 控制台自动输出 Span 树
```

### 接入 Langfuse Cloud

```bash
# .env
LANGFUSE_PUBLIC_KEY=pk-xxx
LANGFUSE_SECRET_KEY=sk-xxx
LANGFUSE_HOST=https://cloud.langfuse.com
```

### 接入 Jaeger

```bash
# .env
OTLP_ENDPOINT=http://localhost:4317

# 启动 Jaeger
docker run -p 16686:16686 -p 4317:4317 jaegertracing/all-in-one
```

---

## 后续维护

### 添加新的 Span

在 `core/llm/tracing.py` 的 `SpanNames` 和 `SpanAttributes` 中添加常量，
然后在关键函数中：

```python
from core.llm.tracing import get_tracer, SpanNames, SpanAttributes

tracer = get_tracer()
with tracer.start_as_current_span("my.new_span", attributes={SpanAttributes.AGENT_NAME: "my_agent"}) as span:
    span.set_attribute("custom_attr", value)
    # 业务逻辑...
```

### 禁用追踪

如果需要禁用追踪，修改 `core/llm/tracing.py` 中的 `_initialized` 逻辑，
或设置环境变量 `OTEL_TRACING_ENABLED=false`（需在 tracing.py 中实现）。

### 与 debug_logger 的关系

两者**完全独立**，同时工作：
- `debug_logger.py` → 文件持久化日志（事后查看）
- `tracing.py` → 实时结构化追踪（立即可见）

---

## 已知问题

**NumPy 版本冲突**：当前环境的 numexpr/bottleneck 与 NumPy 2.x 不兼容，
导致 `uvicorn` 启动时报错。但追踪模块本身验证通过（隔离测试）。

**解决方案**：在新的 conda 环境或虚拟环境中运行，或降级 numpy 到 1.x。

---

## 文件清单

```
core/llm/tracing.py                          # 核心追踪模块
core/llm/multi_agent_orchestrator.py        # 已集成 OTEL Span
core/llm/experts/base_expert.py             # 已集成 LLM/工具 Span
tests/test_multi_agent.py                    # 23 个测试，全通过
docs/reference/tracing.md                    # 技术文档
docs/STATE.md                                # 状态更新
plans/eager-growing-eich.md                  # 审查报告+升级方案
```

---

## 参考文献

- [LangGraph 调试方案](https://github.com/langchain-ai/langgraph)
- [AutoGen + OpenTelemetry](https://medium.com/@milenppavlov/building-better-observability-for-autogen-multi-agent-systems-b0c93b8a50e6)
- [Langfuse 官网](https://langfuse.com)
- [Arize Phoenix](https://arize.com/phoenix/)
- [AgentPrism (Evil Martians)](https://evilmartians.com/chronicles/debug-ai-fast-agent-prism-open-source-library-visualize-agent-traces)
