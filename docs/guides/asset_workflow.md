---
name: 资产工作流指南
type: guide
version: 1.0
date: 2026-04-03
owner: AI（自动维护）
changelog:
  - v1.0 (2026-04-03): 固化 Copilot 作为资产起草者的协作流程，确保新对话可续接
---

# 资产工作流指南

## 1. 角色定义

本项目里，**资产起草者就是 Copilot 对话中的 AI**。

这意味着：
- 人负责给目标、给局面、做审批
- Copilot 负责先取证据，再起草初版
- 新开对话时，Copilot 必须先读 STATE 和本指南，再继续工作

## 2. 新对话开机顺序

每次新开对话，Copilot 必须按这个顺序恢复上下文：

1. 阅读 [docs/DNA.md](../DNA.md)
2. 阅读 [docs/STATE.md](../STATE.md)
3. 阅读本文件 [docs/guides/asset_workflow.md](asset_workflow.md)
4. 若任务和资产相关，优先查看：
   - [data/assets/scenario_examples.jsonl](../../data/assets/scenario_examples.jsonl)
   - [data/assets/rewrite_queue.jsonl](../../data/assets/rewrite_queue.jsonl)
   - [data/assets/failure_cases.jsonl](../../data/assets/failure_cases.jsonl)

## 3. 起草规则

资产初稿默认不能再走“纯脑补”模式。

标准流程：

1. 输入 FEN / 选定 scenario
2. 先调用后端 API 取真实证据
3. 再生成 draft
4. 人工审批教学表达与重点是否合理

当前默认证据接口：
- `/api/position-analysis`
- `/api/engine/evaluate`
- `/api/tactical-tags`
- `/api/board-structure`

当前默认起草脚本：
- [scripts/generate_asset_draft.py](../../scripts/generate_asset_draft.py)

## 4. 数据等级解释

- `engine_verified=true`：引擎数据来自真实后端接口
- `tags_verified=true`：标签数据来自真实规则检测接口
- `grade=draft`：即使证据真实，教学文案仍未经过人工审批

所以：
- “证据真实” 不等于 “资产可直接上线”
- gold/silver 仍然要经过审批台定级

## 5. 审批台定位

[apps/web-gradio/reviewer.py](../../apps/web-gradio/reviewer.py) 当前是原型，不是最终版。

当前用途：
- 浏览资产
- 修改讲解
- 审批定级
- 打回重写
- 手工导入局面

下一阶段目标：
- 直接在审批台里调用后端取证据
- 展示 Evidence Map / 引擎主变 / 标签明细
- 一键生成或重写初稿

## 6. 最重要的约束

如果新对话中的 Copilot 忽略了这份指南，又开始直接脑补 scenario 初稿，那属于流程错误，应立即纠正回“先取证据，再起草”。