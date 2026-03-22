# 前端开发宪法

> 你是前端开发者。阅读本文档是所有工作的前提。

---

## ⚠️ 最高原则：模块边界

### 只允许修改
```
frontend/           ✅ 可以修改
```

### 禁止修改（必须通过接口契约）
```
api/               ❌ 禁止修改
core/              ❌ 禁止修改  
docs/              ❌ 禁止修改（除 docs/frontend/ 外）
```

**如果需要后端能力** → 使用 `src/services/api.ts` 中定义的接口
**如果接口不满足需求** → 先更新 `API_CONTRACT.md`，用户批准后再改

---

## 📋 前端模块结构

```
frontend/
├── src/
│   ├── components/       # React 组件
│   │   ├── ChessBoard.tsx        # 棋盘组件
│   │   ├── EngineChart.tsx       # 引擎评分折线图
│   │   ├── DeepAnalysisPanel.tsx # 深度分析面板
│   │   ├── PositionAnalysisPanel.tsx  # 局面分析面板
│   │   ├── TacticalTagsPanel.tsx  # 战术标签面板
│   │   ├── ReplayPanel.tsx       # 复盘面板
│   │   ├── ReplayNavigator.tsx   # 导航组件
│   │   ├── SynthesisPanel.tsx     # 综合面板
│   │   ├── ExpertCard.tsx        # 专家卡片
│   │   ├── AgentDebutPanel.tsx   # Agent登场动画
│   │   └── BottomTerminalPanel.tsx # 底部终端面板
│   ├── services/
│   │   └── api.ts       # API 调用层（唯一后端通信入口）
│   ├── store/
│   │   └── useGameStore.ts  # Zustand 状态管理
│   ├── hooks/           # 自定义 Hooks
│   ├── types/           # TypeScript 类型
│   ├── App.tsx          # 应用入口
│   └── main.tsx         # React 入口
└── package.json
```

---

## 🔴 开发流程

### Step 1: 阅读必读文档
```
1. docs/frontend/FRONTEND_DNA.md    ← 本文档
2. docs/frontend/API_CONTRACT.md     ← 接口契约
```

### Step 2: 确认工作范围
- 组件开发？→ 阅读 `COMPONENT_GUIDE.md`
- 状态管理？→ 阅读 `STATE_MANAGEMENT.md`
- API 调用？→ 使用 `api.ts` 中已定义的接口

### Step 3: 开发与提交
- 只在 `frontend/` 目录下修改
- 接口变更必须先更新 `API_CONTRACT.md`
- 提交前运行 `pytest -q`（如果改动了后端相关）

---

## 🔴 关机流程

### 更新状态文档
```
更新 docs/frontend/STATE.md：
- 更新"最近更新记录"
- 更新进度状态
```

---

## 📚 前端文档索引

| 文档 | 用途 |
|------|------|
| `FRONTEND_DNA.md` | 本文件 - 前端宪法 |
| `API_CONTRACT.md` | 前后端接口契约 |
| `COMPONENT_GUIDE.md` | 组件开发规范 |
| `STATE_MANAGEMENT.md` | 状态管理规范 |
| `AI_CODING_GUIDE.md` | AI Coding 指南 |
| `STATE.md` | 前端开发状态 |
| `HANDOVER.md` | 交接文档（每次交接时更新） |
| `plan/README.md` | Plan 文档规范 |
| `plan/*.md` | 具体 Plan 文档 |

---

## 🔄 交接流程

每次交接时：
1. 更新 `HANDOVER.md` 的变更记录
2. 更新 `STATE.md` 的进度
3. 如有新想法，创建 `plan/序号-title.md`

---

**文档版本**: v1.0
**生效日期**: 2026-03-19
