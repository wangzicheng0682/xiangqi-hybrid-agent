# 状态管理规范

---

## Store 结构

```typescript
// frontend/src/store/useGameStore.ts

interface GameState {
  // === 棋盘状态 ===
  board: string[][];           // 当前棋盘 10x9
  fen: string;                 // FEN 格式
  currentTurn: 'red' | 'black';
  legalMoves: string[];
  
  // === 历史记录 ===
  moveHistory: string[];        // ICCS 格式走法历史
  historyIndex: number;          // 当前历史位置
  
  // === 分析结果 ===
  analysisResult: AnalysisResult | null;
  isAnalyzing: boolean;
  analysisError: string | null;
  
  // === PGN 相关 ===
  pgnGames: PGNGameInfo[];
  currentGameIndex: number;
  
  // === UI 状态 ===
  orientation: 'red' | 'black';
  showHints: boolean;
  
  // === Actions ===
  // ... actions
}
```

---

## 禁止事项

### ❌ 禁止在组件中直接修改 store 内部状态

```typescript
// ❌ 错误
store.board[5][4] = 'r';  // 直接修改

// ✅ 正确
setBoard(newBoard);  // 通过 action
```

### ❌ 禁止在 store 中直接调用 API

```typescript
// ❌ 错误 - store 不应该有 API 逻辑
async function fetchAnalysis() {
  const response = await api.analyze(...);  // 不应该在 store 里
}

// ✅ 正确 - 在组件或自定义 hook 中调用 API
const handleAnalyze = async () => {
  const result = await api.analyze(fen);
  useGameStore.getState().setAnalysisResult(result);
};
```

---

## 正确的分层

```
组件 (Component)
    ↓ 调用
Action (useGameStore.actions)
    ↓ 更新
State (useGameStore.getState())
    ↓ 触发
UI 更新 (自动)
```

---

## 自定义 Hook 封装

将 API 调用封装为自定义 Hook：

```typescript
// frontend/src/hooks/useAnalysis.ts
export function useAnalysis() {
  const { fen, setAnalysisResult, setAnalyzing, setError } = useGameStore();
  
  const analyze = async () => {
    setAnalyzing(true);
    try {
      const result = await api.analyze({ fen });
      setAnalysisResult(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setAnalyzing(false);
    }
  };
  
  return { analyze };
}
```

---

## 状态持久化

部分状态需要持久化（localStorage）：

```typescript
// 在 store 中
const persistConfig = {
  key: 'xiangqi-game',
  storage: localStorage,
  whitelist: ['orientation', 'showHints']  // 只持久化这些
};
```

---

## 提交检查清单

- [ ] 不直接修改 board 数组（通过 action）
- [ ] API 调用不在 store 中
- [ ] 有 loading/error 状态处理
- [ ] 组件订阅了正确的 state 切片

---

**最后更新**: 2026-03-19
