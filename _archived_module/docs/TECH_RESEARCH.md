# 技术研究文档

**版本**: v2.0
**创建日期**: 2026-03-10
**用途**: 记录关键论文研究和架构决策

---

## 一、核心论文研究

### 1.1 NeurIPS 2024: Amortized Planning with Large-Scale Transformers

**论文标题**: "Amortized Planning with Large-Scale Transformers: A Case Study on Chess"
**来源**: Google DeepMind (NeurIPS 2024)
**开源代码**: https://github.com/google-deepmind/searchless_chess
**本地参考**: `reference/searchless_chess/`

#### 核心发现

| 发现 | 数据/描述 | 对本项目意义 |
|------|----------|-------------|
| **无搜索推理** | 270M参数Transformer达到2895 Elo | 可实现<100ms响应 |
| **Action-value预测** | 预测每个着法的价值优于预测局面价值 | 着法推荐更准确 |
| **训练数据规模** | 15.3B训练数据 | 需要引擎标注 |
| **FEN tokenization** | 77 tokens固定长度（国际象棋） | 中国象棋需90 tokens |

#### 关键数据

| 模型规模 | 参数 | Elo | 备注 |
|----------|------|-----|------|
| 小模型 | 10M | ~2000 | 入门级 |
| 中模型 | 70M | ~2500 | 业余高手 |
| 大模型 | 270M | 2895 | 特级大师 |

#### 训练方法

1. 下载棋谱数据（Lichess等）
2. 用Stockfish标注每个局面：
   - State-value (胜率)
   - Action-values (每个合法着法的价值)
   - Best action (最优着法)
3. Behavioral cloning直接模仿引擎

#### 对本项目的适用性

**完全适用**。本项目的目标不是替代搜索引擎，而是：
- 生成高质量embedding用于相似局面检索
- 为LLM提供结构化语义特征
- 提升解释的专业性

---

### 1.2 arXiv:2602.04447v1: Mixture of Masters (MOM)

**论文标题**: "Mixture of Masters: Sparse Chess Language Models with Player Routing"
**来源**: arXiv 2026

#### 核心创新

| 创新 | 描述 | 对本项目意义 |
|------|------|--------------|
| **MoE架构** | 多个专家模型，每个模仿一个特级大师 | 可学习不同风格 |
| **Player Routing** | 根据局面动态选择专家 | 风格自适应 |
| **Behavioral Stylometry** | 视觉Transformer识别棋手风格 | 强可解释性 |
| **SSL + RL训练** | 自监督 + 强化学习 | 避免死记硬背 |

#### 对本项目的适用性

**作为长期演进目标**。当前版本(V1)采用简化版：
- Position Encoder (NeurIPS方法)
- 预留MoE扩展接口
- 参赛后升级为完整MOM

---

### 1.3 棋局特征提取与解析层深研报告

**来源**: 项目内部技术报告

#### 五种可选架构对比

| 架构 | 表示形式 | 主要用途 | 优势 | 风险 |
|------|----------|----------|------|------|
| **A: ResNet-CNN** | B×C×H×W平面 | policy/value + MCTS | 成熟、吞吐高 | 全局关系依赖堆层数 |
| **B: Transformer** | B×N×d token | embedding/语义标签 | 全局交互直接 | 历史token化会涨N²成本 |
| **C: GNN** | Graph(V,E) | 关系推理、跨棋盘泛化 | 边注意力=可解释 | 图构建复杂 |
| **D: NNUE** | 稀疏二值特征 | 极低延迟评估 | CPU百万级eval/s | 表达力受限 |
| **E: 混合多流** | learned+handcrafted | 语义层+证据绑定终态 | 同时服务检索/解释/决策 | 多任务权重复杂 |

#### 推荐方案

**选择E的简化版**：
- 规则特征层（无训练成本）
- Transformer编码层（NeurIPS方法）
- 预留混合扩展接口

---

## 二、架构决策

### 2.1 当前架构 (V0.7.0)

