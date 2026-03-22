# API 接口契约

> **禁止擅自修改本文档**。接口变更必须先更新本文档，用户批准后再改代码。

---

## 接口变更流程

```
1. 提出变更需求（本文档）
2. 用户批准
3. 后端实现
4. 前端调用
```

---

## 核心接口列表

### 1. /api/analyze (POST)

**用途**: 综合分析局面

**请求**:
```typescript
{
  board: string[][];      // 10x9 棋盘
  fen: string;            // FEN 格式
  iccs_moves: string[];   // 历史走法 ICCS 格式
  last_move: string;      // 最后一步
  player: 'red' | 'black';
}
```

**响应**:
```typescript
{
  fen: string;
  explanation: string;           // 分析讲解
  engine_result: {               // 引擎分析
    bestmove: string;
    score: number;
    depth: number;
    pv: string[];
  } | null;
  kg_result: {                   // 知识图谱
    opening_name: string;
    win_rate: number;
    total_games: number;
    statistics: string;
  } | null;
  rag_results: Array<{            // RAG 检索
    book_name: string;
    content: string;
    relevance: number;
  }>;
  vision_result: {               // 视觉识别
    description: string;
    confidence: number;
  } | null;
  error: string;
}
```

---

### 2. /api/move (POST)

**用途**: 执行一步棋

**请求**:
```typescript
{
  move: string;        // ICCS 格式，如 "e2e3"
  fen: string;        // 当前 FEN
}
```

**响应**:
```typescript
{
  board: string[][];
  fen: string;
  legal_moves: string[];
  captured: string;     // 被吃的棋子
  in_check: boolean;
  game_over: boolean;
}
```

---

### 3. /api/legal-moves (POST)

**用途**: 获取合法走法

**请求**:
```typescript
{
  fen: string;
}
```

**响应**:
```typescript
{
  moves: string[];
  in_check: boolean;
}
```

---

### 4. /api/best-moves (POST)

**用途**: 获取 AI 推荐走法

**请求**:
```typescript
{
  fen: string;
  depth?: number;       // 默认 15
}
```

**响应**:
```typescript
{
  red_best_move: string;
  red_best_from_row: number;
  red_best_from_col: number;
  red_best_to_row: number;
  red_best_to_col: number;
  red_score?: number;
  black_best_move: string;
  black_best_from_row: number;
  black_best_from_col: number;
  black_best_to_row: number;
  black_best_to_col: number;
  black_score?: number;
  current_turn: string;
}
```

---

### 5. /api/analyze/deep (POST) - SSE 流式

**用途**: 深度分析（流式输出）

**请求**:
```typescript
{
  board: string[][];
  fen: string;
  iccs_moves: string[];
  last_move_info: {
    move: string;
    from: string;
    to: string;
  } | null;
  player: 'red' | 'black';
}
```

**响应**: Server-Sent Events (SSE)
```
event: thinking
data: {"stage": "分析阶段", "message": "正在分析局面..."}

event: tags
data: {"tags": ["双车错", "抽将"]}

event: done
data: {"explanation": "最终讲解内容"}
```

---

### 6. /api/pgn-load (POST)

**用途**: 加载 PGN 文件

**请求**:
```typescript
{
  pgn_content: string;
}
```

**响应**:
```typescript
{
  games: Array<{
    game_index: number;
    event: string;
    red_player: string;
    black_player: string;
    result: string;
    date: string;
    moves: string[];
  }>;
  total_games: number;
}
```

---

### 7. /api/pgn-navigate (POST)

**用途**: PGN 导航

**请求**:
```typescript
{
  pgn_content: string;
  game_index: number;
  target_index: number;    // -1=最后, 0=开始, N=第N步
}
```

**响应**:
```typescript
{
  board: string[][];
  fen: string;
  current_index: number;
  total_moves: number;
  move_text: string;
}
```

---

### 8. /api/position-analysis (POST)

**用途**: 局面结构分析

**请求**:
```typescript
{
  fen: string;
  board?: string[][];
}
```

**响应**:
```typescript
{
  analysis_structured: {
    phase: 'opening' | 'middlegame' | 'endgame';
    material: { red: number; black: number };
    piece_activity: { red: number; black: number };
    king_safety: { red: number; black: number };
    center_control: { red: number; black: number };
  };
  tags: string[];
  evidence_map: Record<string, any>;
}
```

---

## 响应格式约定

### 成功响应
```typescript
{
  success: true,
  data: { ... }
}
```

### 错误响应
```typescript
{
  success: false,
  error: "错误信息"
}
```

---

## 状态码约定

| 状态码 | 含义 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 500 | 服务器内部错误 |
| 503 | 服务不可用（如引擎未启动） |

---

**最后更新**: 2026-03-19
**变更记录**: 见 `STATE.md`
