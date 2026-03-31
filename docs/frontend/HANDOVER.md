# 前端交接文档 — 液态玻璃改造

> 每次交接时更新本文档。新窗口的 AI 阅读本文档来快速上手工作。
> **必读顺序**：`docs/frontend/plan/002-liquid-glass.md` — 完整实施方案

---

## 架构（已确认）

```
z=0: WebGL Canvas (全屏)
│     ├── bg.jpg 背景
│     ├── 左侧栏（玻璃 + WebGL 按钮）
│     └── 右侧栏（玻璃 + WebGL 按钮）
│
z=1: DOM — ChessBoard + PokerCard (z=10+)
```

- 整个 UI 层（侧边栏、按钮、背景）都是 canvas
- DOM 只承载棋盘和扑克牌
- **复制粘贴优先**：参考项目 `liquid-glass-studio-main/src/App.tsx` 直接复制，不重写

---

## 参考项目（只读的圣经）

| 文件 | 用途 |
|------|------|
| `liquid-glass-studio-main/src/App.tsx` | 完整实现，复制起点 |
| `liquid-glass-studio-main/src/utils/GLUtils.ts` | 渲染器工具类，直接复制 |
| `liquid-glass-studio-main/src/shaders/*.glsl` | 所有 shader（已复制到 `frontend/src/shaders/liquidglass/`） |

**不要做的事**：
- 不要"理解后重写"渲染器——直接复制 `App.tsx` + `GLUtils.ts`
- 不要改 shader 一行代码
- 不要改 uniform 名字

---

## 当前状态

详细方案见 [002-liquid-glass.md](plan/002-liquid-glass.md)。

Phase 1 ✅ 已完成：
- `LiquidGlassApp.tsx` + `GLUtils.ts` — 直接复制参考项目
- Leva 参数调控面板已接入（右上角悬浮）
- 参考项目默认参数已恢复（blurRadius=1, refThickness=20）

Phase 2 进行中：
- 把玻璃位置从"鼠标拖动"改为"固定 sidebar 坐标"

---

## ⚠️ 已废弃的实现（不要参考）

以下文件是之前"重写"路线的产物，将被清理：
- `LiquidGlassRendererMini.tsx`
- `LiquidGlassSurface.tsx`
- `LiquidGlassBackground.tsx`
- `LiquidGlassGLUtils.ts`（已被 `GLUtils.ts` 覆盖）
- `LiquidGlassConfig.ts`

---

*本文档由AI维护，每次交接时更新*
