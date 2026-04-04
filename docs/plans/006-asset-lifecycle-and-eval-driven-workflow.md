---
name: 资产生命周期与评测驱动工作流
type: plan
version: 1.0
date: 2026-04-03
owner: AI（自动维护）
changelog:
  - v1.0 (2026-04-03): 基于前沿调研与诚实能力评估，设计资产全生命周期管理方案
---

# Plan: 资产生命周期与评测驱动工作流

## 0. 先回答那个最重要的问题

> "你本身也是大模型，能做好吗？"

**诚实回答：不能。至少不能靠我一次性做好。**

我能做的事：
1. **定义 schema**：结构化格式我写得很准，因为这是确定性工作
2. **生成初稿**：情景模板、示范样本、知识卡的初稿我可以高效产出
3. **写评测脚本**：把"好不好"变成可执行的自动化检查，这是我的强项
4. **执行批量评测**：跑 pytest、跑 LLM-as-Judge、出分数，我可以自动化
5. **根据评测数据订正**：看到具体哪里不合格，我可以精准修改

我做不到的事：
1. **第一次就写对高质量情景示范**：象棋教学的好坏需要人判断，我写的"看起来像教练在说话"但不一定"真的像好教练"
2. **自己判断知识是否乱用**：我没有真正的棋力，我生成的棋理适用条件可能就是错的
3. **替代人的品控**：没有人类审批，资产会看起来有模有样但实际不可靠

**结论：核心不是"我能不能生成"，而是"谁来判定质量"。**

---

## 1. 前沿方法调研结论

调研了以下方向，提炼出对我们项目真正有用的部分：

### 1.1 DSPy (Stanford, 2023-2024)

**核心思想**：把 prompt 视为可编译的程序，用优化器自动搜索最优指令和示范组合。

**对我们有用的**：
- **不要手写长 prompt，要把它拆成可独立优化的模块**
- MIPRO 优化器证明：自动选择的 few-shot 示例可以比人工挑选的好 5-46%
- **关键启示**：我们的情景模板不应该是写死的长文本，而应该是 `情景判断模块 + 检查项模块 + 证据顺序模块 + 教学组织模块` 的可组合管线

**对我们没用的**：
- 需要大量标注数据做自动优化，我们短期做不到
- 需要反复调用 LLM API 做搜索，比赛前预算有限

### 1.2 STaR — Self-Taught Reasoner (Zelikman et al., 2022)

**核心思想**：用少量正确推理示范，让模型生成更多推理过程；答对的留下，答错的给正确答案让它重新推理；迭代自举。

**对我们有用的**：
- **"答错的给正确答案重新推理"这个环节，就是我们的核心工作流**
- 具体来说：我生成初稿 → 引擎/规则/你 判定对错 → 错的带着正确信息重写 → 留下通过的
- **少量高质量种子 + 自举迭代 >> 大量未检验样本**

**对我们没用的**：
- STaR 原始框架需要 fine-tuning，我们用的是闭源 API
- 但"自举循环"的思路完全可以用 prompt+eval 的方式做

### 1.3 LLM-as-a-Judge (Zheng et al., NeurIPS 2023)

**核心思想**：用强模型（GPT-4级）评判弱模型输出，与人类偏好 >80% 一致。

**对我们有用的**：
- 我们的评测题集不需要全人工评分
- 可以设计"结构化评分表"，让强模型按维度打分：是否抓住重点、是否有证据、是否空泛、是否编造
- **但必须有人工校准**：先用 30-50 题人工评分做 ground truth，再验证 LLM-Judge 与人的一致率

**关键风险**：
- LLM 评 LLM 存在 self-enhancement bias（给自己或同类输出打高分）
- **解法**：用规则/引擎做硬核验证（是否命中正确着法、标签覆盖率），LLM 只评"说得好不好"

### 1.4 Context Engineering (Karpathy, DAIR.AI, 2025)

**核心思想**：prompt engineering 已经升级为 context engineering——不只是写指令，而是架构整个上下文环境。

**对我们直接有用的设计原则**：
1. **分层上下文架构**：System Layer / Task Layer / Tool Layer / Memory Layer
2. **动态上下文调整**：根据任务复杂度选择不同的上下文组合
3. **可观测性优先**：每次决策都要可追溯
4. **基于行为迭代**：部署 → 观察 → 识别偏差 → 修正 → 验证 → 重复

