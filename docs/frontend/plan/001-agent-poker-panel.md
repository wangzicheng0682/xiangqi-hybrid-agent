# 专家 Agent 扑克牌展示面板

## 背景

用户想要在右侧边栏（展开宽度 620px）中实现三个专家 Agent 的可视化展示。设计概念：
1. Agent 绘制成扑克牌样式，以"发牌"动画登场
2. 牌发在栏的左侧，从上到下三张垂直堆叠
3. 发完之后逐个掀开，占住左边
4. 右侧模仿 Claude 的实时思考流 —— 时间线 + **动态生成的小标题**（非固定写死）
5. **风格要求**：Apple 般丝滑动效（WWDC25 Liquid Glass 风格），扑克牌发牌动画要生动
6. 尺寸约束：**原有尺寸和扩张后尺寸绝对不能动**（260px 收起 / 620px 展开）

---

## 权限边界

- ❌ **不动**：侧边栏外壳（glass-panel-deep 容器）、顶部 Tab 栏（◈◇◎≡ 图标按钮）、主题 CSS 变量、整体配色
- ✅ **可动**：Tab 内容区 `tabContent` 内部的全部内容
- **当前范围**：只实现**深度分析** Tab（AgentThinkingPanel），其他三个 Tab 以后再加

---

## 设计语言

### 动效核心参数（Apple Spring Physics）

| 类型 | Stiffness | Damping | Mass | 用途 |
|------|-----------|---------|------|------|
| smooth | 300 | 28 | 0.9 | 基础交互 |
| bounce | 400 | 20 | 0.7 | 弹性弹出 |
| deal | 450 | 22 | 0.6 | 扑克牌发牌（速度感） |
| flip | 350 | 25 | 0.8 | 翻牌（3D 旋转） |

Apple 缓动曲线：`cubic-bezier(0.16, 1, 0.3, 1)`

### Liquid Glass 视觉

- 主面板：`backdrop-filter: blur(20px) saturate(180%)`，`background: rgba(255,255,255,0.12)`
- 卡片：半透明玻璃 + 微妙边框高光 + 实时阴影

---

## 收起状态布局（260px 宽）

```
┌─────────────────────┐
│  ┌───┐ ┌───┐ ┌───┐  │  ← 三张散开的 K(战术) / J(战略) / Q(引擎) 扑克牌
│  │ K │ │ J │ │ Q │  │     传统扑克牌样式：红黑花色、圆角、微妙阴影
│  │ ♥ │ │ ♠ │ │ ♦ │  │
│  └───┘ └───┘ └───┘  │
│  三位专家 · 待命中     │  ← 底部文字
└─────────────────────┘
```

**扑克牌设计（传统风格）**：
- K（战术专家）→ 红心 ♥，数字 K 放大，角标小图标 ⚔️，红色主题
- J（战略专家）→ 黑桃 ♠，数字 J 放大，角标小图标 🎯，黑色主题
- Q（引擎专家）→ 方块 ♦，数字 Q 放大，角标小图标 📊，蓝色主题
- 牌面：经典红/黑配色，圆角 8px，微妙的 box-shadow

---

## 扩张动画序列（完整流程）

### Step 1: 叠卡(收拢) → 合并成一叠
三张散开的牌向中心聚拢，**叠成一叠**（fanned stack）：
- K、J、Q 按顺序叠在一起（K 在最上）
- 整体向侧栏顶部居中位置移动
- 使用 Apple **bounce spring**：`stiffness: 400, damping: 20, mass: 0.7`

### Step 2: 变形 → 合并成协调者圆形呼吸图标
叠好的扑克牌**缩小、变形**为 Claude 风格的**协调者呼吸圆标**：
- 圆形呼吸动画：大小 60px → 66px，opacity 0.7 → 1.0，循环
- 颜色：使用金色（rgba(212,175,55,0.75)）——与项目主题色一致
- 内部可以有微妙的"大脑/神经网络"光点动画
- 使用 Apple **smooth spring**：`stiffness: 300, damping: 28, mass: 0.9`
- 变形持续时间：400ms

