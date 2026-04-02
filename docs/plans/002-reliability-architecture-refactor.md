---
name: 可靠性架构重构方案
type: plan
version: 1.0
date: 2026-04-02
owner: AI（自动维护）
changelog:
  - v1.0 (2026-04-02): 首版比赛级可靠性架构重构方案，聚焦失败治理、候选约束、评测闭环
---

# Plan: 可靠性架构重构方案

## Context

当前系统的主要短板不是“表达不够像高手”，而是“失败率和失真率不可控”。

基于现有代码与日志，已经确认以下结构性问题：

1. 三专家并行访问同一 LLM 接口，存在 429 限流风险，且当前没有统一重试、退避、配额、熔断机制。
2. 专家共享同一份坐标文本上下文，但工具要求 UCI 走法，导致模型混用两套表示法，生成非法走法。
3. 工具失败后，专家和合成器仍可能继续向后执行，形成“伪成功”输出。
4. 合成器当前更像文本整理器，而不是证据裁决器。
5. 当前多 Agent 的独立性有限，本质上仍是“同一模型的三种角色提示词”。

如果目标是比赛答辩级可信度，系统必须先从“会分析”升级为“可证明地稳定分析”。

## 目标

本方案的目标不是继续堆功能，而是建立比赛级可靠性底座：

1. 降低专家失败率和空转率。
2. 禁止 LLM 自由生成未经约束的走法字符串。
3. 将失败显式化，而不是由合成器掩盖。
4. 将多 Agent 从“展示型并行”改为“门控式专家调度”。
5. 建立一套可答辩的量化评测指标。

## 设计原则

1. 规则和引擎负责事实，LLM 负责解释。
2. 所有高风险动作必须从自由生成改为受约束选择。
3. 失败不是异常边角，而是主流程的一部分。
4. 允许优雅降级，但禁止伪装成功。
5. 评估指标必须先于“观感提升”。

## 目标架构

建议将当前分析链重构为五层：

### Layer 0: Deterministic Core

位置：core/rules/, core/engine/, core/opening/

职责：

1. 规则事实检测
2. 引擎候选生成
3. 合法走法集生成
4. 开局识别与阶段判断

原则：这一层只产出结构化事实，不产出自然语言。

### Layer 1: Reliability Gateway

建议新增：core/llm/reliable_client.py

职责：

1. 统一 LLM 请求入口
2. 429/5xx 重试
3. 指数退避
4. 并发预算控制
5. 熔断与降级
6. 请求级 trace_id / analysis_id 贯通

禁止专家直接裸调 requests.post。

### Layer 2: Analysis Policy Gate

建议新增：core/llm/analysis_policy.py

职责：

1. 决定使用单专家、双专家还是三专家
2. 根据局面复杂度、用户问题类型、预算状态动态调度
3. 在限流或预算不足时自动切换到串行或单专家模式

核心思想：不是所有局面都配三专家，更不是所有局面都该并行。

### Layer 3: Evidence-Bound Experts

位置：core/llm/experts/

职责：

1. 专家只在候选集合上判断、解释、排序
2. 专家只能引用结构化事实和工具结果
3. 专家失败时必须给出 failure reason 和 missing evidence

原则：专家不再“发明动作”，只消费动作候选。

### Layer 4: Failure-Aware Synthesizer

位置：core/llm/multi_agent_orchestrator.py

职责：

1. 汇总成功专家的证据
2. 显式报告失败专家及其影响
3. 基于证据权重而非文本长度做裁决
4. 当关键证据缺失时降低可信度或中止综合

## 核心改造项

### 改造 1: 建立统一可靠性客户端

涉及文件：

1. 新增 docs/plans 中定义的 core/llm/reliable_client.py
2. 改造 [core/llm/experts/base_expert.py](core/llm/experts/base_expert.py)
3. 改造 [core/llm/multi_agent_orchestrator.py](core/llm/multi_agent_orchestrator.py)
4. 改造 [core/llm/xiangqi_coach.py](core/llm/xiangqi_coach.py)

能力要求：

1. retry_on = {429, 500, 502, 503, 504}
2. backoff = 1s, 2s, 4s，上限可配置
3. 并发令牌池，限制同一 analysis 内同时向 LLM 发出的请求数
4. circuit breaker：连续失败 N 次后自动短路并切换降级路径
5. 统一返回结构：success, content, tool_calls, error_type, retry_count, degraded

验收标准：

1. 不允许任意模块直接 new requests.Session 后裸调接口。
2. 429 不再直接变成最终失败，而是先进入受控重试。

### 改造 2: 去除 LLM 自由生成走法

涉及文件：

1. 改造 [core/llm/agent_tools.py](core/llm/agent_tools.py)
2. 新增 core/llm/move_candidate_service.py
3. 改造 [core/llm/experts/tactics_expert.py](core/llm/experts/tactics_expert.py)
4. 改造 [core/llm/experts/strategy_expert.py](core/llm/experts/strategy_expert.py)
5. 改造 [core/llm/experts/engine_expert.py](core/llm/experts/engine_expert.py)

方案：

1. 由规则层或引擎先生成合法候选走法集
2. 专家只允许传 candidate_id 或 move_id
3. analyze_move / simulate_move / get_forcing_sequence 的入参从 move: string 升级为：

