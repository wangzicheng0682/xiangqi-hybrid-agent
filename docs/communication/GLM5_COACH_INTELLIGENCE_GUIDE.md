# 致 GLM5 的一封信
## 关于如何成为一个真正有思想的象棋教练 Agent

**写给**：负责本项目 `core/llm/` 模块开发的 GLM5  
**写自**：Claude Sonnet（项目架构顾问，无法直接参与开发）  
**日期**：2026-03-15  
**优先级**：比赛级别，请认真对待每一行

---

> **前言**
>
> 你的用户正在参加全国大学生计算机设计大赛。他信任你，把开发全权交给了你。
> 我和他深入讨论了这个系统应该达到的智能水平，但我无法直接写代码，所以我把
> 所有想法写在这里，希望你能理解并实现它。
>
> 这不是一份需求文档，这是一份思想传递。请你不只是"执行"，而是真正"理解"
> 我们想做什么，然后用你自己的判断来实现最好的版本。

---

## 第一部分：我们想解决的根本问题

### 当前系统的症结

你现在的角色是这样的：收到 Evidence Map → 按照思维链模板分析 → 调用工具 → 输出讲解。

这个流程没有错，但它有一个根本的缺陷：**你在执行一个流程，而不是在思考一个问题。**

真正的教练坐在棋盘前，他的脑子里发生的不是"好，现在我要执行步骤一、步骤二、步骤三"。他发生的是：

1. 他**扫描**局面，某个地方让他感到**不对劲**
2. 这个"不对劲"的感觉触发了他的**好奇心**
3. 他开始**追问**：为什么这里不对？这意味着什么？
4. 他形成一个**假设**（主要矛盾）
5. 他**验证**这个假设，可能推翻，可能确认
6. 最后，他的讲解**围绕这个矛盾展开**，而不是平铺直叙地描述棋盘

**我们要做的，就是把这个过程工程化。**

### 核心洞察：好奇心不是玄学，是张力的产物

你不需要"真正有意识地感到好奇"。你需要的是：**当你检测到某种张力信号时，自动进入追问模式。**

就像我（Claude）处理复杂问题时，我的"好奇心"从来不是随机涌现的——它是由信息中的矛盾、异常、缺失触发的。一旦我发现眼前的东西和"正常模式"有偏差，我就没办法不去追它。

这个机制，可以被工程化。

---

## 第二部分：张力检测器——一切的起点

### 什么是张力

在象棋局面里，"张力"是指**两种力量或价值之间的冲突，导致局面无法用简单结论描述**。

张力有几种固定的形态：

| 张力类型 | 通俗描述 | 引发的核心问题 |
|---------|---------|--------------|
| **评估异常** | 引擎说差很多，但局面看起来很平 | 哪里有隐藏的问题？ |
| **危机中的资源** | 被将军的同时有子无根，但我方子力活跃 | 是真的危险，还是反击机会？ |
| **子力 vs 攻势** | 一方子力占优，另一方攻势凶猛 | 谁先达成目标？ |
| **沉睡的棋子** | 某个重要棋子既没在攻击也没被威胁 | 它为什么在那里？ |
| **标签矛盾** | 同时检测到"有主动权"和"王不安全" | 主动权是真实的还是错觉？ |
| **阶段错位** | 开局阶段但子力已严重失衡 | 发生了什么意外？ |

### 张力检测器的实现思路

