# 象棋AI混合代理教学与对弈系统 (Xiangqi Hybrid Agent)

**基于规则-LLM混合架构的象棋教练系统，通过Evidence Map约束大模型输出，实现零幻觉的棋局分析。**

---

## 项目概述

本项目是一个开源的中国象棋智能分析、对弈与讲解系统，采用**神经符号AI (Neuro-Symbolic AI)** 架构，结合符号系统的高精度计算与大语言模型的智能讲解，实现"引擎算得准 + AI讲得通"的融合效果。

### 核心创新

| 创新点 | 说明 | 实现方式 |
|--------|------|----------|
| **零幻觉分析** | 所有分析基于规则检测的事实，杜绝LLM编造 | 45个战术标签 + Evidence Map约束 |
| **真Agent模式** | LLM主动调用工具分析，像教练一样思考 | Function Calling + 10个分析工具 |
| **特级大师思维链** | 根据开局/中局/残局自动切换思维框架 | 阶段感知 + 开局知识库 |

### 核心特性

- 🎯 **战术精确计算** - Pikafish引擎提供零漏算评估
- 🏷️ **45个战术标签** - 规则硬判定，置信度二元化（0或1）
- 🤖 **教练级AI讲解** - 基于事实的因果分析，不是念坐标
- ⚡ **双模式响应** - 快速模式<1秒 / 深度模式3-5秒（SSE流式）
- 📚 **知识图谱** - Neo4j存储历史对局，支持相似局面检索
- 👁️ **多模态识别** - 支持棋盘图片识别（YOLO规划中）
- 🖥️ **商业级前端** - React + TypeScript + Vite，CSS Grid 响应式布局 + Apple Spring 动画

---

## 快速开始

### 环境要求

- Python >= 3.10
- Node.js >= 18
- Neo4j >= 5.x (可选，用于知识图谱)

### 安装依赖

```bash
# 克隆仓库
git clone https://github.com/wangzicheng0682/xiangqi-hybrid-agent.git
cd xiangqi-hybrid-agent

# Python依赖
pip install -r requirements.txt

# 前端依赖
cd frontend
npm install
```

### 配置

1. **LLM配置** - 创建 `.env` 文件：
```bash
DASHSCOPE_API_KEY=your_api_key
```

2. **Neo4j配置**（可选）- 创建 `neo4j.ini` 文件：
```ini
uri = "bolt://localhost:7687"
username = "neo4j"
password = "your_password"
database = "neo4j"
```

### 启动服务

```bash
# 1. 启动后端（端口8002）
python -m uvicorn api.main:app --host 0.0.0.0 --port 8002

# 2. 启动前端（端口3000）
cd frontend
npm run dev

# 3. 访问 http://localhost:3000
```

---

## 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        前端 (React + TypeScript)                  │
│  棋盘展示 / 走法输入 / 深度分析面板 / 思考过程实时展示             │
└─────────────────────────────────────────────────────────────────┘
                              ↓ API调用
┌─────────────────────────────────────────────────────────────────┐
│                     后端 (FastAPI)                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │  快速模式   │  │  深度模式   │  │  棋谱模式   │              │
│  │  < 1秒      │  │  3-5秒 SSE  │  │  走法标注   │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      核心能力层（事实层）                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐            │
│  │标签检测器│ │张力检测器│ │引擎分析  │ │Agent工具 │            │
│  │(45标签)  │ │(6种张力) │ │(Pikafish)│ │(10工具)  │            │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘            │
└─────────────────────────────────────────────────────────────────┘
                              ↓ Evidence Map
┌─────────────────────────────────────────────────────────────────┐
│                      表达层（LLM）                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ System Prompt│  │ Function     │  │ 思维链模板   │          │
│  │ (教练身份)   │  │ Calling      │  │ (阶段感知)   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

### 核心数据流

```
FEN输入 → 局面解析 → 标签检测(45个) → Evidence Map → LLM讲解 → 前端展示
                ↓
            张力检测(6种) → 主要矛盾识别 → 假设驱动工具调用
```

---

## 技术栈

| 组件 | 技术选型 | 用途 |
|------|----------|------|
| 前端框架 | React 18 + TypeScript + Vite | 用户界面 |
| 状态管理 | Zustand | 前端状态 |
| UI样式 | Tailwind CSS | 样式系统 |
| 后端框架 | FastAPI | REST API |
| 战术引擎 | Pikafish (Stockfish衍生) | 零漏算计算 |
| 标签检测 | 规则引擎 (Python) | 45个战术标签 |
| LLM核心 | Qwen-Max (阿里云百炼) | 讲解生成 |
| 知识图谱 | Neo4j | 历史对局、胜率统计 |
| 棋书检索 | FAISS + LangChain (规划中) | 经典文献引用 |

---

## API端点

### 核心端点