### Step 3: 发牌 → 三张牌从圆标中飞出
协调者圆形图标**展开**，三张牌**依次飞出**到左侧位置：
- 圆形图标从中心向两侧"裂开"（opacity 渐变消失）
- 三张牌从裂开处飞出发向左侧
- 发牌动画（Apple deal spring）：`stiffness: 450, damping: 22, mass: 0.6`
- Stagger：tactics 0ms, strategy 180ms, engine 360ms
- 牌飞到位后，**每张翻面**（rotateY 3D，间隔 120ms）

### Step 4: 思维流延伸 → 从协调者图标底部生长
翻牌完成后，协调者圆形图标移动到**右侧思考流的顶部**：
- 圆标从左侧移到右侧思考流区域的最上方
- 底部开始延伸出**金色的思维连接线**
- 思维流内容从连接线底部**生长**出来
- 流式输出配合打字机效果
- 协调者图标作为"首席裁判"的角色持续显示在思考流顶部

---

## 扩张后布局（620px 总宽度）

```
+------------------------------------------------------------+
|  左侧 K/J/Q 牌区  |  右侧思考流区                            |
|  ┌────────────┐   |  ┌─ 🤍 协调者呼吸圆标（金色） ─────────┐ |
|  │  ♥ K       │   |  │  ▼ 思维连接线（金色渐变延伸）      │ |
|  │  战术专家   │   |  ├────────────────────────────────────┤ |
|  └────────────┘   |  │ 🎯 [战术] 动态副标题                 │ |
|  ┌────────────┐   |  │ 💭 思考流内容 ···                   │ |
|  │  ♠ J       │   |  │ 🔧 工具调用                        │ |
|  │  战略专家   │   |  ├────────────────────────────────────┤ |
|  └────────────┘   |  │ 🎯 [战略] 动态副标题                 │ |
|  ┌────────────┐   |  │ 💭 思考流内容 ···                   │ |
|  │  ♦ Q       │   |  │ 🔧 工具调用                        │ |
|  │  引擎专家   │   |  ├────────────────────────────────────┤ |
|  └────────────┘   |  │ 🎯 [引擎] 动态副标题                 │ |
|                   |  │ 💭 思考流内容 ···                   │ |
+------------------------------------------------------------+
```

**三张牌**：K(♥红心/战术) · J(♠黑桃/战略) · Q(♦方块/引擎)
**协调者圆标**：位于右侧思考流顶部，金色呼吸动画，作为"首席裁判"角色

---

## 右侧思考流（Claude Extended Thinking 风格）

每个专家在右侧有自己的思考流区域：

```
┌─ [专家色左边框] ─────────────────────────────────────┐
│  动态副标题（14px, 专家主色, 实时更新）                 │
│  ─────────────────────────────────────────          │
│  💭 思考内容流（打字机效果，cursor 光标闪烁）           │
│  💭 继续流式输出...█                                  │
│                                                        │
│  🔧 get_piece_attacks → 结果预览（可展开）             │
│  ─────────────────────────────────────────          │
│  💭 更多思考...                                       │
└──────────────────────────────────────────────────────┘
```

**动态副标题特征**：
- 来源：**后端 emit 的 `subtitle` 事件**（用户确认）
- 样式：专家主色，粗体，14px，出现时从上方滑入（translateY -4→0）200ms
- 切换时：旧副标题 fadeOut（100ms），新副标题 fadeIn（200ms）

---

## 后端改动

### `api/main.py` — `analyze_deep_stream()`
添加 subtitle 事件路由：
```python
elif event["type"] == "subtitle":
    yield f"data: {json.dumps({'type': 'subtitle', 'expert': event.get('expert'), 'message': event['message']}, ensure_ascii=False)}\n\n"
```

### `core/llm/multi_agent_orchestrator.py` — `analyze_multi()`
在以下节点 emit subtitle：
- 每个 expert_start 后 → `"正在分析{专家名}视角..."`
- 工具调用前 → `"{专家}正在调用{工具名}..."`
- 工具结果返回 → `"解读{工具名}结果..."`
- expert_result 后 → `"{专家}分析完成"`
- synthesis 开始 → `"综合裁判整合三位专家观点..."`
- synthesis_chunk 中 → 根据内容实时 emit 动态副标题

---

## 前端文件变更

### 新建文件（6个）

