---
name: 组件开发规范
type: guide
version: 1.0.0
date: 2026-04-01
owner: AI（自动维护）
changelog:
  - v1.0.0 (2026-04-01): 从COMPONENT_GUIDE.md迁移
---

# 组件开发规范

> 本文档定义组件的开发规范和最佳实践。

---

## 一、组件分类

### 业务组件

| 组件 | 说明 |
|------|------|
| `ChessBoard.tsx` | 棋盘组件 |
| `EngineChart.tsx` | 引擎评分折线图 |
| `DeepAnalysisPanel.tsx` | 深度分析面板 |
| `PositionAnalysisPanel.tsx` | 局面分析面板 |
| `ReplayPanel.tsx` | 复盘面板 |

### Agent组件

| 组件 | 说明 |
|------|------|
| `AgentThinkingPanel.tsx` | Agent思考面板容器 |
| `AgentCardFlip.tsx` | 扑克牌翻面动画 |
| `ExpertCard.tsx` | 单专家卡片 |
| `SynthesisPanel.tsx` | 综合裁判面板 |
| `ThinkingStream.tsx` | 协调者思维流 |

### Liquid Glass组件

| 组件 | 说明 |
|------|------|
| `LiquidGlassApp.tsx` | WebGL主控 |
| `LiquidGlassSurface.tsx` | 通用表面 |
| `WebGLButton.tsx` | WebGL按钮 |

---

## 二、组件样式规范

### 优先使用内联样式

```typescript
const styles: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'center',
  alignItems: 'center',
};
```

### 使用设计系统变量

```typescript
// 优先使用 CSS 变量
const styles: React.CSSProperties = {
  color: 'var(--color-primary)',
  background: 'var(--color-bg)',
};
```

---

## 三、动画规范

### 弹簧动画优先使用Framer Motion

```typescript
import { motion } from 'framer-motion';

<motion.div
  initial={{ opacity: 0, scale: 0.9 }}
  animate={{ opacity: 1, scale: 1 }}
  transition={{ type: 'spring', stiffness: 300, damping: 30 }}
/>
```

### CSS动画用于持续循环

```css
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
```

---

## 四、组件测试

每个组件应包含基本的渲染测试：

```typescript
import { render, screen } from '@testing-library/react';
import { MyComponent } from './MyComponent';

test('renders without error', () => {
  render(<MyComponent />);
  expect(screen.getByRole('button')).toBeInTheDocument();
});
```

---

**文档版本**: v1.0.0
**最后更新**: 2026-04-01
