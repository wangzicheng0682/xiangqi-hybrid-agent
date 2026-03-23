# 项目状态

> 本文档记录当前开发进度，架构详情请阅读 [DNA.md](DNA.md)

**版本**: v3.28
**最后更新**: 2026-03-23

---

## 当前阶段

**阶段**: T0比赛冲刺 - 前端视觉打磨
**核心目标**: 现代中式编辑风背景 + 分析面板宽度优化

---

## 进度总览

| 模块 | 进度 | 说明 |
|------|------|------|
| **标签检测体系** | ██████████ 100% | **完成！** 45个标签已定义，12个测试全部通过 |
| **黄金局面测试** | ██████████ 100% | **完成！** 41个测试用例，mAP=1.0 |
| **张力检测器** | ██████████ 100% | 6种张力类型，阈值已优化（cp>300触发） |
| **知识库** | ████████░░ 80% | 张力导向检索，20+棋理原则 |
| Agent工具 | ██████████ 100% | 10个工具已实现，Function Calling已集成 |
| 双模式API | ██████████ 100% | 真Agent模式上线，SSE新消息类型 |
| **SSE流式输出** | ██████████ 100% | **完成！** 延迟问题已定位，旧分析工具已删除 |
| 前端 | ██████████ 100% | 深度分析面板完成，Liquid Glass + 亮暗双模式 |
| Neo4j棋谱 | ████░░░░░░ 40% | 框架已搭建，数据待完善 |

---

## 本周待办

### 高优先级
- [x] ~~张力检测器实现~~ ✅ 6种张力类型
- [x] ~~System Prompt改造~~ ✅ 强制推理步骤
- [x] ~~张力检测阈值修复~~ ✅ cp>300
- [x] ~~引擎工具修复~~ ✅ engine_alternatives属性访问
- [x] ~~两阶段Agent测试~~ ✅ 规划→执行→输出
- [x] ~~SSE延迟问题定位~~ ✅ 旧版analyze-move阻塞
- [x] ~~旧版分析工具删除~~ ✅ 前端+后端已清理
- [ ] 验证走棋后深度分析无延迟

### 中优先级
- [ ] 阶段检测优化（考虑过河判断）
- [ ] 中局思维链框架
- [ ] Neo4j数据完善
- [ ] 三档讲解模式（初学者/进阶/教练）

---

## 最近更新

### 2026-03-23 🎴 分析面板：重写 AgentCardFlip 动画 + 左右分栏思维流

#### 核心改动

重写深度分析面板的动画序列，达到 Apple/WWDC 风格：

**动画序列**：
```
T=0ms      翻面完成，叠卡整齐显露彩虹背面
T=600ms    翻面完成 → morphing 开始
T=800ms    收缩变形完成 → orbMoving 开始（球曲线滑动 + 逐张发牌）
T=1100ms   三张依次弹出（macOS 最小化拉伸效果）
T=1400ms   三张落地左侧，整体垂直居中
T=1500ms   协调者思维流开始输出
```

**Phase 改造**（`useAgentStore.ts`）：
- 新增 `cardsLanded` / `streaming` phase
- 动画序列更流畅，无硬串停顿

**左右分栏布局**（`AgentThinkingPanel.tsx`）：
- `cardsLanded`/`streaming` 阶段：左侧三专家扑克牌 + 右侧协调者思维流
- 紫色渐变分隔线
- 协调者球 + 金色连接线 + 思维流内容

**新建文件**：
| 文件 | 说明 |
|------|------|
| `ThinkingStream.tsx` | 协调者思维流组件，打字机效果 + 金色子弹点 |
| `SplitLandedCards`（内联） | 落地后的三专家扑克牌（边缘彩虹流光） |

**动画细节**：
- 球呼吸：`orb-breathe` + `orb-body-rotate` 持续循环
- 边缘流光：`card-edge-glow` CSS keyframe（conic-gradient + hue-rotate）
- 发牌拉伸：`scaleX/scaleY` 差异化，stagger 150ms

**Bug 修复**：
- API 端口 `8003 → 8002`
- `ToolCall` 类型添加 `id` 字段
- SSE 事件类型添加 `expert` 字段

**死代码清理**：删除 8 个文件