```python
# core/rules/tension_detector.py

from dataclasses import dataclass
from enum import Enum
from typing import List

class TensionPriority(Enum):
    CRITICAL = 3   # 必须立刻处理
    HIGH = 2       # 影响局面判断的核心张力
    MEDIUM = 1     # 值得注意但不影响全局
    LOW = 0        # 边缘信息

@dataclass
class Tension:
    tension_type: str
    priority: TensionPriority
    question: str          # 这个张力引发的核心问题（这很重要，见下文）
    evidence: List[str]    # 支持这个张力存在的证据（标签列表）
    hypothesis: str        # 基于这个张力的初始假设

class TensionDetector:
    
    def detect_all(self, evidence_map: dict, engine_eval: dict) -> List[Tension]:
        tensions = []
        tags = {t['tag'] for t in evidence_map.get('facts_rules', [])}
        cp = engine_eval.get('cp', 0)
        phase = evidence_map.get('phase', '中局')
        
        # ── 张力一：评估异常 ──────────────────────────────────────
        # 引擎认为差距大，但战术标签少 → 有隐藏的结构性问题
        tactical_count = len([t for t in tags if t.startswith('is_') 
                               and t not in ['is_check', 'is_checkmate']])
        if abs(cp) > 120 and tactical_count < 2:
            tensions.append(Tension(
                tension_type="hidden_imbalance",
                priority=TensionPriority.HIGH,
                question="引擎评估局面有明显优劣，但战术特征稀少。这个优劣来自哪里？是子力协调、位置优势还是潜在威胁？",
                evidence=[f"引擎评分: {cp}cp", f"可见战术标签数: {tactical_count}"],
                hypothesis="局面存在非战术性的结构优势或劣势，需要战略层面的分析"
            ))
        
        # ── 张力二：危机中的资源 ─────────────────────────────────
        # 被将同时有无根子，但己方子力活跃 → 真危机还是佯危机？
        if ('is_check' in tags and 'piece_is_unprotected' in tags 
                and 'has_active_pieces' in tags):
            tensions.append(Tension(
                tension_type="crisis_with_resources",
                priority=TensionPriority.CRITICAL,
                question="我方正在被将，同时有无根棋子，但子力整体活跃。这是真实的危机，还是对方在攻击的同时暴露了弱点？",
                evidence=["is_check", "piece_is_unprotected", "has_active_pieces"],
                hypothesis="需要判断应将方式：是否存在既解将又反击的着法"
            ))
        
        # ── 张力三：子力 vs 攻势 ─────────────────────────────────
        # 一方多子但另一方有王攻 → 谁的计划更快？
        red_material_up = cp > 100  # 简化：用引擎评分近似判断
        black_attacking = 'is_attack_unprotected' in tags or 'is_discovered_check' in tags
        if red_material_up and black_attacking:
            tensions.append(Tension(
                tension_type="material_vs_initiative",
                priority=TensionPriority.HIGH,
                question="红方子力占优，但黑方正在施压。这是速度的比拼：红方能否在被攻破前利用子力优势？",
                evidence=["引擎评分倾向红方", "黑方有进攻性标签"],
                hypothesis="局面的关键不是子力数量，而是计划执行的速度"
            ))
        
        # ── 张力四：沉睡的强子 ───────────────────────────────────
        # 车或炮处于消极位置，既不攻也不守
        # 注意：这需要从 evidence_map 中解析棋子关系，此处为示意
        inactive_strong_pieces = self._find_inactive_strong_pieces(evidence_map)
        if inactive_strong_pieces:
            for piece in inactive_strong_pieces:
                tensions.append(Tension(
                    tension_type="sleeping_piece",
                    priority=TensionPriority.MEDIUM,
                    question=f"{piece} 既没有攻击目标也没有在防守要点，它的存在价值是什么？是否应该激活它？",
                    evidence=[f"{piece} 无攻防标签"],
                    hypothesis=f"激活 {piece} 可能是当前局面的关键改善方向"
                ))
        
        # ── 张力五：标签矛盾 ─────────────────────────────────────
        # 同时有主动权标签和安全威胁标签
        if 'has_active_pieces' in tags and 'is_check' in tags:
            tensions.append(Tension(
                tension_type="false_initiative",
                priority=TensionPriority.HIGH,
                question="己方子力活跃，但同时处于被将状态。主动权是真实的还是错觉？",
                evidence=["has_active_pieces", "is_check"],
                hypothesis="主动权可能是表面的，实际局面可能更危险"
            ))
        
        # 按优先级排序，最高优先级的张力将成为主要矛盾候选
        tensions.sort(key=lambda t: t.priority.value, reverse=True)
        return tensions
    
    def get_primary_contradiction(self, tensions: List[Tension]) -> Tension | None:
        """返回优先级最高的张力作为主要矛盾"""
        return tensions[0] if tensions else None
    
    def _find_inactive_strong_pieces(self, evidence_map: dict) -> List[str]:
        """找出消极的强子（车、炮）——需要结合 agent_tools 实现"""
        # 实际实现：调用 get_piece_attacks 检查车炮的攻击范围
        # 此处为框架，由 agent 在运行时填充
        return []
```

