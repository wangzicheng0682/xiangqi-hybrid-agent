# 技术架构文档（合并版）

**版本**: v1.0
**最后更新**: 2026-03-09
**用途**: 技术架构、组件设计、接口规范

---

## 🏗️ 系统架构总览

### 混合Neuro-Symbolic架构
```
┌─────────────────────────────────────────────────┐
│          用户交互层 (Web Interface)          │
│              (Gradio UI)                     │
└───────────────┬─────────────────────────────┘
                │
┌───────────────▼─────────────────────────────┐
│       智能代理编排层 (Agent Layer)          │
│           (LangGraph Orchestrator)            │
└───┬───────┬───────┬───────┬───────┬────┘
    │       │       │       │       │
┌───▼───┐ ┌▼──────┐ ┌▼──────┐ ┌▼──────┐ ┌▼──────┐
│战术引擎│ │知识图谱│ │棋书检索│ │视觉模型│ │LLM核心│
│(Engine)│ │   (KG) │ │  (RAG) │ │(Vision)│ │(LLM)  │
└────────┘ └───────┘ └───────┘ └───────┘ └───────┘
```

### 工作流程
```
用户输入（FEN/图片）
  ↓
[预处理节点] - 判断输入类型，初始化状态
  ↓
  ├─→ [视觉模型] - 如果是图片，识别棋盘
  │     ↓
  └─→ [引擎分析] - 获取最佳着法和评估
        ↓
      [知识检索] - 查询知识图谱和棋书
        ↓
      [讲解生成] - 综合生成自然语言讲解
        ↓
    用户输出（棋盘图片 + 讲解文本）
```

---

## 🔧 技术栈选型

| 组件 | 技术选型 | 版本 | 用途 | 选型理由 |
|------|----------|------|------|----------|
| 战术引擎 | Pikafish | 最新 | 零漏算计算 | 开源最强象棋引擎 |
| 知识图谱 | Neo4j | 5.x | 历史对局存储 | 图查询性能优秀 |
| 棋书检索 | FAISS | 1.7+ | 向量检索 | 高效向量相似度搜索 |
| LLM核心 | Qwen-Max | - | 讲解生成 | 中文理解能力强 |
| 视觉模型 | Qwen-VL-Max | - | 棋盘识别 | 多模态能力 |
| Agent框架 | LangGraph | 0.2+ | 多工具编排 | 状态机式编排 |
| Web界面 | Gradio | 4.x | 用户交互 | 快速原型开发 |

---

## 📐 组件设计

### 1. 战术引擎组件

#### 接口规范
```python
# core/engine/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List

@dataclass
class EngineResult:
    """引擎分析结果"""
    bestmove: str           # 最佳着法 (如: h2e2)
    score: float            # 评估分数 (红方优势为正)
    depth: int             # 搜索深度
    pv: List[str]          # 主变化线

class BaseEngine(ABC):
    """引擎抽象基类"""
    @abstractmethod
    def analyze(self, fen: str, depth: int = 20) -> Optional[EngineResult]:
        """
        分析当前局面

        Args:
            fen: 当前局面FEN字符串
            depth: 搜索深度

        Returns:
            EngineResult或None（分析失败）
        """
        pass

    @abstractmethod
    def stop(self) -> None:
        """停止引擎"""
        pass
```

#### 实现类
- `MockEngine`: Mock实现，用于测试
- `PikafishEngine`: 真实实现，UCI协议通信

---

### 2. 知识图谱组件

#### 接口规范
```python
# core/kg/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

@dataclass
class KGResult:
    """知识图谱查询结果"""
    win_rate: float          # 胜率 (0-1)
    total_games: int        # 总对局数
    opening_name: str      # 开局名称
    statistics: dict       # 额外统计信息

class BaseKG(ABC):
    """知识图谱抽象基类"""
    @abstractmethod
    def query(self, fen: str, moves: Optional[List[str]] = None) -> Optional[KGResult]:
        """
        查询局面知识

        Args:
            fen: 当前局面FEN字符串
            moves: 走法历史（可选）

        Returns:
            KGResult或None（查询失败）
        """
        pass

    @abstractmethod
    def get_similar_positions(self, fen: str, limit: int = 5) -> List[dict]:
        """
        查询相似局面

        Args:
            fen: 当前局面FEN字符串
            limit: 返回数量

        Returns:
            相似局面列表
        """
        pass
```

#### 实现类
- `MockKG`: Mock实现，用于测试
- `Neo4jKG`: 真实实现，Neo4j数据库查询

---

### 3. RAG检索组件

#### 接口规范
```python
# core/rag/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List

@dataclass
class RAGResult:
    """RAG检索结果"""
    book_name: str         # 棋书名称
    content: str           # 检索内容
    relevance: float       # 相关性评分 (0-1)
    page: int             # 页码

class BaseRAG(ABC):
    """RAG检索抽象基类"""
    @abstractmethod
    def search(self, query: str, top_k: int = 3) -> Optional[List[RAGResult]]:
        """
        检索相关内容

        Args:
            query: 查询文本
            top_k: 返回数量

        Returns:
            RAGResult列表或None（检索失败）
        """
        pass
```

