# 设计重点难点

## 一、技术难点总览

| 序号 | 难点 | 分类 | 重要程度 | 创新性 |
|------|------|------|----------|--------|
| 1 | 象棋规则精确实现 | 规则引擎 | P0 | ★★★ |
| 2 | LLM幻觉防护 | AI架构 | P0 | ★★★★★ |
| 3 | 真Agent模式设计 | AI架构 | P0 | ★★★★ |
| 4 | 多专家并行协调 | AI架构 | P0 | ★★★★ |
| 5 | WebGL液态玻璃渲染 | 前端 | P1 | ★★★★ |
| 6 | SSE流式输出 | 后端 | P1 | ★★★ |
| 7 | RAG知识检索系统 | AI架构 | P1 | ★★★★ |

---

## 二、难点一：象棋规则精确实现

### 2.1 问题本质

中国象棋规则比国际象棋复杂得多：

| 规则 | 国际象棋 | 中国象棋 | 实现难度 |
|------|----------|----------|----------|
| 马的走法 | 日字 | 日字+**马腿** | 中国象棋多限制 |
| 象的走法 | 斜线 | 斜线+**象眼** | 中国象棋多限制 |
| 王的位置 | 全棋盘 | **限九宫** | 中国象棋多限制 |
| 王的关系 | 王不见王 | 王不见王+**照面** | 中国象棋多规则 |
| 兵的走法 | 固定 | **过河前后不同** | 中国象棋多变化 |

### 2.2 核心技术：Raw Moves vs 合法走法分离

**关键洞察**：攻击范围（Raw Moves）和合法走法（Legal Moves）是不同的！

