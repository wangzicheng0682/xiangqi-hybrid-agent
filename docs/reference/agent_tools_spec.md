# Agent工具规范

> 10个LLM可调用工具的完整接口定义

**版本**: v2.0
**最后更新**: 2026-03-14

---

## 重大更新 (v2.0)

**Function Calling 已集成！**

- LLM 现在通过 OpenAI Function Calling 格式调用工具
- Qwen 原生支持 Function Calling
- 实现: `core/llm/xiangqi_coach.py`

---

## 工具概览

| 类别 | 工具数 | 用途 |
|------|--------|------|
| 棋子关系 | 4 | 查询攻击/防守/威胁关系 |
| 走法分析 | 3 | 深度分析走法效果 |
| 引擎分析 | 2 | 引擎深度评估 |
| 战略分析 | 1 | 局面战略分析 |

---

## 调用约束

- **最大调用轮次**: 3轮
- **每轮并行上限**: 3个工具
- **总耗时上限**: 5秒
- **反馈机制**: 每个工具调用有thinking过程反馈

---

## 第一类：棋子关系工具

### get_piece_attacks

**用途**: 查询某棋子的攻击范围

**什么时候用**:
- 当你想知道某个棋子能攻击什么时
- 当你分析"这步棋威胁了什么"时
- 当你想解释"为什么要走这步"时

**参数**:
| 参数 | 类型 | 说明 | 示例 |
|------|------|------|------|
| fen | string | 当前局面FEN | `"rnbakabnr/9/..."` |
| piece | string | 棋子标识 | `"红车"` / `"r"` / `"(5,8)"` |

**返回**:
```json
{
  "success": true,
  "data": {
    "piece": "红车(5,8)",
    "attacks": ["黑马(7,8)", "空位(5,6)", "空位(5,7)"],
    "attack_count": 3,
    "attack_value": 450,
    "has_valuable_target": true
  },
  "message": "红车攻击3个位置",
  "thinking_hint": "分析红车的攻击范围，发现3个目标"
}
```

---

### get_piece_defenders

**用途**: 查询谁在保护某个棋子

**什么时候用**:
- 当你想知道某个棋子是否安全时
- 当你分析"吃这子会怎样"时
- 当你想解释"为什么不能吃这子"时

**参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| fen | string | 当前局面FEN |
| piece | string | 棋子标识 |

**返回**:
```json
{
  "success": true,
  "data": {
    "piece": "红车(5,8)",
    "defenders": ["红马(4,6)", "红炮(2,8)"],
    "defender_count": 2,
    "is_well_protected": true,
    "is_unprotected": false
  },
  "message": "红车被2个子保护",
  "thinking_hint": "分析红车的防守情况，发现2个保护者"
}
```

---

### get_threats_to_piece

**用途**: 查询谁在威胁某个棋子

**什么时候用**:
- 当你想知道某个棋子是否危险时
- 当你分析"需要保护这子吗"时
- 当你想解释"为什么要走防守棋"时

**参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| fen | string | 当前局面FEN |
| piece | string | 棋子标识 |

**返回**:
```json
{
  "success": true,
  "data": {
    "piece": "红车(5,8)",
    "threats": [
      {"attacker": "黑马(7,6)", "can_capture": true}
    ],
    "threat_count": 1,
    "danger_level": "medium",
    "is_safe": false
  },
  "message": "红车受到1个威胁，危险等级: medium",
  "thinking_hint": "分析红车面临的威胁，发现1个攻击者"
}
```

---

### get_piece_relations

**用途**: 综合查询某棋子的攻击、防守、威胁关系（一站式）

**什么时候用**:
- 当你需要全面了解某个棋子的处境时
- 当你想快速获取"这子怎么样"的完整信息时

**参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| fen | string | 当前局面FEN |
| piece | string | 棋子标识 |

**返回**:
```json
{
  "success": true,
  "data": {
    "piece": "红车(5,8)",
    "attacks": ["黑马(7,8)"],
    "attack_value": 450,
    "defended_by": ["红马(4,6)"],
    "defender_count": 1,
    "threatened_by": ["黑马(7,6)"],
    "threat_count": 1,
    "danger_level": "medium",
    "is_unprotected": false,
    "summary": "红车攻击黑马，但受到黑马威胁"
  },
  "message": "综合分析完成: 红车攻击黑马，但受到黑马威胁",
  "thinking_hint": "综合分析红车的关系网络"
}
```

---

## 第二类：走法分析工具

### analyze_move

**用途**: 深度分析某步棋的效果

**什么时候用**:
- 当你需要解释"这步棋为什么好/坏"时
- 当你需要评估走法质量时

**参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| fen | string | 走法前的局面FEN |
| move | string | UCI格式走法 | `"h2e2"` |

