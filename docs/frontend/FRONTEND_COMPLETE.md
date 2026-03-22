# 前端完整技术文档

> 象棋 AI 混合代理教学与对弈系统 · 前端
> 文档版本: v1.0 · 更新: 2026-03-22

---

## 1. 项目概述

### 1.1 技术栈

| 类别 | 技术 |
|------|------|
| 框架 | React 18 + TypeScript |
| 构建 | Vite |
| 动画 | Framer Motion 5 |
| 状态管理 | Zustand |
| HTTP 客户端 | Axios |
| 实时通信 | EventSource (SSE) |
| 样式 | Tailwind CSS + 内联 CSS 对象 |
| 路由 | 无（单页应用） |

### 1.2 目录结构

```
frontend/src/
├── App.tsx                    # 主应用入口，三栏布局
├── main.tsx                   # React 挂载入口
├── index.css                  # 全局样式 + CSS动画
├── App.css                    # App级样式（默认Vite模板）
├── services/
│   └── api.ts                 # 所有API调用封装
├── store/
│   └── useGameStore.ts        # Zustand 全局状态
├── utils/
│   └── pieces.ts              # 棋子中文名映射
└── components/
    ├── ChessBoard.tsx         # 棋盘 + 棋子渲染
    ├── EngineChart.tsx        # 引擎评分折线图
    ├── DeepAnalysisPanel.tsx   # 深度分析时间轴
    ├── PositionAnalysisPanel.tsx  # 局面解析面板
    ├── TacticalTagsPanel.tsx   # 战术标签面板
    ├── ReplayPanel.tsx         # 棋谱回放（数据库/PGN）
    ├── ReplayNavigator.tsx     # 回放导航（滑块+按钮）
    ├── ExpertCard.tsx          # 专家卡片（工具+流式文字）
    ├── ExpertDebutPanel.tsx    # 三专家出场动画面板
    ├── SynthesisPanel.tsx      # 综合裁判面板（流式输出）
    ├── BottomTerminalPanel.tsx # 底部终端面板（可拖拽）
    ├── PGNPanel.tsx            # PGN导入面板（备用）
    └── StatCard.tsx            # 统计卡片
```

---

## 2. 全局状态管理

### 2.1 Zustand Store (`useGameStore.ts`)

**核心状态**：

```typescript
{
  board: string[][]          // 9×10 棋盘数组，小写=黑，大写=红
  fen: string               // FEN 格式棋谱
  previousFen: string        // 上一步的FEN（用于深度分析）
  history: string[]          // UCI走法记录
  legalMoves: string[]       // 当前选中棋子的合法走法
  selectedPos: {row, col}    // 选中棋子坐标
  isLoading: boolean         // 移动中加载状态
  redToMove: boolean         // 红方先行
  error: string | null       // 错误消息
  gameMode: GameMode         // 'analysis' | 'pvp' | 'pve_red' | 'pve_black' | 'replay'
  lastMove: {from, to}       // 上一步走法（用于高亮）
  flipped: boolean           // 翻转棋盘
  showArrows: boolean        // 显示AI推荐箭头
  isBoardCollapsed: boolean  // 棋盘收缩（触发分析模式动画）
  bestMoves: BestMovesResponse | null  // AI推荐走法
  highlightedPieces: []      // 高亮棋子（攻击/防守/目标）
  connectionLines: []         // 连接线（攻击/防守/牵制）
  evalHistory: EvalPoint[]    // 引擎评分历史
  replayState: {...}         // 回放状态
}
```

**主要 Action**：

| Action | 说明 |
|--------|------|
| `selectPiece(row, col)` | 选中棋子，调用API获取合法走法 |
| `movePiece(toRow, toCol)` | 走棋，调用API，执行翻转逻辑 |
| `aiMove()` | AI自动走棋（人机模式） |
| `fetchBestMoves()` | 获取红/黑双方AI推荐走法 |
| `setHighlightedPieces / setConnectionLines` | 设置棋盘高亮 |
| `toggleFlip()` | 翻转棋盘 |
| `toggleShowArrows()` | 切换箭头显示 |
| `resetGame()` | 重置到初始局面 |
| `searchGames(query)` | 搜索Neo4j对局 |
| `loadGameFromNeo4j(id)` | 加载指定对局 |
| `loadGameFromPGN(pgn)` | 解析PGN并加载 |
| `navigateReplay(dir, index)` | 回放导航 |
| `exitReplay()` | 退出回放 |