#### 实现类
- `MockRAG`: Mock实现，用于测试
- `FAISSRAG`: 真实实现，向量数据库检索

---

### 4. LLM组件

#### 接口规范
```python
# core/llm/base.py
from abc import ABC, abstractmethod
from typing import Optional, List, Dict

class BaseLLM(ABC):
    """LLM抽象基类"""
    @abstractmethod
    def chat(self, messages: List[Dict], **kwargs) -> str:
        """
        对话接口

        Args:
            messages: 消息列表
            **kwargs: 额外参数

        Returns:
            LLM响应文本
        """
        pass

    @abstractmethod
    def explain_position(self, fen: str, engine_result: dict, kg_result: dict) -> str:
        """
        讲解局面

        Args:
            fen: 当前局面FEN
            engine_result: 引擎分析结果
            kg_result: 知识图谱结果

        Returns:
            讲解文本
        """
        pass
```

#### 实现类
- `QwenLLM`: 阿里云Qwen系列实现

---

### 5. Agent编排组件

#### 状态定义
```python
# core/agent/state.py
from typing import TypedDict, Optional

class AgentState(TypedDict):
    """Agent状态"""
    # 输入
    fen: str                         # 当前局面FEN
    board: List[List[str]]           # 棋盘数组
    input_type: str                  # 输入类型 ("fen" | "image")

    # 中间结果
    engine_result: Optional[dict]     # 引擎结果
    kg_result: Optional[dict]         # 知识图谱结果
    rag_results: Optional[List[dict]]  # RAG检索结果
    vision_result: Optional[dict]     # 视觉识别结果

    # 输出
    explanation: str                # 最终讲解
    bestmove: str                  # 最佳着法
    citations: List[str]            # 引用列表
```

#### 节点设计
```python
# 预处理节点
def preprocess_node(state: AgentState) -> AgentState:
    """判断输入类型，初始化状态"""
    if state['input_type'] == 'image':
        # 调用视觉模型
        state['vision_result'] = vision_analyzer.analyze(state['fen'])
    return state

# 引擎分析节点
def engine_node(state: AgentState) -> AgentState:
    """调用引擎分析"""
    state['engine_result'] = engine.analyze(state['fen'])
    return state

# 知识检索节点
def knowledge_node(state: AgentState) -> AgentState:
    """查询知识图谱和RAG"""
    state['kg_result'] = kg.query(state['fen'])
    state['rag_results'] = rag.search(state['fen'])
    return state

# 讲解生成节点
def explain_node(state: AgentState) -> AgentState:
    """综合生成讲解"""
    prompt = build_explanation_prompt(
        state['engine_result'],
        state['kg_result'],
        state['rag_results']
    )
    state['explanation'] = llm.chat(prompt)
    return state
```

#### 图结构
```python
# core/agent/graph.py
from langgraph.graph import StateGraph, END

# 创建图
workflow = StateGraph(AgentState)

# 添加节点
workflow.add_node("preprocess", preprocess_node)
workflow.add_node("engine", engine_node)
workflow.add_node("knowledge", knowledge_node)
workflow.add_node("explain", explain_node)

# 定义边（节点间的流转）
workflow.set_entry_point("preprocess")
workflow.add_edge("preprocess", "engine")
workflow.add_edge("engine", "knowledge")
workflow.add_edge("knowledge", "explain")
workflow.add_edge("explain", END)

# 编译图
app = workflow.compile()
```

---

## 📂 项目结构（重构后）

