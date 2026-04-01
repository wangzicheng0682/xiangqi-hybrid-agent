---
name: 前端开发指南
type: guide
version: 1.0.0
date: 2026-04-01
owner: AI（自动维护）
changelog:
  - v1.0.0 (2026-04-01): 合并FRONTEND_DNA.md, AI_CODING_GUIDE.md, FRONTEND_COMPLETE.md
---

# 前端开发指南

> 本文档是前端开发的综合指南，包含架构、设计规范、开发流程。

---

## 一、模块边界

### 只允许修改

```
frontend/           ✅ 可以修改
```

### 禁止修改（必须通过接口契约）

```
api/               ❌ 禁止修改
core/              ❌ 禁止修改
docs/              ❌ 禁止修改（除 docs/guides/ 外）
```

**如果需要后端能力** → 使用 `src/services/api.ts` 中定义的接口
**如果接口不满足需求** → 先更新 `docs/reference/api_contract.md`，用户批准后再改

---

## 二、技术栈

| 类别 | 技术 |
|------|------|
| 框架 | React 18 + TypeScript |
| 构建 | Vite |
| 动画 | Framer Motion 5 |
| 状态管理 | Zustand |
| 参数面板 | Leva |
| HTTP 客户端 | Axios |
| 实时通信 | EventSource (SSE) |
| 样式 | Tailwind CSS + 内联 CSS 对象 |
| 3D渲染 | WebGL（原生，无框架） |

---

## 三、目录结构

```
frontend/src/
├── App.tsx                    # 主应用入口，三栏布局
├── main.tsx                   # React 挂载入口
├── index.css                  # 全局样式 + CSS动画
├── services/
│   └── api.ts                 # 所有API调用封装（唯一后端通信入口）
├── store/
│   ├── useGameStore.ts        # Zustand 游戏状态
│   ├── useAgentStore.ts       # Zustand Agent状态
│   └── useGlassParamsStore.ts # Zustand 玻璃参数
├── utils/
│   ├── pieces.ts              # 棋子中文名映射
│   ├── LiquidGlassGLUtils.ts  # WebGL工具函数
│   └── LiquidGlassConfig.ts   # 玻璃配置常量
├── hooks/
│   ├── useLiquidGlass.ts      # 液态玻璃效果Hook
│   ├── useGlassPresets.ts     # 预设管理
│   └── useLiquidCardUniforms.ts # Uniforms管理
├── shaders/
│   └── liquidglass/
│       ├── vertex.glsl        # 顶点着色器
│       ├── fragment-main.glsl # 主渲染着色器（617行）
│       ├── fragment-bg.glsl   # 背景着色器
│       ├── fragment-bg-vblur.glsl  # 竖向模糊
│       ├── fragment-bg-hblur.glsl  # 横向模糊
│       └── fragment-button.glsl    # 按钮着色器
└── components/
    ├── ChessBoard.tsx         # 棋盘 + 棋子渲染
    ├── EngineChart.tsx        # 引擎评分折线图（纯SVG）
    ├── DeepAnalysisPanel.tsx  # 深度分析面板入口
    ├── AgentThinkingPanel.tsx # Agent思考面板容器
    ├── AgentCardFlip.tsx     # 扑克牌翻面动画核心
    ├── ExpertCard.tsx        # 单专家卡片组件
    ├── SynthesisPanel.tsx     # 综合裁判面板
    ├── PositionAnalysisPanel.tsx  # 局面分析面板
    ├── ReplayNavigator.tsx   # 复盘导航
    ├── ReplayPanel.tsx       # 复盘面板
    ├── PGNPanel.tsx          # PGN导入面板
    ├── ThinkingStream.tsx     # 协调者思维流
    ├── LiquidGlassApp.tsx     # WebGL液态玻璃主控
    ├── LiquidGlassSurface.tsx  # 通用液态玻璃表面
    ├── WebGLButton.tsx       # WebGL按钮
    └── CardVisualShader.tsx   # 扑克牌视觉着色器
```

---

## 四、设计理念

> "设计，为专注而生"

```
摒弃冗余的炫酷，回归体验的本质
以空间感，构建界面的秩序
用材质的差异，划分清晰的层级
降低认知负担，让注意力回归棋局本身
让技术隐于无形，让用户聚焦核心
```

### 核心原则

- **安静**：不抢注意力，让用户沉浸在棋局
- **克制**：每个元素都有存在的理由
- **材质隐喻**：玻璃材质暗示"通透"和"层级"
- **空间秩序**：用留白和位置传达信息优先级

---

## 五、Liquid Glass WebGL渲染

### 渲染管线（四步）

```
┌─────────────────────────────────────────────────────────────┐
│  Pass 1: bgPass                                             │
│  渲染: 背景 + 形状阴影                                        │
│  Shader: vertex.glsl + fragment-bg.glsl                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Pass 2: vBlurPass                                          │
│  渲染: 竖向高斯模糊                                           │
│  Shader: vertex.glsl + fragment-bg-vblur.glsl               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Pass 3: hBlurPass                                          │
│  渲染: 横向高斯模糊                                           │
│  Shader: vertex.glsl + fragment-bg-hblur.glsl               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Pass 4: mainPass (输出到屏幕)                               │
│  渲染: 折射 + 色散 + 菲涅尔 + Glare                          │
│  Shader: vertex.glsl + fragment-main.glsl                   │
└─────────────────────────────────────────────────────────────┘
```