| 端点 | 方法 | 说明 | 模式 |
|------|------|------|------|
| `/api/analyze/quick` | POST | 快速分析 | <1秒 |
| `/api/analyze/deep` | POST | 深度分析(SSE流式) | 3-5秒 |
| `/api/tactical-tags` | POST | 战术标签检测 | - |
| `/api/move-quality` | POST | 走法质量检测 | - |
| `/api/legal-moves` | POST | 合法走法查询 | - |
| `/api/best-moves` | POST | 双方最优解 | - |
| `/api/move` | POST | 执行走棋 | - |
| `/api/ai-move` | POST | AI走棋 | - |
| `/api/analyze-move` | POST | 分析走法质量 | - |
| `/api/pgn-load` | POST | 加载PGN文件 | - |
| `/api/pgn-navigate` | POST | PGN导航 | - |

### 示例请求

```bash
# 快速分析
curl -X POST http://localhost:8002/api/analyze/quick \
  -H "Content-Type: application/json" \
  -d '{"fen": "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1", "mode": "hint"}'

# 战术标签检测
curl -X POST http://localhost:8002/api/tactical-tags \
  -H "Content-Type: application/json" \
  -d '{"fen": "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"}'
```

---

## 核心能力详解

### 1. 标签检测体系（45个标签）

**九大层级**：

| 层级 | 标签数 | 核心标签 | 说明 |
|------|--------|----------|------|
| 将杀困毙层 | 3 | is_check, is_checkmate | 将军、将死、困毙检测 |
| 捉子层 | 3 | is_attack_unprotected | 捉无根子、互捉 |
| 闪击抽将层 | 3 | is_discovered_check | 闪击、抽将、双将 |
| 牵制串打层 | 2 | is_pinned | 牵制、串打 |
| 标准杀法层 | 8 | 马后炮、铁门栓等 | 经典杀法模式 |
| 子力状态层 | 2 | piece_is_unprotected | 无根子、炮架 |
| 走法质量层 | 6 | move_is_blunder | 失误、吃子、将军等 |
| 战略评估层 | 5 | has_initiative | 主动权、出子效率 |
| 引擎对齐层 | 3 | engine_best_by_margin | 引擎推荐对齐 |

### 2. 张力检测器（6种张力类型）

自动识别局面中的矛盾和异常：

| 张力类型 | 说明 | 示例 |
|----------|------|------|
| 评估异常 | 引擎评估与标签检测矛盾 | 评分领先但无优势标签 |
| 威胁失衡 | 一方威胁远大于另一方 | 红方多重威胁 |
| 子力失衡 | 子力对比与局面不符 | 多子但被动 |
| 阶段异常 | 阶段特征与回合数不符 | 10回合进入残局 |
| 王安全异常 | 王暴露但无防守 | 将帅暴露 |
| 战术机会 | 存在可利用的战术 | 捉双、牵制机会 |

### 3. Agent工具（10个工具）

LLM可自主调用的分析工具：

| 类别 | 工具 | 用途 |
|------|------|------|
| 棋子关系 | get_piece_attacks | 查询棋子攻击范围 |
| | get_piece_defenders | 查询棋子保护关系 |
| | get_threats_to_piece | 查询棋子受威胁情况 |
| | get_piece_relations | 综合关系查询 |
| 走法分析 | analyze_move | 深度分析走法效果 |
| | compare_moves | 对比多步棋优劣 |
| | get_forcing_sequence | 分析强制序列 |
| 引擎分析 | engine_deep_analysis | 引擎深度分析 |
| | engine_alternatives | 候选走法对比 |
| 战略分析 | analyze_position_strategy | 局面战略分析 |

---

## 项目结构

```
xiangqi-hybrid-agent/
├── api/
│   └── main.py                 # FastAPI后端主入口
├── frontend/
│   ├── src/
│   │   ├── components/         # React组件
│   │   │   ├── ChessBoard.tsx      # 棋盘组件
│   │   │   ├── EngineChart.tsx     # 引擎评分折线图
│   │   │   ├── DeepAnalysisPanel.tsx # 深度分析面板
│   │   │   ├── PositionAnalysisPanel.tsx # 局面分析面板
│   │   │   ├── TacticalTagsPanel.tsx # 战术标签面板
│   │   │   ├── ReplayPanel.tsx     # 复盘面板
│   │   │   ├── ReplayNavigator.tsx # 导航组件
│   │   │   ├── SynthesisPanel.tsx  # 综合面板
│   │   │   ├── ExpertCard.tsx      # 专家卡片
│   │   │   └── AgentDebutPanel.tsx # Agent登场动画
│   │   ├── store/
│   │   │   └── useGameStore.ts     # Zustand状态管理
│   │   ├── services/
│   │   │   └── api.ts              # API服务
│   │   └── App.tsx
│   └── package.json
├── core/                       # 核心模块
│   ├── rules/                  # 规则引擎
│   │   ├── tactical_tags.py    # 45个标签定义
│   │   ├── tactical_detector.py # 标签检测器
│   │   └── tension_detector.py # 张力检测器
│   ├── llm/                    # LLM相关
│   │   ├── client.py           # LLM客户端
│   │   ├── xiangqi_coach.py    # 教练Agent
│   │   ├── agent_tools.py      # 10个Agent工具
│   │   ├── thinking_templates.py # 思维链模板
│   │   ├── opening_knowledge.py # 开局知识库
│   │   └── fewshot_examples.py # Few-shot示例
│   ├── engine/                 # 引擎封装
│   │   └── pikafish_engine.py  # Pikafish封装
│   ├── kg/                     # 知识图谱
│   │   └── neo4j_kg.py         # Neo4j封装
│   └── semantic/               # 语义层
├── data/                       # 数据目录
│   ├── engine/                 # Pikafish引擎
│   ├── init_data/              # 原始PGN棋谱
│   └── training/               # 训练数据
├── docs/                       # 文档
│   ├── DNA.md                  # 项目DNA（必读）
│   ├── STATE.md                # 当前状态
│   └── reference/              # 技术参考
└── tests/                      # 测试套件
```