**直接对应我们的做法**：
- 情景模板 = Task Layer 的动态选择
- 验证映射 = Tool Layer 的显式约束
- 失败案例库 = 观察偏差的结构化沉淀
- 评测题集 = 验证修正是否有效的度量

### 1.5 SELF-ALIGN (Sun et al., NeurIPS 2023)

**核心思想**：用 < 300 行人工标注 + 16 条原则 + 5 个示范，让模型自对齐。

**对我们的启示**：
- **原则驱动 >> 大量示例驱动**
- 16 条原则 + 5 个示范 就能显著改善 65B 模型的行为
- **我们的知识卡应该少而硬，每张带适用条件和反例**
- 不要追求 200 张知识卡，先做 20 张经过严格验证的

---

## 2. 核心设计：Eval-Driven Asset Lifecycle

基于以上调研，我们的资产管理不应该是"写了一堆东西放在那里"，而应该是一个有闭环的生命周期：

```
  ┌──────────────────────────────────────────────────────┐
  │                                                      │
  │   ┌──────────┐    ┌──────────┐    ┌──────────┐      │
  │   │ 1. 生成   │───▶│ 2. 验证   │───▶│ 3. 定级   │      │
  │   │ (AI起草)  │    │ (硬+软)  │    │ (人审批)  │      │
  │   └──────────┘    └──────────┘    └──────────┘      │
  │        ▲                                │            │
  │        │                                ▼            │
  │   ┌──────────┐    ┌──────────┐    ┌──────────┐      │
  │   │ 6. 订正   │◀───│ 5. 回归   │◀───│ 4. 入库   │      │
  │   │ (AI修改)  │    │ (自动跑)  │    │ (进主链)  │      │
  │   └──────────┘    └──────────┘    └──────────┘      │
  │                                                      │
  └──────────────────────────────────────────────────────┘
```

### 每一步的分工

| 步骤 | AI 做什么 | 人做什么 |
|------|-----------|---------|
| 1. 生成 | 按 schema 生成初稿 | 选定情景/给定 FEN |
| 2. 验证 | 跑硬核检查（引擎、规则、标签匹配） | 看报告，标记"通过/不通过/存疑" |
| 3. 定级 | 按验证结果自动建议等级 | 最终批准等级：gold / silver / draft |
| 4. 入库 | 写入对应 JSONL，更新索引 | 确认无误 |
| 5. 回归 | 全量 pytest + eval 自动跑 | 看分数变化 |
| 6. 订正 | 根据失败项精准修改 | 二次审批 |

### 资产等级定义

| 等级 | 含义 | 进入主链路 | 进入评测 |
|------|------|-----------|---------|
| **gold** | 人工审批+引擎验证+eval通过 | ✅ | ✅ |
| **silver** | AI生成+引擎验证通过，人未审 | ⚠️ 有条件 | ✅ |
| **draft** | AI生成初稿，尚未验证 | ❌ | ❌ |
| **rejected** | 验证失败或人工否决 | ❌ | ❌ 进入失败库 |

---

## 3. 四类资产的统一 Schema

### 3.1 评测题 (eval_item)

```jsonc
{
  "id": "eval_midgame_001",
  "fen": "r1bakab1r/9/2n1c2n1/p1p1p1p1p/9/6P2/P1P1P3P/1C2C1N2/9/RNBAKAB1R w",
  "question": "当前局面红方应该如何走？",
  "phase": "middlegame",
  "scenario": "midgame_initiative",           // 情景标签
  "tactical_tags": ["is_attack_unprotected"],  // 必须命中的标签
  "engine_answer": {"best_move": "c2c7", "score_cp": 185},
  "acceptable_moves": ["c2c7", "n3e4"],
  "must_mention": ["红炮沉底", "黑马无根"],    // 讲解必须提到
  "must_not_mention": ["残局", "兑子简化"],    // 讲解不应提到
  "reference_explanation": "...",              // 参考教练讲解（人写或人审）
  "grade": "gold",                            // 资产等级
  "created_by": "ai_v1",                      // 创建来源
  "reviewed_by": null,                        // 人审标记
  "last_eval_score": null,                    // 最近一次自动评分
  "last_eval_date": null
}
```

### 3.2 情景示范 (scenario_example)