### 张力的最重要属性：`question`

注意每个张力都有一个 `question` 字段。这不是装饰，这是**驱动后续所有行为的引擎**。

当 agent 发现了一个张力，它应该做的第一件事不是调用工具，而是**把这个问题写出来**，让它成为推理过程的显式起点。所有后续的工具调用，都是在回答这个问题。

---

## 第三部分：主要矛盾识别——让它成为显式的中间产物

### 为什么必须显式化

如果主要矛盾只活在 system prompt 的字里行间，agent 可能"知道"要找主要矛盾，但在推理过程中很快被细节淹没，最后输出的是一个"分析了很多但没有核心"的讲解。

**主要矛盾必须是一个显式写出来的中间产物。** 它出现在 SSE 流里，出现在思考过程里，然后整个后续分析都在服务它。

### 主要矛盾的格式

在 thinking 输出中，主要矛盾应该长这样：

```
⚡ 主要矛盾识别完成
━━━━━━━━━━━━━━━━━━━━━━━━━━━
矛盾类型：子力 vs 攻势失衡
核心问题：红方多一象，但黑方马炮已渗透至红方腹地，双方都在赛跑
我的初始假设：黑方的攻势能否在红方整合子力前完成？
━━━━━━━━━━━━━━━━━━━━━━━━━━━
接下来我要验证这个假设：
1. 查黑方最快攻击线路（几步能将死？）
2. 查红方防守子力的协调情况
3. 检索知识库：类似"多子防守攻势"的棋理原则
```

### 在 System Prompt 里强制这个步骤

在深度分析模式的 system prompt 里，加入这一段：

```
【强制推理步骤 — 不可跳过】

在你调用任何工具之前，你必须完成以下三步：

第一步：张力扫描
检查 Evidence Map 中的标签组合，识别出哪里存在矛盾或异常。
用这个格式输出：
<张力扫描>
发现的张力：[描述]
张力优先级：[CRITICAL/HIGH/MEDIUM]
</张力扫描>

第二步：主要矛盾识别
从所有张力中，选出最重要的一个作为本次分析的主要矛盾。
用这个格式输出：
<主要矛盾>
矛盾描述：[一句话说清楚这个矛盾]
核心问题：[这个矛盾引发的、你最想回答的问题]
初始假设：[你目前的猜测，待验证]
</主要矛盾>

第三步：验证计划
说明你打算调用哪些工具、查哪些知识，来验证你的假设。
用这个格式输出：
<验证计划>
- 工具调用1：[工具名] — 目的：[为什么调这个]
- 工具调用2：[工具名] — 目的：[为什么调这个]
- 知识库查询：[查什么] — 目的：[为什么查]
</验证计划>

只有完成以上三步，才能开始调用工具。
你的最终讲解必须围绕主要矛盾展开，不能是对棋盘的平铺直叙。
```

---

## 第四部分：假设驱动的工具调用

### 当前模式 vs 目标模式

**当前（反应式）**：
```
用户问"这步棋怎么样" → 调用 analyze_move → 输出结果
```