```
xiangqi-hybrid-agent/
├── docs/                      # 文档（核心4个）
│   ├── STATE.md                # 当前状态 ⭐AI必读
│   ├── REQUIREMENTS.md          # 产品需求
│   ├── ARCHITECTURE.md         # 技术架构
│   └── ROADMAP.md              # 路线图
│
├── xiangqi/                    # 核心包（重命名core）
│   ├── __init__.py
│   ├── engine/                 # 引擎模块
│   │   ├── __init__.py
│   │   ├── base.py           # 抽象基类
│   │   ├── mock.py           # Mock实现
│   │   └── pikafish.py      # Pikafish实现
│   │
│   ├── kg/                     # 知识图谱模块
│   │   ├── __init__.py
│   │   ├── base.py           # 抽象基类
│   │   ├── mock.py           # Mock实现
│   │   └── neo4j.py         # Neo4j实现
│   │
│   ├── rag/                    # RAG检索模块
│   │   ├── __init__.py
│   │   ├── base.py           # 抽象基类
│   │   ├── mock.py           # Mock实现
│   │   └── faiss.py          # FAISS实现
│   │
│   ├── llm/                    # LLM模块
│   │   ├── __init__.py
│   │   ├── base.py           # 抽象基类
│   │   └── qwen.py           # Qwen实现
│   │
│   ├── vision/                 # 视觉模块
│   │   ├── __init__.py
│   │   └── analyzer.py       # Qwen-VL分析器
│   │
│   ├── agent/                  # Agent编排
│   │   ├── __init__.py
│   │   ├── state.py          # 状态定义
│   │   ├── graph.py          # LangGraph图
│   │   └── nodes/           # 节点实现
│   │       ├── __init__.py
│   │       ├── preprocess.py
│   │       ├── engine.py
│   │       ├── knowledge.py
│   │       └── explain.py
│   │
│   ├── game/                   # 游戏逻辑
│   │   ├── __init__.py
│   │   ├── board.py          # 棋盘逻辑
│   │   └── rules.py          # 象棋规则
│   │
│   ├── types/                  # 类型定义
│   │   ├── __init__.py
│   │   └── models.py         # 数据模型
│   │
│   └── utils/                  # 工具函数
│       ├── __init__.py
│       ├── fen.py            # FEN处理
│       └── validators.py     # 校验函数
│
├── web/                        # Web应用
│   ├── __init__.py
│   ├── app.py                 # 主应用入口（<200行）
│   ├── routes/                # 路由模块
│   │   ├── __init__.py
│   │   ├── play.py          # 人机对战
│   │   ├── pgn.py           # 下棋谱
│   │   └── review.py        # 复盘
│   ├── components/            # Gradio组件
│   │   ├── __init__.py
│   │   ├── board.py         # 棋盘组件
│   │   ├── analysis.py      # 分析面板
│   │   └── controls.py      # 控制按钮
│   └── state/                # 前端状态
│       ├── __init__.py
│       └── session.py       # 会话管理
│
├── tests/                      # 测试目录
│   ├── __init__.py
│   ├── conftest.py           # pytest配置
│   ├── unit/                 # 单元测试
│   │   ├── test_engine.py
│   │   ├── test_kg.py
│   │   └── test_llm.py
│   ├── integration/           # 集成测试
│   │   └── test_agent.py
│   └── e2e/                  # 端到端测试
│       └── test_web.py
│
├── scripts/                    # 工具脚本
│   ├── setup.py              # 环境设置
│   ├── import_data.py        # 数据导入
│   ├── export_data.py        # 数据导出
│   └── gates/                # 门禁脚本
│       ├── check.sh          # 综合检查
│       ├── check_tests.py    # 测试检查
│       ├── check_docs.py     # 文档检查
│       └── check_code.py    # 代码检查
│
├── config/                     # 配置文件
│   ├── __init__.py
│   ├── settings.py           # 统一配置管理
│   ├── engine.yaml           # 引擎配置
│   ├── database.yaml         # 数据库配置
│   └── llm.yaml             # LLM配置
│
├── data/                       # 数据目录
│   ├── engine/               # 引擎数据
│   │   └── pikafish-avx2.exe
│   ├── books/                # 棋书数据
│   ├── games/                # 对局数据
│   └── cache/                # 缓存数据
│
├── archive/                    # 归档目录
│   ├── old_docs/            # 旧文档
│   └── deprecated/          # 过时代码
│
├── README.md                  # 项目说明
├── requirements.txt           # Python依赖
├── pytest.ini               # pytest配置
├── .gitignore               # Git忽略配置
└── pyproject.toml           # 项目配置
```

---

## 🔌 配置管理

### 统一配置类
```python
# config/settings.py
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """统一配置管理"""

    # 应用配置
    app_name: str = "象棋AI混合代理"
    app_version: str = "0.4.0"
    debug: bool = False

    # 服务器配置
    host: str = "0.0.0.0"
    port: int = 7867

    # 引擎配置
    engine_path: str = "data/engine/pikafish-avx2.exe"
    engine_depth: int = 15
    engine_timeout: int = 30

    # 数据库配置
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"

    # LLM配置
    llm_api_key: str = ""
    llm_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    llm_model: str = "qwen-max"
    llm_timeout: int = 30

    # 视觉配置
    vision_api_key: str = ""
    vision_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    vision_model: str = "qwen-vl-max"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
```

---

## 🧪 测试策略

### 测试金字塔
```
        /\
       /  \
      / E2E \         10%
     /________\
    /          \
   / Integration \     30%
  /______________\
 /                \
/     Unit         \  60%
/__________________\
```

### 测试覆盖率要求
| 模块 | 目标覆盖率 | 关键测试点 |
|------|-----------|------------|
| xiangqi/engine | > 80% | UCI通信、结果解析、异常处理 |
| xiangqi/kg | > 70% | 连接、查询、结果转换 |
| xiangqi/rag | > 70% | 索引构建、检索、相关性 |
| xiangqi/llm | > 70% | API调用、Prompt构建、响应解析 |
| xiangqi/utils | > 90% | FEN校验、格式转换 |

---

## 🚀 部署架构

### 开发环境
```
┌─────────────────────────────────┐
│  本地开发环境                 │
│  - Python 3.12+             │
│  - Neo4j (本地)             │
│  - Pikafish引擎              │
│  - Gradio Web界面             │
└─────────────────────────────────┘
```

### 生产环境（参赛演示）
```
┌─────────────────────────────────┐
│  单机演示环境                │
│  - Python + Gradio           │
│  - 内置Neo4j + 数据集       │
│  - 内置Pikafish引擎         │
│  - 无需外网API调用          │
└─────────────────────────────────┘
```

---

**文档版本**: v1.0
**最后更新**: 2026-03-09
**维护者**: AI开发团队
