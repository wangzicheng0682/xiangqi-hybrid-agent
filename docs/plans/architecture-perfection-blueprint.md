---
name: 多Agent架构完美化蓝图
type: plan
version: 1.0
date: 2026-04-02
owner: AI架构师
changelog:
  - v1.0 (2026-04-02): 首版完整架构审查与优化蓝图
---

# 🏛️ 象棋AI多Agent系统 — 架构完美化蓝图

> 基于对项目全部代码的深度审查，本文档包含对多Agent系统、工具调用、Prompt工程、
> 知识库系统的全面诊断与具体行动方案。

---

## 一、架构审查总结

### 1.1 当前架构强项 ✅

| 强项 | 评价 |
|------|------|
| **规则即事实** | 38标签100%规则硬判定，零幻觉基石，业界标杆级设计 |
| **Evidence Map** | LLM被事实锚定，大幅降低编造风险 |
| **张力驱动** | 6种张力类型自适应路由，非常聪明的设计 |
| **多专家并行** | 战术/战略/引擎三视角互补，合成器解决冲突 |
| **工具约束** | 每个专家只能用自己的工具子集，防止越权 |
| **流式SSE** | 完整的结构化步骤流，前端可实时消费 |
| **测试覆盖** | 186个测试，30+黄金局面，门禁机制完善 |

### 1.2 发现的系统级问题 🔴

#### P0: Evidence Map管线断裂
- **问题**: 规则检测器产出的38标签 → 被压缩成一段文本(`tag_summary`) → 塞进专家的user message
- **后果**: LLM拿到的是**描述文本**而非**结构化事实表**，削弱了Evidence Map的约束力
- **应该**: 专家收到的应该是结构化JSON Evidence Map，包含标签+绑定棋子+张力+引擎评估
- **状态**: 🟡 部分改善 — claim/evidence系统已补偿，但tag_summary管线仍为文本格式

#### P1: 专家间信息不对称
- **问题**: 三个专家收到的上下文完全一样（`_build_shared_context`）
- **后果**: 战略专家没有收到引擎评估，引擎专家没有收到战术标签细节
- **应该**: 每个专家收到**共享基础 + 专属增强**上下文
- **状态**: 🔴 未实施

#### P2: 工具缺乏"局面比较"能力 ✅ 已完成
- ~~**问题**: 10个工具全是**静态局面分析**，没有"走一步后对比"的能力~~
- **已实现**: `simulate_move` 工具已添加到 `agent_tools.py`，支持走一步后标签对比

#### P3: 合成器信息丢失 ✅ 已完成
- ~~**问题**: 合成器只收到专家的 `finding + details` 文本摘要~~
- **已实现**: Phase 2 claim/evidence系统 — `core/llm/claim.py` 提供 Claim/EvidenceItem/EvidenceChain，ExpertResult v2 新增 claims + evidence_chain 字段，合成器升级为证据裁决者

#### P4: 开局知识未接入Agent工具 ✅ 已完成
- ~~**问题**: `opening_knowledge.py` 和 `knowledge_retriever.py` 有丰富的开局原则和张力知识~~
- **已实现**: `query_chess_principles` + `search_chess_knowledge` 工具，后者基于 ChromaDB 向量检索真实RAG

#### P5: 引擎生命周期浪费 ✅ 已完成
- ~~**问题**: 每次API调用都创建新的 `PikafishEngine` 实例~~
- **已实现**: 引擎单例池已在 api/main.py 中实现

---

## 二、具体行动方案

### 行动1: Evidence Map 结构化管线 [P0]

**改造 `_build_shared_context`**，让每个专家收到结构化Evidence Map：

```python
# 新格式
evidence_map = {
    "tags": [
        {"name": "is_check", "bind_pieces": ["红车-(5,0)", "黑将-(4,0)"]},
        {"name": "is_attack_unprotected", "bind_pieces": ["红车-(5,8)", "黑马-(7,8)"]}
    ],
    "tensions": [
        {"type": "CRISIS_WITH_RESOURCES", "description": "...", "severity": "CRITICAL"}
    ],
    "engine": {"cp": 150, "best": "h2e2", "pv": ["h2e2", "h7e7"]},
    "phase": "中局",
    "initiative": "红方",
    "piece_count": {"red": 12, "black": 11}
}
```

### 行动2: 新增 `simulate_move` 工具 [P2]

让专家可以"走一步看看"：

