# 组件开发规范

---

## 组件目录结构

```
frontend/src/components/
├── ChessBoard.tsx           # 棋盘主组件（核心）
├── DeepAnalysisPanel.tsx    # 深度分析面板
├── PositionAnalysisPanel.tsx # 局面分析面板
├── TacticalTagsPanel.tsx    # 战术标签面板
├── ReplayPanel.tsx         # 复盘面板
├── ReplayNavigator.tsx     # 复盘导航
├── PGNPanel.tsx            # PGN 面板
└── *.tsx                   # 其他组件
```

---

## 组件设计原则

### 1. 单一职责
每个组件只负责一个功能区域。

### 2. 受控组件
组件状态由父组件通过 props 控制，局部状态仅用于 UI 临时状态。

### 3. 纯展示 vs 容器

| 类型 | 特点 | 示例 |
|------|------|------|
| 纯展示组件 | 只接收 props，渲染 UI | `Piece.tsx` |
| 容器组件 | 连接 store，调用 API | `DeepAnalysisPanel.tsx` |

---

## ChessBoard 组件

**核心 Props**:
```typescript
interface ChessBoardProps {
  board: string[][];           // 10x9 棋盘数据
  onMove: (move: string) => void;  // 走棋回调
  lastMove?: { from: string; to: string };
  highlights?: string[];       // 高亮位置
  orientation?: 'red' | 'black';  // 视角
}
```

---

## 面板组件模式

深度分析、局面分析等面板遵循统一模式：

```typescript
// 面板组件标准结构
interface PanelProps {
  fen: string;           // 当前局面
  board: string[][];     // 棋盘数据
  onDataUpdate?: (data: any) => void;  // 数据更新回调
}

// SSE 流式数据处理
const handleSSEEvent = (event: MessageEvent) => {
  const [type, data] = parseSSEMessage(event.data);
  switch (type) {
    case 'thinking': setThinking(data); break;
    case 'tags': setTags(data.tags); break;
    case 'done': setExplanation(data.explanation); break;
  }
};
```

---

## 样式规范

### CSS 变量
```css
:root {
  --color-red: #c41e3a;      /* 红方 */
  --color-black: #1a1a1a;   /* 黑方 */
  --color-board: #deb887;    /* 棋盘底色 */
  --color-highlight: #4caf50; /* 高亮 */
  --font-chinese: 'KaiTi', 'STKaiti', serif;
}
```

### 命名规范
```
ChessBoard.tsx        # PascalCase
chess_board.css       # snake_case
```

---

## 状态管理模式

组件不直接调用 API，而是：

```typescript
// ✅ 正确方式：通过 store
const { fetchAnalysis } = useGameStore();
fetchAnalysis(fen);

// ❌ 错误方式：直接调用 API
const response = await api.analyze({ ... });
```

详见 `STATE_MANAGEMENT.md`

---

## 提交检查清单

- [ ] 组件有清晰的 props 接口定义
- [ ] 错误边界处理好（API 失败、网络错误）
- [ ] 加载状态有 UI 反馈
- [ ] 遵循现有的 CSS 变量规范
- [ ] 不直接操作 store 内部状态

---

**最后更新**: 2026-03-19
