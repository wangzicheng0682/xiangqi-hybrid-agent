# 归档模块清单

**归档日期**: 2026-03-13  
**归档原因**: 核心语义分析模块存在致命逻辑错误，需彻底重构  
**归档执行人**: 技术架构师

---

## 一、致命Bug代码归档 (core/semantic/)

### 1.1 position_analyzer.py
- **文件大小**: 800+ 行
- **致命错误**:
  - **炮攻击逻辑错误**: 未检查炮架，将无炮架的炮错误标记为可攻击目标
  - **马腿判断错误**: 己方棋子被错误标记为"别马腿"，开局正常阵型被误判
  - **防御检测错误**: "无根子"标签泛滥，错误逻辑导致正常局面被标记为危险
- **影响范围**: 所有局面分析结果、AI点评、标签生成
- **归档状态**: 永久归档，禁止恢复使用

### 1.2 position_analysis_schema.py
- **文件大小**: 411 行
- **致命错误**:
  - **标签生成泛滥**: extract_retrieval_tags() 函数生成大量错误标签
  - **错误标签示例**: "无根子"、"马腿受堵"在正常开局中被错误标记
  - **数据结构污染**: 所有基于该Schema的分析结果均不可靠
- **影响范围**: 检索标签、AI讲解、知识图谱查询
- **归档状态**: 永久归档，禁止恢复使用

### 1.3 其他分析器文件
| 文件名 | 归档原因 | 备注 |
|--------|----------|------|
| board_structure_parser.py | 依赖错误Schema | 与position_analysis_schema耦合 |
| conflict_detector_v1.py | 基于错误分析结果 | 检测逻辑建立在错误数据上 |
| enhanced_piece_analyzer.py | 增强版错误分析 | 继承并放大了原分析器错误 |
| label_generator.py | 标签生成器 | 生成与事实不符的语义标签 |
| semantic_state_v1.py | 状态管理 | 管理的是错误状态 |

---

## 二、研究内容归档

### 2.1 reference/ 目录
- **内容**: NeurIPS论文相关研究代码 (searchless_chess)
- **归档原因**: 预研性质，与当前比赛目标无关
- **包含文件**:
  - searchless_chess/ (完整项目)
  - 论文: Amortized Planning with Large-Scale Transformers

### 2.2 docs/ 研究文档
| 文档名 | 归档原因 |
|--------|----------|
| TECH_RESEARCH.md | MoE预研、高级训练策略 |
| TRAINING_LOG.md | 训练实验记录 |
| contradiction_classifier_design.md | 矛盾分类器设计（未实现） |
| contradiction_classifier_v2.md | 矛盾分类器v2（未实现） |
| model_diagnosis_report.md | 模型诊断报告 |
| model_transformation_report.md | 模型转换报告 |
| integration_report.md | 集成报告 |
| explanation_experiment_report.json | 解释实验报告 |
| stability_test_report.json | 稳定性测试报告 |
| validation_report.json | 验证报告 |
| 2602.04447v1.pdf | NeurIPS相关论文 |
| NeurIPS-2024-amortized-planning*.pdf | NeurIPS论文 |
| UPDATE1.pdf | 更新文档 |
| 棋局特征提取与解析层深研报告*.pdf | 预研报告 |

---

## 三、核心资产保护清单（未归档）

以下资产**不受影响**，继续正常使用：

### 3.1 LangGraph Agent (core/agent/)
- graph.py - 工作流编排
- state.py - 状态定义
- nodes/ - 6个分析节点
- **状态**: 可用，不受影响

### 3.2 Neo4j知识图谱 (core/kg/)
- neo4j_kg.py - 知识图谱实现
- mock_kg.py - 模拟实现
- **状态**: 可用，不受影响

### 3.3 React前端 (frontend/)
- ChessBoard.tsx - 棋盘组件
- AnalysisPanel.tsx - 分析面板
- useGameStore.ts - 状态管理
- **状态**: 可用，不受影响

### 3.4 数据与模型 (data/)
- models/ - 已训练模型（5个）
- init_data/ - 原始对局数据（80万+）
- games/ - 游戏数据
- **状态**: 可用，不受影响

### 3.5 引擎封装 (core/engine/)
- pikafish_engine.py - Pikafish引擎封装
- mock_engine.py - 模拟引擎
- **状态**: 可用，不受影响

---

## 四、重构方向

### 4.1 新架构原则
1. **规则检查器**: 仅做合法性校验，不计算攻击/防御
2. **事实识别器**: 基于引擎真值(bestmove/score/pv)，不自研攻击计算
3. **禁止项**: 禁止生成"无根子"、"受阻"等衍生标签

### 4.2 设计规范文档
重构工作需遵循以下规范：
- `docs/03_DEVELOPMENT_GUIDE/03.1_RULE_ENGINE_SPEC.md` - 规则检查器规范
- `docs/03_DEVELOPMENT_GUIDE/03.2_FACT_EXTRACTOR_SPEC.md` - 事实识别器规范
- `docs/03_DEVELOPMENT_GUIDE/03.3_BUG_FIX_PLAN.md` - Bug修复方案

---

## 五、历史记录

### 5.1 错误影响统计
- **错误代码行数**: 约1200行（7个文件）
- **错误标签类型**: 12种错误标签
- **受影响API**: /api/position-analysis, /api/analyze-move
- **错误持续时间**: 约2个Sprint

### 5.2 关键教训
1. **不要自行实现攻击/防御计算** - 象棋规则复杂，容易出错
2. **不要生成无法验证的语义标签** - "无根子"等标签缺乏真值来源
3. **引擎真值是唯一可信来源** - bestmove/score/pv是客观事实

---

## 六、恢复策略

**警告**: 本归档目录下的代码**禁止直接恢复使用**。

如需参考旧代码逻辑：
1. 仅可作为"错误示例"参考
2. 任何恢复必须经过架构师审核
3. 必须配套完整的单元测试

---

**归档完成确认**: ✅ 2026-03-13  
**下次审查日期**: 项目重构完成后