**文件变更**：
- `AgentCardFlip.tsx` — 重写动画逻辑
- `AgentThinkingPanel.tsx` — 左右分栏布局
- `ThinkingStream.tsx` — 新建
- `index.css` — 新增 `card-edge-glow` keyframe
- `useAgentStore.ts` — phase 类型更新
- `ExpertCard.tsx` — ToolCall 类型更新

### 2026-03-23 🔧 Liquid Glass 按钮效果修复

**v2 问题**：尝试用 SVG `feDisplacementMap` 位移滤镜替代假白点，但：
- `filter` 属性导致 `backdrop-filter` 失效，按钮完全不可见
- `rgba(255,255,255,0.10)` 背景太透明，几乎融入暖米色背景
- 白字在暖米色背景上对比极差

**v3 正确实现**：
- 去掉 SVG 滤镜（与 `backdrop-filter` 不兼容）
- `rgba(255,255,255,0.40)` 背景 — 与 `.glass-panel` 一致的可见度
- `rgba(80,60,40,0.90)` 深色文字 — 在暖米色背景上清晰可见
- `border-top-color` 加亮 — 模拟玻璃顶部高光边
- 径向渐变 `::before` — 左上角柔和光晕，悬停时显现
- 金色变体：深色文字 `rgba(140,100,20,0.95)` + 金色边框 + 顶部高光

**涉及组件**：App.tsx 侧边栏全部按钮 + 分析面板组件

#### Apple iOS 26 水滴边缘反光效果

所有按钮统一升级为 Apple Liquid Glass 悬停光效：

**核心 CSS 类** `.liquid-glass-btn`：
- `backdrop-filter: blur(12px) saturate(160%)` — 玻璃模糊质感
- 多层 `inset box-shadow` — 模拟水滴四边镜面高光（上/下/左/右各有不同强度的白色边缘）
- `::before` / `::after` 伪元素 — 左上角微小白点光斑，悬停时出现（模拟水滴表面反光）
- 悬停时 `scale(1.03)` + 背景变亮 + 四边高光加强
- 按下时 `scale(0.97)` 反馈

**变体**：
- `.sm` — 小尺寸（padding: 4px 10px, border-radius: 8px）
- `.primary` — 金色主题（背景 `rgba(212,175,55,...)`，四边金色高光）
- `:disabled` — 禁用状态保持原样式但禁用交互

**涉及组件**：
- `App.tsx` — 左侧侧边栏全部按钮（☀️主题/在线对局/拍照识别/分析/人机/双人/打棋谱/翻转棋盘/显示提示/重新开始）
- `DeepAnalysisPanel.tsx` — 收起/快速/深度/分析主按钮
- `ReplayNavigator.tsx` — 导航圆按钮（⏮◀▶⏭）/自动讲解开关
- `PositionAnalysisPanel.tsx` — 摘要/棋子/标签标签按钮
- `PGNPanel.tsx` — 加载棋谱按钮
- `ReplayPanel.tsx` — 数据库/PGN标签/搜索/加载/退出按钮
- `ChessBoard.tsx` — 错误关闭按钮
- `ExpertCard.tsx` — 展开/收起按钮
- `BottomTerminalPanel.tsx` — 最小化/关闭按钮
- `AgentDebutPanel.tsx` — 关闭按钮

### 2026-03-22 🎴 分析面板：扑克牌收叠翻面动画 + 全部原有功能恢复

#### 动画序列（Apple 风格）

点击"开始深度分析"后，扑克牌全程连续动画，不消失：

```
T=0ms     面板扩张，卡片随布局自然位移（不中断）
T=100ms   三卡开始收叠（spring stiffness:320, damping:26）
T=600ms   收叠完成，三卡完美重叠
T=700ms   整体 3D 翻面（rotateY spring stiffness:260, damping:28）
T=1100ms  翻面完成，Agent 流光液态玻璃背面展示
```

#### 架构改动

**一套卡片全程渲染**：
- `AgentThinkingPanel` 始终渲染 `AgentCardFlip`，不切换组件
- `AgentCardFlip` 内部通过 `phase` 状态驱动动画
- 无 `AnimatePresence` 组件切换，无卡片消失