---

## 3. 布局架构

### 3.1 三栏布局（CSS Grid）

```
┌──────────────┬───────────────────────────┬──────────────────┐
│   左侧栏       │      中央 boardArea         │     右侧栏        │
│   240px      │   boardGroup (fit-content) │   20vw → 35vw   │
│   (固定)      │  (棋盘+引擎图垂直堆叠)       │   (分析面板)      │
│  Grid 第1列   │      Grid 第2列             │   Grid 第3列     │
└──────────────┴───────────────────────────┴──────────────────┘
```

**布局实现**：外层 `div (display:grid)` → Grid 三列
- 第1列：左侧栏固定 240px
- 第2列：`1fr` 自适应，中央区域
- 第3列：`20vw → 35vw`，由 `isBoardCollapsed` 控制
- Grid 容器 CSS transition 使列宽变化平滑

### 3.2 右侧栏宽度动画

```typescript
<motion.aside
  style={styles.rightSidebar}
  layout
  transition={{ type: 'spring', stiffness: 260, damping: 26 }}
>
```

- 分析模式（`isBoardCollapsed=true`）：右侧栏展开到 35vw
- 普通模式：收缩到 20vw
- 动画：统一 Apple Spring (`stiffness: 260, damping: 26`)

### 3.3 棋盘收缩动画

```typescript
<motion.div
  layout
  animate={{ scale: isBoardCollapsed ? 0.75 : 1 }}
  transition={{ type: 'spring', stiffness: 260, damping: 26 }}
  style={{ transformOrigin: '0 0', width: 'fit-content' }}
/>
```

- 收缩：仅 `scale: 0.75`，无手动 x/y 偏移
- `transformOrigin: '0 0'` 锚定左上角
- boardGroup 组合容器用 `width: fit-content` 锁定宽度

### 3.4 引擎窗口

```typescript
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

- `height: 0 → 'auto'` 从零高度展开动画
- `width: 100%` 跟随 boardGroup 宽度（=棋盘宽度）
- `AnimatePresence` 支持退出动画


---

## 4. 棋盘组件 (`ChessBoard.tsx`)

### 4.1 尺寸计算

```typescript
// 基础值
const BASE_CELL = 55;
const BASE_PAD = 32;
const COLS = 9;
const ROWS = 10;

// 根据视口动态计算
const targetWidth = (window.innerWidth - 32) * 0.8;
const targetHeight = (window.innerHeight - 32) * 0.85;
const cellByWidth = (targetWidth - BASE_PAD * 2) / 8;
const cellByHeight = (targetHeight - BASE_PAD * 2) / 9;
const newCell = Math.min(cellByWidth, cellByHeight, 150);  // 最大150px
const newPad = Math.max(newCell * 0.5, 16);