---

## 开发规范

本项目严格遵循**文档驱动开发**原则：

- **单一事实来源**: `docs/DNA.md` 是项目架构全貌
- **当前状态**: `docs/STATE.md` 记录最新进度
- **可追溯性**: 每个功能必须记录在 `docs/TRACEABILITY.md`
- **测试门禁**: `pytest -q` 必须全绿才能提交

### 运行测试

```bash
# 运行所有测试
pytest -q

# 运行特定测试
pytest tests/test_tactical_detector.py -v
pytest tests/test_fewshot_examples.py -v
```

---

## 功能演示

### 游戏模式

- 📊 **分析模式** - 双方均可操作，引擎实时分析每步棋
- 👥 **双人对战** - 双方轮流操作
- 🔴 **执红对战** - 您执红方，AI执黑方
- ⚫ **执黑对战** - 您执黑方，AI执红方（棋盘自动翻转）

### 分析功能

- 实时评分变化显示
- 好棋/劣着判断
- AI自然语言点评（基于Evidence Map）
- 相似局面历史数据查询（Neo4j）
- 红黑双方最优解箭头提示
- 45个战术标签实时检测
- 深度分析（SSE流式，展示AI思考过程）

---

## 文档

### 核心文档

- [项目DNA](docs/DNA.md) - 项目架构全貌（必读）
- [项目状态](docs/STATE.md) - 当前进度与任务
- [总控母版](MASTER_BLUEPRINT.md) - 比赛答辩唯一依据

### 技术参考

- [标签参考](docs/reference/tag_reference.md) - 45个标签完整定义
- [Agent工具规范](docs/reference/agent_tools_spec.md) - 10个工具接口
- [思维链框架](docs/reference/thinking_framework.md) - 特级大师思维链

---

## 路线图

### ✅ 已完成

- [x] 45个战术标签体系定义与检测器实现（100%覆盖，mAP=1.0）
- [x] 张力检测器（6种张力类型）
- [x] 10个Agent工具实现
- [x] Function Calling Agent模式（最多3轮调用）
- [x] 双模式API（快速/深度SSE流式）
- [x] React前端框架（现代化中式设计）
- [x] 开局知识库（十大原则）
- [x] Few-shot示例库（9个经典示例）
- [x] Neo4j知识图谱框架
- [x] Pikafish引擎集成
- [x] 前端深度分析面板（SSE实时展示）
- [x] 多Agent并行架构（三专家：战术/战略/引擎）
- [x] Orchestrator协调器
- [x] 标签检测准确性验证（经典棋局测试通过）
- [x] pytest测试套件（18个用例全绿）

### 🔄 进行中

- [ ] Neo4j数据完善（框架已搭建，数据部分导入）
- [ ] 中局/残局思维链框架（模板已有，待完善）

### ⏳ 待开始

- [ ] RAG棋书知识库录入
- [ ] YOLO棋盘识别
- [ ] 三档讲解模式（初学者/进阶/教练）
- [ ] 性能优化（缓存机制）

---

## 贡献指南

本项目目前处于内部开发阶段。开源后欢迎社区贡献！

### 提交规范

1. 阅读 `docs/DNA.md` 理解项目架构
2. 确保 `pytest -q` 全绿
3. 更新 `docs/STATE.md` 记录变更
4. 提交PR并描述变更内容

---

## 许可证

MIT License

---

## 联系方式

- 项目仓库: https://github.com/wangzicheng0682/xiangqi-hybrid-agent
- 问题反馈: 请提交 GitHub Issue

---

**当前版本**: v0.8.0 (T0比赛就绪 - 多Agent并行架构)

**最后更新**: 2026-03-22