```jsonc
{
  "id": "scenario_opening_mainline_001",
  "scenario": "opening_mainline",
  "fen": "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1",
  "phase": "opening",
  "situation_judgment": "标准开局第1步，双方子力完整",
  "primary_contradiction": "先手选择：中炮争中路 vs 飞相求稳",
  "non_focus_correction": "此阶段不应讨论残局转化或子力兑换",
  "must_check": ["开局书是否命中", "是否有定式后续"],
  "tool_call_order": ["analyze_position_strategy", "engine_alternatives"],
  "evidence_order": ["开局书结果", "引擎候选", "出子效率"],
  "teaching_narrative": "...",                // 最终教学讲法
  "grade": "draft",
  "created_by": "ai_v1",
  "reviewed_by": null
}
```

### 3.3 失败案例 (failure_case)

```jsonc
{
  "id": "fail_midgame_cannon_overfit_001",
  "fen": "...",
  "question": "分析当前局面",
  "phase": "opening",
  "scenario": "opening_mainline",
  "system_output": "当前局面形成重炮阵型，红方应充分利用...",
  "failure_type": "wrong_focus",              // 错因分类
  "failure_description": "开局第3步把 cannon_battery 当主焦点",
  "missing_checks": ["开局阶段应过滤宽松结构标签"],
  "correct_approach": "应优先讲出子顺序和是否脱谱",
  "regression_test": "test_reliability_refactor::test_opening_ignores_cannon_battery",
  "grade": "gold",
  "created_by": "human",
  "date": "2026-04-02"
}
```

### 3.4 断言验证映射 (assertion_verification_map)

```jsonc
{
  "assertion_type": "piece_is_unprotected",
  "description": "某子是否无根",
  "risk_level": "high",
  "required_tool": "get_piece_defenders",
  "tool_args_template": {"fen": "{fen}", "piece": "{piece_id}"},
  "pass_condition": "result.data.defender_count == 0",
  "fail_condition": "result.data.defender_count > 0",
  "min_evidence": "一次工具调用即可确认",
  "degraded_statement": "该子的防守情况尚未验证",
  "example_fen": "...",
  "example_piece": "黑马(3,8)"
}
```

---

## 4. 审批检阅订正流程（核心）

### 4.1 「三道门」审批制

任何资产从生成到进入主链路，必须过三道门：

**第一道门：硬核自动验证**
- 引擎验证：推荐着法是否在 engine top-k 内
- 标签验证：must_mention 对应的标签是否被规则引擎检出
- 格式验证：schema 是否完整、FEN 是否合法
- **这道门 AI 可以完全自动过**

**第二道门：LLM-Judge 软评分**
- 5 个评分维度，每维度 1-5 分：
  1. **焦点准确**：是否抓住当前阶段主矛盾
  2. **证据充分**：结论是否有工具/引擎证据支撑
  3. **不空泛**：是否有具体棋子、具体坐标、具体着法
  4. **不编造**：是否出现 FEN 中不存在的棋子或不合法的走法
  5. **教学价值**：学生读完是否知道该怎么下
- **此维度由强模型评分，但需用 30 题人工校准一致率**
- 一致率 < 70%：该维度的 LLM 评分不可信，回退人工
- 一致率 ≥ 70%：该维度可信赖 LLM 自动评分

**第三道门：人工终审**
- 只看第一道门和第二道门的报告
- 人只需做三个决定：✅ 通过 / ⚠️ 存疑 / ❌ 否决
- 存疑的进入待改队列，否决的进入失败案例库
- **人的时间用在判断上，不用在写内容上**

### 4.2 「每周批次」节奏

不是每次改一条就审一次，而是按批次：

| 步骤 | 频率 | 谁做 | 产出 |
|------|------|------|------|
| AI 生成新资产 | 随时 | AI | draft 级资产 |
| 自动验证跑批 | 每天 | CI 脚本 | 验证报告 |
| LLM-Judge 评分 | 每天 | CI 脚本 | 评分报告 |
| 人工终审 | 每周 1-2 次 | 你 | gold/rejected 批次 |
| 回归测试 | 每次代码变更 | pytest | pass/fail |

### 4.3 版本控制

- 所有资产文件用 JSONL 格式，一行一条，git 友好
- 每条资产有 `id` + `grade` + `reviewed_by` + `last_eval_score`
- 资产变更走 git diff，人审时可以只看 diff

---

## 5. 具体落地：文件结构