### 渲染器架构

```
z=0: WebGL Canvas (全屏)
│     ├── bg.jpg 背景
│     ├── 左侧栏（玻璃 + WebGL 按钮）
│     └── 右侧栏（玻璃）

z=1: DOM — ChessBoard + PokerCard (z=10+)
```

### 参考项目

> **重要**：复制粘贴优先，不要"理解后重写"

| 文件 | 用途 |
|------|------|
| `liquid-glass-studio-main/src/App.tsx` | 完整实现，复制起点 |
| `liquid-glass-studio-main/src/utils/GLUtils.ts` | 渲染器工具类，直接复制 |
| `liquid-glass-studio-main/src/shaders/*.glsl` | 所有 shader |

### 不要做的事

- 不要"理解后重写"渲染器——直接复制 `App.tsx` + `GLUtils.ts`
- 不要改 shader 一行代码（除非有充分理由）
- 不要改 uniform 名字

---

## 六、状态管理

### 三个Store

```typescript
// 1. useGameStore - 游戏核心状态
interface GameState {
  board: string[][];              // 9x10棋盘
  fen: string;                    // FEN格式
  history: string[];              // 走法历史
  legalMoves: string[];           // 当前合法走法
  selectedPos: {row, col};       // 选中位置
  gameMode: 'pvp'|'pve_red'|'pve_black'|'replay';
  lastMove: {from, to};         // 最后一步
  evalHistory: EvalPoint[];      // 评分历史
}

// 2. useAgentStore - Agent状态
interface AgentStore {
  phase: AgentAnimationPhase;    // idle|stacking|flipped|morphing|streaming...
  experts: Record<ExpertType, ExpertAgentState>;
  orchestrator: OrchestratorState;
  isPanelActive: boolean;
  isAnalyzing: boolean;
}

// 3. useGlassParamsStore - 玻璃参数
// 使用 zustand/middleware persist，持久化到 localStorage
// Leva GUI 双向同步
```

### 禁止事项

```typescript
// ❌ 错误 - 不要直接修改 store 内部状态
store.board[5][4] = 'r';

// ✅ 正确 - 通过 action
setBoard(newBoard);

// ❌ 错误 - 不要在 store 中直接调用 API
async function fetchAnalysis() {
  const response = await api.analyze(...);
}

// ✅ 正确 - 在组件或自定义 hook 中调用 API
const handleAnalyze = async () => {
  const result = await api.analyze({ fen });
  useGameStore.getState().setAnalysisResult(result);
};
```

---

## 七、API调用规范

### Base URL

```typescript
const API_BASE = 'http://127.0.0.1:8002/api';
// 使用 127.0.0.1 避免 localhost DNS 解析延迟
```

### SSE流式处理

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
    if (json.type === 'result') {
      onResult(json);
      eventSource.close();
    }
  };
}
```

### 连接管理

- `_activeEventSource` 类属性：持有当前活跃连接
- 每次新建连接前关闭旧连接
- 防止浏览器连接数耗尽

---

## 八、动画系统

### Apple Spring 参数

```typescript
const APPLE_SPRING = {
  snappy:  { stiffness: 392, damping: 33 },  // 交互反馈
  smooth:  { stiffness: 300, damping: 30 },  // 面板展开
  engine:  { stiffness: 400, damping: 30 },  // 引擎窗口弹出
};
```

### 组件动画优先级

| 场景 | 工具 | 说明 |
|------|------|------|
| 弹簧动画 | Framer Motion | 布局、位置、scale动画 |
| CSS动画 | @keyframes | 持续循环、颜色变换 |
| 手写动画 | RAF + useEffect | 复杂逐帧动画 |

---

## 九、SSE事件类型

| 事件类型 | 说明 |
|----------|------|
| `expert_start` | 专家开始分析 |
| `expert_tactics_thinking` | 战术专家思考过程 |
| `expert_strategy_thinking` | 战略专家思考过程 |
| `expert_engine_thinking` | 引擎专家思考过程 |
| `expert_tactics_tool` | 战术专家工具调用 |
| `expert_result` | 专家完成（含核心发现） |
| `synthesis_chunk` | 合成器流式输出 |
| `orchestrator_subtitle` | 协调者思维流 |
| `result` | 最终结果 |
| `error` | 错误 |

---

## 十、开发流程

### Step 1: 阅读必读文档

```
1. docs/DNA.md                  ← 项目全貌（必读）
2. docs/STATE.md               ← 当前状态
3. docs/guides/frontend.md     ← 本文档
```

### Step 2: 确认工作范围

- 组件开发？→ 阅读 `docs/guides/component.md`
- 状态管理？→ 阅读 `docs/guides/state_management.md`
- Liquid Glass？→ 阅读 `docs/plans/frontend/002-liquid-glass.md`

### Step 3: 开发与提交

- 只在 `frontend/` 目录下修改
- 接口变更必须先更新 `docs/reference/api_contract.md`
- 提交前运行 `npm run build` 确保编译通过

---

## 十一、快速启动

```bash
# 安装依赖
cd frontend && npm install

# 开发模式
npm run dev

# 构建
npm run build

# 访问
# http://localhost:3000
```

---

**文档版本**: v1.0.0
**最后更新**: 2026-04-01