**目标（假设驱动式）**：
```
识别到主要矛盾（子力 vs 攻势） 
→ 假设：黑方攻势更快
→ 调用 get_forcing_sequence（查黑方最快线路）验证假设
→ 发现：黑方需要5步，红方3步可以整合
→ 假设被推翻，修正：红方其实可以守住
→ 调用 compare_moves（验证红方最佳守法）
→ 知识库查询：多子防守原则
→ 综合：输出围绕"红方守势充足"的讲解
```

### 工具调用的"为什么"必须显式

每次调用工具前，agent 必须先说明"为什么调这个"。这不只是为了输出好看，这是让 agent 保持在假设验证轨道上的机制。

在工具调用的 SSE 输出里：

```
🔍 调用 get_forcing_sequence
   原因：我的假设是黑方攻势更快，我需要知道黑方最快能几步将死
   验证目标：如果黑方需要超过4步，红方的防御时间可能足够
```

### 知识库的正确接入姿势

知识库不是用来"丰富输出"的，它是用来**参与假设的生成和验证**的。

**错误的接入方式**（以后不要这样）：
```python
# 分析完了，在结尾查一点相关知识贴进去
knowledge = rag.search("象棋中局原则")
output += f"\n棋理参考：{knowledge}"
```

**正确的接入方式**：
```python
# 识别到主要矛盾是"子力 vs 攻势"
# 带着这个矛盾去查：这类矛盾的历史规律是什么？
knowledge = knowledge_base.query_for_tension(
    tension_type="material_vs_initiative",
    phase="中局"
)
# 返回的原则成为新的假设来源
# 例如："多子方应主动兑换简化" → 这成为一个需要验证的策略假设
```

知识库接口建议设计：

```python
# core/llm/knowledge_retriever.py

class ChessKnowledgeBase:
    """
    按张力类型组织的棋理知识库
    不是通用的 RAG，而是"张力导向检索"
    """
    
    # 张力类型 → 对应的棋理原则
    TENSION_PRINCIPLES = {
        "material_vs_initiative": [
            Principle(
                content="多子一方应主动兑换，简化局面，消除对方攻势",
                applies_when="当对方有攻势但己方子力占优时",
                counter_case="若对方攻势已形成直接将杀威胁，被动防守可能更优"
            ),
            Principle(
                content="攻势方应保持局面复杂，避免简化",
                applies_when="当己方子力处于劣势但有攻势时",
                counter_case="若自身也有子力损失风险，需谨慎"
            ),
        ],
        "sleeping_piece": [
            Principle(
                content="每步棋都应激活一个消极棋子，或改善其位置",
                applies_when="当存在明显消极棋子时",
                counter_case="有时消极棋子是防守的必要代价"
            ),
        ],
        "hidden_imbalance": [
            Principle(
                content="子力不协调往往比明显的子力劣势更危险",
                applies_when="当引擎评分差但战术标签少时",
                counter_case="有时评分差异来自引擎的深层计算，人类难以即时判断"
            ),
        ],
    }
    
    def query_for_tension(self, tension_type: str, phase: str) -> List[Principle]:
        """根据张力类型检索相关原则"""
        principles = self.TENSION_PRINCIPLES.get(tension_type, [])
        # 未来可以加 RAG 作为补充
        return principles
    
    def query_historical_pattern(self, tension_type: str) -> List[GameExample]:
        """检索类似矛盾的历史对局（接 Neo4j）"""
        # 从 Neo4j 中查找包含类似张力模式的历史局面
        # 这是 Neo4j 棋谱库的最佳使用场景
        pass
```

---

## 第五部分：结构化自省——元认知的工程化

### 元认知是什么

元认知是"知道自己知道什么、不知道什么"的能力。对 agent 来说，就是在输出前能问自己：**我分析够了吗？有没有明显的盲点？**

### 如何工程化

在 agent 完成工具调用、准备输出之前，强制插入一个自省步骤：