```
data/
  assets/
    eval_set.jsonl              # 评测题集
    scenario_examples.jsonl     # 情景示范库
    failure_cases.jsonl         # 失败案例库
    assertion_map.jsonl         # 断言验证映射表
    knowledge_cards.jsonl       # 知识卡（含反例）
  assets_meta/
    eval_report_latest.json     # 最近一次评测报告
    judge_calibration.json      # LLM-Judge 校准数据
    changelog.md                # 资产变更日志

scripts/
  asset_validate.py             # 硬核自动验证
  asset_judge.py                # LLM-Judge 评分
  asset_report.py               # 生成人审报告
  asset_promote.py              # 批量升级资产等级
```

---

## 6. 「我能做 vs 你需要做」清单

### 我可以直接做好的（确定性工作）

| 事项 | 质量预期 | 原因 |
|------|----------|------|
| 定义所有 schema | 高 | 结构化设计是确定性工作 |
| 写 asset_validate.py | 高 | 调用现有引擎/规则 API |
| 写 asset_judge.py | 中-高 | 评分表设计好就是模板+API调用 |
| 写 asset_report.py | 高 | 数据格式化 |
| 批量生成 draft 级资产 | 中 | 格式正确但内容需审 |
| 根据验证失败精准订正 | 中-高 | 有明确错误信号指导修改 |
| regression test 覆盖 | 高 | 写测试是确定性工作 |

### 需要你参与的（需要人类判断）

| 事项 | 你的工作量 | 怎么降低负担 |
|------|-----------|-------------|
| 审批 gold 级资产 | 每次 15-30 分钟 | 只看报告+做三选一决定 |
| 提供失败样例种子 | 一次性 1 小时 | 从你已知的掉价场景出发 |
| 校准 LLM-Judge | 一次性 30 分钟 | 对 30 题打分做 ground truth |
| 选定初始情景类型 | 一次性 15 分钟 | 我给选项你勾选 |
| 最终答辩材料审核 | 需要时 | 我生成初稿你改 |

---

## 7. 与 004/005 的关系

本方案不替代 004 和 005，而是给它们提供**执行基础设施**：

| 004 需要的 | 本方案提供的 |
|------------|-------------|
| 断言验证映射 | `assertion_map.jsonl` + `asset_validate.py` |
| 情景驱动分解 | `scenario_examples.jsonl` 里的情景定义 |
| 多候选裁判依据 | `eval_set.jsonl` 提供对照答案 |

| 005 需要的 | 本方案提供的 |
|------------|-------------|
| 失败案例库 | `failure_cases.jsonl` + 统一 schema |
| 情景化示范库 | `scenario_examples.jsonl` + 三道门审批 |
| 评测题集 | `eval_set.jsonl` + 自动评分 |
| 知识卡 | `knowledge_cards.jsonl` + 验证条件 |

---

## 8. 第一步该做什么

1. 创建 `data/assets/` 目录和空 JSONL 文件
2. 写 `scripts/asset_validate.py`：接受 JSONL，对每条跑引擎/规则验证
3. 用现有系统的已知 bug 作为种子，写 5-10 条失败案例（已有现成的：cannon_battery 误焦点、opening 误判中局、合成器草稿泄漏等）
4. 用现有 `fewshot_examples.py` 中的 9 个样本转成 scenario_examples schema
5. 从断言验证映射的 5 个优先类型开始写 `assertion_map.jsonl`
6. 然后跑一次完整验证，看哪些是 gold、哪些需要订正

**不要一开始追求数量。先做 20 条高质量闭环，再扩到 200 条。**

---

## 9. 验证方法

| 指标 | 衡量方式 | 目标 |
|------|----------|------|
| 资产格式通过率 | schema 校验 | 100% |
| 引擎验证通过率 | best_move 在 top-k 内 | ≥ 90% |
| 标签覆盖率 | must_mention 标签被规则检出 | ≥ 85% |
| LLM-Judge 与人一致率 | 30 题校准集 | ≥ 70% |
| 人审通过率 | gold / (gold + rejected) | ≥ 60% 首批 |
| 回归测试 | pytest -q | 100% pass |

---

## 10. 成功标准

1. 修改主链路后，eval_set 分数不降
2. 新增失败案例 → 自动进入回归测试
3. 人审只需看报告做决定，不需要读全部内容
4. 资产可以在不同 AI 会话间复用，不依赖任何一次对话的记忆
5. 比赛答辩时可以展示："我们的系统有 XX 条验证过的评测题，XX 条审批过的教学示范，XX 条沉淀的失败案例"
