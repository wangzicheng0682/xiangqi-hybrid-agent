# 作品简介

## 一、项目概述

### 1.1 项目名称
**象棋AI混合代理教学与对弈系统**（Xiangqi Hybrid Agent Teaching & Game System）

### 1.2 一句话定义
让AI像教练一样**读懂棋局**、**讲解棋局**，而不是念坐标。

### 1.3 项目定位
基于神经符号AI架构的象棋教练系统，通过Evidence Map约束大模型输出，实现零幻觉的棋局分析。

---

## 二、项目背景与意义

### 2.1 象棋教学现状痛点

| 痛点 | 描述 | 现有解决方案 |
|------|------|-------------|
| **学习门槛高** | 象棋入门需要理解开局原则、中局战术、残局技术 | 视频教程、棋谱书籍 |
| **反馈不及时** | 学习者走棋后无法立即获得专业点评 | 搜索引擎、请教老师 |
| **分析工具专业性不足** | 现有引擎只给评分，不解释原因 | Stockfish、象棋巫师 |
| **LLM幻觉严重** | 通用AI分析象棋时经常编造棋子位置 | 无有效解决方案 |

### 2.2 项目意义

通过**规则引擎+LLM混合架构**，实现：
- 专业级棋局分析（教练式讲解）
- 零幻觉的事实保证（Evidence Map约束）
- 实时思考过程展示（多专家并行+SSE流式输出）
- 可解释的AI决策（工具调用+证据链）

---

## 三、核心功能

### 3.1 深度分析模式
三专家并行分析（战术/战略/引擎），SSE流式返回实时思考过程，像特级大师一样讲解。

### 3.2 快速分析模式
响应时间<1秒，返回45个战术标签检测结果、引擎评估分数、张力类型分析。

### 3.3 人机对弈
支持三级难度（简单/中等/困难），即时反馈走棋效果。

### 3.4 棋盘视觉识别
拍照上传棋盘图片，YOLO本地识别，自动生成FEN进入分析。

### 3.5 棋谱管理
支持PGN棋谱导入、历史对局检索、局面相似度匹配。

### 3.6 RAG知识检索
基于ChromaDB向量数据库，语义检索80+棋理原则和14万局棋谱开局。

---

## 四、技术架构

### 4.1 核心架构

```
┌────────────────────────────────────────────────────┐
│              前端：React + Liquid Glass            │
│        棋盘/分析面板/专家扑克牌动画/SSE流式        │
└────────────────────────┬─────────────────────────┘
                         │ REST API / SSE
┌────────────────────────▼─────────────────────────┐
│              后端：FastAPI                         │
│    端点路由/请求验证/SSE流式管理                   │
└────────────────────────┬─────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────┐
│           事实层（规则引擎 - 100%准确）            │
│    标签检测器/张力检测器/规则引擎/Pikafish引擎     │
└────────────────────────┬─────────────────────────┘
                         │ Evidence Map
┌────────────────────────▼─────────────────────────┐
│            表达层（LLM - 教练式讲解）               │
│     System Prompt/12个Agent工具/多专家协调器       │
└────────────────────────────────────────────────────┘
```

### 4.2 技术栈

| 层级 | 技术 | 用途 |
|------|------|------|
| 前端框架 | React 18 + TypeScript | UI框架 |
| 动画 | Framer Motion | 复杂动画 |
| 状态管理 | Zustand | 轻量状态 |
| 3D渲染 | WebGL原生 | Liquid Glass |
| 后端框架 | FastAPI | Web框架 |
| 象棋引擎 | Pikafish | 深度计算 |
| 图数据库 | Neo4j | 棋谱存储 |
| 向量数据库 | ChromaDB | RAG检索 |
| LLM | GLM-5/Qwen-Max | 讲解生成 |

---

## 五、技术指标

### 5.1 标签检测体系
- 标签总数：45个
- 检测方法：100%规则硬判定，准确率100%
- 九大层级：将杀/捉子/闪击/牵制/杀法/子力/走法/战略/引擎

### 5.2 张力检测
- 张力类型：6种，自动识别局面矛盾
- 触发条件：可配置（默认cp>300）

### 5.3 Agent系统
- 专家数量：3个（战术/战略/引擎）
- 工具数量：13个，Function Calling自主决策
- 并行模式：自适应（根据张力数量选择）

### 5.4 性能指标
| 指标 | 数值 |
|------|------|
| 快速分析 | <1秒 |
| 深度分析 | 3-5秒 |
| 标签检测 | <0.5秒 |
| 测试覆盖 | 300+项 |

---

## 六、创新点

### 6.1 零幻觉架构（核心创新）
规则引擎负责"事实提取"（100%准确），Evidence Map作为"事实锚点"传递给LLM，LLM只负责"教练式表达"。

### 6.2 真Agent模式
LLM主动调用12个专业工具分析，像教练一样思考，最多3轮调用循环。

### 6.3 三专家并行架构
战术、战略、引擎三个Agent并行分析，合成器证据裁决，综合三方结论。

### 6.4 开局快答调度
识别开局定式时跳过重型多专家链路，直接用开局书+原则库生成快答。

### 6.5 RAG知识检索
ChromaDB向量检索，80+棋理原则自动索引，支持语义检索和按阶段/类型过滤。

### 6.6 Liquid Glass设计
Apple iOS 26液态玻璃效果，WebGL四步渲染管线（折射+色散+菲涅尔）。

---

## 七、应用场景

| 场景 | 价值 |
|------|------|
| 象棋学习者 | 教练式讲解，因果分析 |
| 棋谱研究者 | 19万局历史对局，相似局面检索 |
| 比赛选手 | 实时流式展示AI思考过程 |
| 内容创作者 | 自动生成教练级讲解 |
| 人机对弈练习 | 三级难度适应不同水平 |

