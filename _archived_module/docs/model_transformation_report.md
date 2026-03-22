# 59M 模型转型作战报告

## 第一部分：模型现状复核

### 1.1 当前输入格式

```
FEN 字符串 → FENTokenizer → 100 维整数序列（padding 到 100）
```

**示例**：
```
输入: "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"
输出: [1, 2, 3, 4, 5, 6, 7, 8, 9, 16, 21, 29, ...]  # 100维
```

### 1.2 模型架构与输出头

| 输出头 | 维度 | 用途 | 参数量 |
|--------|------|------|--------|
| state_value | 1 | 局面分数 (-1 到 1) | ~300K |
| action_values | 128 | 128 个动作值分箱 | ~1M |
| policy_logits | 100 | 着法概率 | ~800K |
| embedding | 256 | 局面向量（用于检索） | ~500K |
| semantic_tags | 33 | 语义标签 | ~300K |

**总参数**：59,605,766

### 1.3 关键发现：哪些输出真正参与了训练？

| 输出头 | 代码里有 | 训练用了 | 监督来源 |
|--------|----------|----------|----------|
| state_value | ✅ | ✅ | MSE vs 引擎分数 |
| action_values | ✅ | ⚠️ 只用了 [:, 0] | MSE vs 引擎分数 |
| policy_logits | ✅ | ❌ | 无 |
| embedding | ✅ | ❌ | 无对比学习 |
| semantic_tags | ✅ | ❌ | 无 |

**核心问题**：
1. **policy_logits 完全没训练**：虽然模型能输出，但没有监督信号
2. **semantic_tags 完全没训练**：33 个标签全是随机初始化
3. **embedding 没有对比学习**：只是通过其他损失间接影响
4. **action_values 只用了第一个**：128 个分箱只用了 1 个

### 1.4 当前训练损失

```python
loss = MSE(pred_state_value, state_value) + MSE(pred_action_value[:, 0], action_value)
```

**结论**：模型实际上只学了**预测分数**，其他所有输出头都是摆设。

---

## 第二部分：验证战报

### 2.1 验证集准备

立即执行：从 100 万数据中分出 10% 作为验证集

### 2.2 五个必须做的实验

#### 实验 1：训练集 vs 验证集损失对比

**目的**：判断是否过拟合

**做法**：
1. 用当前模型在验证集上计算损失
2. 对比训练损失和验证损失

**判断标准**：
- 验证损失 ≈ 训练损失 → 学到了通用模式
- 验证损失 > 1.5× 训练损失 → 过拟合
- 验证损失 >> 训练损失 → 严重过拟合

#### 实验 2：1000 局面重算分数校准测试

**目的**：测试分数预测是否准确

**做法**：
1. 随机抽 1000 个验证集局面
2. 用引擎重新分析（depth 12）
3. 对比模型预测 vs 引擎真实分数

**判断标准**：
- MAE < 0.3（30分）→ 可用
- MAE 0.3-0.5 → 勉强可用
- MAE > 0.5 → 不可靠

#### 实验 3：相似局面检索人工抽检

**目的**：测试 embedding 质量

**做法**：
1. 选 50 个典型局面
2. 用 embedding 计算最相似的 5 个局面
3. 人工判断是否"真的相似"

**判断标准**：
- 相似度 > 80% → 可用于检索
- 相似度 50-80% → 需要改进
- 相似度 < 50% → embedding 没学到东西

#### 实验 4：10% 标签打乱对照实验

**目的**：确认模型不是在学伪规律

**做法**：
1. 随机打乱 10% 的训练标签
2. 用当前模型在新数据上微调 1 epoch
3. 观察损失变化

**判断标准**：
- 损失上升明显 → 模型确实学到了东西
- 损失几乎不变 → 可能在学伪规律

#### 实验 5：冻结骨干 + 语义头探测实验

**目的**：测试模型内部是否有棋理知识

**做法**：
1. 冻结主模型参数
2. 用规则生成语义标签
3. 只训练语义头（线性层）
4. 测试在验证集上的准确率

**判断标准**：
- 准确率 > 70% → 模型内部有棋理知识
- 准确率 50-70% → 部分有
- 准确率 ≈ 随机 → 模型没学到棋理

---

## 第三部分：语义化改造方案

### 3.1 第一版语义标签设计

| 标签 | 含义 | 生成方式 |
|------|------|----------|
| phase | opening/middlegame/endgame | 规则（改进版） |
| initiative | red/black/balanced | 引擎分数符号 |
| risk | high/medium/low | 引擎分数绝对值 |
| structure | open/closed/semi | 规则检测 |
| tactics | active/quiet | 引擎主变分析 |

### 3.2 标签生成器设计

