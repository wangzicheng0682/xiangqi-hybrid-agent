# Position Encoder 训练日志

**项目**: 象棋AI混合代理系统
**模块**: Position Encoder (基于NeurIPS 2024)
**创建日期**: 2026-03-10
**硬件**: RTX 5060 Laptop

---

## 📋 训练概览

| 项目 | 规格 |
|------|------|
| 目标模型 | 10M-70M 参数 |
| 训练数据 | 10K-100K 局面 |
| 标注引擎 | Pikafish (depth 12-15) |
| 目标性能 | 2000-2500 Elo等效理解 |
| 响应时间 | <100ms |

---

## 📊 模型配置

### 模型规格选项

| 规格 | 参数量 | embedding_dim | num_layers | num_heads | 显存需求 |
|------|--------|---------------|------------|-----------|----------|
| **小型** | 10M | 128 | 4 | 4 | ~2GB |
| **中型** | 30M | 256 | 6 | 8 | ~4GB |
| **大型** | 70M | 384 | 8 | 8 | ~6GB |

### 当前配置

```yaml
model:
  vocab_size: 300
  embed_dim: 256
  num_heads: 8
  num_layers: 6
  max_moves: 100
  dropout: 0.1

training:
  batch_size: 32
  learning_rate: 1e-4
  weight_decay: 0.01
  epochs: 10
  optimizer: AdamW
  scheduler: CosineAnnealingLR
```

---

## 📝 训练记录

### Session 0: 项目初始化 (2026-03-10)

**状态**: ✅ 完成

**完成内容**:
- [x] Position Encoder架构实现
- [x] FEN Tokenizer实现
- [x] 语义标签生成器实现
  - RuleBasedLabeler: 规则弱监督
  - EngineInducedLabeler: 引擎诱导
  - LLMAssistedLabeler: LLM辅助
- [x] 数据管线集成
- [x] 训练器框架
- [x] DeepMind参考代码克隆

**技术决策**:
- 选择**从头训练**而非迁移学习
- 理由：架构差异大（77→90 tokens），规则差异大

**下一步**:
- [ ] 生成训练数据（Pikafish标注）
- [ ] 训练第一个模型
- [ ] 验证模型效果

---

### Session 1: 待开始

**状态**: ⏳ 待开始

**计划内容**:
- [ ] 从Neo4j提取局面数据
- [ ] 用Pikafish标注
- [ ] 生成语义标签
- [ ] 保存训练数据

**预期输出**:
- `data/training/position_data_10k.jsonl`

---

## 📈 指标追踪

### 训练指标模板

| Epoch | Train Loss | Val Loss | Value Loss | Semantic Loss | LR |
|-------|------------|----------|------------|---------------|-----|
| 1 | - | - | - | - | - |
| 2 | - | - | - | - | - |
| ... | - | - | - | - | - |

### 评估指标模板

| 指标 | 目标 | 当前 |
|------|------|------|
| Top-1 命中率 | >30% | - |
| Top-3 命中率 | >50% | - |
| Value MSE | <0.1 | - |
| Semantic F1 | >0.5 | - |

---

## 🔧 实验记录

### 实验模板

```markdown
### Experiment X: [实验名称]

**日期**: YYYY-MM-DD
**目标**: [实验目标]

**配置变更**:
- param1: value1
- param2: value2

**结果**:
- metric1: value1
- metric2: value2

**结论**:
- [结论内容]

**下一步**:
- [下一步计划]
```

---

## 📁 文件结构

```
data/
├── training/
│   ├── position_data_10k.jsonl      # 10K训练数据
│   ├── position_data_100k.jsonl     # 100K训练数据
│   └── positions_preprocessed.jsonl # 预处理中间文件
├── models/
│   ├── position_encoder_10m.pt      # 10M模型
│   ├── position_encoder_30m.pt      # 30M模型
│   └── position_encoder_70m.pt      # 70M模型
└── logs/
    └── training_YYYYMMDD.log        # 训练日志
```

---

## 🎯 里程碑

| 里程碑 | 目标日期 | 状态 |
|--------|----------|------|
| 数据生成 | Week 5 | ⏳ 待开始 |
| 10M模型训练 | Week 5 | ⏳ 待开始 |
| 30M模型训练 | Week 6 | ⏳ 待开始 |
| 效果验证 | Week 6 | ⏳ 待开始 |
| API集成 | Week 7 | ⏳ 待开始 |

---

## 📞 快速命令

```bash
# 生成训练数据
python -m core.encoder.data_generator

# 训练模型
python -m core.encoder.trainer

# 测试语义标签生成器
python -m core.encoder.semantic_labeler

# 运行测试
pytest -q
```

---

**文档版本**: v1.0
**最后更新**: 2026-03-10
**维护者**: AI全栈开发总指挥