// 渲染宽高
const W = (COLS - 1) * CELL + PAD * 2;  // 8*CELL + 2*PAD
const H = (ROWS - 1) * CELL + PAD * 2;  // 9*CELL + 2*PAD
```

### 4.2 SVG 棋盘绘制

| 元素 | 说明 |
|------|------|
| 棋盘背景 | 双层 rect，外层深色内层浅色 |
| 横线 | 10条（中间不断） |
| 竖线 | 9条（楚河汉界处断开） |
| 九宫斜线 | 4条（将/帅九宫内） |
| 楚河汉界文字 | 两格高，中文字体 |
| 提示箭头 | SVG line + arrowhead + 评分气泡 |
| 战术连线 | SVG line（攻击=红虚线，防守=绿虚线，牵制=橙虚线） |

### 4.3 棋子层

- 使用 `position: absolute` 覆盖在 SVG 上方
- 通过 `marginTop: -H` 重叠
- 每个格子中心点定位：`left = PAD + col * CELL - CELL/2`

### 4.4 棋子外观

| 阵营 | 背景渐变 | 边框色 | 文字色 |
|------|----------|--------|--------|
| 红方 | `linear-gradient(#fff, #f0e6d3)` | `#C41E3A` | `#C41E3A` |
| 黑方 | `linear-gradient(#4a4a4a, #2a2a2a)` | `#333` | `#fff` |

- 选中时：`box-shadow: 0 0 0 4px #D4AF37` + `transform: scale(1.12)`
- 棋子尺寸：`CELL * 0.84`
- 字号：`CELL * 0.33`

### 4.5 棋盘宽度与引擎图联动

棋盘宽度通过 `boardGroup` 组合容器自动处理，无需手动测量。

**布局结构**：
- `boardArea`（Grid 第2列）：`alignItems: flex-start`，棋盘靠左对齐左侧栏
- `boardGroup`：用 `width: fit-content` 锁定为棋盘宽度
- 引擎图：`width: 100%`，自动等于棋盘宽度，紧贴棋盘下方展开

**棋盘动画**：`scale: 0.75`，`transformOrigin: '0 0'`（左上角锚点），无手动 x/y 偏移

**引擎图动画**：`height: 0 → 'auto'` 展开，`AnimatePresence` 包裹，支持退出动画

**ChessBoard 组件**：不再接收 `onWidthChange` prop

### 4.6 棋盘坐标

- 内部使用 row(0-9) × col(0-8)，row=0 是黑方底线
- 外部UCI坐标：`a0` 到 `i9`（列a-i，行0-9）
- FEN 坐标：列a-i，行9-1

---

## 5. 引擎评分图 (`EngineChart.tsx`)

### 5.1 两种模式

```typescript
// 固定尺寸模式
<EngineChart compact={false} fluid={false} />
// 宽480/高80 或 宽400/高120

// 流体模式（分析模式使用）
<EngineChart fluid={true} />
// 宽度由父容器决定，高度由 width/2
```

### 5.2 渲染逻辑

- SVG `viewBox` 固定宽高，`preserveAspectRatio="none"` 拉伸
- 评分 → 胜率映射：`1 / (1 + 10^(-cp/400))`
- 胜率曲线面积填充 + 评分折线
- 数据点动画（framer-motion pathLength）
- 最新数据点脉冲动画

### 5.3 分析模式下的定位

```typescript
// App.tsx 中的计算
const boardScale = isBoardCollapsed ? 0.75 : 1;
const boardVisualWidth = engineWidth * boardScale;

// 棋盘视觉中心（相对于 boardArea 左边缘）
// = boardRect.left - areaRect.left + boardRect.width * boardScale / 2
setBoardCenter(boardRect.left - areaRect.left + boardRect.width * boardScale / 2);

// 引擎图 left = 棋盘视觉左边缘
left: boardCenter - boardVisualWidth / 2

// 引擎图尺寸
width: boardVisualWidth
height: boardVisualWidth / 2
```

**关键修复**：`boardCenter` 的计算必须考虑 `scale` 变换，否则引擎图会偏右。

---

## 6. 右侧分析面板

### 6.1 四大标签页

| 标签 | 图标 | 面板组件 |
|------|------|----------|
| 深度分析 | 🧠 | `DeepAnalysisPanel` |
| 局面解析 | 🏰 | `PositionAnalysisPanel` |
| 战术标签 | 🏷️ | `TacticalTagsPanel` |
| 走法记录 | 📜 | `ReplayPanel` |

### 6.2 深度分析面板 (`DeepAnalysisPanel`)

- **模式切换**：快速/深度
- **分析按钮**：调用 `/api/analyze/deep-stream`（SSE）
- **时间轴**：流式渲染thinking节点
  - `thinking` → 黄色节点（流式累积内容）
  - `thinking_chunk` → 追加到上一个 `thinking` 节点
  - `tool_call` → 蓝色节点
  - `tool_result` → 绿色节点（可展开/收起）
  - `result` → 最终分析结果
- **动画**：节点依次出现，120ms 间隔

### 6.3 局面解析面板 (`PositionAnalysisPanel`)

- **三个子标签**：摘要 / 棋子 / 标签
- **总览卡片**：红黑子数、活跃棋子、受限棋子、是否被将军
- **棋子列表**：
  - 攻击棋子（红边框）
  - 战术棋子（金边框）
  - 受限棋子（灰边框）
- **标签云**：金黄色药丸标签 + 查询提示

### 6.4 战术标签面板 (`TacticalTagsPanel`)

- **按分类显示**：将杀困毙、捉子、闪击抽将、牵制串打、标准杀法、子力状态、局面语义
- **交互**：Hover 标签时棋盘高亮相关棋子 + 连接线
- **杀法检测**：绿色背景高亮框
- **局面语义徽章**：阶段（开局/中局/残局）、主动权、将帅危急

### 6.5 走法记录面板 (`ReplayPanel`)

- **两个标签**：数据库 / 导入PGN
- **数据库搜索**：输入棋手名或赛事 → Neo4j查询
- **PGN导入**：粘贴内容或上传文件
- **对局信息**：红黑方、赛事、日期、结果、总步数

---

## 7. 回放导航 (`ReplayNavigator`)

### 7.1 导航控制

- 四按钮：⏮ (开始) ◀ (上一步) ▶ (下一步) ⏭ (结束)
- 进度滑块：`0 ~ totalMoves`，点击跳转
- 进度条：金色渐变填充

### 7.2 当前走法卡片

- 显示 UCI 格式走法
- 自动讲解：根据走法字典返回预设描述

### 7.3 走法列表

- 彩色标签：红方(红底)/黑方(灰底)
- 激活项：金色背景 + 阴影
- 走法质量：↗优/→良/→中/↘差（随机模拟）

---

## 8. 三专家 Agent 系统

### 8.1 组件层级

```
AgentDebutPanel (出场动画编排)
├── ExpertDebutGrid (3列网格)
│   ├── OutlineCard (虚线框，Phase 2-3)
│   └── FullExpertCard (完整卡片，Phase 4+)
│       └── ExpertCard (战术/战略/引擎专家)
└── SynthesisPanel (综合裁判，流式输出)
```

### 8.2 出场动画相位

| Phase | 触发时间 | 效果 |
|-------|----------|------|
| 1 | 300ms | 三个呼吸光点出现 |
| 2 | 600ms | 三个专家虚线轮廓依次出现 |
| 3 | 900ms | 专家身份信息（名字）打字机效果 |
| 4 | 1200ms | 切换为完整 ExpertCard |

### 8.3 专家卡片 (`ExpertCard`)

每个专家卡片包含：

- **头部**：图标 + 专家名称 + 描述 + 状态徽章
- **状态**：`idle`(灰) / `thinking`(黄) / `completed`(绿) / `failed`(红)
- **思考区域**：流式打字机文字（25ms/字）
- **工具调用**：气泡式展示，可展开/收起详情
- **核心发现**：完成后显示关键结论

**三位专家**：

| 类型 | 图标 | 颜色 | 职责 |
|------|------|------|------|
| tactics | ⚔️ | 红色 | 棋子攻防·战术组合 |
| strategy | 🎯 | 橙色 | 全局态势·战略布局 |
| engine | 📊 | 蓝色 | 深度分析·候选走法 |

### 8.4 综合裁判 (`SynthesisPanel`)

- **共识区**：绿色背景，列出三位专家一致的观点
- **分歧区**：橙色背景，列出分歧点
- **最终讲解**：流式输出，打字机效果（18ms/字）
- **智能高亮**：
  - `**粗体**` → 白色粗体
  - `[工具名]` → 蓝色代码背景
  - `(坐标)` → 紫色等宽

### 8.5 底部终端面板 (`BottomTerminalPanel`)

- 从屏幕底部弹出的全宽面板
- **可拖拽调整高度**（鼠标拖动顶部把手）
- **Framer Motion 动画**：
  - 出现：`y: '100%' → 0`，spring 弹性
  - 背景遮罩：淡入淡出
- 高度范围：300px ~ 屏幕75%
- 高度保存到 localStorage
- **快捷键**：Esc 关闭

---

## 9. API 通信层 (`api.ts`)

### 9.1 Base URL

```typescript
const API_BASE = 'http://127.0.0.1:8003/api';
// 使用 127.0.0.1 避免 localhost DNS 解析延迟
```

### 9.2 所有接口

| 方法 | 接口 | 说明 |
|------|------|------|
| POST | `/position-analysis` | 局面结构化分析 |
| POST | `/analyze` | 局面综合分析 |
| POST | `/legal-moves` | 获取棋子合法走法 |
| POST | `/move` | 执行一步棋 |
| POST | `/ai-move` | AI走棋 |
| POST | `/best-moves` | 红/黑双方最佳走法 |
| POST | `/review` | 生成对局复盘 |
| POST | `/pgn-load` | 加载PGN棋谱 |
| POST | `/pgn-navigate` | PGN局面导航 |
| POST | `/tactical-tags` | 获取战术标签 |
| POST | `/games/search` | 搜索对局 |
| GET | `/games/{id}` | 获取对局详情 |
| GET(SSE) | `/analyze/deep-stream` | 深度分析流式输出 |

### 9.3 SSE 流式处理

```typescript
analyzeDeep(data, onThinking, onResult, onError) {
  // 1. 关闭旧连接（防止连接泄漏）
  if (api._activeEventSource) {
    api._activeEventSource.close();
  }

  // 2. 创建新 EventSource
  const eventSource = new EventSource(url);

  // 3. 事件处理
  eventSource.onmessage = (event) => {
    const json = JSON.parse(event.data);
    if (json.type === 'thinking' || 'thinking_chunk' || 'tool_call' || 'tool_result') {
      onThinking(json);  // 实时更新时间轴
    } else if (json.type === 'result') {
      onResult(json);    // 最终结果
      eventSource.close();
    } else if (json.type === 'error') {
      onError(json.message);
    }
  };
}
```

### 9.4 连接管理

- `_activeEventSource` 类属性：持有当前活跃连接
- 每次新建连接前关闭旧连接
- 防止浏览器连接数耗尽

---

## 10. 动画系统

### 10.1 Apple Spring 参数

```typescript
const APPLE_SPRING = {
  snappy:  { stiffness: 392, damping: 33 },  // 交互反馈
  smooth:  { stiffness: 300, damping: 30 },  // 面板展开
  engine:  { stiffness: 400, damping: 30 },  // 引擎窗口弹出
};
```

### 10.2 棋子动画

```typescript
// 落子缩放动画（Framer Motion）
<motion.div
  initial={{ scale: 0 }}
  animate={{ scale: 1 }}
  style={{ ... }}
/>
```

### 10.3 CSS 动画

| 动画名 | 效果 | 用途 |
|--------|------|------|
| `pulse` | 透明度+缩放 1→0.7→1 | 加载中、脉冲点 |
| `fadeIn` | 淡入+上移10px | 通用淡入 |
| `glow` | 盒阴影发光 | 专家思考发光 |
| `twinkle` | 星光闪烁 | 装饰粒子 |
| `floatCloud` | 祥云浮动 | 背景装饰 |
| `fadeInUp` | 向上淡入 | 时间轴节点 |
| `slideInFromTop` | 从顶部滑入 | 主要矛盾卡片 |
| `boardCollapsePop` | 收缩弹跳 | 棋盘收缩 |
| `boardExpandPop` | 展开弹跳 | 棋盘展开 |

### 10.4 引擎图动画

- `pathLength` 动画：0 → 1，800ms easeOut
- 评分数字弹跳：`key={score} initial={{ scale: 1.4 }} animate={{ scale: 1 }}`
- 最新点脉冲：`r: [8, 12, 8], opacity: [0.2, 0.4, 0.2]`

### 10.5 专家出场动画

- 呼吸光点：`scale [1, 1.08, 1]`，2秒循环
- 轮廓卡出现：`opacity 0→1`，120ms 间隔
- 身份打字机：35ms/字
- 完整卡片弹入：spring `stiffness: 260, damping: 22`，12% 间隔

---

## 11. 样式系统

### 11.1 主题色彩

| 用途 | 色值 |
|------|------|
| 主金色 | `#D4AF37` |
| 红色（红方） | `#C41E3A` |
| 黑色（黑方） | `#2C3E50` |
| 背景渐变 | `#FFF8F0 → #F5EDE4 → #EDE4D8` |
| 棋盘底色 | `#E8D4A8 → #D4C090` |
| 棋盘线 | `#6B5344` |
| 边框金色 | `rgba(212,175,55,0.3)` |

### 11.2 Tailwind 类使用

- `StatCard.tsx` 使用 Tailwind 类（`bg-paper-white/90`、`border-gilt-gold`）
- 其他组件全部使用内联 `React.CSSProperties`

### 11.3 全局 CSS 变量 / 工具类

```css
/* 滚动条 */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-thumb { background: linear-gradient(#D4AF37, #B8860B); }

/* 棋子交互 */
.chess-piece:hover { transform: scale(1.08) translateY(-2px); }
.chess-piece:active { transform: scale(0.95); }

/* 合法走法提示 */
.legal-move-indicator { animation: pulse-glow 1.2s infinite; }

/* 终端面板 */
.terminal-panel, .terminal-resize-handle, .terminal-titlebar { ... }
```

---

## 12. 棋子映射

```typescript
const PIECE_NAMES = {
  'K': '帅', 'k': '将',
  'A': '仕', 'a': '士',
  'B': '相', 'b': '象',
  'R': '车', 'r': '車',
  'C': '炮', 'c': '砲',
  'N': '马', 'n': '馬',
  'P': '兵', 'p': '卒',
};
```

---

## 13. 战术标签体系

### 13.1 七大分类

| 分类 | 颜色 | 标签示例 |
|------|------|----------|
| 将杀困毙层 | 红色 | 被将军、将死、困毙 |
| 捉子层 | 金色 | 攻无根、互吃、攻将邻 |
| 闪击抽将层 | 橙红 | 闪将、抽将、闪击 |
| 牵制串打层 | 紫色 | 被牵制、炮串打 |
| 标准杀法层 | 绿色 | 马后炮、铁门栓、双车错、卧槽马、白脸将、重炮杀、海底捞月、侧面虎 |
| 子力状态层 | 蓝色 | 子无根、炮有架 |
| 局面语义层 | 橙色 | 开局/中局/残局、将帅危急、主动权 |

### 13.2 棋盘高亮交互

- Hover 标签 → 解析 `bind_pieces` 坐标
- 第一个棋子：红色高亮（攻击方）
- 第二个棋子：目标色高亮
- 同时绘制连接线（攻击=红、防守=绿、牵制=橙）

---

## 14. 开发规范

### 14.1 组件样式

- 优先内联 `React.CSSProperties`
- Tailwind 仅在 `StatCard.tsx` 使用
- 颜色使用设计系统变量

### 14.2 动画优先使用 Framer Motion

- 弹簧动画 → `framer-motion`
- CSS 动画 → `index.css` 中 `@keyframes`
- 避免混用

### 14.3 API 调用规范

- 所有 API 通过 `services/api.ts` 封装
- SSE 连接通过 `_activeEventSource` 管理
- 错误处理：catch → setError

### 14.4 React.StrictMode

- 当前已禁用（注释状态）
- 原因：开发环境下双重渲染导致 SSE 连接泄漏

---

## 15. 启动方式

```bash
# 后端（端口8003）
python -m uvicorn api.main:app --host 0.0.0.0 --port 8003

# 前端（端口5173）
cd frontend && npm run dev

# 前后端联调
# 前端 Vite proxy 配置将 /api 转发到 127.0.0.1:8003
```