**牌的正面**：`CollapsedCardsView` 原有的 Liquid Glass 卡片（含全部交互）：
- Apple 风格 `borderRadius: 16` + `overflow: hidden`
- 鼠标悬停 `onMouseEnter/onMouseLeave`（phase===idle 时启用）
- `hovered` 状态 → `glowColor` box-shadow 光晕增强
- `isSqueezed` 邻居卡让位动画（左右各偏移16px）
- `isHovered ? 1.18 : 1` 悬浮放大
- `ExpertGlassPanel` Portal 弹出详情（abilities 列表）

**牌的背面**：Apple 彩色流光液态玻璃：
- `conic-gradient`（蓝→紫→粉→金→蓝）+ `liquid-shimmer` hue-rotate 动画（3秒无限循环）
- `mixBlendMode: overlay` 叠加质感
- `backdrop-filter: blur(20px) saturate(180%)`
- 多层 inset box-shadow 模拟玻璃厚度
- 皇冠 ♕ + 闪电 ⚡ + 装饰线 + Agent 金色文字

#### CSS 新增

- `@keyframes liquid-shimmer`：hue-rotate + brightness 脉冲流光

**文件变更**：
- `frontend/src/components/AgentCardFlip.tsx` — 新建，核心动画组件
- `frontend/src/components/AgentThinkingPanel.tsx` — 简化为单组件渲染
- `frontend/src/index.css` — 新增 `liquid-shimmer` 动画

### 2026-03-22 🎨 前端视觉增强：侧边栏 Liquid Glass 强化 + 亮暗双模式

#### 侧边栏 Liquid Glass 增强

左右侧边栏从弱玻璃效果升级为 Apple iOS 26 Liquid Glass 风格：

**核心改动**：
- `backdrop-filter: blur(12px)` → `blur(40px)`，玻璃模糊感大幅增强
- 背景透明度提升：`rgba(255,255,255,0.15)` → `rgba(255,255,255,0.18)`
- 边框加粗：`rgba(180,160,140,0.15)` → `rgba(255,255,255,0.28)`
- 多层 box-shadow：外阴影 + inset 高光（模拟玻璃厚度）
- 顶部白边高光：内 inset 反射感

**CSS 新增**：
- `.lg-sidebar` — 完整 Liquid Glass 样式
- `.lg-sidebar-left` / `.lg-sidebar-right` — 左右专属白边
- CSS 变量支持亮暗双模式

**文件变更**：
- `frontend/src/index.css` — 新增 CSS 变量 + `.lg-sidebar` 完整样式
- `frontend/src/App.tsx` — 侧边栏改用 `className="lg-sidebar"`，移除内联弱玻璃样式

#### CollapsedCardsView 扑克牌 Liquid Glass 化

收起状态的三张专家扑克牌（K/J/Q）升级为 Apple Liquid Glass 风格：

- 尺寸 `110×150` → `130×175`
- `backdrop-filter: blur(12px) saturate(150%)`
- 内高光 + 内暗边（inset box-shadow 玻璃厚度感）
- 每张牌专属渗色光晕（K红/J银/Q蓝）
- KJQ 字母 `44px` → `54px`，悬浮时加文字光晕
- 标题字号 `11px → 14px`，金色 `#D4AF37` + 光晕
- 底部文字透明度 `0.5 → 0.75`

**文件变更**：
- `frontend/src/components/CollapsedCardsView.tsx` — 完整重构卡片样式

#### 亮暗双模式切换

- 新增 `data-theme="dark"` 属性切换
- ☀️/🌙 切换按钮放置于左侧 Logo 区域
- 暗色模式：暖色暗底 `rgba(20,15,10,0.32)`，适配暖黄木纹背景
- 亮色模式：微透明白底 `rgba(255,255,255,0.18)`，Apple 原生风格

### 2026-03-22 🎨 前端视觉打磨：高级通透背景 + 分析面板扩张

#### 背景设计重构

将前端背景从"Apple Liquid Glass增强版"升级为"现代中式编辑风 + Apple高级质感"混合方案：

**核心元素**：
- **强颗粒噪点层**：SVG `feTurbulence` 生成电影级颗粒感（`baseFrequency=0.80, numOctaves=4, opacity=0.10`），作为背景材质感核心
- **顶部深墨晕染**：`linear-gradient` 从顶部压下来（`0.28` 起始渐隐），模拟水墨书卷气
- **左上自然光晕**：`radial-gradient` 左上角提亮，模拟自然光感
- **清晰棋盘格**：`0.18` 透明度，清晰可见但不抢眼
- **宣纸拉丝纹**：新增垂直纸纹层，模拟宣纸纤维质感
- **暖灰宣纸底**：`#E0DBD1`，和白色毛玻璃形成良好对比