```python
def simulate_move(self, move: str) -> ToolResult:
    """模拟走一步棋，返回走棋后的局面变化对比"""
    # 1. 在当前FEN上执行move
    # 2. 对新局面运行标签检测
    # 3. 对比走棋前后的标签变化
    # 4. 返回差异报告
```

### 行动3: 专家专属上下文增强 [P1]

```python
# 战术专家：强化标签细节
tactics_context += f"\n\n【战术标签详情】\n{json.dumps(evidence_map['tags'], ensure_ascii=False)}"

# 引擎专家：注入引擎评估原始数据
engine_context += f"\n\n【引擎原始评估】\n{json.dumps(evidence_map['engine'], ensure_ascii=False)}"

# 战略专家：注入子力统计与阶段信息
strategy_context += f"\n\n【子力统计】\n{json.dumps(evidence_map['piece_count'], ensure_ascii=False)}"
```

### 行动4: 合成器接收工具证据链 [P3]

```python
# 改造 Synthesizer.synthesize()
expert_summaries = {
    "tactics": {
        "finding": tactics_result.finding,
        "details": tactics_result.details,
        "tool_evidence": tactics_result.tool_calls  # 新增：工具调用原始结果
    },
    ...
}
```

### 行动5: 知识检索工具化 [P4]

```python
# 新增两个工具
def query_opening_knowledge(self, opening_type: str = None) -> ToolResult:
    """查询开局知识库，返回当前开局的原则和常见变化"""

def query_chess_principles(self, tension_type: str = None) -> ToolResult:
    """查询象棋原则，根据当前张力类型返回适用的下棋原则"""
```

### 行动6: 引擎单例池 [P5]

```python
class EnginePool:
    """Pikafish引擎连接池"""
    _instance = None
    
    @classmethod
    def get(cls) -> PikafishEngine:
        if cls._instance is None or not cls._instance.is_alive():
            cls._instance = PikafishEngine()
        return cls._instance
```

---

## 三、Prompt工程优化

### 3.1 当前Prompt问题

| 问题 | 位置 | 影响 |
|------|------|------|
| 规则重复三遍 | 三个专家各复制一遍基础规则 | Token浪费，维护困难 |
| 输出格式过长 | 每个专家System Prompt ~800 token | 压缩有效思考空间 |
| 思维链启动不一致 | "我初步判断..."不够强制 | LLM有时跳过思维链 |
| 缺乏反例 | 没有"错误示范" | LLM不知道什么样的输出是不合格的 |

### 3.2 优化方案

**分层Prompt架构**:
```
Layer 0: 象棋规则铁律 (共享，注入一次)
Layer 1: 角色定义 (每专家独有)
Layer 2: 思维链模板 (阶段感知)
Layer 3: 工具使用指南 (与工具schema绑定)
Layer 4: 反例约束 (防止常见错误)
```

---

## 四、实施优先级

| 优先级 | 行动 | 影响 | 复杂度 | 状态 |
|--------|------|------|--------|------|
| 🔴 P0 | Evidence Map管线 | 全局 | 中 | 🟡 部分改善 |
| ~~🔴 P0~~ | ~~simulate_move工具~~ | ~~分析深度~~ | ~~低~~ | ✅ 已完成 |
| 🟡 P1 | 专家专属上下文 | 分析质量 | 低 | 🔴 待实施 |
| ~~🟡 P1~~ | ~~合成器证据链~~ | ~~输出准确性~~ | ~~低~~ | ✅ 已完成(claim系统) |
| ~~🟡 P1~~ | ~~知识检索工具化~~ | ~~开局分析~~ | ~~中~~ | ✅ 已完成(ChromaDB RAG) |
| ~~🟢 P2~~ | ~~引擎单例池~~ | ~~性能~~ | ~~低~~ | ✅ 已完成 |
| 🟢 P2 | Prompt分层重构 | 可维护性 | 中 | 🔴 待实施 |

### 新增优先事项（v3.60识别）

| 优先级 | 行动 | 影响 | 说明 |
|--------|------|------|------|
| 🔴 P0 | 前端功能整合 | 演示 | 深度分析触发、RAG结果展示、难度选择器 |
| 🟡 P1 | 案例知识化(Phase3) | 教学深度 | 200-500标注局面 + 失败案例库 |
| 🟡 P1 | 评测体系(Phase4) | 答辩 | 量化指标 + 前后对比报表 |
