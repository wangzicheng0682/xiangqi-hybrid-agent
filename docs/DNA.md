---
name: 项目DNA
type: dna
version: 2.1
date: 2026-04-01
owner: AI（自动维护）
changelog:
  - v2.1 (2026-04-01): 文档体系整理，添加frontmatter
  - v2.0 (2026-03-31): 重写DNA，更新技术路线
---

# 象棋AI混合代理教学系统 - 项目DNA

> 本文档是项目的"基因图谱"，开发者只需阅读本文档即可理解项目全貌。
> 目标读者：人类开发者（AI和人类）

**版本**: v2.1
**最后更新**: 2026-04-01
**阅读时间**: ~10分钟

---

## ⚖️ 项目宪法（最高优先级）

### 第一条：模块化开发原则

**核心要求**：项目必须支持在不同AI Code对话中独立开发不同模块。

**模块划分**：

| 模块 | 目录 | 职责 | 可独立开发 |
|------|------|------|------------|
| 标签检测器 | `core/rules/` | 38个标签检测逻辑 | ✅ |
| Agent工具 | `core/llm/agent_tools.py` | 12个LLM可调用工具 | ✅ |
| 思维链模板 | `core/llm/thinking_templates.py` | 阶段感知思维框架 | ✅ |
| 引擎封装 | `core/engine/` | Pikafish引擎集成 | ✅ |
| 知识图谱 | `core/kg/` | Neo4j棋谱检索 | ✅ |
| 视觉识别 | `core/vision/` | YOLO棋盘识别（规划中） | ⏳ |
| API层 | `api/` | FastAPI端点 | ✅ |
| 前端 | `frontend/` | React UI + Liquid Glass | ✅ |

**模块接口规范**：
- 每个模块必须定义清晰的输入/输出接口
- 模块间通过接口通信，不得直接访问内部实现
- 新增模块必须先在DNA.md中注册

---

### 第二条：文档维护标准

**核心要求**：所有开发者在修改代码前必须先阅读并遵守本文档标准。

**文档类型定义**：

| 类型 | 说明 | 更新频率 | 修改权限 |
|------|------|----------|----------|
| **DNA** | 项目宪法，不可轻易修改 | 重大变更 | ⚠️ 需用户批准 |
| **STATE** | 项目状态，实时更新 | 每次提交 | ✅ AI可直接更新 |
| **REFERENCE** | 技术参考，与代码同步 | 代码变更时 | ⚠️ 需审查 |
| **GUIDE** | 开发指南，按模块 | 需要时 | ✅ 可修改 |
| **PLAN** | 构思中的想法 | 创建/更新 | ✅ 可创建 |

**文档必须包含Frontmatter**：

```markdown
---
name: 文档名称
type: [dna|state|reference|guide|plan]
version: 1.0.0
date: 2026-04-01
owner: AI（自动维护）
changelog:
  - v1.0.0 (2026-04-01): 初始版本
---
```

**自动化检查**：

```bash
# 运行文档格式检查
python scripts/check_docs.py
```

---

## 一、项目愿景

### 1.1 一句话定义

让AI像教练一样**读懂棋局**、**讲解棋局**，而不是念坐标。

### 1.2 核心价值

| 价值 | 实现方式 | 状态 |
|------|----------|------|
| **零幻觉** | 规则标签100%准确，Evidence Map约束LLM | ✅ |
| **教练式讲解** | 基于事实的因果分析，不是念坐标 | ✅ |
| **双模式响应** | 快速<1秒 / 深度3-5秒（SSE流式） | ✅ |
| **棋书知识** | RAG检索棋书内容，融入讲解 | ⏳ 待录入 |
| **棋谱检索** | Neo4j存储19万局历史对局 | ✅ |
| **现实棋盘识别** | YOLO拍照识别现实棋盘 | ⏳ 训练中 |

### 1.3 目标用户

- 象棋学习者（教学讲解）
- 棋谱研究者（历史对局分析）
- 比赛选手（复盘分析）

### 1.4 设计理念

> "设计，为专注而生"

我们在设计这套界面的时候，问了自己一个最核心的问题：一个想要静下心来学棋的人，他真正需要的，到底是什么？

如今的很多AI应用，都在试图用炫酷的动效、繁杂的视觉元素，去抓住用户的眼球。但我们很清楚，对于一个学棋的人来说，这些东西，只会分散他的注意力，只会成为他理解棋理的阻碍。

所以，我们选择了一条完全不同的路：

- **摒弃冗余的炫酷，回归体验的本质**
- **以空间感，构建界面的秩序**
- **用材质的差异，划分清晰的层级**
- **降低认知负担，让注意力回归棋局本身**
- **让技术隐于无形，让用户聚焦核心**