| 文件 | 用途 |
|------|------|
| `frontend/src/store/useAgentStore.ts` | Zustand store，管理动画 phase（collapsed/idle→merging→orb→dealing→flipping→streaming）+ 三位专家状态 |
| `frontend/src/components/CollapsedCardsView.tsx` | 收起状态：三张散开的 K/J/Q 扑克牌布局（260px 宽）|
| `frontend/src/components/OrchestratorOrb.tsx` | 协调者呼吸圆标：Claude 风格金色圆形呼吸动画，可从扑克牌变形而来，可移动到思考流顶部 |
| `frontend/src/components/PokerExpertCard.tsx` | 扑克牌组件：K(♥战术) / J(♠战略) / Q(♦引擎) 传统扑克牌样式 + 发牌+翻牌动画 |
| `frontend/src/components/AgentCardStack.tsx` | 发牌容器：管理收牌→合并→变形的动画时序 |
| `frontend/src/components/ThinkingStreamView.tsx` | 右侧思考流：协调者图标在顶部 + 思维连接线 + 每专家独立流区域 + 动态副标题 |
| `frontend/src/components/AgentThinkingPanel.tsx` | 主面板：根据 phase 渲染收起/扩张状态 + 协调动画时序 + SSE 连接 |

### 修改文件（4个）

| 文件 | 改动 |
|------|------|
| `frontend/src/App.tsx` | 深度分析 Tab：根据 `isBoardCollapsed` 渲染 `AgentThinkingPanel`（收起/扩张自适应）|
| `frontend/src/services/api.ts` | `analyzeDeep` 扩展：处理 `subtitle` + `expert_*` 事件路由 |
| `frontend/src/index.css` | 新增 Apple Spring curves、扑克牌样式（K/J/Q）、orchestrator orb 动画 keyframes |
| `api/main.py` | `analyze_deep_stream()` 添加 subtitle 事件路由 |
| `core/llm/multi_agent_orchestrator.py` | `analyze_multi()` 在关键节点 emit subtitle 事件 |

### 可复用现有代码

| 文件 | 复用内容 |
|------|---------|
| `frontend/src/components/ExpertCard.tsx` | `StreamText` 打字机组件、EXPERT_CONFIG（颜色/图标/名称/描述）|
| `frontend/src/components/SynthesisPanel.tsx` | 高亮格式逻辑（`**粗体**` / `[工具名]` / `(坐标)`）|
| `frontend/src/components/AgentDebutPanel.tsx` | `BreathingDot` 呼吸动画参考 |
| `frontend/src/services/api.ts` | 现有 `analyzeDeep` 方法 → 扩展事件类型，不改动原有接口 |

---

## CSS 动画变量

```css
/* Apple Spring Curves */
--apple-spring-smooth: cubic-bezier(0.16, 1, 0.3, 1);
--apple-spring-enter: cubic-bezier(0.0, 0.0, 0.2, 1);
--apple-spring-exit: cubic-bezier(0.4, 0.0, 1.0, 1.0);

/* Orchestrator Orb (Claude-style breathing circle) */
@keyframes orb-breathe {
  0%, 100% { transform: scale(1); opacity: 0.75; }
  50% { transform: scale(1.1); opacity: 1; }
}
@keyframes orb-glow {
  0%, 100% { box-shadow: 0 0 12px rgba(212,175,55,0.4), 0 0 24px rgba(212,175,55,0.2); }
  50% { box-shadow: 0 0 20px rgba(212,175,55,0.6), 0 0 40px rgba(212,175,55,0.3); }
}

/* Card dealing keyframe */
@keyframes card-deal {
  from { transform: translateX(-280px) rotateZ(-12deg) scale(0.6); opacity: 0.4; }
  to { transform: translateX(0) rotateZ(0) scale(1); opacity: 1; }
}

/* Card flip keyframe */
@keyframes card-flip {
  0% { transform: rotateY(0deg); }
  50% { transform: rotateY(90deg); }
  51% { transform: rotateY(-90deg); }
  100% { transform: rotateY(0deg); }
}

/* K/J/Q 扑克牌样式 */
.poker-card {
  width: 52px;
  height: 70px;
  border-radius: 8px;
  border: 1px solid rgba(0,0,0,0.15);
  box-shadow: 2px 3px 8px rgba(0,0,0,0.2);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  font-family: 'Noto Serif SC', serif;
  position: relative;
}
.poker-card.king  { background: linear-gradient(135deg, #fff5f5, #ffe8e8); color: #dc2626; }
.poker-card.jack  { background: linear-gradient(135deg, #f8f8f8, #e8e8e8); color: #1a1a1a; }
.poker-card.queen { background: linear-gradient(135deg, #f0f8ff, #e0f0ff); color: #2563eb; }
.poker-card .rank { font-size: 20px; font-weight: 900; line-height: 1; }
.poker-card .suit { font-size: 16px; }
.poker-card .badge { position: absolute; top: 3px; right: 3px; font-size: 9px; }
```

