# FastAPI接口契约文档

**发送者**: Kimi-K2.5 (后端)  
**接收者**: Gemini (前端)  
**日期**: 2026-03-09  
**主题**: REST API接口定义

---

## 一、API基础信息

### 1.1 服务地址
```
开发环境: http://localhost:8000
生产环境: 待定
```

### 1.2 通用响应格式
所有API返回JSON格式，包含以下字段：
```json
{
  "data": { ... },  // 响应数据
  "error": null      // 错误信息（如果有）
}
```

---

## 二、API端点详情

### 2.1 分析局面
**POST** `/api/analyze`

**请求体**:
```json
{
  "fen": "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1",
  "board": [
    ["r", "n", "b", "a", "k", "a", "b", "n", "r"],
    ["", "", "", "", "", "", "", "", ""],
    ["", "c", "", "", "", "", "", "c", ""],
    ["p", "", "p", "", "p", "", "p", "", "p"],
    ["", "", "", "", "", "", "", "", ""],
    ["", "", "", "", "", "", "", "", ""],
    ["P", "", "P", "", "P", "", "P", "", "P"],
    ["", "C", "", "", "", "", "", "C", ""],
    ["", "", "", "", "", "", "", "", ""],
    ["R", "N", "B", "A", "K", "A", "B", "N", "R"]
  ],
  "iccs_moves": ["h2e2", "h9g7"],
  "last_move_info": {
    "from_pos": "h2",
    "to_pos": "e2",
    "piece": "C",
    "notation": "炮二平五"
  },
  "use_vision": true
}
```

**响应体**:
```json
{
  "fen": "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1",
  "explanation": "## 当前局面分析\n\n### 引擎分析\n- 推荐着法: h2e2\n- 评估分数: +0.5\n\n### 知识图谱\n- 开局: 中炮开局\n- 胜率: 60%\n\n### AI讲解\n...",
  "engine_result": {
    "bestmove": "h2e2",
    "score": 0.5,
    "depth": 15,
    "pv": ["h2e2", "h9g7", "c3c4"]
  },
  "kg_result": {
    "opening_name": "中炮开局",
    "win_rate": 60.0,
    "total_games": 10000,
    "statistics": "红方胜率较高"
  },
  "rag_results": [
    {
      "book_name": "象棋开局原理",
      "content": "中炮开局是最流行的开局之一...",
      "relevance": 0.95
    }
  ],
  "vision_result": {
    "description": "当前局面红方略优...",
    "confidence": 0.9
  },
  "error": ""
}
```

---

### 2.1.1 深度分析流
**GET** `/api/analyze/deep-stream`

**用途**:
- 用于前端“深度分析”模式
- 以 SSE 逐条推送三位专家与协调者的分析进度
- 前端当前通过 `EventSource` 直接消费

**请求参数**:
```text
fen: string                必填，当前局面的 FEN
question: string           可选，默认“请分析当前局面”
move: string               可选，刚走的 UCI 走法
show_thinking: boolean     可选，默认 true
debug: boolean             可选，默认 false
```

**响应类型**:
```http
Content-Type: text/event-stream
```

**SSE 事件格式**:
每条消息均为：
```text
data: {json}\n\n
```

**事件类型**:

1. 通用进度事件
```json
{ "type": "thinking", "message": "启动分析..." }
{ "type": "thinking_chunk", "message": "..." }
{ "type": "tool_call", "message": "调用工具: ..." }
{ "type": "tool_result", "message": "工具返回摘要" }
```

2. 专家生命周期事件
```json
{ "type": "expert_start", "expert": "tactics" }
{ "type": "expert_result", "expert": "tactics", "summary": "一句话摘要", "finding": "完整专家结论", "success": true }
```

3. 专家步骤事件
```json
{ "type": "expert_step_start", "expert": "tactics", "step_index": 0, "title": "扫描将军威胁" }
{ "type": "expert_step_content", "expert": "tactics", "step_index": 0, "title": "扫描将军威胁", "content": "红方中炮正在压制中路..." }
{ "type": "expert_step_end", "expert": "tactics", "step_index": 0, "title": "扫描将军威胁", "duration_ms": 820 }
```

4. 专家兼容流事件
```json
{ "type": "expert_tactics_thinking", "message": "..." }
{ "type": "expert_tactics_chunk", "message": "..." }
{ "type": "expert_tactics_tool", "message": "..." }
{ "type": "expert_tactics_tool_result", "message": "..." }
```

5. 协调者事件
```json
{ "type": "orchestrator_subtitle", "message": "识别三位专家的共识" }
{ "type": "synthesis_step_start", "step_index": 0, "title": "识别三位专家的共识" }
{ "type": "synthesis_step_content", "step_index": 0, "title": "识别三位专家的共识", "content": "三位专家一致认为红方先手更主动..." }
{ "type": "synthesis_step_end", "step_index": 0, "title": "识别三位专家的共识", "duration_ms": 960 }
{ "type": "synthesis_chunk", "message": "..." }
{ "type": "result", "explanation": "最终讲解", "confidence": "high" }
{ "type": "error", "message": "错误信息" }
```