```
┌─────────────────────────────────────────────────────────────┐
│  Position Encoder (基于NeurIPS 2024)                        │
│  ├── FEN → 90 tokens (适配中国象棋9×10棋盘)                 │
│  ├── Transformer encoder (Decoder-only)                     │
│  └── 输出:                                                  │
│      ├── embedding (用于Neo4j相似检索)                      │
│      ├── action_values (用于着法推荐)                       │
│      └── semantic_tags (喂给LLM)                           │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│  相似局面检索  │    │  着法推荐     │    │  增强LLM      │
│  (Neo4j向量)  │    │  (Top-k)      │    │  Prompt       │
└───────────────┘    └───────────────┘    └───────────────┘
```

### 2.2 语义标签生成架构

```
┌─────────────────────────────────────────────────────────────┐
│  语义标签生成流水线 (SemanticLabelerPipeline)               │
├─────────────────────────────────────────────────────────────┤
│  1. 规则弱监督 (RuleBasedLabeler)                           │
│     - 零成本，纯规则判定                                     │
│     - 标签：opening/middlegame/endgame, check, pinned,      │
│            material, pawn_structure, open_file, active_rook │
│     - 来源标记：RULE                                         │
├─────────────────────────────────────────────────────────────┤
│  2. 引擎诱导伪标签 (EngineInducedLabeler)                    │
│     - 用PV差异与评估变化生成                                 │
│     - 标签：blunder, improving_move, critical_position,     │
│            initiative, quiet_position                        │
│     - 来源标记：ENGINE                                       │
├─────────────────────────────────────────────────────────────┤
│  3. LLM辅助标注 (LLMAssistedLabeler)                        │
│     - 抽象语义标签                                           │
│     - 标签：initiative, tempo, space, mobility, attack      │
│     - 来源标记：INFERRED                                     │
└─────────────────────────────────────────────────────────────┘
```

---

## 三、技术路线

### 3.1 核心优势

| 优势 | 说明 |
|------|------|
| **数据优势** | Pikafish引擎可生成高质量标注 |
| **时间优势** | 2周+开发周期 |
| **算力优势** | RTX 5060可训练中小模型 |
| **架构优势** | 已有的Neo4j + LLM管线可复用 |
| **参考代码** | DeepMind searchless_chess已开源 |

### 3.2 风险缓解

| 风险 | 缓解措施 |
|------|----------|
| 训练不成功 | 先做规则特征层(保底) |
| 时间不够 | 分阶段交付，核心功能优先 |
| 效果不佳 | 回退到引擎直接输出 + 简单后处理 |

---

## 四、迁移学习可行性分析

### 4.1 DeepMind模型分析

| 组件 | 国际象棋 | 中国象棋 | 差异 |
|------|----------|----------|------|
| 棋盘大小 | 8×8 | 9×10 | +26格 |
| Token长度 | 77 | ~90 | +13 tokens |
| 特殊规则 | 升变、王车易位 | 无 | 架构差异 |
| 棋子种类 | 6种 | 7种 | +1种 |

### 4.2 迁移学习结论

**不推荐迁移学习，选择从头训练**

| 方案 | 成本 | 风险 | 效果 |
|------|------|------|------|
| 从头训练 | 1-3天 | 低 | 可控 |
| 迁移学习 | 未知 | 高 | 不确定 |

### 4.3 可借鉴的部分

| 组件 | 借鉴内容 |
|------|----------|
| **Transformer架构** | Decoder-only + SwiGLU |
| **训练方法** | Action-value预测 |
| **损失函数** | 多任务学习 |
| **评估方法** | Elo计算、Puzzle测试 |

---

## 五、参考文献

1. NeurIPS 2024: "Amortized Planning with Large-Scale Transformers: A Case Study on Chess"
   - 开源代码: https://github.com/google-deepmind/searchless_chess
   - 本地路径: `reference/searchless_chess/`

2. arXiv 2602.04447: "Mixture of Masters: Sparse Chess Language Models with Player Routing"

3. 项目内部: "棋局特征提取与解析层深研报告"

---

**文档版本**: v2.0
**最后更新**: 2026-03-10
**维护者**: AI全栈开发总指挥
