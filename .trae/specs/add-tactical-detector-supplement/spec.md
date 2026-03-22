# 战术标签检测器补充功能 Spec

## Why

现有战术标签检测器 (`tactical_detector.py`) 缺少部分经典杀法标签和局面语义层标签，无法为下游 `semantic_state` 提供完整的中间变量支持。需要新增 **15个战术/语义标签** 以完善检测体系。

## What Changes

### 第五层补充 — 标准杀法（新增 5 个）

| 标签名 | 中文名 |
|--------|--------|
| checkmate_horse_corner | 卧槽马 |
| checkmate_bare_king | 白脸将 |
| checkmate_double_cannon_battery | 重炮杀 |
| checkmate_sea_bottom_moon | 海底捞月 |
| checkmate_side_tiger | 侧面虎 |

### 第七层 — 局面语义层（新增 10 个）

| 标签名 | 中文名 | 层级 |
|--------|--------|------|
| phase_opening | 开局阶段 | 静态 |
| phase_middlegame | 中局阶段 | 静态 |
| phase_endgame | 残局阶段 | 静态 |
| king_safety_critical | 将帅危急 | 静态 |
| has_initiative | 握有主动权 | 静态 |
| is_forcing_move | 强制手段 | 动态 |
| horse_leg_blocked | 马脚被别 | 静态 |
| kings_face_to_face | 双将对面 | 静态 |
| cannon_battery | 重炮阵型 | 静态 |
| favorable_exchange | 有利兑换 | 静态 |

## Impact

- **Affected specs**: 战术标签检测器、Evidence Map生成、semantic_state
- **Affected code**: 
  - `core/rules/tactical_detector.py`
  - `core/rules/tactical_tags.py`

## ADDED Requirements

### Requirement: 标准杀法标签扩展

系统应检测5种新增的经典杀法模式。

#### Scenario: 卧槽马检测
- **WHEN** 己方马盘踞在敌方九宫格外攻击位，直接将死对方将/帅
- **THEN** 应触发 `checkmate_horse_corner` 标签

#### Scenario: 白脸将检测
- **WHEN** 双方将/帅同列且无阻挡，形成对面将死
- **THEN** 应触发 `checkmate_bare_king` 标签

#### Scenario: 重炮杀检测
- **WHEN** 己方一门炮以另一门己方炮为炮架，攻击敌方将/帅形成将死
- **THEN** 应触发 `checkmate_double_cannon_battery` 标签

#### Scenario: 海底捞月检测
- **WHEN** 己方车深入敌方底线，在底线将死对方将/帅
- **THEN** 应触发 `checkmate_sea_bottom_moon` 标签

#### Scenario: 侧面虎检测
- **WHEN** 己方车与敌方将/帅同行，横向将死
- **THEN** 应触发 `checkmate_side_tiger` 标签

### Requirement: 局面阶段检测

系统应根据棋子数量判断当前局面阶段。

#### Scenario: 开局阶段
- **WHEN** 棋盘上棋子总数 ≥ 28
- **THEN** 应触发 `phase_opening` 标签

#### Scenario: 中局阶段
- **WHEN** 棋盘上棋子总数在 15-27 之间
- **THEN** 应触发 `phase_middlegame` 标签

#### Scenario: 残局阶段
- **WHEN** 棋盘上棋子总数 ≤ 14
- **THEN** 应触发 `phase_endgame` 标签

### Requirement: 将帅安全检测

系统应评估将/帅的安全程度。

#### Scenario: 将帅危急
- **WHEN** 将/帅周围防守子力严重不足，且存在敌方进攻威胁
- **THEN** 应触发 `king_safety_critical` 标签

### Requirement: 主动权检测

系统应判断当前行棋方是否握有主动权。

#### Scenario: 握有主动权
- **WHEN** 当前行棋方拥有明显更多的强制手段（将军威胁、捉无根子）
- **THEN** 应触发 `has_initiative` 标签

### Requirement: 强制手段检测（动态）

系统应检测某步走法是否为强制手段。

#### Scenario: 强制手段
- **WHEN** 某步走法是将军、捉对方无根子、或直接威胁将死
- **THEN** 应触发 `is_forcing_move` 标签

### Requirement: 马脚被别检测

系统应检测马的行动受限情况。

#### Scenario: 马脚被别
- **WHEN** 马的某个方向马脚被棋子占据
- **THEN** 应触发 `horse_leg_blocked` 标签

### Requirement: 双将对面检测

系统应检测双将对面位置特征。

#### Scenario: 双将对面
- **WHEN** 双方将/帅处于同一列且两将之间无任何棋子
- **THEN** 应触发 `kings_face_to_face` 标签

### Requirement: 重炮阵型检测

系统应检测重炮阵型的存在。

#### Scenario: 重炮阵型
- **WHEN** 同色两门炮处于同一行或同一列，且两炮之间无任何棋子
- **THEN** 应触发 `cannon_battery` 标签

### Requirement: 有利兑换检测

系统应检测有利兑换机会。

#### Scenario: 有利兑换
- **WHEN** 己方可以吃掉对方价值更高的棋子，或免费吃掉对方无保护棋子
- **THEN** 应触发 `favorable_exchange` 标签

### Requirement: 标签来源标记

所有新增标签均为规则可判定，来源标记为 RULES。

#### Scenario: Evidence Map来源
- **WHEN** 生成 Evidence Map
- **THEN** 所有新增标签的 evidence_source 应为 "RULES"

## MODIFIED Requirements

### Requirement: 检测器入口函数扩展

系统应在主检测入口中调用新增的检测函数。

原实现：仅调用 v1.0 的六层检测
修正后：追加调用 v1.1 补充的标准杀法和语义层检测

## REMOVED Requirements

无移除的需求。