**技术实现**：
- 颗粒噪点使用 SVG Data URI 背景图片，浏览器原生支持，稳定可靠
- 8层背景叠加（颗粒 + 墨染 + 光晕 + 反光 + 棋盘格 + 纸纹 + 版式线 + 底色）
- 移除之前失败的 `filter: url(#grain-filter)` 伪元素方案

**文件变更**：
- `frontend/index.html` — 添加 SVG Grain 噪点滤镜定义（后移除，改用 Data URI）
- `frontend/src/index.css` — 完整重构 body 背景层，新增8层渐变 + grain 背景
- CSS变量：`--apple-bg` 更新为 `#E0DBD1`
- 顶部注释更新为"Modern Chinese Editorial Style"

#### 分析面板宽度优化

- 分析模式下右侧面板：`380px → 620px`，扩大近一倍
- 正常模式保持 `260px`
- 使用 CSS Grid `gridTemplateColumns` 动态切换

**文件变更**：
- `frontend/src/App.tsx` — `gridTemplateColumns` 分析模式从 `380px` → `620px`

### 2026-03-22 🎨 前端布局重构：命令式 → 声明式（响应式Grid）

#### 核心改动

将前端的坐标计算从命令式（Imperative）重构为声明式（Declarative）响应式布局，彻底解决棋盘缩放时的坐标偏差和动画抖动问题。

**变更内容**：
- 外层容器：`display: flex` → `display: grid`，动态控制第三列宽度 `20vw ↔ 35vw`
- 棋盘动画：移除硬编码 `x: -350`, `y: -80`，仅保留 `scale: 0.75` + `transformOrigin: '0 0'`
- 引擎窗口：移除 `position: absolute` + 手动坐标计算，改为 `flex: 1` 流体填充
- 右侧栏：移除 `position: fixed`，参与 Grid 布局
- 清理：`boardRef`、`ResizeObserver`、`boardCenter`、`engineWidth` 等全部删除
- 动画参数：三组不同参数 → 统一 `stiffness: 260, damping: 26`

**文件变更**：
- `frontend/src/App.tsx` — 重构布局逻辑，清理 ~100行代码
- `frontend/src/components/ChessBoard.tsx` — 移除 `onWidthChange` prop 和 `measureRef`
- `docs/frontend/ENGINE_CHART_DEBUG.md` — 更新文档，记录重构结果
- `docs/frontend/FRONTEND_COMPLETE.md` — 更新 4.5 节说明

### 2026-03-21 🎨 前端整合：替换为新版UI (frontend_new)

#### 核心改动

将 `docs/communication/frontend_new/` 的前端代码整合到 `frontend/` 目录：

**新前端特点**：
- 明亮温暖米色主题（浅色水墨风格）
- 简洁flex布局（三列：左240px | 中auto | 右380px）
- 时间轴式深度分析面板（DeepAnalysisPanel）
- 完整棋子/局面/战术标签/棋谱/PGN组件

**保留的高级功能**（来自旧版frontend）：
- `ExpertCard.tsx` — 三专家卡片组件（战术/战略/引擎）
- `SynthesisPanel.tsx` — 合成器输出面板
- `AgentDebutPanel.tsx` — 专家登场动画
- `EngineChart.tsx` — 引擎评分折线图
- Store 中的 `evalHistory`、`EvalPoint` 类型

**集成要点**：
- 全部新组件替换：`App.tsx`, `main.tsx`, `index.css`, `App.css`, `ChessBoard.tsx`, `DeepAnalysisPanel.tsx`, `PositionAnalysisPanel.tsx`, `TacticalTagsPanel.tsx`, `ReplayPanel.tsx`, `ReplayNavigator.tsx`, `StatCard.tsx`, `PGNPanel.tsx`
- Store/API服务使用新版（简化版）
- 高级组件（ExpertCard等）从旧版保留，未被新App.tsx引用但可复用

**编译状态**：`npm run build` 全绿 ✅

### 2026-03-21 🎯 布局重设计 v2：棋盘左上 + 侧边栏全右 + 苹果登场 (Plan: optimized-jingling-duckling v2)