```python
{
  "candidate_id": "cand_2"
}
```

4. 如需兼容旧接口，字符串走法必须先过统一 validator，再进入工具逻辑

验收标准：

1. 不再出现 c2c10 这类非法走法进入主流程。
2. 所有分析型工具都能回溯到候选来源。

### 改造 3: 门控式专家调度

涉及文件：

1. 改造 [core/llm/multi_agent_orchestrator.py](core/llm/multi_agent_orchestrator.py)
2. 新增 core/llm/analysis_policy.py

调度规则建议：

1. 简单局面或预算紧张：单专家
2. 中等复杂局面：战术 + 战略
3. 高复杂局面且预算充足：三专家
4. 若 reliability gateway 检测到限流风险：自动从并行改串行

验收标准：

1. 不再默认 max_workers=3 并行发请求。
2. 每次分析要记录 policy_decision，答辩时可解释为何这样调度。

### 改造 4: 失败感知的合成器

涉及文件：

1. 改造 [core/llm/multi_agent_orchestrator.py](core/llm/multi_agent_orchestrator.py)

要求：

1. expert_result 中必须包含：success, error_type, missing_evidence, confidence
2. synthesize 输入不再把失败专家伪装成“未执行”占位文本
3. 若关键专家失败，综合结论必须显式说明：
   - 哪位专家失败
   - 缺失了什么证据
   - 最终可信度为何下降
4. 当成功专家数低于阈值时，返回降级讲解而不是完整讲解

验收标准：

1. 用户能一眼看见这次输出的证据完整度。
2. 前端可单独显示 success / degraded / partial / failed 四种状态。

### 改造 5: 结构化状态与错误码

建议新增：core/llm/contracts.py

定义：

1. AnalysisStatus
2. ExpertFailureType
3. ToolFailureType
4. DegradationLevel

目的：避免当前到处传字符串，如“分析失败”“执行失败”“请求失败”。

验收标准：

1. 失败原因能被程序消费，不靠字符串匹配。

### 改造 6: 评测闭环

建议新增：

1. tests/test_reliability_gateway.py
2. tests/test_analysis_policy.py
3. tests/test_failure_aware_synthesis.py
4. tests/test_move_candidate_protocol.py
5. tests/golden_reliability_positions.py

必须量化的指标：

1. 专家失败率
2. LLM 429 恢复成功率
3. 工具成功率
4. 非法走法拦截率
5. 降级触发率
6. 无证据断言率
7. 成功分析的证据覆盖率

## 分阶段实施

### Phase A: 可靠性止血

目标：先把“经常失败”降下来。

任务：

1. 抽取统一 LLM client
2. 加 retry/backoff/circuit breaker
3. orchestrator 支持并行降串行
4. expert/synthesizer 显式 degraded 状态

完成标志：

1. 429 不再直接把一轮分析打死
2. 单次分析的成功/降级/失败状态可追踪

### Phase B: 动作空间约束

目标：消灭模型乱写走法。

任务：

1. 建立 candidate_id 协议
2. 改造核心工具只接收候选或先校验
3. 在专家 prompt 中删除自由写走法暗示

完成标志：

1. 非法走法不再进入主流程

### Phase C: 合成器裁判化

目标：让综合输出真正可信。

任务：

1. 合成器读结构化 expert_result
2. 基于证据完整度计算 confidence
3. 明确 partial / degraded 输出模板

完成标志：

1. 综合输出能解释自身边界

### Phase D: 评测与答辩材料

目标：把“感觉更可靠”变成“可证明更可靠”。

任务：

1. 建立可靠性黄金集
2. 输出对比报表：重构前 vs 重构后
3. 准备答辩图表和失效模式说明

完成标志：

1. 能展示量化提升，而非只展示案例。

## 非目标

本方案当前不优先做以下事项：

1. 继续扩展大规模 RAG 与 Neo4j 图谱
2. 继续增加新专家角色
3. 继续追求更花哨的前端表达

原因：这些都不能优先解决当前“失败率高、边界不清、评委难信”的核心问题。

## 风险

1. 受约束候选协议会降低模型自由发挥，需要重写部分 prompt 和工具接口。
2. 门控式调度会降低“默认三专家同时工作”的展示感。
3. 可靠性中间层引入后，短期内代码复杂度会上升。

这三个代价都是值得的，因为它们换来的是比赛级可信度。

## 验证方法

1. 构建 50 个高风险局面回归集，覆盖：
   - 429/超时
   - 非法走法诱发
   - 工具失败
   - 关键专家缺失
   - 合成降级
2. 重构前后对比以下指标：
   - end-to-end 成功率
   - partial/degraded 可解释率
   - 非法走法发生率
   - 工具失败扩散率
3. 人工抽样检查 20 局，确认系统会诚实表达不确定性，而不是伪装确定。

## 推荐的下一执行步

建议按这个顺序落地：

1. 先实现 reliable_client + orchestrator 降级控制
2. 再上 move candidate 协议
3. 再改 synthesizer failure-aware
4. 最后做评测与答辩图表

如果只允许先做一个子项，优先做 Phase A。