**代码实现**（[xiangqi_rules.py:106-127](core/rules/xiangqi_rules.py#L106-L127)）：
```python
@staticmethod
def _get_raw_moves(board, row, col):
    """获取棋子原始走法（不过滤自将），供攻击检测使用"""
    piece = board[row][col]
    if not piece:
        return []
    # ... 直接返回步法规则，不做任何将军过滤
    return XiangqiRulesEngine._knight_moves(...)  # 或其他棋子
```

**分离原因**：
```
场景：黑车被红马牵制，不能横走
- Raw Moves：黑车可以横走（能攻击红帅方向）
- 合法走法：黑车不能横走（会送将）

如果用合法走法计算攻击范围，会漏掉"牵制"效果！
```

### 2.3 马腿检测原理（精确代码）

**马的8个方向偏移**（[xiangqi_rules.py:352-361](core/rules/xiangqi_rules.py#L352-L361)）：
```python
knight_moves = [
    (2, 1, 1, 0),   # dr=2, dc=1, block_r=1, block_c=0（蹩腿位置）
    (2, -1, 1, 0),  # dr=2, dc=-1, block_r=1, block_c=0
    (-2, 1, -1, 0), (-2, -1, -1, 0),
    (1, 2, 0, 1), (1, -2, 0, -1),
    (-1, 2, 0, 1), (-1, -2, 0, -1),
]

for dr, dc, block_r, block_c in knight_moves:
    nr, nc = row + dr, col + dc      # 落脚位置
    mr, mc = row + block_r, col + block_c  # 马腿位置

    if 0 <= nr < 10 and 0 <= nc < 9:
        if 0 <= mr < 10 and 0 <= mc < 9 and not board[mr][mc]:
            # 马腿空 → 可以走
            pass
```

**步骤详解**：
```
例如：马在(5,5)，想走(2,1)方向到(7,6)
Step 1: 计算马腿位置
    block_r = 1, block_c = 0
    mr = 5 + 1 = 6, mc = 5 + 0 = 5
    马腿 = (6, 5)

Step 2: 检查马腿是否有棋
    if board[6][5] is not None:
        跳过此方向（被蹩腿）

Step 3: 检查落脚点
    if board[7][6] is None or is_enemy(board[7][6]):
        可以走到(7,6)
```

### 2.4 自将过滤：递归陷阱的解决

**问题**：判断A走法是否合法 → 需要检查B是否被将军 → 判断B应将是否合法 → 又要检查A是否被将军 → 无限递归！

**解决：使用Raw Moves构建`_is_square_attacked`**（[xiangqi_rules.py:130-138](core/rules/xiangqi_rules.py#L130-L138)）：
```python
@staticmethod
def _is_square_attacked(board, row, col, by_red: bool) -> bool:
    """判断某格子是否被指定方攻击（基于Raw Moves，无递归）"""
    for r in range(10):
        for c in range(9):
            piece = board[r][c]
            if piece and XiangqiRulesEngine.is_red(piece) == by_red:
                # 调用 _get_raw_moves（原始走法），不是 get_legal_moves（合法走法）
                if (row, col) in XiangqiRulesEngine._get_raw_moves(board, r, c):
                    return True
    return False
```

**关键**：`_is_square_attacked`内部调用`_get_raw_moves`，而非`get_legal_moves`——不触发递归。

### 2.5 将帅照面检测

**规则**：双方将帅在同一列上直接对面（中间无子）时，构成照面违规。

**代码实现**（[xiangqi_rules.py:142-155](core/rules/xiangqi_rules.py#L142-L155)）：
```python
@staticmethod
def _kings_face_each_other(board) -> bool:
    red_king = XiangqiRulesEngine._find_king(board, True)
    black_king = XiangqiRulesEngine._find_king(board, False)
    if not red_king or not black_king:
        return False
    if red_king[1] != black_king[1]:
        return False  # 不同列，不照面

    # 检查中间是否有其他棋子
    for r in range(min(red_king[0], black_king[0]) + 1,
                    max(red_king[0], black_king[0])):
        if board[r][red_king[1]]:
            return False  # 中间有子，不照面
    return True  # 同一列且中间无子 = 照面
```

### 2.6 炮架与保护的关系

**区别**：
- **炮架**：被炮隔着打的棋子，是炮的攻击目标，会被吃掉
- **保护**：己方棋子保护另一个己方棋子，敌方吃被保护的子，我方可以吃回

**错误理解**："炮架=保护" → 错！炮架不是保护关系。

---

## 三、难点二：LLM幻觉防护

### 3.1 问题本质

通用LLM在象棋分析中会产生严重的"幻觉"：

| 类型 | 表现 | 危害 |
|------|------|------|
| 棋子幻觉 | "红车在5路"（实际在3路） | 完全误导 |
| 关系幻觉 | "黑马被红炮保护"（实际没有） | 分析错误 |
| 走法幻觉 | "红马可以走马三进四"（蹩腿） | 违反规则 |
| 分数幻觉 | "这步棋让优势扩大50分"（实际-30分） | 误导判断 |

### 3.2 核心方案：三层Evidence Map约束

**第一层：规则引擎（100%准确的事实）**

[xiangqi_rules.py](core/rules/xiangqi_rules.py)提取FEN→45个标签检测→每条标签绑定棋子坐标：
```python
# tactical_detector.py:296-307
for tag_item in em_tags:
    tag_name = tag_item.get("name", "")
    bind_pieces = tag_item.get("bind_pieces", [])  # 绑定棋子坐标
    pieces_str = "、".join(bind_pieces)
    # 例: "is_attack_unprotected [红车-(5,8)、黑马-(7,8)]"
```

**第二层：System Prompt硬约束**（[xiangqi_coach.py:150-179](core/llm/xiangqi_coach.py#L150-L179)）：
```
以下内容只能来自 Evidence Map 或工具返回，绝对不能凭感觉填写：
- 任何具体棋子的坐标或位置
- 任何走法的具体效果
- 任何引擎评估数值

关于"保护"关系的硬规则：
如果你提到"保护"，必须调用 get_piece_defenders 验证，
绝对不能在未调用工具验证的情况下说"XX保护了YY"
```

**第三层：工具调用验证**

当LLM想输出"红车威胁黑马"时：
```
Step 1: LLM调用 get_piece_defenders(fen, "黑马")
Step 2: 工具返回: {"defenders": ["黑炮"]} 或 {"defenders": []}
Step 3: LLM基于验证结果输出，不能无中生有
```

### 3.3 保护关系的精确验证

**错误做法**（幻觉）：
```
LLM: 黑马无根，因为红炮能直接打过来
真相：黑马实际上有黑炮保护 → 幻觉！
```

**正确做法**（[agent_tools.py:172-232](core/llm/agent_tools.py#L172-L232)）：
```python
def get_piece_defenders(self, fen, piece) -> ToolResult:
    # 遍历所有己方棋子，检查谁的攻击范围包含目标位置
    defenders = []
    for r in range(10):
        for c in range(9):
            p = board[r][c]
            if p and self._is_red(p) == is_red and (r,c) != target:
                attacks = self._get_attacks(board, r, c)
                if target in attacks:  # 该棋子的攻击范围包含目标
                    defenders.append(...)  # 才是真正的保护关系
    return {"defender_count": len(defenders), ...}
```

---

## 四、难点三：真Agent模式设计

### 4.1 问题本质

传统"AI象棋"是"LLM自由发挥"模式：
```
用户问题 → LLM直接回答 → （可能幻觉）
```

LLM不知道该用什么工具，只能凭感觉回答。

### 4.2 解决方案：Function Calling自主决策

**Agent循环**（[xiangqi_coach.py:899-985](core/llm/xiangqi_coach.py#L899-L985)）：
```python
for round_num in range(config.max_rounds):  # 默认max_rounds=3
    response = self._call_api_stream(messages, tools=TOOLS_SCHEMA)
    if response.tool_calls:
        # 自主调用工具
        for tool_call in response.tool_calls:
            result = self._execute_tool(tool_call, fen)
            messages.append({"role": "tool", "content": json.dumps(result)})
    else:
        break  # LLM认为信息足够，输出最终答案
```

### 4.3 11个工具的精确分类与使用场景

**第一类：棋子关系查询（原子工具）**

| 工具名 | 核心方法 | LLM什么时候用 |
|--------|----------|-------------|
| `get_piece_attacks` | `_get_attacks()`返回Raw Moves | 想确认某棋子的攻击范围 |
| `get_piece_defenders` | 遍历己方找攻击范围含目标者 | 想确认某棋子是否有保护 |
| `get_threats_to_piece` | 遍历敌方找攻击范围含目标者 | 分析防守需要 |
| `get_piece_relations` | 综合调用以上三个 | 需要完整关系时（推荐优先用这个） |

**第二类：走法分析工具**

| 工具名 | 核心逻辑 | LLM什么时候用 |
|--------|----------|-------------|
| `get_move_candidates` | 调用`RuleEngine.get_legal_moves` | 分析具体走法之前 |
| `analyze_move` | 前后标签对比+质量评级 | 评估走法质量 |
| `compare_moves` | 多走法评分对比 | 比较多个候选 |
| `get_forcing_sequence` | 递归将军-应将链（深度可配置） | 检查强制序列 |

**第三类：引擎深度分析**

| 工具名 | 核心实现 | LLM什么时候用 |
|--------|----------|-------------|
| `engine_deep_analysis` | 调用`EnginePool.analyze(depth)` | 获取权威评估 |
| `engine_alternatives` | 调用`EnginePool.analyze_multipv(depth, num_pv)` | 对比多个候选 |

**第四类：战略与模拟**

| 工具名 | 核心逻辑 |
|--------|----------|
| `analyze_position_strategy` | 综合阶段+主动权+关键特征 |
| `simulate_move` | 执行走法前后标签对比 |
| `query_chess_principles` | 根据张力类型检索棋理 |

### 4.4 防止LLM"跳过工具"（System Prompt约束）

[xiangqi_coach.py:155-179](core/llm/xiangqi_coach.py#L155-L179)中明确规定：
```
【禁止】
- 不要自由编造 UCI 走法再直接分析
- 绝对不能在没有调用工具验证的情况下说"XX保护了YY"
- 如需验证，必须先调用工具
```

---

## 五、难点四：多专家并行协调

### 5.1 问题本质

三个专家（战术/战略/引擎）如何协同？合并时如何避免冲突？

### 5.2 自适应决策：六路门控策略

**实现**（[analysis_policy.py:14-62](core/llm/analysis_policy.py#L14-L62)）：
```python
def choose_analysis_policy(question, tensions, phase_name, ...):
    text = question or ""

    if force_full_team:
        selected = ["tactics", "strategy", "engine"]
    elif any(kw in text for kw in ENGINE_KEYWORDS):
        selected = ["engine", "strategy"]       # 问引擎评分
    elif any(kw in text for kw in TACTICAL_KEYWORDS):
        selected = ["tactics", "engine"]          # 问战术杀法
    elif phase_name == "开局" and move_count <= 4 and not tension_count:
        selected = ["strategy"]                   # 简单开局
    elif tension_count >= 3:
        selected = ["tactics", "strategy", "engine"]  # 复杂局面
    else:
        selected = ["tactics", "strategy"]        # 默认双专家
```

### 5.3 开局快答路径

**判定条件**（[multi_agent_orchestrator.py:657-681](core/llm/multi_agent_orchestrator.py#L657-L681)）：
```python
def _should_use_opening_fast_path(...) -> bool:
    if phase_info.phase_name != "开局":
        return False
    if any(keyword in text for keyword in ENGINE_KEYWORDS):
        return False  # 问引擎评分 → 不走快答
    if len(tensions) > 1:
        return False  # 张力多 → 不走快答
    # 开局前6步以内，或识别到定式的前8步
    return effective_move_count <= 6 or (opening and effective_move_count <= 8)
```

**快答内容**：开局识别名称 + 棋理原则 + 轻量引擎评分（不调用三专家）。

### 5.4 并行执行策略

[multi_agent_orchestrator.py:1108-1121](core/llm/multi_agent_orchestrator.py#L1108-L1121)：
```python
if policy.parallelism <= 1:
    # 串行执行（降级模式）
    for name, span_name, func in selected_jobs:
        _, result = run_expert(name, span_name, func)
        results[name] = result
else:
    # 真并行（ThreadPoolExecutor）
    with ThreadPoolExecutor(max_workers=policy.parallelism) as executor:
        futures = [executor.submit(run_expert, name, span_name, func)
                   for name, span_name, func in selected_jobs]
        for future in futures:
            name, result = future.result(timeout=180)
            results[name] = result
```

### 5.5 证据裁决合成器

**核心思想**：合成不是拼接，而是裁判。

[multi_agent_orchestrator.py:48-125](core/llm/multi_agent_orchestrator.py#L48-L125)中的合成器System Prompt：
```
【证据裁决规则】
| 情况 | 处理方式 |
|------|----------|
| 工具验证断言 vs 纯推理断言 | 工具验证优先 |
| 引擎评估 vs 战术发现（都有工具验证） | 战术发现优先（精确规则） |
| 断言矛盾 | 高权重胜出，或都保留并标注矛盾 |
```

**Claim结构化输出**（[claim.py:33-48](core/llm/claim.py#L33-L48)）：
```python
@dataclass
class Claim:
    statement: str                    # 断言内容
    source: str                        # tool_verified / reasoning / unverified
    confidence: str                     # high / medium / low
    evidence: List[EvidenceItem]         # 支持证据列表

# 格式化输出示例：
# CLAIM-1: 红车控制将门线 [来源:工具验证] [置信:高]
#   证据: get_piece_attacks(红车) → 攻击(0,4),(0,5)
# CLAIM-2: 黑马被牵制 [来源:推理] [置信:中]
```

---

## 六、难点五：WebGL液态玻璃渲染

### 6.1 问题本质

实现Apple iOS 26液态玻璃效果，需要模拟真实物理光学。

### 6.2 五步WebGL渲染管线

[LiquidGlassApp.tsx](frontend/src/components/LiquidGlassApp.tsx)中的管线实现：

| Pass | Shader | 作用 | 关键参数 |
|------|--------|------|----------|
| 1 | fragment-bg | 背景渲染，输出到纹理A | - |
| 2 | fragment-bg-vblur | 竖向高斯卷积，纹理A→纹理B | blurRadius |
| 3 | fragment-bg-hblur | 横向高斯卷积，纹理B→纹理C | blurRadius |
| 4 | fragment-main（shape1） | 左侧栏液态玻璃 | refThickness, refFactor, refDispersion, fresnel |
| 5 | fragment-main（shape3） | 右侧栏液态玻璃 | 独立参数集 |

### 6.3 物理光学核心参数

[LiquidGlassApp.tsx](frontend/src/components/LiquidGlassApp.tsx)中的参数定义：
```typescript
interface Controls {
  refThickness: number;    // 折射厚度，影响UV偏移量
  refFactor: number;         // 折射强度，1.4（蓝移最大）
  refDispersion: number;    // 色散强度，0.6
  refFresnelRange: number;  // 菲涅尔范围，30px
  refFresnelHardness: number;  // 菲涅尔锐度，12
  refFresnelFactor: number;    // 菲涅尔强度，60
  glareFactor: number;         // 炫光强度，90
  glareAngle: number;         // 炫光角度，-45度
  blurRadius: number;         // 高斯模糊半径
  shadowExpand: number;        // 阴影外扩，25px
}
```

### 6.4 折射+色散+菲涅尔实现原理

片段着色器中的核心计算：
```glsl
// 折射采样（背景模糊纹理 + 法线偏移）
vec2 refractUV = uv + normal * u_refraction;
vec4 bgColor = texture2D(u_blurredBg, refractUV);

// 色散（RGB三通道不同偏移，实现彩虹边缘）
float r = texture2D(u_blurredBg, refractUV * (1.0 - u_dispersion * 0.5)).r;
float g = texture2D(u_blurredBg, refractUV).g;
float b = texture2D(u_blurredBg, refractUV * (1.0 + u_dispersion * 0.5)).b;

// 菲涅尔（观察角度影响反射强度）
float fresnel = pow(1.0 - abs(dot(normal, vec3(0,0,1))), u_fresnelHardness);
float reflection = fresnel * u_fresnelFactor;
```

---

## 七、难点六：SSE流式输出

### 7.1 问题本质

实时展示AI思考过程，让用户看到"AI是怎么想的"。

### 7.2 SSE vs 轮询对比

| 方案 | 延迟 | 服务器压力 | 实现复杂度 |
|------|------|-----------|-----------|
| 轮询 | 高（每次请求间隔） | 高 | 低 |
| WebSocket | 低 | 高 | 高 |
| **SSE** | **低** | **低** | **中** |

### 7.3 后端实现（FastAPI StreamingResponse）

[api/main.py:1514-1754](api/main.py#L1514-L1754)中的SSE实现：
```python
from fastapi.responses import StreamingResponse
import json, queue, threading

async def generate():
    event_queue = queue.Queue()

    # 后台线程执行分析，结果放入队列
    def run_agent():
        result = orchestrator.analyze(..., on_thinking=lambda s,m: event_queue.put(...))
        event_queue.put(None)  # 结束信号

    agent_thread = threading.Thread(target=run_agent, daemon=True)
    agent_thread.start()

    # 实时从队列读取并发送SSE事件
    while True:
        event = event_queue.get(timeout=0.1)
        if event is None:
            break
        yield f"data: {json.dumps({'type': event['type'], **event})}\n\n"
        await asyncio.sleep(0.01)
```

### 7.4 14种SSE事件类型

[api/main.py:1661-1723](api/main.py#L1661-L1723)：
```python
# 专家事件
"expert_start"              # 专家开始分析
"expert_step_start"         # 专家步骤开始
"expert_step_content"       # 步骤内容（增量追加）
"expert_step_end"           # 步骤结束
"expert_result"            # 专家最终结果

# 合成器事件
"synthesis_step_start"       # 合成步骤开始
"synthesis_step_content"    # 合成内容
"synthesis_step_end"        # 合成步骤结束
"synthesis_chunk"           # 合成器流式片段

# 元事件
"orchestrator_subtitle"     # 协调者子标题
"dispatch_info"            # 调度决策信息
"tool_call"                # 工具调用名称
"tool_result"              # 工具返回结果
"headline"                 # 摘要提示
"thinking_chunk"           # 思考内容片段
```

---

## 八、难点七：RAG知识检索

### 8.1 问题本质

让AI分析有"知识支撑"，而不是凭空发挥。

### 8.2 向量检索原理

**传统检索 vs 向量检索**：

| 方案 | 原理 | 局限 |
|------|------|------|
| 关键词检索 | 匹配关键词 | "马后炮"查不到"马炮配合" |
| **向量检索** | 语义相似度 | 可以找到意思相近的内容 |

**向量检索流程**：
```
1. 文本 → 向量（text2vec模型，chinese挂载）
2. 查询 → 向量
3. 计算向量相似度（余弦距离）
4. distance → relevance = 1.0 - distance
5. 返回最相似的文档
```

### 8.3 ChromaDB懒加载索引

[core/rag/chroma_rag.py](core/rag/chroma_rag.py)中的实现：
```python
def _get_collection():
    if _collection.count() == 0:
        # 自动索引80+条棋理原则
        _index_principles(_collection)
    return _collection

def retrieve(self, query: str, top_k: int = 5):
    results = _get_collection().query(
        query_texts=[query],
        n_results=top_k
    )
    # distance → relevance
    for doc, dist in zip(results['documents'], results['distances']):
        rag_results.append(RAGResult(content=doc, relevance=1.0 - dist))
    return rag_results
```

用户首次使用时自动索引，无需手动操作。

---

## 九、创新点总结

### 9.1 核心技术创新

| 创新点 | 技术原理 | 突破 |
|--------|----------|------|
| Evidence Map约束 | 规则100%准确→LLM只能基于事实 | 解决LLM幻觉 |
| 真Agent模式 | LLM自主决策调用11个工具 | 从硬编码到自主智能 |
| 三专家并行 | 战术/战略/引擎协同分析 | 多角度深度分析 |
| 证据裁决合成 | 工具验证→交叉验证→权重裁决 | 从文本合并到证据推理 |
| 开局快答调度 | 识别定式→跳过重链路 | 效率与深度平衡 |

### 9.2 工程创新

| 创新点 | 技术原理 |
|--------|----------|
| Raw Moves与合法走法分离 | 攻击范围vs合法性，解决递归问题 |
| 45标签检测体系 | 规则硬判定，覆盖所有战术类型 |
| 马腿/象眼精确检测 | 8方向偏移+步法规格化 |
| LLM高可靠调用 | 信号量+指数退避+熔断器 |
| WebGL五步管线 | 折射+色散+菲涅尔+双高斯模糊 |
| SSE 14种事件类型 | 实时推送专家思考步骤 |

### 9.3 应用创新

| 创新点 | 用户价值 |
|--------|----------|
| 教练式讲解 | 因果分析，理解"为什么" |
| 零幻觉保证 | 可靠的专业分析 |
| 三级难度对弈 | 适应不同水平 |
| 棋盘视觉识别 | 拍照即分析 |
