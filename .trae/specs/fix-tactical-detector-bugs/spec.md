# 战术标签检测器错误修复 Spec

## Why

战术标签检测器 (`tactical_detector.py`) 存在多处逻辑错误和命名问题，会导致检测结果不准确或误导下游模块。经逐行审查验证，共发现 **9项问题**（严重错误4项、中等缺陷3项、轻微问题2项）。

## What Changes

### 严重错误（必须修复）

- **E-01**: 文档标签总数声称15个，实际为16个
- **E-02**: 双车错标签名 `checkmate_double_cannon` 与实现不符（cannon=炮，实际检测双车）
- **E-03**: 马后炮炮架检测用 `any()` 只验证>=1个子，应验证恰好1个子
- **E-04**: 牵制检测对车和炮使用相同逻辑，未正确区分规则差异

### 中等缺陷（建议修复）

- **E-06**: 闪将检测未绑定具体是哪颗棋子造成将军，可能误报
- **E-07**: 炮串打炮架后遇己方棋子未停止扫描，导致穿透误判
- **E-08**: 铁门栓只检测车与将同列无阻挡，未验证是否真正将死

### 轻微问题（可选修复）

- **E-09**: 抽将攻击目标列表未过滤敌方将/帅本身
- **E-10**: 攻无根代码注释步骤编号与检测思路描述不一致

### 标签定义修正

- `cannon_has_platform` 描述从"己方棋子"改为"任意棋子"（炮架颜色无关）

## Impact

- **Affected specs**: 战术标签检测器、Evidence Map生成
- **Affected code**: 
  - `core/rules/tactical_detector.py`
  - `core/rules/tactical_tags.py`
  - `docs/03_DEVELOPMENT_GUIDE/03.4_TACTICAL_DETECTOR_ALGORITHM.md`

## ADDED Requirements

### Requirement: 标签命名一致性

系统应确保标签名称与实际检测内容一致。

#### Scenario: 双车错标签修正
- **WHEN** 检测双车交替将军将死
- **THEN** 标签名应为 `checkmate_double_rook` 而非 `checkmate_double_cannon`

### Requirement: 炮架检测精确性

系统应正确验证炮架数量恰好为1个。

#### Scenario: 马后炮炮架检测
- **WHEN** 检测马后炮杀法
- **THEN** 应验证炮与将/帅之间恰好有1个棋子作为炮架

### Requirement: 牵制检测规则区分

系统应根据牵制方棋子类型（车/炮）使用不同的检测逻辑。

#### Scenario: 车牵制检测
- **WHEN** 车牵制己方棋子
- **THEN** 连线上必须只有1个己方棋子且无其他任何棋子

#### Scenario: 炮牵制检测
- **WHEN** 炮牵制己方棋子
- **THEN** 炮与将之间恰好有1个己方棋子作为炮架

### Requirement: 铁门栓将死验证

系统应在铁门栓检测中验证敌方确实处于将死状态。

#### Scenario: 铁门栓完整检测
- **WHEN** 检测铁门栓杀法
- **THEN** 应同时验证：车与将同列、无阻挡、敌方被将军、敌方无合法走法

### Requirement: 炮串打穿透停止

系统应在炮串打检测中正确处理炮架后遇到的棋子。

#### Scenario: 炮串打目标检测
- **WHEN** 炮架后遇到任何棋子（敌方或己方）
- **THEN** 应立即停止扫描，不应穿透继续寻找目标

## MODIFIED Requirements

### Requirement: 闪将检测归因精确性

系统应在闪将检测中精确绑定造成将军的后方棋子。

原实现：只判断走子后是否将军，未验证是哪个后方棋子造成
修正后：验证后方棋子的攻击范围是否包含敌方将/帅位置

## REMOVED Requirements

无移除的需求。
