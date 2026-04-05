---
name: SSE步骤实时性与thinking面板体验优化
type: plan
version: 1.0.0
date: 2026-04-05
status: 完成
owner: AI
---

# Plan 007: SSE步骤实时性与thinking面板体验优化

## 问题诊断

通过 `test_sse_step_timing.py` 对真实后端 8002 端口的测量，发现以下问题：

### 已用实际数据确认的问题

| # | 问题 | 证据 |
|---|------|------|
| 1 | **步骤事件极度稀疏** | 99秒分析仅12个步骤事件，视觉上只有4-5行标题 |
| 2 | **步骤之间巨大空白** | tactics: expert_start(2.25s)→tool(16.88s)=14.6s无步骤；strategy: start(2.25s)→result(20.22s)=18s无步骤 |
| 3 | **dispatch_info 和 expert_start 重复发送** | 预览阶段(preview_dispatch)发送一次，orchestrator.analyze()再发一次，前端看到6个步骤事件而非3个 |
| 4 | **引擎专家完全缺失** | 0个engine相关事件，三张卡牌只有两张有内容 |
| 5 | **Chunk数据丰富但不生成步骤** | tactics=288 chunks, strategy=135 chunks，但它们不创建任何thinking步骤 |
| 6 | **合成仅为"保底综合讲解"** | synthesis_step仅1条，标题为"生成保底综合讲解"，瞬间完成 |

### 对比目标

截图参考：顶尖大模型thinking面板
- 每一条step只有图标+标题，一个一个动态冒出
- 平均每2-5秒出现一条新step
- 整个过程30-40秒显示15-20条step

## 解决方案

### Fix 1: 消除重复事件（后端 api/main.py）

**问题根源**: `api/main.py` 第1655-1670行在预分析等待期间发送"预览"的 `dispatch_info` 和 `expert_start` 事件。随后 `orchestrator.analyze()` 内部再次发送真实的同名事件。前端收到两轮重复。

**方案**: 预览阶段不再发送 `expert_start` 和 `dispatch_info`，改为发送专用的 `precompute_preview` 事件类型。或者更简单地：直接删除预览的 expert_start/dispatch_info，仅保留 orchestrator 内部发送的真实事件。

### Fix 2: 前端chunk驱动步骤生成器（App.tsx）

**核心思路**: 当 `expert_*_chunk` 事件流入时，每隔 ~4秒 自动创建一个新的标题步骤。标题从预定义的专家思考阶段列表中轮换选取。

```
战术专家阶段: ["扫描战术威胁", "检测强制序列", "分析子力交换", "评估战术组合", "验证分析结果"]
战略专家阶段: ["评估局面形势", "分析阵型结构", "检测位置弱点", "审视子力协调", "整理战略建议"]
引擎专家阶段: ["启动深度算路", "计算候选变化", "评估最佳着法"]
```

每个阶段持续 ~4秒，然后 finalize 当前步骤并创建下一个。这样一个30秒的专家分析可产生 ~7个步骤，加上工具调用步骤，总计约 10-15 个。

### Fix 3: 合成步骤优化（可选）

如果合成器只触发"保底综合讲解"，在前端也自动插入"综合各方观点"过渡步骤。

## 实施步骤

1. [x] 编写本规划文档
2. [x] 修改 `api/main.py` 消除预览阶段的重复事件
3. [x] 修改 `frontend/src/App.tsx` 实现chunk驱动步骤生成器
4. [x] frontend build 验证
5. [x] 重启后端并运行 `test_sse_frontend_simulation.py` 取证
6. [x] 更新 STATE.md

## 验证结果

| 指标 | 修复前 | 修复后 |
|---|---|---|
| 总步骤数 | 12 | **35** |
| 最大间隔 | 47s | **4.14s** |
| 间隔>5s | 3个 | **0个** |
| 平均间隔 | ~8s | **1.99s** |
| 重复事件 | 6对 | **0对** |
| pytest | 314 passed | 314 passed |
