# 前端开发状态

> 记录前端开发的当前进度、最近更新、待办事项。

---

## 📊 模块进度

| 模块 | 进度 | 状态 | 说明 |
|------|------|------|------|
| 棋盘组件 | 100% | ✅ 完成 | ChessBoard.tsx |
| 引擎评分图 | 100% | ✅ 完成 | EngineChart.tsx |
| 深度分析面板 | 100% | ✅ 完成 | DeepAnalysisPanel.tsx |
| 局面分析面板 | 100% | ✅ 完成 | PositionAnalysisPanel.tsx |
| 战术标签面板 | 100% | ✅ 完成 | TacticalTagsPanel.tsx |
| 复盘功能 | 100% | ✅ 完成 | ReplayPanel.tsx |
| 状态管理 | 100% | ✅ 完成 | useGameStore.ts |
| 布局动画 | 100% | ✅ 完成 | CSS Grid + Apple Spring |
| 新组件 | 100% | ✅ 完成 | SynthesisPanel, ExpertCard, AgentDebutPanel, BottomTerminalPanel |
| Agent扑克牌 | 100% | ✅ 完成 | AgentCardFlip.tsx - 呼吸光晕 + 立体浮雕 + 纯净液态玻璃 |
| 左侧栏 DOM 清理 | 100% | ✅ 完成 | 删除冗余 aside，WebGL canvas 全屏穿透 |
| WebGL 液态玻璃 UI 层 | 20% | 🔄 进行中 | Phase 1 完成（左侧栏接管），Phase 2 进行中 |

---

## 最近更新

### 2026-03-30 - WebGL 液态玻璃 UI 层立项

**核心决策**：
- 推翻之前"重写渲染器"路线，改为**直接复制粘贴参考项目** `App.tsx` + `GLUtils.ts`
- 架构确认为：全 WebGL UI 层（除棋盘和扑克牌外），DOM 只保留 ChessBoard + PokerCard
- 详细方案见 `docs/frontend/plan/002-liquid-glass.md`
- 待清理：之前重写的 `LiquidGlassRendererMini.tsx` 等废弃组件

### 2026-03-23 - Agent扑克牌视觉效果升级

**核心变更**：
- `AgentCardFlip.tsx` 中 `CardVisual` 组件完全重写
- **呼吸光晕**：使用 `box-shadow` 动画直接作用在外壳，颜色循环变换（红→橙→黄 / 冰蓝→紫 / 蓝→青→靛）
- **立体浮雕文字**：多层 `text-shadow` 堆叠（顶部白色高光 → 底部黑色阴影 → 外层彩色发光）
- **纯净液态玻璃**：移除边缘流光和内部扫光，保留顶部折射高光 + 右下暗角
- 三种专家专属能量色系：
  - 战术 (K♥): `#ff4060` → `#ff9020` → `#ffdd00`
  - 战略 (J♠): `#c8d8ff` → `#a090ff` → `#e8c8ff`
  - 引擎 (Q♦): `#40b0ff` → `#5060ff` → `#40e0c0`

### 2026-03-22 - 布局重构：声明式响应式 Grid + 引擎窗口填充

**核心变更**：
- 外层 Flex → CSS Grid，`gridTemplateColumns: 240px 1fr 20vw→35vw`
- 棋盘动画：`scale(0.75) + x(-120) + y(-80)`，统一 Apple Spring (`stiffness: 260, damping: 26`)
- 引擎窗口：`position: absolute`，`left: 16, right: 16, bottom: 16`，`top` 动态跟随棋盘底部
- 移除 ResizeObserver/getBoundingClientRect/boardRef 等手动坐标计算
- 移除 `ChessBoard.onWidthChange` prop
- 新增文档：`ENGINE_CHART_DEBUG.md`、`FRONTEND_COMPLETE.md`

### 2026-03-21 - 组件扩充

- 新增 EngineChart.tsx（引擎评分折线图）
- 新增 SynthesisPanel.tsx（综合面板）
- 新增 ExpertCard.tsx（专家卡片）
- 新增 AgentDebutPanel.tsx（Agent登场动画）
- 新增 BottomTerminalPanel.tsx（底部终端面板）

### 2026-03-19 - 前端文档体系建立

- 新建 `docs/frontend/` 目录
- 建立前端宪法 `FRONTEND_DNA.md`
- 建立接口契约 `API_CONTRACT.md`
- 建立组件规范 `COMPONENT_GUIDE.md`
- 建立状态管理规范 `STATE_MANAGEMENT.md`
- 建立 AI Coding 指南 `AI_CODING_GUIDE.md`

---

## 布局架构

```
初始状态：                                    分析模式：
┌─────────┬──────────────────────────┬────────┐  ┌─────────┬──────────────────────┬──────────┐
│ 左侧栏   │      棋盘居中              │ 右侧栏  │  │ 左侧栏   │ 棋盘←──────────      │ 右侧栏    │
│ 16.6vw  │                          │ 16.6vw │  │         │  ↑缩小靠左上         │ 扩张到    │
│         │                          │        │  │         │ 引擎窗口填满剩余空间   │ 25vw     │
└─────────┴──────────────────────────┴────────┘  └─────────┴──────────────────────┴──────────┘
```

- Grid 第1列：左侧栏固定 240px
- Grid 第2列：中央区域（棋盘 + 引擎图）
- Grid 第3列：右侧栏 `20vw → 35vw`，CSS transition 平滑动画
- 棋盘收缩动画：`scale(0.75) + x(-120) + y(-80)`
- 引擎窗口：`position: absolute`，跟随棋盘底部位置

---

## 待办事项

### 高优先级

- [ ] 演示界面优化
- [ ] 移动端适配

### 中优先级

- [ ] 动画效果增强
- [ ] 走法提示优化

### 低优先级

- [ ] 主题切换功能
- [ ] 历史对局收藏

---

## 已知问题

- 无

---

## 对接后端注意事项

### 当前后端端口
- API 服务: `http://127.0.0.1:8002`

### 前端 API 调用层
- 所有后端调用通过 `src/services/api.ts`
- 不要直接在后端代码中调用 API

---

**最后更新**: 2026-03-30
