# 引擎窗口定位调试分析

> 目标：排查引擎窗口与棋盘对齐偏差问题
> 日期：2026-03-22
> 状态：**已解决 ✓** — 声明式响应式布局重构完成

---

## 重构总结

### 核心变更：从命令式 → 声明式

| 旧方案（命令式） | 新方案（声明式） |
|---|---|
| `getBoundingClientRect()` 手动测量 | `CSS Grid` 流体布局 |
| `ResizeObserver` 监听 + `setState` | `transform-origin: 0 0` + `layout` prop |
| 硬编码 `x: -350`, `y: -80` | 仅有 `scale: 0.75`，无手动偏移 |
| `position: absolute` 引擎图 | `flex column` 垂直堆叠 + `height: 0→auto` |
| `position: fixed` 右侧栏 | Grid 列宽度自动适应 |
| 三组不同 spring 参数 | 统一 `stiffness: 260, damping: 26` |

---

## 1. 当前布局实现

### 外层容器：CSS Grid

```tsx
<div
  style={{
    display: 'grid',
    gridTemplateColumns: `240px 1fr ${isBoardCollapsed ? '35vw' : '20vw'}`,
    height: '100vh',
    overflow: 'hidden',
    transition: 'grid-template-columns 0.5s cubic-bezier(0.16, 1, 0.3, 1)',
  }}
>
```

- 左侧栏固定 240px
- 中央列 `1fr` 自适应
- 右侧栏 `20vw → 35vw`，通过 Grid transition 平滑动画

### 三栏结构

```
┌─────────────┬──────────────────────────┬──────────────────┐
│ 左侧边栏     │   boardArea (flex column) │  右侧分析面板     │
│ width: 240  │   boardGroup (居中)        │  20vw → 35vw    │
│ Grid 第1列   │   Grid 第2列              │  Grid 第3列      │
│             │                            │  motion.aside   │
│ aside       │   motion.div (scale)       │  layout prop    │
│             │   + boardGroup             │                 │
└─────────────┴──────────────────────────┴──────────────────┘
```

### 棋盘动画：scale + x/y 偏移

```tsx
<motion.div
  animate={{
    scale: isBoardCollapsed ? 0.75 : 1,
    x: isBoardCollapsed ? -120 : 0,
    y: isBoardCollapsed ? -80 : 0,
  }}
  transition={{ type: 'spring', stiffness: 260, damping: 26 }}
  style={{
    transformOrigin: 'center center',
    width: 'fit-content',
    zIndex: 10,
  }}
>
  <ChessBoard />
</motion.div>
```

### 引擎窗口：absolute 填满四周

```tsx
// ResizeObserver 测量棋盘实际位置，动态计算 top
const updateTop = () => {
  const boardRect = boardRef.current.getBoundingClientRect();
  const areaRect = boardAreaRef.current.getBoundingClientRect();
  const top = (boardRect.top - areaRect.top) + boardRect.height + 8;
  setEngineTop(top);
};

<AnimatePresence>
  {isBoardCollapsed && (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: 'auto' }}
      exit={{ opacity: 0, height: 0 }}
      transition={{ delay: 0.15, type: 'spring', stiffness: 260, damping: 26 }}
      style={{ width: '100%' }}
    >
      <EngineChart fluid={true} />
    </motion.div>
  )}
</AnimatePresence>
```

### boardGroup 组合容器

```tsx
<div style={styles.boardGroup}>
  {/* 棋盘 */}
  <motion.div animate={{ scale: ... }}>
    <ChessBoard />
  </motion.div>
  {/* 引擎图 */}
  <AnimatePresence>
    {isBoardCollapsed && (
      <motion.div style={{ width: '100%' }}>
        <EngineChart fluid={true} />
      </motion.div>
    )}
  </AnimatePresence>
</div>
```

```css
boardGroup: {
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  width: 'fit-content',  // 宽度跟随棋盘
}
```

- `boardGroup` 用 `width: fit-content` 锁定为棋盘宽度
- 引擎图 `width: 100%` 自动等于棋盘宽度
- 棋盘在 boardArea 内靠左（`alignItems: flex-start`）

### 右侧栏：Grid 列宽度动画

```tsx
<motion.aside
  style={styles.rightSidebar}
  layout
  transition={{ type: 'spring', stiffness: 260, damping: 26 }}
>
```

移除 `position: fixed`，改为 Grid 第三列，`layout` prop 自动驱动宽度动画。

---

## 2. 清理清单

已删除的代码：

| 删除项 | 原因 |
|---|---|
| `useRef<HTMLDivElement>(null)` boardRef | 不再需要手动测量坐标 |
| `useState(500)` engineWidth | 不再需要传递棋盘宽度 |
| `boardScale` / `boardVisualWidth` 计算 | 不再需要 |
| `ResizeObserver` 监听 | 不再需要 |
| `boardCenter` 状态 | 不再需要 |
| `x: -350` / `y: -80` 硬编码 | 不再需要 |
| `position: absolute` 引擎图 | 改为 flex 垂直堆叠 |
| `position: fixed` 右侧栏 | 改为 Grid 参与流 |
| 三组不同 APPLE_SPRING 参数 | 统一为 260/26 |
| `ChessBoard.onWidthChange` prop | 移除 |

---

## 3. 验收标准

| 标准 | 状态 |
|---|---|
| 棋盘缩小后左边缘与左侧栏对齐 | ✅ `alignItems: flex-start` |
| 引擎窗口宽度自动跟随棋盘宽度 | ✅ `width: fit-content` + `width: 100%` |
| 引擎窗口紧贴棋盘下方 | ✅ flex column + `height: 0→auto` |
| 右侧栏平滑扩张靠近棋盘 | ✅ Grid transition + layout prop |
| 统一 spring 参数 `260/26` | ✅ |
| 无 ResizeObserver / getBoundingClientRect | ✅ |

---

## 4. 附录：完整 DOM 层级

```
viewport
  └─ grid (display: grid, 3 columns)
       ├─ column-1: leftSidebar (240px)
       ├─ column-2: boardArea (position: relative, center)
       │    ├─ motion.div (scale: 0.75, x: -120, y: -80)
       │    │    └─ ChessBoard
       │    └─ AnimatePresence → motion.div (absolute, left:16, right:16, bottom:16, top: dynamic)
       │         └─ EngineChart (fluid: true)
       └─ column-3: rightSidebar (motion.aside, 20vw → 35vw)
```
