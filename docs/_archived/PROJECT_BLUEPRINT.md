# 象棋AI混合代理系统 - 项目蓝图

**版本**: v1.0  
**基于**: 新建文本文档.txt 技术方案  
**核心资源**: 19万局专业PGN + Pikafish引擎  

---

## 🎯 核心目标

基于19万局专业比赛PGN和Pikafish引擎，构建一个**零幻觉**的象棋AI混合代理系统：

1. **提取可落地战术标签** - 规则硬判定，绑定棋子坐标
2. **高维检索向量** - 128-512维特征，支持相似棋谱检索
3. **棋子绑定** - 所有战术标签必须关联具体棋子
4. **抑制LLM幻觉** - Evidence Map约束，只允许基于事实讲解

---

## 🏗️ 三层架构

```
┌─────────────────────────────────────────────────────────────┐
│  上层：LLM讲解层                                             │
│  - 接收Evidence Map（事实锚点）                              │
│  - 基于事实生成自然语言讲解                                  │
│  - 禁止编造任何未提及的战术                                  │
└─────────────────────────────────────────────────────────────┘
                              ↑
┌─────────────────────────────────────────────────────────────┐
│  中层：Transformer特征层                                     │
│  - 棋盘Token编码（90个位置Token）                            │
│  - 输出：256维高维检索向量                                   │
│  - 输出：20个战术标签置信度（拟合规则层）                     │
│  - 辅助：价值回归 + 策略分类（拟合Pikafish）                  │
└─────────────────────────────────────────────────────────────┘
                              ↑
┌─────────────────────────────────────────────────────────────┐
│  底层：规则事实层                                            │
│  - Pikafish引擎：生成bestmove/score/PV等引擎真值             │
│  - 规则引擎：提取可验证战术标签（100%规则判定）               │
│  - 输出：带棋子绑定的结构化事实                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 📋 六大实施阶段

### 阶段一：PGN数据预处理
**目标**: 将19万局PGN解析为训练数据集

**核心任务**:
1. PGN解析 → FEN局面 + 走子序列 + 胜负标签
2. Pikafish批量生成引擎真值（bestmove/score/PV）
3. 数据清洗：过滤残缺局、重复局
4. 数据增强：视角归一、左右镜像
5. 存储格式：Parquet（高效读写）

**预期产出**:
- 150-200万条有效单局面FEN
- 每条FEN附带：引擎真值 + 胜负标签

---

### 阶段二：规则层特征提取
**目标**: 基于象棋规则提取100%可验证的战术标签

**设计原则**:
- ✅ 规则可硬检：所有标签均有明确判定逻辑
- ✅ 棋子必绑定：每个标签关联核心棋子坐标
- ✅ 置信度二元化：仅1.0（满足）/0.0（不满足）
- ✅ 术语专业化：贴合象棋通用术语
- ✅ 标签无嵌套：一个场景一个主标签

**六大标签层级**:

| 层级 | 优先级 | 标签示例 |
|------|--------|----------|
| 将杀困毙层 | 最高 | `is_check`, `is_checkmate`, `is_stalemate` |
| 捉子层 | 高 | `is_attack_unprotected`, `is_mutual_attack` |
| 闪击抽将层 | 高 | `is_discovered_check`, `is_double_attack_with_check` |
| 牵制串打层 | 中 | `is_pinned`, `is_cannon_double_attack` |
| 标准杀法层 | 中 | `checkmate_horse_back_cannon`, `checkmate_iron_gate` |
| 子力状态层 | 基础 | `piece_is_unprotected`, `cannon_has_platform` |

**棋子绑定格式**:
```
颜色-兵种-坐标
示例：红车-(5,8), 黑将-(5,1), 红马-(7,7)
坐标：列1-9，行1-10（红方行1-5，黑方行6-10）
```

---

### 阶段三：Transformer模型训练
**目标**: 训练输出高维向量+语义标签的模型

**输入编码**:
- 90个棋盘格作为Token
- 每个Token = 棋子Embedding（14类+空位，dim=64）+ 2D位置编码
- 输入形状：B×90

**模型结构**:
```python
XiangqiTransformer(
    d_model=256,      # 模型维度
    nhead=8,          # 注意力头数
    num_layers=6,     # 编码器层数
    num_tags=20       # 战术标签数
)
```

**输出头**:
1. **Embedding Head**: 256维高维检索向量（可压缩128/512维）
2. **Semantic Head**: 20个战术标签置信度（sigmoid输出0-1）
3. **Value Head**: 价值回归（拟合Pikafish score_cp）
4. **Policy Head**: 策略分类（拟合Pikafish bestmove）

**训练策略**:
- 损失函数：多任务损失
  ```
  L = λ1*BCE(sem_true, sem_pred) + λ2*MSE(value_true, value_pred) + λ3*CE(policy_true, policy_pred)
  ```
- 批次大小：64/128
- 优化器：AdamW（lr=1e-4）
- 训练轮数：20-30轮
- 早停：监控语义标签F1和价值回归MSE

---

### 阶段四：高维向量落地（Neo4j）
**目标**: 实现相似棋谱/棋书检索

**特征后处理**:
1. L2归一化（保证余弦相似度准确性）
2. 可选融合：模型向量(256维) + 规则标签独热向量(20维) = 276维

**Neo4j节点设计**:
```cypher
(:ChessPosition {
    fen: "rnbakabnr/9/...",
    embedding: [0.23, -0.15, ...],  // 256/276维向量
    rules_tags: {is_check: true, ...},
    engine_data: {bestmove: "...", score_cp: 1200},
    match_info: {event: "2023全国象棋甲级联赛", ...}
})
```

**向量索引**:
- Neo4j 5.0+ 余弦相似度索引
- 检索速度：毫秒级
- 返回：Recall@K（K=5/10最相似局面）

---

### 阶段五：LLM幻觉抑制
**目标**: 通过Evidence Map约束LLM，实现零幻觉讲解

**Evidence Map格式**:
```json
{
  "facts_rules": [
    {
      "tag": "is_check",
      "confidence": 1.0,
      "bind_pieces": ["黑将-(5,1)", "红车-(5,8)"]
    },
    {
      "tag": "checkmate_horse_back_cannon",
      "confidence": 1.0,
      "bind_pieces": ["红马-(6,8)", "红炮-(6,5)", "黑将-(5,1)"]
    }
  ],
  "facts_engine": {
    "bestmove": "车5平6",
    "score_cp": 1200,
    "PV": ["车5平6", "将5平4", "马6进8"],
    "depth": 20
  },
  "retrieval_result": [
    {
      "fen": "...",
      "match_info": "2023全国象棋甲级联赛 红方XX-黑方XX",
      "similarity": 0.98
    }
  ],
  "evidence_source": {
    "rules": "RULE_ENGINE",
    "engine": "PIKAFISH",
    "retrieval": "NEO4J_PGN"
  }
}
```

**LLM Prompt模板**:
```
你是专业象棋讲解师，仅能基于以下提供的棋盘事实特征讲解，
不得编造任何未提及的战术、棋理、棋子位置，
所有战术必须绑定具体棋子坐标。