---

## 八、关键数据结构（实现细节）

### 8.1 Claim 结构化断言

专家每个结论都是一个 Claim，包含来源分类和置信度：

```python
# core/llm/claim.py:33-49
@dataclass
class EvidenceItem:
    """单条证据：一次工具调用的输入→输出"""
    tool_name: str
    arguments: dict
    result_summary: str
    success: bool = True

@dataclass
class Claim:
    """一个结构化断言"""
    statement: str
    source: str = ClaimSource.UNVERIFIED   # tool_verified / reasoning / unverified
    confidence: str = ClaimConfidence.LOW  # high / medium / low
    evidence: List[EvidenceItem] = field(default_factory=list)
```

来源分类规则：
- **tool_verified**：证据文本中包含 `get_piece_attacks`、`engine_deep_analysis` 等工具名
- **reasoning**：有逻辑推理但无工具验证
- **unverified**：未验证的判断

### 8.2 AnalysisPolicyDecision 自适应调度

```python
# core/llm/analysis_policy.py:14-62
def choose_analysis_policy(question, tensions, phase_name,
                          engine_eval=None, move_count=0,
                          force_full_team=False) -> AnalysisPolicyDecision:
    tension_count = len(tensions or [])
    if force_full_team:
        selected = ["tactics", "strategy", "engine"]
    elif any(kw in question for kw in ENGINE_KEYWORDS):
        selected = ["engine", "strategy"]
    elif any(kw in question for kw in TACTICAL_KEYWORDS):
        selected = ["tactics", "engine"]
    elif phase_name == "开局" and move_count <= 4 and not tension_count:
        selected = ["strategy"]                          # 开局快答：单专家
    elif tension_count >= 3 or any(kw in question for kw in STRATEGIC_KEYWORDS):
        selected = ["tactics", "strategy", "engine"]   # 复杂局面：全专家
    else:
        selected = ["tactics", "strategy"]              # 默认：双专家
    parallelism = min(len(selected), env_parallel)
```

### 8.3 Evidence Map 证据锚点

Evidence Map 是从45个标签检测结果提取的结构化事实，作为 LLM 输出的约束边界：

```python
# core/rules/tactical_detector.py (2600+行)
# 检测结果 → Evidence Map 格式
evidence_map = {
    "facts_rules": [
        {"type": "attack", "from": "红车-(0,4)", "to": "黑将-(4,0)", "tag": "is_attack"},
        {"type": "protected", "piece": "红炮-(2,4)", "protected_by": "红马-(2,2)", "tag": "piece_is_protected"},
        {"type": "pinned", "piece": "黑马-(7,2)", "pinned_by": "红车-(0,2)", "tag": "is_pinned"},
        ...
    ],
    "phase": "中局",
    "tensions": [...],
    "move_quality": {...}
}
```

### 8.4 引擎连接池单例

```python
# core/engine/pool.py:12-44
class EnginePool:
    """Pikafish引擎单例池（线程安全）"""
    _instance: Optional["EnginePool"] = None
    _lock = threading.Lock()

    def analyze(self, fen: str, depth: int = 20):
        """线程安全的分析接口，自动串行化并发请求"""
        with self._analyze_lock:
            for attempt in range(2):
                engine = self.get_engine()
                try:
                    return engine.analyze(fen, depth=depth)
                except RuntimeError as exc:
                    if "Engine process not running" not in str(exc) or attempt == 1:
                        raise
                    self.release()   # 自动重启崩溃的引擎
```

### 8.5 SSE流式事件类型

后端通过 `queue.Queue` + `threading.Thread` + `StreamingResponse` 实现实时推送，共支持14种事件类型：

```python
# api/main.py:1650-1722（关键分发逻辑）
if event["type"] == "expert_step_start":
    yield f"data: {json.dumps({'type': event['type'], **step_data})}\n\n"
elif event["type"] == "synthesis_chunk":
    # 流式合成文本 chunk
    yield f"data: {json.dumps({'type': 'synthesis_chunk', 'message': msg})}\n\n"
elif event["type"] == "dispatch_info":
    yield f"data: {json.dumps({'type': 'dispatch_info', **dispatch_data})}\n\n"
```

前端事件总线将 SSE 事件映射到对应 store 操作：
```typescript
// frontend/src/App.tsx:170-180
} else if (msg.type === `expert_${expertType}_thinking`) {
    store.updateExpert(expertType, { status: 'thinking' });
    store.appendExpertThinking(expertType, msg.message || '');
} else if (msg.type === `expert_${expertType}_tool`) {
    store.addExpertToolCall(expertType, {
        toolName: toChineseToolLabel(msg.message || 'tool'),
        params: '', result: '',
    });
```

---

## 九、系统能力评估

| 能力维度 | 评分 | 说明 |
|----------|------|------|
| 棋力深度 | 6/10 | Pikafish引擎，可配置深度 |
| 知识面广度 | 6/10 | RAG知识库支撑 |
| 教学能力 | 7/10 | 教练式讲解，零幻觉 |
| 对弈能力 | 6/10 | 三级难度对弈 |
| 对局复盘 | 5/10 | 深度分析+证据裁决 |
| 前端体验 | 8/10 | Liquid Glass，SSE流式 |

---

## 十、项目信息

| 项目属性 | 内容 |
|---------|------|
| 项目名称 | 象棋AI混合代理教学与对弈系统 |
| 技术方向 | 人工智能 / 软件应用与开发 |
| 开发语言 | Python + TypeScript |
| 当前版本 | v3.72 |
| 测试覆盖 | 300+项全部通过 |