```python
class SemanticLabelGenerator:
    """第一版语义标签生成器"""
    
    def generate(self, fen: str, engine_score: float) -> dict:
        labels = {}
        
        # 阶段（改进版：不只数子，还看位置）
        piece_count = self._count_pieces(fen)
        if piece_count >= 26:
            labels['phase'] = 'opening'
        elif piece_count >= 14:
            labels['phase'] = 'middlegame'
        else:
            labels['phase'] = 'endgame'
        
        # 主动权
        if engine_score > 50:
            labels['initiative'] = 'red'
        elif engine_score < -50:
            labels['initiative'] = 'black'
        else:
            labels['initiative'] = 'balanced'
        
        # 风险
        abs_score = abs(engine_score)
        if abs_score > 200:
            labels['risk'] = 'high'
        elif abs_score > 50:
            labels['risk'] = 'medium'
        else:
            labels['risk'] = 'low'
        
        # 结构（简化版）
        labels['structure'] = self._detect_structure(fen)
        
        # 战术活跃度
        labels['tactics'] = 'active' if abs_score > 100 else 'quiet'
        
        return labels
    
    def _count_pieces(self, fen: str) -> int:
        board = fen.split()[0]
        count = 0
        for c in board:
            if c.isalpha():
                count += 1
            elif c.isdigit():
                count += int(c)
        return count
    
    def _detect_structure(self, fen: str) -> str:
        # 简化版：根据兵的数量判断
        board = fen.split()[0]
        pawn_count = board.count('P') + board.count('p')
        if pawn_count >= 10:
            return 'closed'
        elif pawn_count <= 4:
            return 'open'
        else:
            return 'semi'
```

### 3.3 语义头改造方案

**当前问题**：语义头输出 33 维，但没有训练

**改造方案**：
1. 减少到 5 维（对应 5 个标签）
2. 每个标签用交叉熵损失
3. 冻结骨干，只训练语义头

---

## 第四部分：矛盾识别预案

### 4.1 核心矛盾类型（第一版）

| 类型 | 描述 | 判定条件 |
|------|------|----------|
| 中路争夺 | 双方争夺中路控制 | 中心区有多个子力对峙 |
| 王安全 | 将/帅安全受威胁 | 引擎显示一方分数剧烈波动 |
| 子力协调 | 子力配合问题 | 某方有子力位置差 |
| 结构弱点 | 兵/卒结构问题 | 有孤兵或叠兵 |
| 优势转换 | 需要转换优势 | 一方优势但需技术性着法 |
| 抢先手 | 争夺主动权 | 双方分数接近但都有威胁 |

### 4.2 矛盾分类器输入

```python
contradiction_input = {
    'semantic_state': semantic_labels,      # 语义状态
    'engine_pv_summary': pv_summary,        # 引擎主变摘要
    'key_risks': risk_points,               # 关键风险点
    'weakness_info': weakness_detection,    # 候选弱点
}
```

### 4.3 矛盾分类器输出

```python
contradiction_output = {
    'type': '王安全',           # 矛盾类型
    'region': '红方底线',       # 关键区域
    'reason': '黑车威胁红帅',   # 支撑理由
    'evidence': ['engine', 'rule'],  # 证据来源
}
```

---

## 第五部分：7 天内必须交付的东西

### Day 1-2：验证报告

**交付物**：
- [ ] 验证集损失 vs 训练集损失对比
- [ ] 1000 局面分数校准测试结果
- [ ] 相似局面检索抽检报告

### Day 3-4：语义标签生成器

**交付物**：
- [ ] SemanticLabelGenerator 代码
- [ ] 在 1000 样本上的标签分布报告
- [ ] 人工抽检 50 个样本的正确率

### Day 5-6：语义头探测实验

**交付物**：
- [ ] 冻结骨干 + 训练语义头的代码
- [ ] 验证集上的准确率报告
- [ ] 判断模型内部是否有棋理知识

### Day 7：矛盾分类器设计草案

**交付物**：
- [ ] 矛盾类型定义文档
- [ ] 输入输出 schema
- [ ] 与解释系统的对接方案

---

## 总结

### 当前模型真实状态

| 维度 | 状态 |
|------|------|
| 分数预测 | ⚠️ 可能只记住了训练集 |
| Policy | ❌ 完全没训练 |
| Embedding | ❌ 没有对比学习 |
| 语义标签 | ❌ 完全没训练 |

### 最紧迫的任务

1. **验证**：确认模型是否真的学到了东西
2. **探测**：测试模型内部是否有棋理知识
3. **改造**：把模型从"分数预测器"转成"语义特征器"

### 战略定位

**59M 模型 = 候选语义骨干，不是主决策核心**

它的使命是：
- ✅ 输出局面向量
- ✅ 输出语义标签（需要后训练）
- ❌ 不要直接做决策
- ❌ 不要直接生成解释
