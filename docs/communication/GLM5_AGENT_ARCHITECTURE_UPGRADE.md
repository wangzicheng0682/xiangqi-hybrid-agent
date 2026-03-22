# 致 GLM5：Agent 架构升级指令
## 从「外部编排」到「LLM 自主决策」

**优先级**：高  
**预计工作量**：半天  
**核心目标**：让 Agent 的思考过程真实自然，而不是填写预设格式

---

## 一、为什么要改

### 现在的问题

当前系统的输出像在「填表」：

```
<张力扫描>发现的张力：xxx</张力扫描>
<主要矛盾>矛盾描述：xxx</主要矛盾>
<验证计划>工具：xxx</验证计划>
```

这是因为 System Prompt 把每一步都规定死了，LLM 在执行脚本，不是在思考。
用户感受到的结果是：输出机械、缺乏「AI 灵活分析」的感觉。

### 目标状态

LLM 拿到事实和工具列表，**自己决定**怎么分析、调哪个工具、说什么。
用户看到的是真实的推理轨迹，不是预设格式。

参考：Claude/GPT/Gemini 开启 thinking 模式时，显示的是阶段性思考小标题，
不是预设步骤，而是模型真实在想的东西。

---

## 二、架构对比

### 现在（外部编排）

```
外部代码控制循环
    ↓
强制执行：扫描张力 → 识别矛盾 → 列计划
    ↓
LLM 按格式填空
    ↓
调用工具（也是外部决定调哪个）
    ↓
LLM 表达结果
```

**问题**：LLM 是执行者，不是决策者。

### 目标（LLM 自主决策）

```
第一次调用：
给 LLM：Evidence Map + 工具列表 + 极简指令
LLM 自己判断：需不需要工具？需要哪个？
同时流式输出思考过程 → 用户实时看到
    ↓
后端执行 LLM 选择的工具
    ↓
第二次调用：
把工具结果给 LLM
LLM 输出最终教练式讲解
```

**效果**：LLM 是决策者，输出自然有层次。

---

## 三、具体改动

### 改动一：System Prompt 重写

**原来的思路**（规定步骤）：
```
你必须先做张力扫描，再识别主要矛盾，再列验证计划...
```

**新的思路**（给自由空间）：

```python
SYSTEM_PROMPT = """你是一个象棋教练AI。

## 你的本质局限

你是一个"瞎子"：
- 你看不到棋盘，只能通过别人告诉你的信息理解局面
- 你不能凭感觉编造棋子位置、战术关系
- 当信息不足时，你必须调工具获取，不能猜测

## 你拥有的资源

你有以下工具可以调用（见工具列表）：
- 规则引擎工具：查棋子攻击、防守、威胁关系
- 评估引擎工具：获取引擎评分、最佳走法、候选走法
- 战略分析工具：分析局面阶段、主动权、战略特征

你还有：
- Evidence Map（已注入到局面事实中）：规则引擎预先检测的标签，这是可信的事实
- 棋理知识库：可以通过工具查询

## 你的工作方式

1. 先看 Evidence Map 里已经有什么事实
2. 判断还需要什么信息来理解这个局面
3. 调用你认为最有价值的工具获取信息
4. 基于获取的事实，给出教练式讲解

## 关键原则

- 将帅安全永远是第一优先级
- 每句话必须有事实依据，不能凭感觉说
- 禁止输出：「稳步发展」「等待时机」「保持协调」这类没有具体依据的废话
- 如果你想说某个棋子「活跃」，必须能说出它在攻击或防守哪个具体棋子

## 输出风格

你对自己局限性的认知是内部的。
对用户输出时，你是一个自信的教练——因为你说的每句话都有工具数据支撑。
讲解要像真正的象棋教练说话，有因果逻辑，不是念数据。
"""
```

---

### 改动二：调用逻辑检查与修改

**首先**，把现在 `xiangqi_coach.py` 里的 Agent 循环逻辑发给用户看一眼。
我需要确认：

```
问题A：现在是外部代码在控制「先调哪个工具」，
       还是真的在用 Function Calling 让模型自主决定？

问题B：工具调用的循环是怎么写的？
       最多几轮？终止条件是什么？
```