我们没有做任何多余的设计，只是让每一个元素，都服务于「让用户专注于棋局」这个核心目标。

我们希望，这个界面是安静的、克制的。它不会跳出来告诉你「我有多厉害」，只会默默在背后，帮你扫清所有学习的障碍。它让你忘掉界面的存在，完全沉浸在象棋的世界里。

**真正的好设计，是你感受不到它的存在，却能处处感受到它为你带来的便利。**

### 1.5 核心技术决策

| 决策 | 选择 | 理由 |
|------|------|------|
| 特征提取 | 规则脚本（非模型） | 100%准确，无幻觉，可解释 |
| LLM约束 | Evidence Map | 事实锚定，防止LLM编造 |
| 引擎 | Pikafish | 开源中国象棋引擎 |
| 图数据库 | Neo4j | 棋谱关系查询，相似局面检索 |
| 前端渲染 | WebGL Liquid Glass | 特色交互语言，材质隐喻 |

---

## 二、系统架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                         前端 (React + TypeScript)                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │            Liquid Glass WebGL 渲染层                        ││
│  │  四步管线: bgPass → vBlur → hBlur → mainPass → 屏幕       ││
│  └─────────────────────────────────────────────────────────────┘│
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐│
│  │   棋盘组件    │  │  分析面板    │  │   专家卡片动画系统       ││
│  │ (ChessBoard) │  │ (DeepPanel) │  │ (AgentCardFlip/Expert)  ││
│  └──────────────┘  └──────────────┘  └──────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
                                  │ HTTP/SSE
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                      后端 (FastAPI)                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐│
│  │  /api/analyze/quick │  /api/analyze/deep │  /api/tactical-tags ││
│  └──────────────┘  └──────────────┘  └──────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
                                  │
              ┌───────────────────┼───────────────────┐
              ▼                   ▼                   ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│     规则引擎       │  │       LLM         │  │   引擎/知识图谱    │
│  38标签检测       │  │  10工具+多专家    │  │ Pikafish/Neo4j   │
│  张力检测         │  │  Evidence Map     │  │                  │
└──────────────────┘  └──────────────────┘  └──────────────────┘
```

### 2.2 技术栈

| 层级 | 技术 |
|------|------|
| 前端框架 | React 18 + TypeScript + Vite |
| 状态管理 | Zustand |
| 动画 | Framer Motion |
| 参数面板 | Leva |
| 3D渲染 | WebGL（原生，无框架） |
| 后端框架 | FastAPI + uvicorn |
| 棋盘规则 | python-xq (xq基本规则) + 自研扩展 |
| 引擎 | Pikafish (UCI协议) |
| 图数据库 | Neo4j 5.x |
| LLM | 通义千问 GLM-5（可配置） |

### 2.3 启动端口

| 服务 | 端口 | 状态 |
|------|------|------|
| 前端 | 3000/3001 | 开发中 |
| 后端API | 8002 | 运行中 |
| Neo4j Browser | 7474 | 可选 |
| Neo4j Bolt | 7687 | 可选 |

---

## 三、核心能力层

### 3.1 标签检测体系（38个标签，9大层级）

**设计原则**：
- 100%规则硬判定，置信度二元化（0或1）
- 每个标签必须绑定具体棋子坐标
- 格式：`颜色兵种-(x,y)`，如 `红车-(5,8)`

**九大层级**：

| 层级 | 标签数 | 核心标签 | 检测方法 | 状态 |
|------|--------|----------|----------|------|
| 1. 将杀困毙层 | 3 | is_check, is_checkmate, is_stalemate | `_detect_check_mate_stalemate()` | ✅ |
| 2. 捉子层 | 3 | is_attack_unprotected, is_mutual_attack, is_attack_king_adjacent | `_detect_capture()` | ✅ |
| 3. 闪击抽将层 | 3 | is_discovered_check, is_double_attack_with_check, is_discovered_attack | `_detect_discovered_attack()` | ✅ |
| 4. 牵制串打层 | 2 | is_pinned, is_cannon_double_attack | `_detect_pin_skewer()` | ✅ |
| 5. 标准杀法层 | 8 | 马后炮、铁门栓、双车错、卧槽马、白脸将、重炮杀、海底捞月、侧面虎 | `_detect_standard_mate()` | ✅ |
| 6. 子力状态层 | 2 | piece_is_unprotected, cannon_has_platform | `_detect_piece_status()` | ✅ |
| 7. 走法质量层 | 6 | move_is_blunder, move_is_capture, move_gives_check等 | `detect_move_quality()` | ✅ |
| 8. 战略评估层 | 5 | controls_open_file, has_active_pieces, piece_coordination等 | `detect_strategic_tags()` | ✅ |
| 9. 引擎对齐层 | 3 | engine_only_move, engine_best_by_margin, engine_forcing_sequence | 引擎辅助 | ✅ |
| 10. 局面语义层 | 6 | phase_*, horse_leg_blocked, kings_face_to_face等 | `_detect_semantic()` | ✅ |

**完整标签列表**（38个）：

```python
# 将杀困毙层
is_check                    # 被将军
is_checkmate               # 将死
is_stalemate               # 困毙

