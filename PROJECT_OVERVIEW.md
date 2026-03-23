# 象棋 AI 混合代理教学与对弈系统

> **版本**: v3.28 | **最后更新**: 2026-03-23 | **阶段**: T0比赛冲刺

---

## 目录

- [1. 项目概述](#1-项目概述)
- [2. 系统架构](#2-系统架构)
- [3. 前端系统](#3-前端系统)
- [4. 后端系统](#4-后端系统)
- [5. 核心能力](#5-核心能力)
- [6. 当前状态](#6-当前状态)
- [7. 快速启动](#7-快速启动)

---

## 1. 项目概述

### 1.1 项目愿景

**象棋 AI 混合代理教学与对弈系统** 是一个让 AI 像教练一样**读懂棋局**、**讲解棋局**，而不是念坐标的智能系统。

传统的象棋引擎只能给出"炮二平五"这样的坐标式输出，本项目通过神经符号 AI 架构，实现：

- **教练式讲解**：基于事实的因果分析，解释"为什么这步好"
- **零幻觉**：规则标签 100% 准确，Evidence Map 约束 LLM
- **实时分析**：双模式响应，快速 <1秒 / 深度 3-5秒

### 1.2 核心价值

| 传统引擎 | 本系统 |
|---------|--------|
| 输出坐标（炮二平五） | 教练式讲解（为什么这样走） |
| 单一评分数字 | 多维度分析（战术+战略+引擎） |
| 黑盒计算 | 可解释的推理过程 |
| 无知识沉淀 | 融合棋理知识库 |

### 1.3 技术特色：神经符号 AI

```
┌─────────────────────────────────────────────────────────────┐
│                    神经符号 AI 架构                          │
├─────────────────────────────────────────────────────────────┤
│  规则引擎（符号）           LLM（神经）                       │
│  ┌─────────────────┐       ┌─────────────────┐             │
│  │ 45个战术标签     │  ───▶ │ Evidence Map    │             │
│  │ 100%准确无幻觉   │       │ 约束生成        │             │
│  └─────────────────┘       └─────────────────┘             │
│           │                        │                        │
│           ▼                        ▼                        │
│  ┌─────────────────────────────────────────────┐           │
│  │           教练式自然语言输出                   │           │
│  │  "红方马三进四将军，黑方必须应将..."            │           │
│  └─────────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────┘
```

**核心创新**：
- **Evidence Map**：规则检测的客观事实约束 LLM 生成，防止编造
- **三专家并行**：战术、战略、引擎三个 Agent 并行分析
- **自适应决策**：根据局面复杂度自动选择单/多 Agent 模式

---

## 2. 系统架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              用户界面层                                      │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                     React Frontend (TypeScript)                       │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │  │
│  │  │  ChessBoard │  │ AgentPanel  │  │ EngineChart │  │  PGNPanel   │ │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘ │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ REST API / SSE
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              API 服务层                                      │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                     FastAPI Backend (Python)                          │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │  │
│  │  │ /api/analyze│  │ /api/move   │  │ /api/pgn-*  │  │ /api/deep   │ │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘ │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            核心能力层                                        │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐               │
│  │   标签检测器    │  │  Agent 工具    │  │  多Agent协调器  │               │
│  │  (45个标签)    │  │  (10个工具)    │  │  (三专家并行)   │               │
│  └────────────────┘  └────────────────┘  └────────────────┘               │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐               │
│  │  Pikafish引擎  │  │  知识图谱      │  │  思维链模板     │               │
│  │  (深度计算)    │  │  (Neo4j)      │  │  (特级大师)     │               │
│  └────────────────┘  └────────────────┘  └────────────────┘               │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            数据/知识层                                       │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐               │
│  │  PGN 棋谱库    │  │  棋理知识库    │  │  向量数据库     │               │
│  │  (19万局)     │  │  (20+原则)    │  │  (规划中)      │               │
│  └────────────────┘  └────────────────┘  └────────────────┘               │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 技术栈一览

#### 前端技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| React | 18.2.0 | UI 框架 |
| TypeScript | 5.3.0 | 类型系统 |
| Vite | - | 构建工具 |
| Framer Motion | 11.0.0 | 动画库 |
| Zustand | 4.5.0 | 状态管理 |
| Axios | 1.6.0 | HTTP 客户端 |
| React Markdown | 9.0.0 | Markdown 渲染 |

#### 后端技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| FastAPI | 0.109.0 | Web 框架 |
| Uvicorn | 0.27.0 | ASGI 服务器 |
| LangGraph | 0.2.0 | Agent 框架 |
| LangChain | 0.3.0 | LLM 工具链 |
| Pikafish | - | 中国象棋引擎 |
| Neo4j | - | 知识图谱数据库 |
| Pytest | 9.0.0 | 测试框架 |

### 2.3 数据流图

#### 快速分析模式 (< 1秒)

```
用户走棋 ──▶ FEN 发送 ──▶ 标签检测器 ──▶ Evidence Map ──▶ 快速讲解
                                │
                                └──▶ 引擎评估 (bestmove, score)
```

#### 深度分析模式 (3-5秒, SSE流式)

```
用户请求深度分析
      │
      ▼
┌─────────────────────────────────────────────────────┐
│                  多 Agent 协调器                     │
│  ┌─────────────────────────────────────────────┐   │
│  │ 自适应决策：简单局面单Agent / 复杂局面三专家  │   │
│  └─────────────────────────────────────────────┘   │
│                    │                                │
│     ┌──────────────┼──────────────┐                │
│     ▼              ▼              ▼                │
│ ┌────────┐   ┌────────┐   ┌────────┐              │
│ │战术专家│   │战略专家│   │引擎专家│              │
│ │        │   │        │   │        │              │
│ │棋子攻防│   │局面评估│   │深度计算│              │
│ │战术组合│   │战略目标│   │候选走法│              │
│ └────────┘   └────────┘   └────────┘              │
│     │              │              │                │
│     └──────────────┼──────────────┘                │
│                    ▼                                │
│           ┌────────────────┐                       │
│           │   合成器       │                       │
│           │ 综合三方结论   │                       │
│           │ 生成统一讲解   │                       │
│           └────────────────┘                       │
└─────────────────────────────────────────────────────┘
      │
      ▼
  SSE 流式输出到前端
```

---

## 3. 前端系统

### 3.1 目录结构

```
frontend/
├── src/
│   ├── components/           # UI 组件
│   │   ├── AgentCardFlip.tsx       # 🎴 扑克牌翻面动画（核心）
│   │   ├── CardContent.tsx         # 扑克牌内容
│   │   ├── ThinkingStream.tsx      # 思维流组件
│   │   ├── ChessBoard.tsx          # 象棋棋盘
│   │   ├── AgentThinkingPanel.tsx  # Agent 思考面板
│   │   ├── DeepAnalysisPanel.tsx   # 深度分析面板
│   │   ├── ExpertCard.tsx          # 专家卡片
│   │   ├── EngineChart.tsx         # 引擎评分图表
│   │   ├── PGNPanel.tsx            # PGN 棋谱面板
│   │   ├── PositionAnalysisPanel.tsx # 局面分析面板
│   │   ├── ReplayNavigator.tsx     # 复盘导航器
│   │   ├── ReplayPanel.tsx         # 复盘面板
│   │   └── AgentDebutPanel.tsx     # Agent 登场动画
│   │
│   ├── store/                # 状态管理 (Zustand)
│   │   ├── useAgentStore.ts        # Agent 状态
│   │   └── useGameStore.ts         # 游戏状态
│   │
│   ├── services/             # API 服务层
│   │   └── api.ts                  # 后端 API 封装
│   │
│   ├── utils/                # 工具函数
│   │   └── pieces.ts               # 棋子显示工具
│   │
│   ├── App.tsx               # 主应用组件
│   ├── main.tsx              # 入口文件
│   ├── App.css               # 应用样式
│   └── index.css             # 全局样式（Liquid Glass）
│
├── package.json              # 依赖配置
├── tsconfig.json             # TypeScript 配置
└── vite.config.ts            # Vite 配置
```

### 3.2 核心组件详解

#### 3.2.1 AgentCardFlip.tsx - 扑克牌翻面动画

这是前端最核心的组件，实现了 Apple/WWDC 风格的复杂动画序列。

**动画阶段流程**：

```
T=0ms      idle: 三张扑克牌散开（K红心/J黑桃/Q方块）
T=100ms    stacking: 三张牌向中心聚拢成叠
T=600ms    flipped: 翻面完成，显示彩虹背面
T=700ms    morphing: 叠卡收缩变形
T=1100ms   orbMoving: 球体滑到右上角 + 逐张发牌
T=1500ms   cardsLanding: 三张落地左侧，整体垂直居中
T=2100ms   cardsLanded: 最终稳定布局
T=2600ms   streaming: 协调者思维流开始输出
```

**核心代码结构**：

```typescript
type FlipPhase = 'idle' | 'stacking' | 'flipped' | 'morphing' |
                 'orbMoving' | 'cardsLanding' | 'cardsLanded' | 'streaming';

// 三位专家定义
const EXPERT_TYPES: ExpertType[] = ['tactics', 'strategy', 'engine'];

const EXPERT_DETAILS = {
  tactics:  { rank: 'K', suit: '♥', color: '#dc2626' }, // 战术专家
  strategy: { rank: 'J', suit: '♠', color: '#1a1a1a' }, // 战略专家
  engine:   { rank: 'Q', suit: '♦', color: '#2563eb' }, // 引擎专家
};
```

**技术亮点**：
- Framer Motion 3D 动画（`rotateY`, `transformStyle: 'preserve-3d'`）
- CSS-in-JS 动态注入关键帧动画
- Portal 渲染确保层级正确
- 支持悬停交互，显示专家详情

#### 3.2.2 ThinkingStream.tsx - 思维流组件

显示协调者的实时分析输出：

```typescript
// 打字机效果显示流式内容
// 金色子弹点 + 渐变背景
// 与 Agent Store 集成
```

**视觉效果**：
- 打字机动画效果
- 金色渐变子弹点
- Markdown 内容渲染
- 自动滚动到底部

#### 3.2.3 ChessBoard.tsx - 棋盘组件

核心棋盘渲染和交互：

**功能**：
- 9×10 棋盘网格渲染
- 棋子拖拽移动
- 合法走法高亮
- 箭头提示（最佳走法）
- 悬停信息显示

**交互**：
- 点击选中棋子
- 拖拽走棋
- 右键取消选择
- 双击快速分析

#### 3.2.4 DeepAnalysisPanel.tsx - 深度分析面板

分析模式的主面板：

**三种模式**：
- 收起状态：显示三张专家扑克牌
- 快速分析：直接显示分析结果
- 深度分析：触发 AgentCardFlip 动画

### 3.3 状态管理 (Zustand)

#### useAgentStore - Agent 状态

```typescript
interface AgentStore {
  // 动画阶段
  phase: AgentAnimationPhase;
  setPhase: (phase: AgentAnimationPhase) => void;

  // 三位专家状态
  experts: Record<ExpertType, ExpertAgentState>;

  // 协调者状态
  orchestrator: OrchestratorState;

  // 面板控制
  isPanelActive: boolean;
  isAnalyzing: boolean;

  // 方法
  resetAll: () => void;
  updateExpert: (type: ExpertType, update: Partial<ExpertAgentState>) => void;
  appendExpertThinking: (type: ExpertType, chunk: string) => void;
  appendOrchestratorContent: (chunk: string) => void;
}
```

**动画阶段类型**：

```typescript
type AgentAnimationPhase =
  | 'collapsed'    // 收起状态
  | 'idle'         // 分析未开始
  | 'stacking'     // 叠卡阶段
  | 'flipped'      // 翻面完成
  | 'morphing'     // 收缩变形
  | 'orbMoving'    // 球体滑动
  | 'cardsLanded'  // 落地完成
  | 'streaming';   // 思维流输出
```

#### useGameStore - 游戏状态

```typescript
interface GameState {
  // 棋盘状态
  board: string[][];
  fen: string;
  history: string[];

  // 游戏模式
  gameMode: 'analysis' | 'pvp' | 'pve_red' | 'pve_black' | 'replay';

  // UI 状态
  flipped: boolean;           // 棋盘翻转
  showArrows: boolean;        // 显示提示箭头
  isBoardCollapsed: boolean;  // 棋盘收缩状态

  // 引擎历史
  evalHistory: EvalPoint[];
}
```

### 3.4 API 服务层

封装了与后端的所有通信：

```typescript
export const api = {
  // 分析接口
  analyzePosition: async (fen: string, board: string[][]): Promise<AnalyzeResponse>,
  analyzeDeep: async (data, onThinking, onResult, onError): Promise<void>,

  // 走棋接口
  makeMove: async (data: MoveRequest): Promise<MoveResponse>,
  aiMove: async (data: AIMoveRequest): Promise<AIMoveResponse>,
  getLegalMoves: async (data): Promise<LegalMovesResponse>,

  // 棋谱接口
  pgnLoad: async (pgn_content: string): Promise<PGNLoadResponse>,
  pgnNavigate: async (data): Promise<PGNNavigateResponse>,

  // 标签接口
  getTacticalTags: async (fen: string): Promise<TacticalTagsResponse>,
  getPositionAnalysis: async (fen: string): Promise<PositionAnalysisResponse>,

  // 搜索接口
  searchGames: async (params): Promise<GameSearchResponse>,
  getGameDetail: async (gameId: number): Promise<GameDetailResponse>,
};
```

**SSE 流式分析**：

```typescript
// 深度分析使用 EventSource API
analyzeDeep: async (data, onThinking, onResult, onError) => {
  const eventSource = new EventSource(fullUrl);

  eventSource.onmessage = (event) => {
    const json = JSON.parse(event.data);

    // 处理不同类型的事件
    if (json.type === 'thinking' || json.type === 'expert_start' ||
        json.type === 'synthesis_chunk') {
      onThinking(json);
    } else if (json.type === 'result') {
      onResult(json);
      eventSource.close();
    }
  };
}
```

### 3.5 设计系统 (Liquid Glass)

前端采用 **Apple Liquid Glass** 设计语言：

**核心 CSS 变量**：

```css
:root {
  /* 调色板 */
  --apple-bg: #E0DBD1;           /* 暖灰宣纸底 */
  --glass-bg: rgba(255,255,255,0.40);
  --glass-border: rgba(255,255,255,0.28);

  /* 物理光学 */
  --glass-blur: blur(28px) saturate(200%);
  --glass-shadow:
    inset 0  1.5px 0 rgba(255,255,255,0.30),
    inset 0 -1.5px 0 rgba(0,0,0,0.20),
    inset  1.5px 0 0 rgba(255,255,255,0.14),
    inset -1.5px 0 0 rgba(0,0,0,0.12);
}
```

**背景层次（8层）**：

```css
body {
  background:
    /* 1. 颗粒噪点层 */
    url("data:image/svg+xml,...feTurbulence..."),
    /* 2. 顶部深墨晕染 */
    linear-gradient(180deg, rgba(0,0,0,0.28) 0%, transparent 40%),
    /* 3. 左上自然光晕 */
    radial-gradient(ellipse at 15% 10%, rgba(255,250,240,0.35) 0%, transparent 50%),
    /* 4-8. 其他层次... */
    #E0DBD1;
}
```

**Liquid Glass 按钮**：

```css
.liquid-glass-btn {
  backdrop-filter: blur(12px) saturate(160%);
  background: rgba(255,255,255,0.40);
  border: 1px solid rgba(255,255,255,0.28);
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,0.5),   /* 顶部高光 */
    inset 0 -1px 0 rgba(0,0,0,0.1),         /* 底部暗边 */
    0 4px 16px rgba(0,0,0,0.1);             /* 外阴影 */

  /* 悬停效果 */
  &:hover {
    transform: scale(1.03);
    background: rgba(255,255,255,0.55);
  }
}
```

### 3.6 动画系统 (Framer Motion)

**Apple 弹簧参数**（来自 WWDC23）：

```typescript
// 换算公式
stiffness = (2π / duration)²
damping = 1 - 4π × bounce / duration

// 常用参数
const springs = {
  snappy:      { stiffness: 308, damping: 23 },  // duration=0.4s
  interactive: { stiffness: 395, damping: 28 },  // duration=0.35s
  smooth:      { stiffness: 260, damping: 26 },  // 通用
  bouncy:      { stiffness: 340, damping: 20 },  // 悬停效果
};
```

**动画编排示例**：

```tsx
// 扑克牌入场动画
<motion.div
  initial={{ opacity: 0, y: 20 }}
  animate={{ opacity: 1, y: 0 }}
  transition={{
    type: 'spring',
    stiffness: 320,
    damping: 26,
    mass: 0.75
  }}
>
  <CardContent type="tactics" />
</motion.div>
```

---

## 4. 后端系统

### 4.1 目录结构

```
api/
└── main.py                  # FastAPI 主入口（68KB）

core/
├── rules/                   # 规则引擎
│   ├── tactical_tags.py          # 45个标签定义
│   ├── tactical_detector.py      # 标签检测器（100KB，核心）
│   ├── tension_detector.py       # 张力检测器（6种类型）
│   └── xiangqi_rules.py          # 象棋规则定义
│
├── llm/                     # LLM 相关
│   ├── agent_tools.py            # 10个 Agent 工具（39KB）
│   ├── xiangqi_coach.py          # 教练 Agent（37KB）
│   ├── multi_agent_orchestrator.py # 多 Agent 协调器（17KB）
│   ├── thinking_templates.py     # 思维链模板
│   ├── opening_knowledge.py      # 开局知识库
│   └── fewshot_examples.py       # Few-shot 示例库
│
├── engine/                  # 引擎封装
│   └── pikafish_engine.py        # Pikafish 中国象棋引擎
│
├── kg/                      # 知识图谱
│   └── neo4j_kg.py              # Neo4j 数据库封装
│
├── semantic/                # 语义层
└── vision/                  # 视觉识别（规划中）
```

### 4.2 API 端点

#### 分析端点

| 端点 | 方法 | 说明 | 响应时间 |
|------|------|------|----------|
| `/api/analyze` | POST | 综合分析 | < 1s |
| `/api/analyze/deep-stream` | GET | 深度分析（SSE） | 3-5s |
| `/api/tactical-tags` | POST | 战术标签检测 | < 0.5s |
| `/api/position-analysis` | POST | 局面详细分析 | < 1s |
| `/api/move-quality` | POST | 走法质量检测 | < 0.5s |

#### 游戏端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/move` | POST | 执行走棋 |
| `/api/ai-move` | POST | AI 走棋 |
| `/api/legal-moves` | POST | 合法走法查询 |
| `/api/best-moves` | POST | 最佳走法查询 |

#### 棋谱端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/pgn-load` | POST | 加载 PGN 文件 |
| `/api/pgn-navigate` | POST | PGN 导航 |
| `/api/games/search` | POST | 搜索对局 |
| `/api/games/{id}` | GET | 获取对局详情 |

### 4.3 核心模块

#### 4.3.1 标签检测器（45个标签）

**九大层级**：

```
层级 1: 将杀困毙层   - checkmate, stalemate, check_threat
层级 2: 捉子层       - capture, capture_threat, fork, discovered_attack
层级 3: 闪击抽将层   - discovered_check, xray_attack
层级 4: 牵制串打层   - pin, skewer
层级 5: 标准杀法层   - double_check, smothered_mate, Arabian_mate
层级 6: 子力状态层   - hanging, protected, trapped, exchanged
层级 7: 走法质量层   - only_move, best_move, blunder, mistake
层级 8: 战略评估层   - material_balance, piece_activity, king_safety
层级 9: 引擎对齐层   - centipawn_loss, depth_reached
```

**检测原理**：

```python
class TacticalDetector:
    def detect_all(self, fen: str) -> List[TacticalTag]:
        """
        100% 规则硬判定，置信度二元化（0或1）
        绑定具体棋子坐标：格式 `颜色兵种-(x,y)`
        """
        tags = []

        # 检测将军
        if self._is_in_check(fen, 'red'):
            tags.append(TacticalTag(
                name='check',
                confidence=1.0,
                bind_pieces=[f"红帅-{king_pos}"]
            ))

        # 检测捉子
        for capture in self._find_captures(fen):
            tags.append(TacticalTag(
                name='capture',
                confidence=1.0,
                bind_pieces=[capture.attacker, capture.victim]
            ))

        return tags
```

#### 4.3.2 Agent 工具（10个工具）

**四类工具**：

| 类别 | 工具 | 说明 |
|------|------|------|
| 棋子关系 | `get_piece_attacks` | 获取棋子攻击范围 |
| | `get_piece_defenders` | 获取棋子保护者 |
| | `get_piece_constraints` | 获取棋子受限情况 |
| | `get_piece_mobility` | 获取棋子活动性 |
| 走法分析 | `get_legal_moves` | 获取合法走法 |
| | `analyze_move` | 分析走法效果 |
| | `compare_moves` | 对比多个走法 |
| 引擎分析 | `get_engine_analysis` | 获取引擎评估 |
| | `get_candidate_moves` | 获取候选走法 |
| 战略分析 | `evaluate_position` | 评估局面战略 |

**工具调用约束**：

```python
# 最多 3 轮调用
# 每轮最多 3 个工具
# 总耗时 < 5 秒
MAX_ROUNDS = 3
MAX_TOOLS_PER_ROUND = 3
TIMEOUT_SECONDS = 5
```

#### 4.3.3 多 Agent 协调器

**架构**：

```
                    ┌─────────────────────────┐
                    │     Orchestrator        │
                    │  自适应决策（简单/复杂） │
                    └────────────┬────────────┘
                                 │
         ┌─────────────────────┼─────────────────────┐
         ▼                     ▼                     ▼
  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐
  │  战术专家    │      │  战略专家    │      │  引擎专家    │
  │(TacticsAgent)│      │(StrategyAgent)│    │(EngineAgent)│
  └─────────────┘      └─────────────┘      └─────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │      Synthesizer        │
                    │  综合三方结论 → 统一讲解 │
                    └─────────────────────────┘
```

**自适应决策策略**：

| 条件 | 执行模式 |
|------|----------|
| 张力数量==0 且 开局 | 单 Agent 快速分析 |
| 张力<=2 | 单 Agent + 扩展轮次 |
| 张力>=3 或 CRITICAL | 多 Agent 并行 |
| 用户明确要求深度 | 多 Agent 并行 |

#### 4.3.4 引擎封装

```python
class PikafishEngine:
    """Pikafish 中国象棋引擎封装"""

    def analyze(self, fen: str, depth: int = 20) -> EngineResult:
        """
        返回：
        - bestmove: 最佳走法
        - score: 评估分数（厘兵值）
        - depth: 搜索深度
        - pv: 主变例
        """
        pass

    def get_alternatives(self, fen: str, count: int = 3) -> List[Move]:
        """获取多个候选走法"""
        pass
```

### 4.4 SSE 流式输出

**事件类型**：

| 事件类型 | 说明 |
|----------|------|
| `thinking` | 通用思考过程 |
| `expert_start` | 专家开始分析 |
| `expert_result` | 专家完成（含核心发现） |
| `expert_{name}_thinking` | 专家思考过程 |
| `expert_{name}_tool` | 专家工具调用 |
| `synthesis_chunk` | 合成器流式输出 |
| `orchestrator_subtitle` | 协调者副标题更新 |
| `result` | 最终结果 |
| `error` | 错误信息 |

**SSE 实现**：

```python
async def deep_analyze_stream(fen: str, request: Request):
    async def event_generator():
        # 1. 发送专家开始事件
        yield f"data: {json.dumps({'type': 'expert_start', 'expert': 'tactics'})}\n\n"

        # 2. 流式发送思考过程
        async for chunk in tactics_expert.analyze(fen):
            yield f"data: {json.dumps({'type': 'thinking_chunk', 'content': chunk})}\n\n"

        # 3. 发送专家结果
        yield f"data: {json.dumps({'type': 'expert_result', 'expert': 'tactics', 'finding': finding})}\n\n"

        # 4. 合成器综合
        async for chunk in synthesizer.synthesize(results):
            yield f"data: {json.dumps({'type': 'synthesis_chunk', 'content': chunk})}\n\n"

        # 5. 发送最终结果
        yield f"data: {json.dumps({'type': 'result', 'explanation': final})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )
```

---

## 5. 核心能力

### 5.1 标签检测体系

**标签分类（45个）**：

```
┌─────────────────────────────────────────────────────────────┐
│                     标签检测体系                             │
├─────────────────────────────────────────────────────────────┤
│  将杀困毙层 (3)    │ checkmate, stalemate, check_threat      │
│  捉子层 (4)       │ capture, capture_threat, fork, discovered│
│  闪击抽将层 (2)    │ discovered_check, xray_attack           │
│  牵制串打层 (2)    │ pin, skewer                             │
│  标准杀法层 (3)    │ double_check, smothered_mate, Arabian   │
│  子力状态层 (4)    │ hanging, protected, trapped, exchanged  │
│  走法质量层 (4)    │ only_move, best_move, blunder, mistake  │
│  战略评估层 (3)    │ material_balance, piece_activity, king  │
│  引擎对齐层 (2)    │ centipawn_loss, depth_reached           │
└─────────────────────────────────────────────────────────────┘
```

**标签输出格式**：

```json
{
  "name": "fork",
  "category": "capture_layer",
  "description": "一子同时攻击两个或以上目标",
  "confidence": 1.0,
  "bind_pieces": ["红马-(4,5)", "黑车-(4,7)", "黑炮-(6,5)"],
  "metadata": {
    "targets": ["黑车-(4,7)", "黑炮-(6,5)"],
    "attacker": "红马-(4,5)"
  }
}
```

### 5.2 Agent 工具调用

**工具示例**：

```python
# 战术专家可用工具
tactics_tools = [
    "get_piece_attacks",      # 获取棋子攻击范围
    "get_piece_defenders",    # 获取棋子保护者
    "get_piece_constraints",  # 获取棋子受限情况
    "get_legal_moves",        # 获取合法走法
    "analyze_move",           # 分析走法效果
    "get_engine_analysis",    # 获取引擎评估
]

# 战略专家可用工具
strategy_tools = [
    "evaluate_position",      # 评估局面战略
    "compare_moves",          # 对比多个走法
    "get_piece_mobility",     # 获取棋子活动性
    "get_engine_analysis",    # 获取引擎评估
]

# 引擎专家可用工具
engine_tools = [
    "get_engine_analysis",    # 获取引擎评估
    "get_candidate_moves",    # 获取候选走法
    "compare_moves",          # 对比多个走法
    "analyze_move",           # 分析走法效果
]
```

**Function Calling 集成**：

```python
# 工具定义示例
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_piece_attacks",
            "description": "获取指定棋子的攻击范围",
            "parameters": {
                "type": "object",
                "properties": {
                    "piece_id": {
                        "type": "string",
                        "description": "棋子ID，格式：颜色兵种-坐标，如 红马-(4,5)"
                    }
                },
                "required": ["piece_id"]
            }
        }
    }
]
```

### 5.3 双模式讲解

#### 快速模式 (< 1秒)

```python
def quick_analyze(fen: str) -> QuickAnalysisResult:
    """
    预计算 Evidence Map，直接返回标签+引擎数据
    """
    # 1. 标签检测（100% 准确）
    tags = tactical_detector.detect_all(fen)

    # 2. 引擎评估
    engine_result = engine.analyze(fen, depth=15)

    # 3. 知识库检索
    kg_result = kg.query_position(fen)

    # 4. 快速生成讲解
    explanation = quick_explain(tags, engine_result, kg_result)

    return QuickAnalysisResult(
        fen=fen,
        explanation=explanation,
        tags=tags,
        engine_result=engine_result
    )
```

#### 深度模式 (3-5秒, SSE)

```python
async def deep_analyze(fen: str) -> AsyncGenerator[SSEEvent, None]:
    """
    Agent 主动调用工具分析，SSE 流式返回
    """
    # 1. 自适应决策
    complexity = assess_complexity(fen)
    mode = decide_mode(complexity)

    if mode == "single":
        # 单 Agent 模式
        async for event in single_agent_analyze(fen):
            yield event
    else:
        # 多 Agent 并行模式
        async for event in multi_agent_analyze(fen):
            yield event
```

### 5.4 特级大师思维链

**阶段感知分析**：

```python
def detect_phase(fen: str) -> GamePhase:
    """
    根据棋子数量判断游戏阶段
    """
    piece_count = count_pieces(fen)

    if turn <= 15 and piece_count >= 26:
        return "opening"  # 开局
    elif 15 <= piece_count <= 27:
        return "middlegame"  # 中局
    else:
        return "endgame"  # 残局
```

**开局十大原则**：

```
1. 尽早出动大子
2. 避免子力拥堵
3. 重视中央控制
4. 避免走动帅将
5. 避免孤军深入
6. 避免浪费步数
7. 尽可能活马
8. 发挥车的威力
9. 开局炮略高于马
10. 适当联动士象
```

**思维链模板**：

```python
THINKING_TEMPLATE = """
## 阶段分析
当前处于【{phase}】阶段，{phase_description}

## 关键标签
{tags_summary}

## 战术分析
{tactics_analysis}

## 战略评估
{strategy_analysis}

## 引擎建议
{engine_analysis}

## 综合结论
{final_conclusion}
"""
```

---

## 6. 当前状态

### 6.1 模块进度表

| 模块 | 进度 | 状态 | 说明 |
|------|------|------|------|
| **标签检测体系** | ██████████ 100% | ✅ 完成 | 45个标签，41个测试用例 |
| **黄金局面测试** | ██████████ 100% | ✅ 完成 | mAP=1.0 |
| **张力检测器** | ██████████ 100% | ✅ 完成 | 6种张力类型 |
| **知识库** | ████████░░ 80% | 🔄 进行中 | 20+棋理原则 |
| **Agent 工具** | ██████████ 100% | ✅ 完成 | 10个工具 |
| **双模式 API** | ██████████ 100% | ✅ 完成 | 真Agent模式 |
| **SSE 流式输出** | ██████████ 100% | ✅ 完成 | 延迟问题已修复 |
| **前端** | ██████████ 100% | ✅ 完成 | Liquid Glass |
| **Neo4j 棋谱** | ████░░░░░░ 40% | 🔄 进行中 | 框架已搭建 |

### 6.2 最近更新

#### 2026-03-23 🎴 分析面板：重写 AgentCardFlip 动画

**动画序列**：
- T=0ms: 翻面完成，叠卡整齐显露彩虹背面
- T=600ms: 翻面完成 → morphing 开始
- T=1100ms: 三张依次弹出（macOS 最小化拉伸效果）
- T=1500ms: 协调者思维流开始输出

**新建文件**：
| 文件 | 说明 |
|------|------|
| `ThinkingStream.tsx` | 协调者思维流组件 |
| `CardContent.tsx` | 扑克牌内容组件 |

#### 2026-03-22 🎨 前端视觉增强

- 侧边栏 Liquid Glass 强化
- 亮暗双模式切换
- 高级通透背景（8层渐变）
- 分析面板宽度优化（380px → 620px）

#### 2026-03-21 🚀 多 Agent 并行架构

- 三专家并行：战术、战略、引擎
- 自适应决策策略
- SSE 新事件类型
- 降级策略

### 6.3 待办事项

#### 高优先级
- [ ] 验证走棋后深度分析无延迟
- [ ] Neo4j 数据完善

#### 中优先级
- [ ] 阶段检测优化（考虑过河判断）
- [ ] 中局思维链框架
- [ ] 三档讲解模式（初学者/进阶/教练）

---

## 7. 快速启动

### 7.1 环境要求

**后端**：
- Python 3.10+
- Neo4j 5.x（可选）
- Qwen API Key

**前端**：
- Node.js 18+
- npm 9+

### 7.2 启动命令

```bash
# 后端
python -m uvicorn api.main:app --host 0.0.0.0 --port 8002

# 前端
cd frontend && npm run dev

# 测试
pytest -q
```

**访问地址**：
- 前端：http://127.0.0.1:3000
- API 文档：http://127.0.0.1:8002/docs

### 7.3 常见问题

**Q: 前端连接不上后端？**

A: 检查 `frontend/src/services/api.ts` 中的 `API_BASE` 是否正确：
```typescript
const API_BASE = 'http://127.0.0.1:8002/api';
```

**Q: SSE 流式输出没有内容？**

A: 确保后端正确启动，检查控制台是否有错误日志。

**Q: 标签检测不准确？**

A: 运行测试验证：
```bash
pytest tests/test_tactical_detector.py -v
```

---

## 附录

### 相关文档

| 文档 | 位置 | 说明 |
|------|------|------|
| 项目 DNA | [docs/DNA.md](docs/DNA.md) | 项目愿景和架构 |
| 当前状态 | [docs/STATE.md](docs/STATE.md) | 开发进度 |
| 标签参考 | [docs/reference/tag_reference.md](docs/reference/tag_reference.md) | 45个标签定义 |
| Agent 工具 | [docs/reference/agent_tools_spec.md](docs/reference/agent_tools_spec.md) | 10个工具规范 |
| 前端开发 | [docs/frontend/FRONTEND_DNA.md](docs/frontend/FRONTEND_DNA.md) | 前端开发指南 |

### 技术亮点总结

1. **神经符号 AI**：规则引擎 100% 准确 + LLM 智能表达
2. **三专家并行**：战术、战略、引擎三个 Agent 并行分析
3. **Apple Liquid Glass**：现代化中式编辑风格设计
4. **SSE 流式输出**：实时展示 Agent 思考过程
5. **特级大师思维链**：阶段感知的专业讲解

---

**文档版本**: v1.0
**生成时间**: 2026-03-23
**作者**: Claude Code