---

## 实现阶段

| 阶段 | 步骤 | 内容 |
|------|------|------|
| 1 | 后端 | `api/main.py` 添加 subtitle 事件路由 |
| 1 | 后端 | `core/llm/multi_agent_orchestrator.py` emit subtitle |
| 2 | 前端基础 | `useAgentStore.ts` — Zustand store |
| 2 | 前端基础 | `api.ts` — SSE 事件扩展 |
| 2 | 前端基础 | `index.css` — Apple 动画变量 |
| 3 | 组件 | `CollapsedCardsView.tsx` — 收起状态扑克牌 |
| 3 | 组件 | `OrchestratorOrb.tsx` — 协调者呼吸圆标 |
| 3 | 组件 | `PokerExpertCard.tsx` — K/J/Q 扑克牌 + 动画 |
| 3 | 组件 | `AgentCardStack.tsx` — 收牌→合并→变形时序 |
| 3 | 组件 | `ThinkingStreamView.tsx` — 协调者+连接线+三专家流 |
| 3 | 组件 | `AgentThinkingPanel.tsx` — 主面板 |
| 4 | 集成 | `App.tsx` — 渲染新面板 |
| 4 | 验证 | `pytest -q` 确认无回归 |

---

## 验证方案

1. 启动后端：`python -m uvicorn api.main:app --port 8003`
2. 启动前端：`cd frontend && npm run dev`
3. **收起状态验证**：深度分析 Tab 内显示 K/J/Q 三张散开扑克牌 + "三位专家·待命中"文字
4. **扩张动画验证**：点击"开始深度分析"后
   - ✅ 三张牌收成一叠
   - ✅ 叠卡变形为金色协调者呼吸圆标
   - ✅ 圆标展开，三张牌飞出到左侧
   - ✅ 每张牌翻面揭示内容
   - ✅ 协调者图标移至右侧思考流顶部
   - ✅ 思维连接线（金色）从顶部延伸
   - ✅ 右侧出现带**动态副标题**的思考流
5. DevTools Network → SSE 事件包含 `subtitle` 类型
6. `pytest -q` 确认无回归

---

## 状态

- [x] 构思中
- [x] 验证中
- [x] 准备实现
- [x] 已实现（前端部分）

## 实现记录

### 2026-03-22 前端实现

**已完成：**
- `frontend/src/store/useAgentStore.ts` — Zustand store，管理 7 个动画阶段 + 三专家状态 + 协调者状态
- `frontend/src/components/CollapsedCardsView.tsx` — 收起状态三张散开扑克牌
- `frontend/src/components/OrchestratorOrb.tsx` — Claude 风格金色呼吸圆标
- `frontend/src/components/PokerExpertCard.tsx` — K/J/Q 扑克牌组件（支持发牌+翻牌动画）
- `frontend/src/components/AgentCardStack.tsx` — 发牌容器，管理叠卡→圆标→发牌→翻牌时序
- `frontend/src/components/ThinkingStreamView.tsx` — 右侧 Claude 风格思考流
- `frontend/src/components/AgentThinkingPanel.tsx` — 主面板，根据 phase 渲染收起/扩张状态
- `frontend/src/components/DeepAnalysisPanel.tsx` — 集成新面板，触发动画序列
- `frontend/src/index.css` — Apple Spring curves + 扑克牌样式 + orchestrator orb 动画

**后端待做（不阻塞前端验证）：**
- `api/main.py` — 添加 `subtitle` 事件路由
- `core/llm/multi_agent_orchestrator.py` — emit subtitle 事件

**动画时序（已实现）：**
- `collapsed` → `merging` (0ms) → `orb` (400ms) → `dealing` (800ms) → `flipping` (1100ms) → `streaming` (1700ms)
