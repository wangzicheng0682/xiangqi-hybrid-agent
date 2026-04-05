---
name: Plan文档规范
type: plan
version: 1.0.0
date: 2026-04-01
owner: AI（自动维护）
changelog:
  - v1.0.0 (2026-04-01): 初始版本
---

# Plan 文档规范

> 本目录包含项目构思中的想法和计划。

---

## 目录结构

```
plans/
├── README.md                  # 本文件
├── 001-three-layer-prompt.md   # 三层分离Prompt框架
├── 002-reliability-architecture-refactor.md  # 比赛级可靠性架构重构方案
├── 003-competition-grade-roadmap.md  # 从当前系统到比赛答辩级作品的长期路线图
├── 004-inference-control-upgrade.md  # 推理时控制升级方案
├── 005-data-and-knowledge-assets.md  # 数据与知识资产建设方案
├── 006-asset-lifecycle-and-eval-driven-workflow.md  # 资产生命周期与评测驱动工作流
├── 007-sse-realtime-thinking-steps.md  # SSE步骤实时性与thinking面板体验优化
├── 008-right-stage-and-evidence-court-redesign.md  # 右侧分析舞台与证据裁决台重设计
└── frontend/                  # 前端相关Plan
    ├── README.md               # 前端Plan规范
    ├── 001-agent-poker-panel.md
    └── 002-liquid-glass.md
```

---

## Plan文档格式

每个Plan文档应包含以下部分：

```markdown
# Plan: [标题]

## Context

为什么需要这个改动？问题是什么？

## 目标

要达到什么效果？

## 实施方案

具体步骤

## 验证方法

如何验证改动正确？
```

---

## Plan命名规范

- 文件名格式：`序号-title.md`
- 序号使用三位数字（001, 002, 003...）
- 标题使用kebab-case（短横线分隔）

---

## 生命周期

| 阶段 | 说明 |
|------|------|
| 构思中 | 正在思考，还没有具体方案 |
| 已批准 | 用户批准，可以开始实施 |
| 进行中 | 正在实施 |
| 已完成 | 实施完成，可以归档 |
| 已废弃 | 放弃的想法 |

---

**最后更新**: 2026-04-01