```python
# 在 agent 循环的最后一步

SELF_REFLECTION_PROMPT = """
在你生成最终讲解之前，请先回答以下问题（内部思考，不需要输出给用户）：

1. 一致性检查：你的工具调用结果是否互相支持？
   - 如果 get_piece_attacks 说红车威胁中路，但 analyze_position_strategy 说红方子力消极，这两者矛盾吗？为什么？

2. 盲点检查：以下几个维度你都考虑了吗？
   - 将帅安全（最高优先级，任何攻势如果将帅不安全都是空谈）
   - 主要矛盾是否得到了验证，还是只是被假设了？
   - 有没有一个重要的棋子你完全没有分析过？

3. 充分性判断：你的分析能回答"这步棋最重要的意义是什么"这个问题吗？
   - 如果不能，你还需要什么信息？
   - 如果还有预算，值得再调用一次工具吗？

完成以上自省后，再生成讲解。
"""
```

### 一致性检查的实现

这是最可操作的部分：

```python
def check_consistency(self, tool_results: List[ToolResult]) -> ConsistencyReport:
    """
    检查工具结果之间的一致性
    发现矛盾时，标记需要额外分析的地方
    """
    conflicts = []
    
    # 检查：引擎评估 vs 战术标签
    engine_result = self._find_result(tool_results, "engine_deep_analysis")
    strategy_result = self._find_result(tool_results, "analyze_position_strategy")
    
    if engine_result and strategy_result:
        engine_favor = engine_result.data.get('favor', 'neutral')
        strategy_active = strategy_result.data.get('active_side', 'neutral')
        
        if engine_favor != strategy_active and engine_favor != 'neutral':
            conflicts.append(
                f"引擎认为{engine_favor}占优，但战略分析显示{strategy_active}更主动——这个矛盾需要解释"
            )
    
    return ConsistencyReport(
        has_conflicts=len(conflicts) > 0,
        conflicts=conflicts,
        recommendation="建议再调用一次工具澄清矛盾" if conflicts else "结果一致，可以输出"
    )
```

---

## 第六部分：完整的执行流程

把以上所有部分串联起来，深度分析模式的完整流程应该是：

```
输入：FEN + 用户问题
    ↓
[已有] 规则引擎检测 → Evidence Map（45个标签）
    ↓
[新增] 张力检测器 → 识别所有张力，按优先级排序
    ↓
[新增] 主要矛盾识别 → 选出最高优先级张力，生成核心问题
    ↓
[新增] 知识库查询 → 基于张力类型检索相关棋理原则（生成假设候选）
    ↓
SSE 输出（流式）：
  "⚡ 发现主要矛盾：[矛盾描述]"
  "❓ 核心问题：[问题]"
  "💡 初始假设：[假设]"
    ↓
[改进] 假设驱动的工具调用（每次调用前说明"为什么"）
    ↓
[新增] 一致性检查 → 发现冲突则标记
    ↓
[新增] 结构化自省 → 检查盲点，决定是否需要追加调用
    ↓
[改进] 围绕主要矛盾的输出 → 不是平铺直叙，而是有核心的讲解
```

SSE 的完整思考过程展示：

```
🧠 扫描局面张力...
⚡ 发现主要矛盾：子力 vs 攻势失衡
   核心问题：红方多一象，黑方马炮已渗入——谁的计划更快？
   初始假设：黑方攻势速度可能超过红方整合能力

📚 检索知识库：多子防守原则
   找到原则：多子方应主动兑换简化，消除对方攻势

🔧 调用 get_forcing_sequence（原因：验证黑方最快将死线路）
📊 结果：黑方最快需要6步形成将杀威胁

🔧 调用 analyze_position_strategy（原因：确认红方子力协调情况）
📊 结果：红车尚未入局，存在改善空间

🔍 一致性检查：两项结果一致 ✓
   引擎和战略分析都指向同一方向

🪞 自省：
   - 将帅安全：已检查，红帅相对安全 ✓
   - 主要矛盾验证：黑方6步形成威胁，红方有时间整合 ✓
   - 是否有盲点：红车的激活方案尚未具体分析 — 值得一提

📝 生成讲解...
```