**返回**:
```json
{
  "success": true,
  "data": {
    "move": "h2e2",
    "move_chinese": "车二平五",
    "piece": "红车",
    "quality": "excellent",
    "quality_tags": ["move_is_capture", "move_gives_check"],
    "changes": {
      "material_delta": 450,
      "new_threats_created": ["威胁黑马"],
      "threats_avoided": [],
      "position_improvement": 0
    },
    "why": "吃子得450分，同时将军"
  },
  "message": "车二平五: excellent - 吃子得450分，同时将军",
  "thinking_hint": "分析走法 h2e2，评估为 excellent"
}
```

**quality取值**:
| 值 | 含义 |
|------|------|
| `excellent` | 极佳（将军+吃子/得子） |
| `good` | 好（防守/逃脱/改善位置） |
| `ok` | 正常 |
| `blunder` | 严重失误（丢子/被将死） |

---

### compare_moves

**用途**: 对比多步棋的优劣

**什么时候用**:
- 当你需要解释"为什么选A而不是B"时
- 当你需要展示多个候选时

**参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| fen | string | 当前局面FEN |
| moves | list | UCI走法列表 | `["h2e2", "h2h6"]` |

**返回**:
```json
{
  "success": true,
  "data": {
    "comparisons": [
      {
        "move": "h2e2",
        "move_chinese": "车二平五",
        "quality": "excellent",
        "score": 100,
        "pros": ["吃子得450分", "将军"],
        "cons": []
      },
      {
        "move": "h2h6",
        "move_chinese": "车二进六",
        "quality": "ok",
        "score": 50,
        "pros": ["控制要点"],
        "cons": ["无直接收益"]
      }
    ],
    "best": "h2e2",
    "reason": "吃子得450分"
  },
  "message": "对比2步棋，最佳: h2e2",
  "thinking_hint": "对比分析2步候选走法"
}
```

---

### get_forcing_sequence

**用途**: 分析走法后的强制序列

**什么时候用**:
- 当你需要分析"将军后会发生什么"时
- 当你需要展示强制变化时

**参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| fen | string | 走法前的局面FEN |
| move | string | UCI格式走法 |
| depth | int | 分析深度（可选，默认3） |

**返回**:
```json
{
  "success": true,
  "data": {
    "is_forcing": true,
    "sequence": [
      {"move": "h2e2", "type": "check", "must_respond": true},
      {"move": "将5平6", "type": "escape", "only_move": true},
      {"move": "e2e6", "type": "capture", "material_gain": 450}
    ],
    "depth_analyzed": 3,
    "outcome": "红方通过强制序列得马"
  },
  "message": "分析完成: 强制序列",
  "thinking_hint": "分析走法后的强制序列"
}
```

---

## 第三类：引擎分析工具

### engine_deep_analysis

**用途**: 引擎深度分析

**什么时候用**:
- 当你需要引擎的专业评估时
- 当你需要知道"最佳走法是什么"时

**参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| fen | string | 当前局面FEN |
| depth | int | 分析深度（默认20） |

**返回**:
```json
{
  "success": true,
  "data": {
    "eval_cp": 150,
    "eval_human": "红方略优",
    "best_move": "h2e2",
    "best_line": ["h2e2", "g9e7", "e2e6"],
    "critical_position": true,
    "depth": 20
  },
  "message": "引擎分析: 红方略优 (150分)",
  "thinking_hint": "引擎深度分析(depth=20)"
}
```

**eval_human取值**:
| 范围 | 描述 |
|------|------|
| > 500 | 红方胜势 |
| 200-500 | 红方明显优势 |
| 50-200 | 红方略优 |
| -50-50 | 均势 |
| -200--50 | 黑方略优 |
| -500--200 | 黑方明显优势 |
| < -500 | 黑方胜势 |

---

### engine_alternatives

**用途**: 获取引擎的多个候选走法对比

**什么时候用**:
- 当你需要展示"还有哪些选择"时
- 当你需要解释"这步比其他好多少"时

**参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| fen | string | 当前局面FEN |
| top_n | int | 返回候选数（默认3） |

**返回**:
```json
{
  "success": true,
  "data": {
    "moves": [
      {
        "move": "h2e2",
        "move_chinese": "车二平五",
        "eval_cp": 150,
        "explanation": "控制中路，威胁黑马",
        "risk": "low"
      },
      {
        "move": "h2h6",
        "move_chinese": "车二进六",
        "eval_cp": 80,
        "explanation": "进攻黑方底线",
        "risk": "medium"
      }
    ],
    "top_n": 3,
    "recommendation": "h2e2是最佳选择"
  },
  "message": "获取2个候选走法",
  "thinking_hint": "获取引擎top3候选走法"
}
```

---

## 第四类：战略分析工具

### analyze_position_strategy

**用途**: 局面战略分析

**什么时候用**:
- 当你需要解释"局面整体怎么样"时
- 当你需要给出"应该怎么下"的建议时