#### 布局
- 棋盘：居中 → 左上角 smooth slide（spring stiffness:180, damping:22，scale:0.75）
- 侧边栏：380px → 62% 视口宽度，spring 扩张动画
- 中央区域宽高协同动画，无瞬移

#### 登场动画（苹果轮廓 + Claude 呼吸融合）
1. T=0: 三个呼吸光球脉冲聚集（Claude眨眼风格）
2. T=300: 光球→虚线轮廓浮现
3. T=600: 身份揭示 — 图标旋转出现 + 名称打字机效果
4. T=900: 填充着色 + 边框solid化
5. T=1200: 卡片内容 stagger 渐次展开

#### 技术要点
- `motion.div` 作为中央区域容器，`animate={{ width }}` 协同棋盘和侧边栏
- Board: `spring stiffness:180, damping:22` + `scale: 0.75` + margin 动画
- 登场: 纯 CSS `scale/opacity` 循环 + 打字机 effect hook
- 引擎图: 保留在棋盘下方（棋盘左侧+下方空间内）

#### 新增文件
| 文件 | 说明 |
|------|------|
| `frontend/src/components/EngineChart.tsx` | 纯SVG引擎评分折线图（无依赖） |
| `frontend/src/components/AgentDebutPanel.tsx` | 融合登场动画主组件 |
| `frontend/src/components/BottomTerminalPanel.tsx` | 已废弃（可删除） |

### 2026-03-21 🎯 布局重设计：棋盘滑动 + 专家登场动画 (Plan: optimized-jingling-duckling)

#### 核心改动

从"底部终端面板"改为"棋盘滑动 + 扩张侧边栏 + 专家登场动画"：

```
正常状态：
[左侧240px] | [居中棋盘] | [右侧380px]

分析模式：
[左侧240px] | [左上滑动棋盘 scale(0.82)] | [右侧560px - 专家登场动画]
            | [下方：引擎折线图 + 走法记录]
```

#### 动画序列
```
T=0ms     棋盘向左上滑动 (spring)
T=100ms     侧边栏从380px扩张到560px
T=200ms     底部区域出现
T=300ms     三个光球脉冲聚集
T=600ms     光球爆发 + 虚线轮廓浮现
T=900ms     身份揭示 + 专家名打字机
T=1200ms    填充着色 + 卡片展开
T=1500ms    卡片内容 stagger 出现
```

#### 技术实现

- ✅ **BottomTerminalPanel.tsx** — 底部弹出主组件（Framer Motion）
  - 毛玻璃：`backdrop-filter: blur(24px) saturate(180%)`
  - Spring 动画：`stiffness: 400, damping: 28, mass: 0.8`
  - 高度拖拽调整（mousedown/mousemove/mouseup）
  - ESC / 点击背景关闭
  - 高度持久化到 localStorage

- ✅ **Framer Motion 动画编排**
  - 面板：y: 100% → 0 spring 滑入
  - 卡片：staggerChildren 0.12s 依次出现
  - 合成器：delayChildren 0.51s 后淡入

- ✅ **棋盘联动缩放** (Zustand store)
  - 面板打开：`terminalPanelScale = 0.92`
  - 面板关闭：`terminalPanelScale = 1.0`
  - 缓动：`cubic-bezier(0.34, 1.56, 0.64, 1)` — 苹果风格弹性

#### 新增文件
| 文件 | 说明 |
|------|------|
| `frontend/src/components/BottomTerminalPanel.tsx` | 底部弹出终端主组件 |

#### 修改文件
- `frontend/src/store/useGameStore.ts` — 新增 `terminalPanelScale` 状态
- `frontend/src/components/DeepAnalysisPanel.tsx` — 状态管理中枢，渲染 BottomTerminalPanel
- `frontend/src/App.tsx` — 棋盘区域缩放 transform
- `frontend/src/index.css` — 毛玻璃 + 标题栏 + 拖拽条 + 动画

### 2026-03-21 🎨 前端重设计：三列专家卡片布局

#### 核心改动（Plan: delegated-zooming-alpaca）

将深度分析面板从"时间轴"改为"三列专家卡片 + 合成器"布局：

- ✅ **ExpertCard.tsx** — 单专家卡片组件
  - 专家头像/图标 + 名称 + 状态标签
  - 流式思考区域（打字机效果）
  - 工具调用气泡可视化
  - 核心发现区
  - 三种配色：战术(红)、战略(黄)、引擎(蓝)