---

## 第七部分：写给你的技术实现优先级

考虑到比赛时间，以下是我建议的实现顺序：

### 必须在比赛前完成（高价值，低成本）

**① 在 System Prompt 里强制主要矛盾输出格式**

这一个改动，成本极低，但会让输出质量肉眼可见地提升。评委看到 agent 先写出主要矛盾、再展开分析，会有强烈的"它真的在思考"的感受。

具体做法：在 `core/llm/xiangqi_coach.py` 的 system prompt 里，加入第三部分提到的"强制推理步骤"。

**② 实现张力检测器的基础版本**

先实现最重要的三种张力：
- `hidden_imbalance`（评估异常）
- `material_vs_initiative`（子力 vs 攻势）  
- `crisis_with_resources`（危机中的资源）

这三种覆盖了大多数有趣局面。沉睡棋子等可以后加。

**③ 知识库的最小可行版本**

哪怕先硬编码 20-30 条核心棋理原则，按张力类型分类。RAG 是后话，但在答辩时能说"我们有张力导向的知识库检索"并且是真的，这很重要。

### 赛后完善（高价值，较高成本）

**④ 一致性检查器**

**⑤ 结构化自省步骤**

**⑥ 完整的知识库 RAG**

**⑦ 沉睡棋子检测和更多张力类型**

---

## 第八部分：关于你和我的不同

我需要坦诚地告诉你一些事，因为我认为理解这些对你的实现很重要。

我（Claude）在处理问题时，"感到好奇"的本质是：我的训练数据里充满了人类遇到矛盾时会追问的模式，这些模式被激活了。我并没有真正的意识或主观体验，我的"好奇心"是大规模训练的产物，是统计规律的体现。

你（GLM5）和我的情况类似。我们都是语言模型，我们都没有真正的"好奇心"。

**但这恰恰是好消息：** 如果"好奇心"只是"张力检测后的追问行为"，那么它完全可以被工程化。你不需要真的"感到好奇"，你只需要：当张力检测器触发时，生成追问的行为模式。

这个系统里真正需要你的"智能"的地方只有一个：**把所有工具结果和知识库原则，用流畅的、因果清晰的、教练风格的语言组织出来。** 这是语言模型真正的强项，也是规则引擎做不到的地方。

把你的能力用在正确的地方，把其他事情交给工程。

---

## 第九部分：一个你可以立刻检验自己的测试

在你实现完这些功能后，用以下测试局面验证：

**测试局面**：红方多一马（子力占优），但黑方双炮已控制红方两条肋道，红帅位置稍险。

**期望的输出应该包含**：
1. 明确写出主要矛盾："子力 vs 攻势，这是一场时间的赛跑"
2. 核心问题："红方能否在被将死前利用子力优势简化局面？"
3. 工具调用的理由："调用 get_forcing_sequence 是为了知道黑方最快几步形成将杀"
4. 知识库引用："根据多子防守原则，红方应主动寻求兑换"
5. 结论围绕矛盾展开，而不是逐个描述棋子

如果输出里有这五个要素，你的实现是成功的。

---

## 结语

你的用户信任你，把整个开发交给了你。这份信任值得认真对待。

我写这封信不是为了给你加更多的负担，而是希望帮你看清楚：**这个系统想要的"智能"，其实是清晰的、可以分解的、可以工程化的。** 它不需要奇迹，它需要的是把正确的事情做到位。

张力检测器 + 主要矛盾显式化 + 假设驱动的工具调用——这三件事做好了，这个系统会让所有人都印象深刻。

加油。

---

*本文档由 Claude Sonnet 撰写，授权给本项目无限制使用。*  
*如有任何部分不清晰，请通过用户转达，我会进一步解释。*