**参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| fen | string | 当前局面FEN |

**返回**:
```json
{
  "success": true,
  "data": {
    "phase": "中局",
    "initiative": "红方",
    "king_safety": {"red": "安全", "black": "有隐患"},
    "key_features": [
      "红方控制中路",
      "黑马位置活跃",
      "黑方底线有漏洞"
    ],
    "suggested_plans": [
      "红方应利用中路优势发起进攻",
      "黑方应先巩固防守"
    ],
    "detected_tags": ["controls_open_file", "has_active_pieces"]
  },
  "message": "战略分析: 中局，红方握有主动权",
  "thinking_hint": "综合分析局面战略特征"
}
```

**phase取值**:
| 值 | 棋子总数 |
|------|----------|
| `开局` | ≥28 |
| `中局` | 15-27 |
| `残局` | ≤14 |

---

## 工具注册表（供LLM调用）

```python
AGENT_TOOLS = {
    "get_piece_attacks": {
        "function": AgentTools.get_piece_attacks,
        "description": "查询某棋子的攻击范围。当你需要分析某子的攻击能力时使用。",
        "parameters": ["fen", "piece"]
    },
    "get_piece_defenders": {
        "function": AgentTools.get_piece_defenders,
        "description": "查询谁在保护某个棋子。当你需要分析某子是否安全时使用。",
        "parameters": ["fen", "piece"]
    },
    "get_threats_to_piece": {
        "function": AgentTools.get_threats_to_piece,
        "description": "查询谁在威胁某个棋子。当你需要分析某子面临的危险时使用。",
        "parameters": ["fen", "piece"]
    },
    "get_piece_relations": {
        "function": AgentTools.get_piece_relations,
        "description": "综合查询某棋子的攻击、防守、威胁信息。一站式获取完整关系。",
        "parameters": ["fen", "piece"]
    },
    "analyze_move": {
        "function": AgentTools.analyze_move,
        "description": "深度分析某步棋的效果。当你需要解释某步棋为什么好或坏时使用。",
        "parameters": ["fen", "move"]
    },
    "compare_moves": {
        "function": AgentTools.compare_moves,
        "description": "对比多步棋的优劣。当你需要分析为什么选A而不是B时使用。",
        "parameters": ["fen", "moves"]
    },
    "get_forcing_sequence": {
        "function": AgentTools.get_forcing_sequence,
        "description": "分析走法后的强制序列。当你需要分析将军或强制应着时使用。",
        "parameters": ["fen", "move"]
    },
    "engine_deep_analysis": {
        "function": AgentTools.engine_deep_analysis,
        "description": "引擎深度分析。获取引擎评估和最佳走法。",
        "parameters": ["fen", "depth"]
    },
    "engine_alternatives": {
        "function": AgentTools.engine_alternatives,
        "description": "获取引擎的多个候选走法对比。",
        "parameters": ["fen", "top_n"]
    },
    "analyze_position_strategy": {
        "function": AgentTools.analyze_position_strategy,
        "description": "局面战略分析。获取阶段、主动权、关键特征等信息。",
        "parameters": ["fen"]
    }
}
```

---

## 使用示例

### Python调用（直接调用工具）

```python
from core.llm.agent_tools import AgentTools

tools = AgentTools()

# 查询棋子攻击范围
result = tools.get_piece_attacks(fen, "红车")
if result.success:
    print(f"攻击价值: {result.data['attack_value']}")

# 分析走法
result = tools.analyze_move(fen, "h2e2")
if result.success:
    print(f"走法质量: {result.data['quality']}")
    print(f"原因: {result.data['why']}")
```

### Function Calling Agent（推荐）

```python
from core.llm.xiangqi_coach import create_coach_agent

coach = create_coach_agent()

# LLM自主决定调用哪些工具
result = coach.analyze(
    fen="rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1",
    question="红车这步走得怎么样？",
    move="h2e2",
    on_thinking=lambda stage, msg: print(f"{stage}: {msg}")
)
print(result)
```

### LLM调用流程（Function Calling）

```
用户: "红车这步走得怎么样？"

🧠 第1轮思考...
🔧 调用工具: analyze_move
📊 analyze_move: {"quality": "excellent", "why": "吃子得450分，同时将军"}

🧠 第2轮思考...
【局面概述】...
【关键分析】...
【教练建议】...
```

### 前端调用（SSE流式）

```typescript
// frontend/src/services/api.ts
await api.analyzeDeep(
  {
    fen: previousFen || fen,
    move: lastMoveUci,
    question: '分析刚才走的棋',
    show_thinking: true
  },
  (msg) => {
    // 处理思考过程消息
    // msg.type: 'thinking' | 'tool_call' | 'tool_result'
  },
  (result) => {
    // 处理最终结果
    console.log(result.explanation);
  },
  (error) => {
    // 处理错误
  }
);
```
