# 前端交接文档

> 每次交接时更新本文档。用户的 AI 会阅读本文档来了解前端进展并处理相关变更。

---

## 版本信息

| 版本 | 日期 | 更新人 | 说明 |
|------|------|--------|------|
| v1 | 2026-03-19 | AI | 初始版本 |

---

## 最近更新摘要

### 2026-03-19

- 建立了完整的前端文档体系
- 当前前端功能：棋盘、深度分析、局面分析、战术标签、复盘、PGN加载
- 状态管理使用 Zustand
- API 调用统一通过 `src/services/api.ts`

---

## 前端代码结构

```
frontend/
├── src/
│   ├── components/       # React 组件
│   │   ├── ChessBoard.tsx
│   │   ├── DeepAnalysisPanel.tsx
│   │   ├── PositionAnalysisPanel.tsx
│   │   ├── TacticalTagsPanel.tsx
│   │   ├── ReplayPanel.tsx
│   │   └── ReplayNavigator.tsx
│   ├── services/
│   │   └── api.ts       # API 调用入口
│   ├── store/
│   │   └── useGameStore.ts
│   ├── App.tsx
│   └── main.tsx
└── package.json
```

---

## 待办事项

### 高优先级
- [ ] 演示界面优化
- [ ] 移动端适配

### 中优先级
- [ ] 动画效果增强
- [ ] 走法提示优化

---

## 已知问题

- 无

---

## 变更记录

### v1 (2026-03-19)
- 初始版本
- 文档体系建立

---

## 给接手 AI 的指示

当接手前端工作时：

1. **阅读本文档**了解当前状态
2. **阅读 `docs/frontend/FRONTEND_DNA.md`** 了解开发约束
3. **检查 `docs/frontend/STATE.md`** 了解详细进度
4. **如有 plan 需要处理**，检查 `docs/frontend/plan/` 目录

### 变更处理原则

| 变更类型 | 处理方式 |
|----------|----------|
| 前端组件修改 | 直接在 `frontend/` 目录修改 |
| 接口变更 | 先更新 `API_CONTRACT.md`，用户批准后再改 |
| 新增 API 端点 | 找后端开发者在 `api/main.py` 中实现 |
| 文档更新 | 更新 `docs/frontend/` 下的相关文档 |

---

*本文档由 AI 维护，每次交接时更新*
