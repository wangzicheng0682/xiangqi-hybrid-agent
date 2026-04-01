---
name: 状态管理规范
type: guide
version: 1.0.0
date: 2026-04-01
owner: AI（自动维护）
changelog:
  - v1.0.0 (2026-04-01): 从STATE_MANAGEMENT.md迁移
---

# 状态管理规范

> 本文档定义Zustand状态管理的规范和最佳实践。

---

## 一、Store结构

### useGameStore - 游戏状态

```typescript
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

  // === UI 状态 ===
  orientation: 'red' | 'black';
  showHints: boolean;
  gameMode: 'pvp' | 'pve_red' | 'pve_black' | 'replay';
  lastMove: {from, to};

  // === Actions ===
  selectPiece(row: number, col: number): void;
  movePiece(toRow: number, toCol: number): void;
  resetGame(): void;
  // ...
}
```

### useAgentStore - Agent状态

```typescript
interface AgentState {
  phase: AgentAnimationPhase;
  experts: Record<ExpertType, ExpertAgentState>;
  orchestrator: OrchestratorState;
  isPanelActive: boolean;
  isAnalyzing: boolean;
}
```

---

## 二、禁止事项

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
  const result = await api.analyze({ fen });
  useGameStore.getState().setAnalysisResult(result);
};
```

---

## 三、正确的分层

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

## 四、自定义 Hook 封装

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

## 五、状态持久化

部分状态需要持久化（localStorage）：

```typescript
const useGameStore = create(
  persist(
    (set, get) => ({
      // state
      orientation: 'red',
      showHints: true,
      // actions
      toggleOrientation: () => set(state => ({
        orientation: state.orientation === 'red' ? 'black' : 'red'
      })),
    }),
    {
      name: 'xiangqi-game',
      storage: createJSONStorage(() => localStorage),
      whitelist: ['orientation', 'showHints']  // 只持久化这些
    }
  )
);
```

---

## 六、提交检查清单

- [ ] 不直接修改 board 数组（通过 action）
- [ ] API 调用不在 store 中
- [ ] 有 loading/error 状态处理
- [ ] 组件订阅了正确的 state 切片

---

**文档版本**: v1.0.0
**最后更新**: 2026-04-01