若事实特征中无相关战术标签，直接说明"当前局面无该类战术"，不得猜测。

【棋盘事实特征】
{evidence_map}

请按照以下结构讲解：
1. 局面核心事实：说明是否将军/将死，核心战术标签（带绑定棋子）
2. 引擎最佳走法：解析Pikafish推荐的bestmove和PV主变
3. 相似棋谱参考：结合检索到的专业比赛PGN
```

---

### 阶段六：工程优化
**目标**: 满足<3秒响应延迟

**三级缓存策略**:
| 缓存层级 | 内容 | 有效期 |
|----------|------|--------|
| L1 | FEN→Tensor | 1天 |
| L2 | FEN→Legal Mask | 1天 |
| L3 | (FEN,depth=16)→引擎结果 | 1天 |

**两级解析模式**:
| 模式 | 触发条件 | 组件 | 耗时 |
|------|----------|------|------|
| 轻量解析 | 默认在线 | 规则层+轻量Transformer(3层)+Pikafish depth=12 | <1秒 |
| 深度解析 | 用户要求深度讲解 | 全量Transformer+Pikafish depth=20+Neo4j检索 | <2秒 |

**NNUE增量评估**:
- 利用Pikafish的.nnue网络
- 走一步只更新少量特征
- 增量推理耗时<100ms

---

## 🛠️ 工程工具清单

| 模块 | 推荐工具 |
|------|----------|
| PGN解析 | python-xiangqi / wukong-xiangqi |
| UCI引擎通信 | Python自研UCI客户端（多进程） |
| 规则引擎 | 自研轻量引擎 / wukong-xiangqi二次开发 |
| 模型训练 | PyTorch（nn.TransformerEncoder） |
| 向量数据库 | Neo4j 5.0+（余弦相似度索引） |
| 缓存 | Redis |
| 推理加速 | ONNX Runtime（模型导出ONNX） |
| 数据存储 | Parquet（大规模FEN）/ JSON（标签数据） |

---

## 📅 落地优先级（1周内核心功能）

### 紧急（第1周）
- [ ] PGN解析器实现
- [ ] Pikafish批调用脚本
- [ ] 规则层战术标签提取（核心标签）
- [ ] Evidence Map格式定义

### 次紧急（第2-3周）
- [ ] Transformer轻量模型训练（4层，d_model=128）
- [ ] Neo4j向量入库
- [ ] 相似检索API

### 后续优化（第4周+）
- [ ] 模型全量训练（6层，d_model=256）
- [ ] 两级解析模式
- [ ] NNUE增量评估
- [ ] 工程化部署

---

## 📁 项目目录结构（目标）

```
xiangqi-hybrid-agent/
├── core/
│   ├── rules/              # 规则引擎（阶段二）
│   │   ├── __init__.py
│   │   ├── rule_engine.py
│   │   ├── tactical_tags.py    # 战术标签定义
│   │   └── piece_binding.py    # 棋子绑定工具
│   ├── engine/             # Pikafish引擎封装
│   │   ├── __init__.py
│   │   └── pikafish_engine.py
│   ├── model/              # Transformer模型（阶段三）
│   │   ├── __init__.py
│   │   ├── transformer.py
│   │   ├── training.py
│   │   └── inference.py
│   ├── data/               # 数据处理（阶段一）
│   │   ├── __init__.py
│   │   ├── pgn_parser.py
│   │   ├── batch_engine.py
│   │   └── augmentation.py
│   ├── kg/                 # 知识图谱（阶段四）
│   │   ├── __init__.py
│   │   ├── neo4j_client.py
│   │   └── vector_store.py
│   ├── llm/                # LLM讲解（阶段五）
│   │   ├── __init__.py
│   │   ├── client.py
│   │   ├── evidence_map.py
│   │   └── prompt_templates.py
│   └── cache/              # 缓存层（阶段六）
│       ├── __init__.py
│       └── redis_client.py
├── data/
│   ├── raw/                # 原始PGN文件
│   ├── processed/          # 处理后数据（Parquet）
│   └── models/             # 训练好的模型
├── scripts/                # 各阶段脚本
│   ├── stage1_preprocess.py
│   ├── stage2_extract_rules.py
│   ├── stage3_train_model.py
│   ├── stage4_build_index.py
│   └── stage5_test_llm.py
├── api/                    # FastAPI接口
│   └── main.py
├── frontend/               # React前端
│   └── ...
└── docs/                   # 文档
    ├── PROJECT_BLUEPRINT.md    # 本文件
    ├── STATE.md
    └── INDEX.md
```

---

## ✅ 关键设计原则

1. **引擎真值为唯一可信来源** - 不自行计算规则
2. **所有标签必须绑定棋子** - 从根源杜绝LLM幻觉
3. **置信度二元化** - 规则硬判定，无中间值
4. **零标注成本** - 利用19万局PGN和Pikafish，无人工标注
5. **工程可落地** - 所有步骤均可实现，无玄学

---

**文档版本**: v1.0  
**最后更新**: 2026-03-14  
**状态**: 项目蓝图，指导后续开发