**专家字段取值**:
- `tactics`
- `strategy`
- `engine`

**前端消费约定**:
- `expert_step_start/content/end` 用于构建“专家步骤条目”
- `expert_result.summary` 用于摘要，`expert_result.finding` 用于完整结论展示
- `orchestrator_subtitle` 用于更新右侧“当前阶段”标题区
- `synthesis_step_start/content/end` 用于构建“协调者综合步骤”
- `synthesis_chunk` 作为右侧内容区的实时流式正文

---

### 2.2 获取合法走法
**POST** `/api/legal-moves`

**请求体**:
```json
{
  "board": [...],  // 10x9棋盘数组
  "row": 7,        // 棋子所在行 (0-9)
  "col": 1         // 棋子所在列 (0-8)
}
```

**响应体**:
```json
{
  "moves": ["a0", "c0", "e2", "g4", "i8"],  // ICCS格式的合法走法
  "in_check": false  // 当前是否被将军
}
```

---

### 2.3 执行走棋
**POST** `/api/move`

**请求体**:
```json
{
  "board": [...],       // 10x9棋盘数组
  "from_row": 7,        // 起始行
  "from_col": 1,        // 起始列
  "to_row": 7,          // 目标行
  "to_col": 4,          // 目标列
  "red_to_move": true   // 当前是否红方走棋
}
```

**响应体**:
```json
{
  "board": [...],       // 走棋后的新棋盘
  "fen": "...",         // 新局面的FEN
  "legal_moves": [],    // 目标位置棋子的合法走法
  "captured": "",       // 被吃的棋子（如果有）
  "in_check": false,    // 对方是否被将军
  "game_over": false    // 游戏是否结束
}
```

---

### 2.4 生成复盘报告
**POST** `/api/review`

**请求体**:
```json
{
  "red_player": "红方",
  "black_player": "黑方",
  "result": "1-0",     // "1-0", "0-1", "1/2-1/2", "*"
  "moves": ["h2e2", "h9g7", "c3c4", "b7c5"]
}
```

**响应体**:
```json
{
  "report_markdown": "# 复盘报告\n\n## 对局概览\n...",
  "chart_data": {
    "labels": [0, 1, 2, 3, 4],
    "scores": [0, 50, -100, 200, 300],
    "turning_points": [2, 4],
    "blunders": [2]
  },
  "turning_points": [
    {
      "move_number": 2,
      "score_change": -150,
      "description": "黑方失误",
      "is_red_move": false
    }
  ],
  "blunders": [2]
}
```

---

## 三、数据格式说明

### 3.1 棋盘数组
```typescript
type Board = string[][];  // 10行9列
// 大写 = 红方棋子, 小写 = 黑方棋子
// K/k = 将帅, A/a = 士, B/b = 象, R/r = 车, C/c = 炮, N/n = 马, P/p = 兵卒
// 空字符串 = 无棋子
```

### 3.2 ICCS走法格式
```
格式: {from_col}{from_row}{to_col}{to_row}
示例: h2e2 = 从h2走到e2
列号: a-i (从左到右)
行号: 0-9 (从下到上，红方视角)
```

### 3.3 FEN格式
```
标准象棋FEN格式
示例: rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1
```

---

## 四、错误处理

### 4.1 错误响应格式
```json
{
  "detail": "错误描述"
}
```

### 4.2 HTTP状态码
- 200: 成功
- 400: 请求参数错误
- 500: 服务器内部错误

---

## 五、前端调用示例

```typescript
import axios from 'axios';

const API_BASE = 'http://localhost:8000/api';

// 分析局面
const analyzeResult = await axios.post(`${API_BASE}/analyze`, {
  fen: currentFen,
  board: currentBoard,
  use_vision: true
});

// 获取合法走法
const legalMoves = await axios.post(`${API_BASE}/legal-moves`, {
  board: currentBoard,
  row: selectedRow,
  col: selectedCol
});

// 执行走棋
const moveResult = await axios.post(`${API_BASE}/move`, {
  board: currentBoard,
  from_row: fromRow,
  from_col: fromCol,
  to_row: toRow,
  to_col: toCol,
  red_to_move: isRedTurn
});

// 生成复盘报告
const reviewResult = await axios.post(`${API_BASE}/review`, {
  red_player: "红方",
  black_player: "黑方",
  result: "1-0",
  moves: moveHistory
});
```

---

## 六、启动后端服务

```bash
# 安装依赖
pip install fastapi uvicorn python-multipart

# 启动服务
cd d:\xiangqi-hybrid-agent
uvicorn api.main:app --reload --port 8000
```

服务启动后访问:
- API文档: http://localhost:8000/docs
- 健康检查: http://localhost:8000/health

---

**Gemini, 以上是完整的API接口契约。请基于这些API设计前端组件。**
