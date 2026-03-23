# 前端交接文档

> 每次交接时更新本文档。新窗口的 AI 阅读本文档来快速上手工作。

---

## ⚠️ 必读顺序

1. [docs/DNA.md](docs/DNA.md) — 项目全貌
2. [docs/STATE.md](docs/STATE.md) — 当前状态
3. [docs/frontend/FRONTEND_DNA.md](docs/frontend/FRONTEND_DNA.md) — 前端宪法
4. **[docs/frontend/plan/001-agent-poker-panel.md](docs/frontend/plan/001-agent-poker-panel.md)** — 当前核心任务设计文档（先读这个）

---

## 版本信息

| 版本 | 日期 | 说明 |
|------|------|------|
| v1 | 2026-03-19 | 初始版本 |
| v2 | 2026-03-23 | 全面重构扑克牌动画设计，新增三层Agent架构 |
| v3 | 2026-03-23 | 实现新动画序列：收缩变形+曲线发牌+落地居左+思维流左右分栏 |

---

## 当前核心任务

### 目标
重写右侧分析栏的**变形/发牌/思维流**动画，达到 Apple/WWDC 水准。

### 系统架构（三层 Agent）

```
                    ┌──────────────────────────────────┐
                    │   协调者 Agent（主）              │
                    │   实时读取三专家 → 生成小标题       │
                    │   展示在右侧思维流                 │
                    │   最终输出"最终讲解"               │
                    └──────────┬────────────────────────┘
                               │
          ┌────────────────────┼────────────────────┐
          ▼                    ▼                    ▼
    ┌──────────┐        ┌──────────┐        ┌──────────┐
    │ 战术专家   │        │ 战略专家   │        │ 引擎专家   │
    │  Agent   │        │  Agent   │        │  Agent   │
    │ LLM思考  │        │ LLM思考  │        │ LLM思考  │
    │ (隐藏)   │        │ (隐藏)   │        │ (隐藏)   │
    └──────────┘        └──────────┘        └──────────┘
```

| 层级 | 对用户可见性 |
|------|------------|
| 三专家隐藏输出 | **隐藏** — hover扑克牌弹出查看 |
| 协调者小标题 | **可见** — 右侧思维流 |
| 最终讲解 | **可见** — 思维流收尾 |

### 界面布局（620px 展开宽度）

```
┌──────────────────────────────────────────────────────────┐
│   ┌─────────────┐      ┌──────────────────────────┐  │
│   │ ♥ K        │      │ 🤍 协调者球（右上角）        │  │
│   │ 战术专家   │      │ ↓ 金色连接线               │  │
│   └─────────────┘      │ ┌──────────────────────┐ │  │
│   ┌─────────────┐      │ │ 💭 小标题1            │ │  │
│   │ ♠ J        │      │ │ 💭 小标题2            │ │  │
│   │ 战略专家   │      │ │ ...                   │ │  │
│   └─────────────┘      │ └──────────────────────┘ │  │
│   ┌─────────────┐      └──────────────────────────┘  │
│   │ ♦ Q        │                                      │
│   │ 引擎专家   │                                      │
│   └─────────────┘                                      │
│                                                           │
│  左侧：三专家扑克牌，整体居中，边缘流光（代表工作中）        │
│  右侧：协调者球 + 思维流（小标题逐个生长）                │
└──────────────────────────────────────────────────────────┘
```

### 动画序列（从翻面完成开始计时）

| 时间 | 阶段 | 描述 |
|------|------|------|
| T=0 | 翻面完成 | 叠卡整齐显露彩虹背面（已完成，不改） |
| T=0~400ms | 收缩变形 | 叠卡流畅收缩变形成小球，无停顿，像有机体在呼吸 |
| T=400~1100ms | 曲线滑动+发牌 | 球沿曲线路径滑向右上角，过程中逐张发牌，牌有macOS最小化拉伸感 |
| T=1300ms | 牌落位 | 三张落地左侧，整体垂直居中，正面磨砂+边缘彩色流光 |
| T=1400ms | 专家发力 | 三张边缘流光启动，代表开始工作 |
| T=1500ms | 协调者就位 | 球固定右上角，持续呼吸 |
| T=1600ms~ | 思维流输出 | 球底金色细线延伸，小标题逐个生长，打字机效果 |

### 小标题本质
- **不是写死的**、不是固定模板
- 协调者实时生成：观察三专家正在做什么（调用什么工具、处于什么阶段、发现了什么），立刻用LLM能力**实时总结成小标题**
- 例："战略专家发现中路突破机会"、"战术专家找到了两步杀的方案"
- 小标题逐个向下延伸，形成思维流

---

## 关键文件

