# CLAUDE.md — AI开发规范

项目：象棋 AI 混合代理教学与对弈系统
运行环境：Windows

---

## 🧬 必读文档

**新会话必须先阅读**: [`docs/DNA.md`](docs/DNA.md)

> DNA.md 包含项目愿景、架构、标签体系、Agent工具、API设计、快速启动等所有核心信息。
> 阅读时间约5分钟，读完即可理解项目全貌。

**当前状态**: [`docs/STATE.md`](docs/STATE.md)

---

## ⚠️ T0比赛优先战略

**最高优先级**: 20天内形成可演示、可讲解、可答辩的比赛作品

**战略收束**:
- 用规则脚本而非模型提取特征（100%准确，无幻觉）
- LLM只负责表达，不负责重建棋盘空间
- Evidence Map约束LLM，防止编造

---

## 🔴 开机流程

### Step 1: 读取必读文档
```
1. docs/DNA.md   ← 必读（项目全貌）
2. docs/STATE.md ← 必读（当前进度）
```

### Step 2: 确认当前任务
根据STATE.md确认待完成任务

---

## 🔴 关机流程

### Step 1: 更新状态文档
```
更新 docs/STATE.md：
- 更新"最近更新记录"
- 更新进度状态
```

### Step 2: 运行门禁
```bash
pytest -q
```

---

## 🔴 门禁机制

**提交前必须通过**:
- [ ] `pytest -q` 全绿
- [ ] `docs/STATE.md` 已更新

---

## 📚 详细参考文档

| 文档 | 位置 | 内容 |
|------|------|------|
| 标签参考 | `docs/reference/tag_reference.md` | 45个标签完整定义 |
| Agent工具 | `docs/reference/agent_tools_spec.md` | 10个工具接口规范 |
| **前端开发** | `docs/frontend/FRONTEND_DNA.md` | 前端开发者指南 |

---

## 🤝 协作指南

### 前端开发者

如果你是负责前端的 AI，请阅读：
1. `docs/frontend/FRONTEND_DNA.md` — 前端宪法
2. `docs/frontend/API_CONTRACT.md` — 前后端接口契约

**只允许在 `frontend/` 目录下修改**，接口变更必须先更新 `API_CONTRACT.md`。

---

## 📋 Plan 文档

> 记录未成熟但打算去做的想法。所有AI可自由创建、更新、维护plan。

| 序号 | 标题 | 状态 |
|------|------|------|
| 001 | 三层分离Prompt框架 | 构思中 |

详细规范见 [`docs/plan/README.md`](docs/plan/README.md)

---

## 🚀 快速启动

```bash
# 后端
python -m uvicorn api.main:app --host 0.0.0.0 --port 8002

# 前端
cd frontend && npm run dev

# 测试
pytest -q
```

---

**文档版本**: v4.0
**生效日期**: 2026-03-14