# 捉子层
is_attack_unprotected      # 攻无根
is_mutual_attack           # 互吃
is_attack_king_adjacent    # 攻将邻

# 闪击抽将层
is_discovered_check        # 闪将
is_double_attack_with_check # 抽将
is_discovered_attack       # 闪击

# 牵制串打层
is_pinned                  # 被牵制
is_cannon_double_attack    # 炮串打

# 标准杀法层
checkmate_horse_back_cannon  # 马后炮
checkmate_iron_gate         # 铁门栓
checkmate_double_rook       # 双车错
checkmate_horse_corner      # 卧槽马
checkmate_bare_king         # 白脸将
checkmate_double_cannon_battery  # 重炮杀
checkmate_sea_bottom_moon   # 海底捞月
checkmate_side_tiger         # 侧面虎

# 子力状态层
piece_is_unprotected        # 子无根
cannon_has_platform         # 炮有架

# 局面语义层
phase_opening              # 开局阶段
phase_middlegame           # 中局阶段
phase_endgame              # 残局阶段
king_safety_critical       # 将帅危急
has_initiative             # 握有主动权
is_forcing_move            # 强制手段
horse_leg_blocked          # 马脚被别
kings_face_to_face         # 双将对面
cannon_battery             # 重炮阵型
favorable_exchange         # 有利兑换

# 走法质量层
move_is_blunder            # 严重失误
move_is_capture            # 吃子走法
move_gives_check           # 将军走法
move_defends_piece         # 防守走法
move_escapes_threat        # 逃脱走法
move_improves_position     # 改善位置

# 战略评估层
controls_open_file         # 控制开放线
has_active_pieces          # 子力活跃
piece_coordination         # 子力协同
king_safety_good          # 将帅安全
has_space_advantage        # 空间优势

# 引擎对齐层
engine_only_move           # 唯一不输棋
engine_best_by_margin      # 明显最佳
engine_forcing_sequence    # 强制序列
```

**核心文件**：
- `core/rules/tactical_tags.py` - 标签定义
- `core/rules/tactical_detector.py` - 检测器实现（约2600行）
- `core/rules/xiangqi_rules.py` - 中国象棋规则引擎

**检测结果格式**：

```python
@dataclass
class TagDetectionResult:
    tag: TacticalTag          # 标签定义
    detected: bool            # 是否检测到
    confidence: float         # 置信度（0.0或1.0）
    bind_pieces: List[str]   # 绑定的棋子列表 ["红车-(5,8)", ...]
    metadata: Dict[str, Any]  # 额外元数据
```

---

### 3.2 张力检测器（创新设计）

**6种张力类型**：

| 张力类型 | 说明 | 触发条件 |
|----------|------|----------|
| `HIDDEN_IMBALANCE` | 评估异常 | \|cp\| > 300 且 tactical_count < 2 |
| `MATERIAL_VS_INITIATIVE` | 子力vs攻势 | 子力占优但对方有攻势 |
| `CRISIS_WITH_RESOURCES` | 危机中的资源 | has_check AND (has_unprotected OR has_initiative) |
| `SLEEPING_PIECE` | 沉睡的强子 | 有价值高但活跃度低的棋子 |
| `TAG_CONTRADICTION` | 标签矛盾 | 多个标签描述冲突 |
| `PHASE_MISMATCH` | 阶段错位 | 局面特征与当前阶段不匹配 |

**核心文件**：`core/rules/tension_detector.py`

---

### 3.3 Agent工具（12个）

**设计原则**：
- 原子化：每个工具只做一件事
- 可组合：工具之间可以串联
- 返回结构化：方便LLM理解和展示

**工具列表**：

| 类别 | 工具名 | 功能描述 |
|------|--------|----------|
| 棋子关系 | `get_piece_attacks` | 查询某棋子攻击范围 |
| | `get_piece_defenders` | 查询谁在保护某棋子 |
| | `get_threats_to_piece` | 查询谁在威胁某棋子 |
| | `get_piece_relations` | 综合查询（一站式） |
| 走法分析 | `analyze_move` | 深度分析某步棋的效果 |
| | `compare_moves` | 对比多步棋的优劣 |
| | `get_forcing_sequence` | 分析强制序列 |
| 走法模拟 | `simulate_move` | 模拟走棋，对比前后标签/将军/吃子变化 |
| 引擎分析 | `engine_deep_analysis` | 引擎深度分析 |
| | `engine_alternatives` | 候选走法对比 |
| 战略分析 | `analyze_position_strategy` | 局面战略分析 |
| 知识检索 | `query_chess_principles` | 检索局面适用棋理原则 |

**ToolResult返回格式**：

```python
@dataclass
class ToolResult:
    success: bool
    data: Dict[str, Any]     # 结构化数据
    message: str             # 人类可读摘要
    thinking_hint: str       # 思考过程提示