- ✅ **SynthesisPanel.tsx** — 合成器输出面板
  - 共识/分歧分区展示
  - 流式最终讲解输出
  - 状态指示器

- ✅ **DeepAnalysisPanel.tsx** 重构
  - 从 `AnalysisTimeline` 时间轴改为三列 `ExpertCard` 网格
  - SSE 事件路由到对应专家卡片
  - 集成 `SynthesisPanel` 替代 `resultSection`

- ✅ **index.css** — 新增专家卡片样式、动画

#### 修改文件
- `frontend/src/components/ExpertCard.tsx` — 新建
- `frontend/src/components/SynthesisPanel.tsx` — 新建
- `frontend/src/components/DeepAnalysisPanel.tsx` — 重构
- `frontend/src/index.css` — 新增样式
- `frontend/src/App.tsx` — 修复 pre-existing bug（`'analysis'` → `'deep'`）

### 2026-03-21 🚀 多Agent并行架构 (Plan #002)

#### 核心改动

从单一Agent升级为三专家并行架构：

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
  │(TacticsAgent)│      │(StrategyAgent│      │(EngineAgent)│
  │工具:棋子攻防 │      │工具:局面战略 │      │工具:深度分析 │
  │      +走法  │      │      +走法对比│      │      +候选走法│
  └─────────────┘      └─────────────┘      └─────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │      Synthesizer        │
                    │  综合三方结论 → 统一讲解 │
                    └─────────────────────────┘
```

#### 自适应决策策略

| 条件 | 执行 |
|------|------|
| 张力数量==0 且 开局 | 单Agent快速分析 |
| 张力<=2 | 单Agent+扩展轮次 |
| 张力>=3 或 CRITICAL 或用户要求深度 | 多Agent并行 |
| 用户明确要求深度分析 | 多Agent并行 |

#### 新增文件

| 文件 | 说明 |
|------|------|
| `core/llm/experts/__init__.py` | 专家模块入口 |
| `core/llm/experts/base_expert.py` | 专家基类（共享LLM调用、棋盘生成、工具执行） |
| `core/llm/experts/tactics_expert.py` | 战术专家（6个工具） |
| `core/llm/experts/strategy_expert.py` | 战略专家（4个工具） |
| `core/llm/experts/engine_expert.py` | 引擎专家（4个工具） |
| `core/llm/multi_agent_orchestrator.py` | 协调器 + 合成器 |

#### SSE新事件类型

| 事件类型 | 说明 |
|----------|------|
| `expert_start` | 专家开始分析 |
| `expert_result` | 专家完成（含核心发现） |
| `expert_{name}_thinking` | 专家思考过程 |
| `expert_{name}_tool` | 专家工具调用 |
| `expert_{name}_tool_result` | 专家工具结果 |
| `synthesis_chunk` | 合成器流式输出 |

#### 降级策略

多Agent专家超时（>2分钟）→ 自动降级为单Agent + 扩展轮次（max_rounds=5）

#### 修改文件

- `api/main.py` — 集成Orchestrator，适配新SSE事件类型
- `frontend/src/components/DeepAnalysisPanel.tsx` — 支持多专家时间轴展示
- `frontend/src/index.css` — 新增专家节点样式

### 2026-03-21 🔧 布局动画修复：棋盘真正左上平移 + 侧边栏扩张

#### 核心问题
- 棋盘只有缩小，没有平移（只有 `scale`，没有 `x/y` 位移）
- 侧边栏宽度固定 380px，无扩张动画

#### 修复内容
- `mainArea` 改为 `motion.div` + `layout`，`justifyContent`/`alignItems` 从 `center` → `flex-start`
- `boardContainer` + `boardWrapper` 加 `layout` + `scale` 动画，Framer Motion 自动计算空间位移
- `rightSidebar` 从 `<aside>` 改为 `<motion.aside>`，`width` 380 → 420 弹簧动画
- 统一使用 Apple 风格弹簧参数：`stiffness: 180, damping: 22`
- `overflow: hidden` 已从 `mainArea` 移除，确保缩放棋盘不被裁剪

#### 修改文件
- `frontend/src/App.tsx` — 布局动画修复

### 2026-03-21 🔧 布局动画 v3：去掉scale，丝滑平移填满空间（Apple spring参数）

#### 核心问题（v2）
- v2只有scale缩放，无真正位移
- 布局切换不够丝滑

#### 修复内容（v3）
**去掉所有 `scale`，纯空间位移 + Apple spring参数**

| 动画 | 参数 | 来源 |
|------|------|------|
| 布局/位移主弹簧 | `stiffness: 308, damping: 23` | Apple snappy (duration≈0.4s, bounce=0) |
| 引擎窗口展开 | `stiffness: 395, damping: 28` | Apple interactive (duration≈0.35s) |
| 侧边栏宽度 | 380 → 420px，`layout` 自动过渡 | 填满空隙 |

**Apple物理参数换算**（WWDC23）：
```
stiffness = (2π / duration)²
damping = 1 - 4π × bounce / duration
```
- snappy: duration=0.4s, bounce=0 → stiffness≈308, damping≈23
- interactive: duration=0.35s, bounce=0 → stiffness≈395, damping≈28

### 2026-03-21 🔧 布局动画 v3→v4：CSS Grid三列布局，侧边栏真正抵住棋盘

#### 核心问题（v3）
- 侧边栏扩张后仍然不抵棋盘右侧
- 引擎窗口尺寸不对，不填满棋盘下方
- 根本原因：`flex: 1` 让 mainArea 吃掉所有剩余空间，棋盘永远在巨大空白中被居中

#### 修复内容（v4）

**从 flex 改为 CSS Grid 三列布局**：
```
正常模式：         分析模式：
[左240][中auto][右380]  →  [左240][中auto][右540]
                                    ↗ 侧边栏弹簧扩张
                                    ↗ 棋盘左上贴边
                                    ↗ 引擎窗口展开
```

| 改动 | 说明 |
|------|------|
| `container` | `display: flex` → `display: grid`，`gridTemplateColumns` 随 `isAnalysisMode` 动画 |
| `mainArea` | `flex: 1` 移除，只占内容所需空间（棋盘+引擎的自然尺寸） |
| `gridTemplateColumns` | `240px auto 380px` ↔ `240px auto 540px`，Apple spring `308/23` |
| `EngineChart` compact width | 280px → 480px（匹配棋盘宽度） |
| 引擎窗口 | `marginTop: 0→8` + `height: auto`，`spring 395/28` |

### 2026-03-21 🔧 布局动画 v4→v5：引擎跨列贴合四边，侧边栏弹簧抵棋盘

#### 核心问题（v4）
- 引擎窗口在 mainArea 里，宽度受 Grid 中间列限制，无法跨列贴合
- 侧边栏与棋盘不对齐

#### 修复内容（v5）

**Grid 3列×2行动画布局**：
```
正常模式：                  分析模式：
[左240][ 棋盘 ] [右380]    [左240][ 棋盘 ] [右540]
          [ 引擎 ]                   [ 引擎 ]
          (隐藏)                    (弹簧展开120px)
```
- 左栏：`gridColumn: 1, gridRow: 1/3`
- 棋盘：`gridColumn: 2, gridRow: 1`；分析模式靠左上
- 引擎：`gridColumn: 2, gridRow: 2`，`width: 100%` = 棋盘宽度
- 右侧栏：`gridColumn: 3, gridRow: 1/3`，弹簧扩张 380→540px

**引擎窗口四边贴合**：
- 左/右：column 2 宽度 = 棋盘宽度，天然对齐
- 上：紧贴棋盘（同一列）
- 下：`height: 0 → 120px`，`spring 395/28`
- `gridTemplateRows: 'auto 0px' → 'auto 120px'`，Grid 行高同步动画

---

## 服务状态

| 服务 | 端口 | 状态 |
|------|------|------|
| Neo4j | 7687 | ⚪ 待启动 |
| 后端API | 8002 | 🟢 运行中 |
| 前端 | 3007 | 🟢 运行中 |

---

## 快速启动

```bash
# 后端
python -m uvicorn api.main:app --host 0.0.0.0 --port 8003

# 前端
cd frontend && npm run dev
# 访问 http://127.0.0.1:3000
```

---

## 快速链接

- [项目DNA](DNA.md) - 架构全貌（必读）
- [标签参考](reference/tag_reference.md) - 45个标签详细定义
- [Agent工具规范](reference/agent_tools_spec.md) - 10个工具接口