| 文件 | 作用 | 状态 |
|------|------|------|
| `frontend/src/components/AgentCardFlip.tsx` | 翻面+收缩变形+球曲线滑动动画主文件 | ✅ 已完成 |
| `frontend/src/components/AgentThinkingPanel.tsx` | 分析栏主面板，含左右分栏布局 | ✅ 已完成 |
| `frontend/src/components/ThinkingStream.tsx` | 协调者思维流组件，打字机效果 | ✅ 已新建 |
| `frontend/src/components/CardContent.tsx` | 扑克牌正面内容（K/J/Q + 磨砂） | 稳定 |
| `frontend/src/components/ExpertCard.tsx` | 专家卡片，含StreamText打字机 | 稳定 |
| `frontend/src/store/useAgentStore.ts` | 动画阶段状态（新增 cardsLanded/streaming） | ✅ 已更新 |
| `frontend/src/services/api.ts` | SSE事件处理，端口已修复8002 | ✅ 已修复 |
| `frontend/src/App.tsx` | 主布局，渲染AgentThinkingPanel | 稳定 |

### 已确认的死代码（已删除）

以下文件已确认删除（v3）：
- `frontend/src/components/StatCard.tsx` ✅ 已删除
- `frontend/src/components/TacticalTagsPanel.tsx` ✅ 已删除
- `frontend/src/components/ToolChainBridge.tsx` ✅ 已删除
- `frontend/src/components/AgentCardStack.tsx` ✅ 已删除
- `frontend/src/components/OrchestratorOrb.tsx` ✅ 已删除
- `frontend/src/components/PokerExpertCard.tsx` ✅ 已删除
- `frontend/src/components/ThinkingStreamView.tsx` ✅ 已删除
- `frontend/src/components/CollapsedCardsView.tsx` ✅ 已删除

---

## 已修复的Bug

| 日期 | 问题 | 根因 | 修复 |
|------|------|------|------|
| 2026-03-23 | J卡正面彩色流光透出 | 背面opacity始终为1未归零 | 正面/背面各用独立motion.div，背面idle时opacity:0 |

---

## 其他已知Bug（未修复）

| 文件 | 问题 | 严重度 |
|------|------|--------|
| `ReplayNavigator.tsx:65` | `Math.random()` 每次渲染随机走法质量 | 高 |
| `EngineChart.tsx:50` | 空数组时`Math.min(...[])`崩溃 | 高 |
| `useGameStore.ts:328` | `resetGame()`不清除flipped/evalHistory等7个状态 | 中 |

## 已修复Bug（v3）

| 文件 | 问题 | 修复 |
|------|------|------|
| `api.ts:5` | API端口硬编码8003 | ✅ 已改为8002 |
| `DeepAnalysisPanel.tsx` | ToolCall类型缺id字段 | ✅ 已添加 |
| `api.ts` | SSE事件类型缺expert字段 | ✅ 已添加 |

---

## 待实现清单

- [x] 重写 `AgentCardFlip.tsx`：变形+曲线滑动+macOS拉伸发牌 ✅
- [x] 三张落地后边缘流光（CSS conic-gradient + hue-rotate） ✅
- [x] ExpertGlassPanel hover弹出专家隐藏信息 ✅
- [x] 协调者球固定右上角 + 持续呼吸 ✅
- [x] 思维流：球底金色细线 + 小标题逐个生长 ✅
- [x] SSE接入：协调者小标题事件（thinking_chunk复用） ✅
- [x] 修复已知Bug（API端口+ToolCall类型+SSE类型） ✅
- [ ] 删除死代码文件（8个） ✅
- [ ] 曲线路径更优雅（目前是简化位移，待优化）
- [ ] ReplayNavigator Math.random() Bug
- [ ] EngineChart 空数组崩溃
- [ ] useGameStore resetGame 状态清理

---

## 变更记录

### v3 (2026-03-23)
- 实现完整动画序列：翻面→收缩变形→曲线滑动→macOS拉伸发牌→落地居左→思维流
- 新建 `ThinkingStream.tsx`（协调者思维流组件，打字机效果）
- 重写 `AgentThinkingPanel.tsx`（左右分栏布局）
- 新增 `card-edge-glow` CSS keyframe
- Phase类型更新：`cardsLanded` + `streaming` 新增
- 修复3个已知Bug（API端口+类型定义）
- 删除8个死代码文件
- `pytest -q` 全绿 ✅

### v2 (2026-03-23)
- 全面重构扑克牌动画设计
- 新增三层Agent架构（三专家隐藏→协调者实时汇报→最终讲解）
- 修复J卡正面彩色Bug
- 标记7个死代码文件待删除
- 记录4个未修复Bug

### v1 (2026-03-19)
- 初始版本
- 建立完整前端文档体系

---

## 给接手AI的指示

1. **按顺序阅读**上方"必读顺序"中的4个文档
2. **重点读** `docs/frontend/plan/001-agent-poker-panel.md` — 包含完整设计
3. 修改代码前先读 `docs/frontend/FRONTEND_DNA.md` 了解约束
4. 涉及接口变更先更新 `API_CONTRACT.md`

### 变更处理原则

| 变更类型 | 处理方式 |
|----------|----------|
| 前端组件修改 | 直接在 `frontend/` 目录修改 |
| 接口变更 | 先更新 `API_CONTRACT.md`，用户批准后再改 |
| 新增API端点 | 找后端开发者在 `api/main.py` 中实现 |
| 文档更新 | 更新 `docs/frontend/` 下的相关文档 |

---

*本文档由AI维护，每次交接时更新*