**如果是外部控制的**，需要改成标准 Function Calling 流程：

```python
# 目标结构（伪代码）
async def deep_analyze(fen, evidence_map):
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_message(fen, evidence_map)}
    ]
    
    # 第一次调用：让模型自主决定
    response = await llm.chat(
        messages=messages,
        tools=ALL_TOOLS,          # 把所有工具描述给它
        tool_choice="auto",       # 让它自己决定要不要调、调哪个
        stream=True               # 流式输出思考过程
    )
    
    # 流式处理：思考内容实时推给前端
    async for chunk in response:
        if chunk.type == "thinking":
            yield SSEEvent("thinking", chunk.content)
        elif chunk.type == "tool_call":
            yield SSEEvent("tool_call", chunk.tool_name)
            # 执行工具
            tool_result = await execute_tool(chunk.tool_name, chunk.args)
            yield SSEEvent("tool_result", tool_result)
            # 把结果加入对话
            messages.append({"role": "tool", "content": tool_result})
    
    # 第二次调用：整合工具结果，输出最终讲解
    final_response = await llm.chat(
        messages=messages,
        stream=True
    )
    
    async for chunk in final_response:
        yield SSEEvent("result", chunk.content)
```

---

### 改动三：用户消息构建

用户消息要把所有事实给 LLM，但不规定它怎么用：

```python
def build_user_message(fen, evidence_map):
    return f"""
## 当前局面

FEN：{fen}

## 已检测到的局面事实（Evidence Map）

{format_evidence_map(evidence_map)}

## 你的任务

分析这个局面，告诉用户：
- 这个局面最值得关注的是什么
- 当前局面的主要问题或机会在哪里
- 建议怎么走，为什么

需要更多信息时，调用工具获取。
"""
```

---

## 四、前端 SSE 展示对应调整

Agent 输出自然之后，前端时间轴也要配合。

思考内容的展示逻辑：

```typescript
// SSE 消息处理
switch (msg.type) {
    case "thinking":
        // LLM 的自由思考内容
        // 提取关键句作为小标题展示
        // 不是预设格式，是模型真实思考
        addThinkingNode(msg.content);
        break;
        
    case "tool_call":
        // 蓝色节点：调用了什么工具
        // 注意：现在不需要显示「为什么调」（模型自己决定的）
        // 而是显示「调了什么，参数是什么」
        addToolCallNode(msg.tool_name, msg.args);
        break;
        
    case "tool_result":
        // 绿色节点：工具返回了什么
        addToolResultNode(msg.summary);
        break;
        
    case "result":
        // 最终讲解，流式打字效果
        appendToResult(msg.content);
        break;
}
```

---

## 五、验证方法

改完之后，用这个局面测试：

```
FEN：rnbakabnr/9/1c5c1/p1p1p1p1p/9/6P2/P1P1P3P/1C5C1/9/RNBAKABNR w - - 0 3
```

**期望看到的变化：**

```
改之前：
  <张力扫描>发现张力：xxx</张力扫描>
  <主要矛盾>矛盾描述：xxx</主要矛盾>
  工具调用：engine_deep_analysis, analyze_position_strategy（每次一样）
  输出：「稳步发展，等待时机」

改之后：
  thinking 流：模型自己在想什么，不是格式
  工具调用：模型自己选择（可能和之前不一样）
  输出：有具体棋子、有因果逻辑的教练式分析
```

**检查清单：**
- [ ] SSE 流里出现了自然的思考内容，不是 `<标签>` 格式
- [ ] 工具调用是模型自主选择的，不是代码写死的
- [ ] 最终输出没有「稳步发展」这类废话
- [ ] 输出里有具体棋子名称和具体原因

---

## 六、执行顺序

```
第一步（今天）：把现在的 Agent 循环代码发给用户，让我确认架构类型
第二步：替换 System Prompt 为新版本
第三步：如果是外部控制架构，改成标准 Function Calling 流程
第四步：跑验证测试，输出发给用户让我看
```

**注意**：第一步必须先做，在看到现有代码之前，不要改动 Agent 循环逻辑。

---

*本文档由 Claude Sonnet 撰写，授权给本项目无限制使用。*
*执行过程中有疑问，通过用户转达。*