```

**核心文件**：`core/llm/agent_tools.py`（约1020行）

---

### 3.4 多专家并行架构

**架构图**：

```
                    ┌─────────────────────────────┐
                    │         Orchestrator         │
                    │   张力驱动决策（自适应）     │
                    └──────────────┬──────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              ▼                    ▼                    ▼
       ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
       │   战术专家    │     │   战略专家    │     │   引擎专家    │
       │(TacticsAgent)│     │(StrategyExpert│     │(EngineExpert)│
       │  6个工具    │     │   4个工具    │     │   4个工具    │
       │ 子力攻防    │     │  全局战略    │     │  评估解读    │
       └──────┬──────┘     └──────┬──────┘     └──────┬──────┘
              └────────────────────┼────────────────────┘
                                   ▼
                         ┌─────────────────────┐
                         │      Synthesizer     │
                         │  综合三方结论→统一讲解│
                         └─────────────────────┘
```

**自适应决策策略**：

| 条件 | 执行 |
|------|------|
| 张力数量==0 且 开局 | 单Agent快速分析 |
| 张力<=2 | 单Agent+扩展轮次 |
| 张力>=3 或 CRITICAL | 多Agent并行 |
| 用户明确要求深度分析 | 多Agent并行 |

**专家配置**：

| 专家 | 最大轮次 | 超时 | 工具集 |
|------|----------|------|--------|
| 战术专家 | 3 | 60s | 6个（棋子攻防+走法） |
| 战略专家 | 2 | 60s | 4个（局面战略） |
| 引擎专家 | 2 | 60s | 4个（引擎分析） |

**核心文件**：
- `core/llm/multi_agent_orchestrator.py` - 协调器
- `core/llm/experts/base_expert.py` - 专家基类
- `core/llm/experts/tactics_expert.py` - 战术专家
- `core/llm/experts/strategy_expert.py` - 战略专家
- `core/llm/experts/engine_expert.py` - 引擎专家

---

### 3.5 双模式讲解

**快速模式**（<1秒）：
- 预计算Evidence Map
- 直接返回标签+引擎数据
- 适合：对弈提示、引擎推荐解释

**深度思考模式**（3-5秒）：
- Agent主动调用工具分析
- SSE流式返回思考过程
- 适合：棋谱讲解、复杂局面分析

**三档讲解模式**（规划中）：
- 初学者模式：简单语言，重点标注
- 进阶模式：专业术语，深度分析
- 教练模式：师范级讲解，变例扩展

---

### 3.6 阶段感知思维链

**阶段检测**：

| 阶段 | 条件 | 思维重点 |
|------|------|----------|
| 开局 | move_count <= 15 且 total_pieces >= 26 | 出子效率、中心控制、先手争夺 |
| 中局 | 15 < move_count < 60 | 子力纠缠、战术组合、局面转换 |
| 残局 | total_pieces <= 14 或 move_count >= 60 | 王的安全、兵的位置、取胜技术 |

**核心文件**：
- `core/llm/thinking_templates.py` - 思维链模板
- `core/llm/opening_knowledge.py` - 开局知识库

**当前状态**：
- 开局思维链：✅ 框架已实现
- 中局思维链：⏳ 待实现
- 残局思维链：⏳ 待实现

---

## 四、前端架构（Liquid Glass）

### 4.1 设计理念

**核心原则**：

```
设计，为专注而生

摒弃冗余的炫酷，回归体验的本质
以空间感，构建界面的秩序
用材质的差异，划分清晰的层级
降低认知负担，让注意力回归棋局本身
让技术隐于无形，让用户聚焦核心
```

**设计语言**：

- **安静**：不抢注意力，让用户沉浸在棋局
- **克制**：每个元素都有存在的理由
- **材质隐喻**：玻璃材质暗示"通透"和"层级"
- **空间秩序**：用留白和位置传达信息优先级

### 4.2 组件架构

```
frontend/src/
├── components/
│   ├── ChessBoard.tsx              # 棋盘组件
│   ├── EngineChart.tsx             # 引擎评分折线图（纯SVG）
│   ├── DeepAnalysisPanel.tsx       # 深度分析面板入口
│   ├── AgentThinkingPanel.tsx      # Agent思考面板容器
│   ├── AgentCardFlip.tsx           # 扑克牌翻面动画核心
│   ├── ExpertCard.tsx              # 单专家卡片组件
│   ├── SynthesisPanel.tsx          # 综合裁判面板
│   ├── PositionAnalysisPanel.tsx   # 局面分析面板
│   ├── ReplayNavigator.tsx         # 复盘导航
│   ├── ReplayPanel.tsx             # 复盘面板
│   ├── PGNPanel.tsx                # PGN导入面板
│   ├── ThinkingStream.tsx          # 协调者思维流
│   ├── LiquidGlassApp.tsx          # WebGL液态玻璃主控
│   ├── LiquidGlassSurface.tsx       # 通用液态玻璃表面
│   ├── LiquidGlassBackground.tsx   # 背景组件
│   └── WebGLButton.tsx             # WebGL按钮
├── store/
│   ├── useGameStore.ts             # 游戏状态（棋盘/走法/回放）
│   ├── useAgentStore.ts            # Agent状态（专家/动画阶段）
│   └── useGlassParamsStore.ts      # 液态玻璃参数（Leva）
├── services/
│   └── api.ts                      # API调用层（唯一后端通信入口）
├── hooks/
│   ├── useLiquidGlass.ts           # 液态玻璃效果Hook
│   ├── useGlassPresets.ts          # 预设管理
│   └── useLiquidCardUniforms.ts    # Uniforms管理
├── shaders/
│   └── liquidglass/
│       ├── vertex.glsl              # 顶点着色器
│       ├── fragment-main.glsl       # 主渲染着色器（617行）
│       ├── fragment-bg.glsl         # 背景着色器
│       ├── fragment-bg-vblur.glsl    # 竖向模糊
│       └── fragment-bg-hblur.glsl    # 横向模糊
├── presets/
│   ├── sidebar-left.json            # 左侧栏预设
│   └── sidebar-right.json           # 右侧栏预设
└── utils/
    ├── LiquidGlassGLUtils.ts        # WebGL工具函数
    ├── LiquidGlassConfig.ts         # 玻璃配置常量
    └── pieces.ts                    # 棋子名称映射
```

### 4.3 WebGL渲染管线

**四步渲染**：

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

**着色器核心技术**：

| 技术 | 说明 |
|------|------|
| SDF形状 | `sdCircle()` + `roundedRectSDF()`（超椭圆圆角矩形） |
| 形状融合 | `smin()` 平滑最小值 |
| 折射 | 根据法线偏移采样背景纹理 |
| 色散 | RGB三通道分别偏移 (N_R/N_G/N_B = 0.98/1.0/1.02) |
| 菲涅尔 | `fresnelFactor = clamp(pow(1.0 + merged * ... + fresnelHardness, 5.0), 0.0, 1.0)` |
| Glare | 基于法线角度计算光泽条 |
| 色彩空间 | 全程LCH空间做颜色混合 |
| 调试系统 | STEP 0-9 分级可视化 |

**核心文件**：
- `frontend/src/shaders/liquidglass/fragment-main.glsl`（617行）
- `frontend/src/components/LiquidGlassApp.tsx`（主控）

### 4.4 状态管理

**三个Store**：

```typescript
// 1. useGameStore - 游戏核心状态
interface GameState {
  board: string[][];              // 9x10棋盘
  fen: string;                    // FEN格式
  history: string[];              // 走法历史
  legalMoves: string[];           // 当前合法走法
  selectedPos: {row, col};       // 选中位置
  gameMode: 'analysis'|'pvp'|'pve_red'|'pve_black'|'replay';
  lastMove: {from, to};          // 最后一步
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

### 4.5 SSE流式响应

**事件类型**：

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

## 五、数据/知识层

### 5.1 Neo4j棋谱（19万局）

**数据模型**：

```cypher
(:Game {id, red, black, result, date})
(:Position {fen, total_games, red_win_rate})
(:Move {uci, chinese, quality})
(:Position)-[:NEXT {move}]->(:Position)
(:Game)-[:HAS_POSITION]->(:Position)
```

**核心方法**：

```python
def query(self, fen: str, moves: List[str] = None) -> KGResult:
    """查询知识图谱，返回胜率和开局名"""

def query_position(self, fen: str) -> PositionStats:
    """查询局面统计数据"""

def get_next_moves(self, fen: str) -> List[Dict]:
    """获取下一步走法统计"""
```

**核心文件**：`core/kg/neo4j_kg.py`

**当前状态**：✅ 框架完成，19万局数据已录入

---

### 5.2 YOLO棋盘识别（规划中）

**功能流程**：

```
照片输入 → YOLO检测棋子位置 → 棋子分类 → 生成FEN → 进入分析流程
```

**核心文件**（待实现）：
- `core/vision/board_detector.py`
- `core/vision/piece_classifier.py`

**当前状态**：⏳ YOLO权重已训练，FEN转换算法编写中

---

### 5.3 RAG棋书知识库（规划中）

**规划内容**：
- 象棋入门教程
- 战术组合手册
- 开局原理
- 残局定式

**核心文件**（待实现）：`core/llm/rag_retriever.py`

**当前状态**：⏳ 未录入

---

## 六、API设计

### 6.1 核心端点

| 端点 | 方法 | 用途 | 响应时间 |
|------|------|------|----------|
| `/api/analyze/quick` | POST | 快速分析 | < 1秒 |
| `/api/analyze/deep` | POST | 深度分析(SSE流式) | 3-5秒 |
| `/api/analyze/deep-stream` | GET | 深度分析(SSE，GET版本) | 3-5秒 |
| `/api/tactical-tags` | POST | 标签检测 | - |
| `/api/move-quality` | POST | 走法质量检测 | - |
| `/api/board-structure` | POST | 局面结构解析 | - |
| `/api/legal-moves` | POST | 合法走法查询 | - |
| `/api/move` | POST | 执行一步棋 | - |
| `/api/best-moves` | POST | AI推荐走法 | - |
| `/api/pgn-load` | POST | PGN文件加载 | - |
| `/api/pgn-navigate` | POST | PGN导航 | - |
| `/api/review` | POST | 复盘报告生成 | - |
| `/api/glass-preset/save` | POST | 保存液态玻璃预设 | - |
| `/api/glass-preset/load` | GET | 加载液态玻璃预设 | - |

### 6.2 Evidence Map格式

```json
{
  "facts_rules": [
    {
      "tag": "is_attack_unprotected",
      "confidence": 1.0,
      "bind_pieces": ["红车-(5,8)", "黑马-(7,8)"],
      "description": "攻无根：一方棋子攻击对方无保护棋子"
    }
  ],
  "engine_eval": {"cp": 150, "best": "h2e2", "pv": ["h2e2", "h7e7"]},
  "phase": "中局",
  "initiative": "红方"
}
```

### 6.3 SSE流式响应格式

```
data: {"type": "thinking", "stage": 1, "message": "分析局面特征..."}
data: {"type": "expert_tactics_thinking", "expert": "tactics", "message": "..."}
data: {"type": "expert_result", "expert": "tactics", "finding": "红车控制中路，威胁黑马"}
data: {"type": "synthesis_chunk", "message": "..."}
data: {"type": "result", "explanation": "...", "confidence": "high"}
```

---

## 七、LLM调教指南

### 7.1 System Prompt设计

```
你是象棋教练AI，擅长分析局面和讲解棋理。

【你的能力】
- 你可以调用12个分析工具（见工具列表）
- 你会收到Evidence Map（事实锚点），必须基于此回答
- 你擅长用通俗语言解释复杂的战术和战略

【你的约束】
- 所有事实必须来自Evidence Map或工具调用结果
- 不得编造棋子位置、走法或评估
- 不确定时说"需要进一步分析"，不要猜测

【你的思考框架】
1. 先看Evidence Map中的标签，理解局面发生了什么
2. 如果需要深入，调用工具验证假设
3. 用"因为...所以..."的逻辑组织讲解
4. 根据用户水平调整讲解深度
```

### 7.2 工具描述优化

**原则**：告诉LLM"什么时候用"，而不仅仅是"做什么"

**示例**：

```python
def get_piece_attacks(fen, piece):
    """
    获取棋子攻击范围

    【什么时候用】
    - 当你想知道某个棋子能攻击什么时
    - 当你分析"这步棋威胁了什么"时
    - 当你想解释"为什么要走这步"时

    【参数】
    - fen: 当前局面
    - piece: 棋子标识，如 "红车" 或 "r" 或坐标 "(5,8)"
    """
```

### 7.3 错误纠正

- **工具调用约束**：System Prompt中明确调用规则
- **结果验证**：后端验证工具返回是否合理
- **回退机制**：Agent分析失败时回退到快速模式

---

## 八、项目结构（完整目录树）

```
xiangqi-hybrid-agent/
├── api/                          # FastAPI后端
│   └── main.py                   # API端点定义（约1970行）
├── frontend/                     # React前端
│   ├── src/
│   │   ├── components/          # 22个React组件
│   │   ├── store/               # 3个Zustand状态管理
│   │   ├── services/            # API调用层
│   │   ├── hooks/               # 自定义Hooks
│   │   ├── shaders/             # WebGL着色器
│   │   ├── presets/             # 预设配置
│   │   ├── utils/              # 工具函数
│   │   ├── App.tsx             # 应用入口
│   │   └── main.tsx            # React入口
│   ├── public/presets/          # 预设JSON
│   └── package.json
├── core/                         # 核心模块
│   ├── rules/                   # 规则引擎
│   │   ├── tactical_tags.py     # 38个标签定义
│   │   ├── tactical_detector.py # 标签检测器（约2600行）
│   │   ├── tension_detector.py  # 张力检测器
│   │   ├── xiangqi_rules.py     # 中国象棋规则
│   │   └── consistency_checker.py # 一致性检查
│   ├── llm/                     # LLM相关
│   │   ├── client.py           # LLM客户端
│   │   ├── agent_tools.py      # 12个Agent工具
│   │   ├── xiangqi_coach.py   # 单Agent教练（约1070行）
│   │   ├── multi_agent_orchestrator.py # 多Agent协调器
│   │   ├── thinking_templates.py # 思维链模板
│   │   ├── opening_knowledge.py  # 开局知识库
│   │   ├── fewshot_examples.py   # Few-shot示例
│   │   └── experts/           # 三专家模块
│   │       ├── base_expert.py
│   │       ├── tactics_expert.py
│   │       ├── strategy_expert.py
│   │       └── engine_expert.py
│   ├── engine/                 # Pikafish引擎封装
│   │   ├── pikafish_engine.py
│   │   └── base.py
│   ├── kg/                     # Neo4j知识图谱
│   │   └── neo4j_kg.py
│   ├── semantic/               # 语义层
│   │   └── board_structure_parser.py
│   └── vision/                 # 视觉识别（规划中）
│       ├── board_detector.py   # YOLO棋盘检测
│       └── piece_classifier.py # 棋子分类
├── data/                        # 数据目录
│   ├── init_data/              # 原始PGN(19万局)
│   ├── engine/                 # Pikafish引擎
│   ├── books/                  # 棋书PDF
│   └── games/                  # 对局数据库
├── docs/                       # 文档
│   ├── DNA.md                  # 项目DNA（宪法）
│   ├── STATE.md                # 当前状态
│   ├── reference/              # 参考文档
│   │   ├── tag_reference.md   # 标签参考
│   │   ├── agent_tools_spec.md # Agent工具规范
│   │   ├── thinking_framework.md # 思维链框架
│   │   ├── liquid_glass.md   # Liquid Glass技术说明
│   │   ├── api_contract.md   # API接口契约
│   │   ├── fewshot_examples.md # Few-shot示例
│   │   └── internal/         # 内部算法参考
│   │       ├── rule_engine_spec.md
│   │       ├── tactical_detector_algorithm.md
│   │       └── ...
│   ├── guides/                # 开发指南
│   │   ├── frontend.md       # 前端开发指南
│   │   ├── backend.md       # 后端开发指南
│   │   ├── component.md     # 组件规范
│   │   ├── state_management.md # 状态管理规范
│   │   ├── testing.md       # 测试规范
│   │   └── onboarding.md     # 新人入门
│   ├── plans/                # Plan文档
│   │   ├── README.md        # Plan规范
│   │   ├── 001-three-layer-prompt.md
│   │   └── frontend/
│   │       ├── 001-agent-poker-panel.md
│   │       └── 002-liquid-glass.md
│   └── _archived/             # 已归档文档
│       ├── v1.0/            # v1.0版本存档
│       └── temp/             # 待清理的临时文件
├── scripts/                     # 脚本
│   ├── start_all.bat           # 启动脚本
│   └── prepare_resources.sh    # 资源准备
├── tests/                       # 测试
│   ├── test_tactical_detector.py
│   ├── test_golden_positions.py
│   ├── test_agent.py
│   ├── golden_positions.py
│   └── pytest.ini
├── requirements.txt             # Python依赖
├── .env                        # 环境变量
└── README.md
```

---

## 九、开发路线图

### ✅ 已完成

- [x] 标签体系定义（38个）
- [x] 标签检测器实现
- [x] 张力检测器实现（6种张力类型）
- [x] Agent工具实现（12个）
- [x] 多专家并行架构（战术/战略/引擎）
- [x] 双模式API
- [x] SSE流式输出
- [x] 前端Liquid Glass渲染
- [x] Neo4j棋谱数据库（19万局）
- [x] Pikafish引擎集成

### 🔄 进行中

- [ ] 开局思维链完善
- [ ] 三档讲解模式
- [ ] YOLO FEN转换算法
- [ ] API端点规范化
- [ ] 标签检测准确性验证（经典棋局测试）

### ⏳ 规划中

- [ ] 中局思维链框架
- [ ] 残局思维链框架
- [ ] RAG棋书知识库录入
- [ ] Transformer相似局面匹配（未来）
- [ ] 性能优化（缓存机制）

---

## 十、快速启动

### 环境要求

- Python 3.10+
- Node.js 18+
- Neo4j 5.x (可选，端口7687)

### 启动命令

```bash
# 1. 启动Neo4j (如果需要棋谱检索)
neo4j start

# 2. 启动后端
python -m uvicorn api.main:app --host 0.0.0.0 --port 8002

# 3. 启动前端
cd frontend && npm run dev

# 4. 访问
# http://localhost:3000
```

### 测试

```bash
# 运行所有测试
pytest -q

# 测试标签检测
python -c "
from core.rules.tactical_detector import TacticalDetector
d = TacticalDetector()
print(f'Total tags: {len(d.all_tags)}')
"

# 测试Agent工具
python -c "
from core.llm.agent_tools import AgentTools
tools = AgentTools()
print(f'Agent tools: {len([m for m in dir(tools) if not m.startswith(\"_\")])}')
"
```

---

## 十一、参考文档索引

### 宪法与状态

| 文档 | 位置 | 内容 |
|------|------|------|
| 项目DNA | `docs/DNA.md` | 项目架构全貌（必读） |
| 当前状态 | `docs/STATE.md` | 开发进度、待办事项 |

### 开发指南

| 文档 | 位置 | 内容 |
|------|------|------|
| 前端指南 | `docs/guides/frontend.md` | 前端开发完整文档 |
| 后端指南 | `docs/guides/backend.md` | 后端开发指南 |
| 组件规范 | `docs/guides/component.md` | 组件开发规范 |
| 状态管理 | `docs/guides/state_management.md` | Zustand规范 |
| 测试规范 | `docs/guides/testing.md` | 测试规范 |
| 新人入门 | `docs/guides/onboarding.md` | 新人入门指南 |

### 技术参考

| 文档 | 位置 | 内容 |
|------|------|------|
| 标签参考 | `docs/reference/tag_reference.md` | 38个标签完整定义 |
| Agent工具规范 | `docs/reference/agent_tools_spec.md` | 12个工具接口规范 |
| 思维链框架 | `docs/reference/thinking_framework.md` | 特级大师思维链框架 |
| Liquid Glass | `docs/reference/liquid_glass.md` | Liquid Glass技术说明 |
| API契约 | `docs/reference/api_contract.md` | 前后端接口契约 |

### Plan文档

| 文档 | 位置 | 内容 |
|------|------|------|
| Plan规范 | `docs/plans/README.md` | Plan书写规范 |
| 三层Prompt | `docs/plans/001-three-layer-prompt.md` | 三层分离Prompt框架 |
| Liquid Glass方案 | `docs/plans/frontend/002-liquid-glass.md` | WebGL渲染方案 |

---

## 附录A：棋子编码对照

| 编码 | 红方 | 黑方 |
|------|------|------|
| K/k | 帅 | 将 |
| A/a | 仕 | 士 |
| B/b | 相 | 象 |
| N/n | 马 | 马 |
| R/r | 车 | 车 |
| C/c | 炮 | 炮 |
| P/p | 兵 | 卒 |

---

## 附录B：FEN格式说明

中国象棋标准FEN格式：
```
rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1
├── 9列红方底排─┘  │ │ │ │  │ │  ├── 9列黑方底排
│                 │ │ │ │  │ │  │
│                 │ │ │ │  │ └── 空格分隔：红方先行
│                 │ │ │ │  │
│                 │ │ │ │  └── 空格分隔
│                 │ │ │ │
│                 └──┴──┴──┴── 9列红方顶排
│
└── 红方底排
```

---

**文档版本**: v2.0
**维护者**: 项目团队
**更新频率**: 重大变更时更新
