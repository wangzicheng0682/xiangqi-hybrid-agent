# 标签体系参考文档

> 45个战术标签的完整定义和检测算法

**版本**: v1.0
**最后更新**: 2026-03-14

---

## 标签体系概览

### 九大层级

| 层级 | 名称 | 标签数 | 优先级 | 用途 |
|------|------|--------|--------|------|
| 1 | 将杀困毙层 | 3 | 最高 | 检测将军、将死、困毙 |
| 2 | 捉子层 | 3 | 高 | 检测攻击无根子、互吃 |
| 3 | 闪击抽将层 | 3 | 高 | 检测闪将、抽将、闪击 |
| 4 | 牵制串打层 | 2 | 中 | 检测牵制、炮串打 |
| 5 | 标准杀法层 | 8 | 中 | 检测经典杀法模式 |
| 6 | 子力状态层 | 2 | 基础 | 检测无根子、炮架 |
| 7 | 走法质量层 | 6 | 高 | 评估走法质量 |
| 8 | 战略评估层 | 5 | 中 | 局面战略分析 |
| 9 | 引擎对齐层 | 3 | 中 | 解释引擎推荐 |

---

## 第一层：将杀困毙层

### is_check
- **描述**: 一方将/帅处于对方棋子的合法攻击范围内
- **检测逻辑**: 遍历对方所有棋子，检查是否攻击到将/帅位置
- **绑定棋子**: 攻击方棋子 + 被将军的将/帅
- **代码位置**: `core/rules/tactical_detector.py::_detect_check_mate_stalemate()`

### is_checkmate
- **描述**: 一方将/帅被将军，且无任何合法解将手段
- **检测逻辑**: is_check=True 且 合法走法列表为空
- **绑定棋子**: 将/帅
- **代码位置**: `core/rules/tactical_detector.py::_detect_check_mate_stalemate()`

### is_stalemate
- **描述**: 一方行棋时无任何合法着法，且未被将军
- **检测逻辑**: is_check=False 且 合法走法列表为空
- **绑定棋子**: 行棋方将/帅
- **代码位置**: `core/rules/tactical_detector.py::_detect_check_mate_stalemate()`

---

## 第二层：捉子层

### is_attack_unprotected
- **描述**: 一方棋子攻击对方无保护棋子
- **检测逻辑**:
  1. 遍历己方每个棋子的攻击目标
  2. 检查目标是否为对方棋子
  3. 检查目标是否无己方保护（_is_protected返回False）
- **绑定棋子**: 攻击方 + 被攻击的无根子
- **代码位置**: `core/rules/tactical_detector.py::_detect_capture()`

### is_mutual_attack
- **描述**: 红黑双方棋子互相攻击，形成互捉
- **检测逻辑**: A攻击B 且 B攻击A
- **绑定棋子**: 双方互捉的棋子
- **代码位置**: `core/rules/tactical_detector.py::_detect_capture()`

### is_attack_king_adjacent
- **描述**: 棋子攻击将/帅相邻空位（将军前兆）
- **检测逻辑**: 检查攻击范围是否包含将/帅九宫内的相邻空位
- **绑定棋子**: 攻击方棋子 + 将/帅
- **代码位置**: `core/rules/tactical_detector.py::_detect_capture()`

---

## 第三层：闪击抽将层

### is_discovered_check
- **描述**: 移开己方棋子后，露出后方远程棋子将军
- **检测逻辑**:
  1. 解析走法，获取移动的棋子
  2. 检查走法后是否有新的将军
  3. 确认将军来自未移动的棋子
- **绑定棋子**: 移动的棋子 + 闪将的棋子
- **代码位置**: `core/rules/tactical_detector.py::_detect_discovered_attack()`

### is_double_attack_with_check
- **描述**: 将军的同时，另一棋子攻击对方无根子/关键子
- **检测逻辑**:
  1. 走法后is_check=True
  2. 同时存在其他攻击无根子的情况
- **绑定棋子**: 将军棋子 + 攻击无根子的棋子
- **代码位置**: `core/rules/tactical_detector.py::_detect_double_attack_with_check()`

### is_discovered_attack
- **描述**: 移开己方棋子后，露出后方棋子攻击对方无根子
- **检测逻辑**: 类似闪将，但目标是无根子而非将/帅
- **绑定棋子**: 移动的棋子 + 闪击的棋子 + 被攻击的棋子
- **代码位置**: `core/rules/tactical_detector.py::_detect_discovered_attack()`

---

## 第四层：牵制串打层

### is_pinned
- **描述**: 一方棋子被对方车/炮牵制，移动后会导致己方将/帅被将军
- **检测逻辑**:
  1. 检查是否存在将/帅-己方棋子-对方远程棋子共线
  2. 中间无其他棋子阻挡
- **绑定棋子**: 被牵制的棋子 + 牵制方棋子
- **代码位置**: `core/rules/tactical_detector.py::_detect_pin_skewer()`

### is_cannon_double_attack
- **描述**: 炮隔一个炮架同时攻击两个对方棋子
- **检测逻辑**:
  1. 找到炮和炮架
  2. 检查炮架另一侧是否有对方棋子
- **绑定棋子**: 炮 + 炮架 + 两个被攻击棋子
- **代码位置**: `core/rules/tactical_detector.py::_detect_pin_skewer()`

---

## 第五层：标准杀法层

### checkmate_horse_back_cannon
- **描述**: 马后炮 - 马和炮配合将死对方
- **检测逻辑**: 马控制将的逃跑路线，炮在马后将军
- **绑定棋子**: 马 + 炮 + 将/帅
- **代码位置**: `core/rules/tactical_detector.py::_detect_horse_back_cannon()`

### checkmate_iron_gate
- **描述**: 铁门栓 - 车在将/帅门线上配合其他子将死
- **检测逻辑**: 车在将门线（中路或肋道），配合其他子完成将死
- **绑定棋子**: 车 + 配合子 + 将/帅
- **代码位置**: `core/rules/tactical_detector.py::_detect_iron_gate()`

### checkmate_double_rook
- **描述**: 双车错 - 双车交替将军将死
- **检测逻辑**: 双车连续将军，对方无法解将
- **绑定棋子**: 双车 + 将/帅
- **代码位置**: `core/rules/tactical_detector.py::_detect_double_rook()`

### checkmate_horse_corner
- **描述**: 卧槽马 - 马盘踞在敌方九宫格外攻击位
- **检测逻辑**: 马在九宫角位将军，且对方无法解将
- **绑定棋子**: 马 + 将/帅
- **代码位置**: `core/rules/tactical_detector.py::_detect_horse_corner()`

### checkmate_bare_king
- **描述**: 白脸将 - 利用双将不能对面规则
- **检测逻辑**: 移开遮挡棋子后两将同列无阻挡
- **绑定棋子**: 移动的棋子 + 双方将/帅
- **代码位置**: `core/rules/tactical_detector.py::_detect_bare_king()`

### checkmate_double_cannon_battery
- **描述**: 重炮杀 - 一门炮以另一门炮为炮架
- **检测逻辑**: 前炮将军，后炮作为炮架，对方无法躲避
- **绑定棋子**: 双炮 + 将/帅
- **代码位置**: `core/rules/tactical_detector.py::_detect_double_cannon_battery_checkmate()`

### checkmate_sea_bottom_moon
- **描述**: 海底捞月 - 车深入敌方底线将死
- **检测逻辑**: 车在底线将军，配合其他子完成将死
- **绑定棋子**: 车 + 将/帅
- **代码位置**: `core/rules/tactical_detector.py::_detect_sea_bottom_moon()`

### checkmate_side_tiger
- **描述**: 侧面虎 - 车与将/帅同行横向将死
- **检测逻辑**: 车和将/帅在同一行，车横向将军
- **绑定棋子**: 车 + 将/帅
- **代码位置**: `core/rules/tactical_detector.py::_detect_side_tiger()`

---

## 第六层：子力状态层

### piece_is_unprotected
- **描述**: 某个棋子无任何己方棋子保护
- **检测逻辑**: 遍历每个棋子，检查_is_protected()
- **绑定棋子**: 无根子
- **代码位置**: `core/rules/tactical_detector.py::_detect_piece_status()`

### cannon_has_platform
- **描述**: 炮有可用的炮架
- **检测逻辑**: 炮的攻击范围内存在可作为炮架的棋子
- **绑定棋子**: 炮 + 炮架
- **代码位置**: `core/rules/tactical_detector.py::_detect_piece_status()`

---

## 第七层：走法质量层（动态检测）

### move_is_blunder
- **描述**: 严重失误 - 走法导致丢子（价值≥300分）或被将死
- **检测逻辑**:
  1. 执行走法前后对比
  2. 计算子力损失
  3. 检查是否被将死
- **绑定棋子**: 移动的棋子
- **代码位置**: `core/rules/tactical_detector.py::_detect_move_blunder()`

### move_is_capture
- **描述**: 吃子走法
- **检测逻辑**: 走法目标位置有对方棋子
- **绑定棋子**: 移动棋子 + 被吃棋子
- **代码位置**: `core/rules/tactical_detector.py::_detect_move_capture()`

### move_gives_check
- **描述**: 将军走法
- **检测逻辑**: 走法后对方被将军
- **绑定棋子**: 移动棋子
- **代码位置**: `core/rules/tactical_detector.py::_detect_move_check()`

### move_defends_piece
- **描述**: 防守走法 - 保护了己方原本无根的棋子
- **检测逻辑**: 走法后某子从无根变有根
- **绑定棋子**: 移动棋子 + 被保护的棋子
- **代码位置**: `core/rules/tactical_detector.py::_detect_move_defense()`

### move_escapes_threat
- **描述**: 逃脱走法 - 走法前被攻击，走法后安全
- **检测逻辑**: 走法前is_piece_under_attack=True，走法后=False
- **绑定棋子**: 移动棋子
- **代码位置**: `core/rules/tactical_detector.py::_detect_move_escape()`

### move_improves_position
- **描述**: 改善位置 - 走法后活跃度提升
- **检测逻辑**: 走法后控制点数增加
- **绑定棋子**: 移动棋子
- **代码位置**: `core/rules/tactical_detector.py::_detect_move_improvement()`

---

## 第八层：战略评估层

### controls_open_file
- **描述**: 控制开放线 - 车在某列无阻挡
- **检测逻辑**: 检查车所在列是否有其他子阻挡
- **绑定棋子**: 车
- **代码位置**: `core/rules/tactical_detector.py::_detect_open_file_control()`

### has_active_pieces
- **描述**: 子力活跃 - 多个子控制多个关键点
- **检测逻辑**: 统计控制点数≥3的棋子数量
- **绑定棋子**: 活跃子列表
- **代码位置**: `core/rules/tactical_detector.py::_detect_active_pieces()`

### piece_coordination
- **描述**: 子力协同 - 多个子攻击同一区域
- **检测逻辑**: 检查多个子是否有共同的攻击目标
- **绑定棋子**: 协同的棋子
- **代码位置**: `core/rules/tactical_detector.py::_detect_piece_coordination()`

### king_safety_good
- **描述**: 将帅安全 - 周围有防守子，无直接威胁
- **检测逻辑**: 将/帅周围防守子数≥2且无威胁
- **绑定棋子**: 将/帅
- **代码位置**: `core/rules/tactical_detector.py::_detect_king_safety_good()`

### has_space_advantage
- **描述**: 空间优势 - 己方控制的格子数多于对方
- **检测逻辑**: 统计双方控制点数对比
- **绑定棋子**: 无
- **代码位置**: `core/rules/tactical_detector.py::_detect_space_advantage()`

---

## 第九层：引擎对齐层

### engine_only_move
- **描述**: 唯一不输棋 - 引擎分析显示其他走法评估值大幅下降
- **检测逻辑**: 对比引擎top候选走法评估值差距
- **绑定棋子**: 推荐走法涉及的棋子
- **数据来源**: Pikafish引擎

### engine_best_by_margin
- **描述**: 明显最佳 - 这步棋比第二选择高100分以上
- **检测逻辑**: 最佳走法与第二选择评估值差距>100cp
- **绑定棋子**: 最佳走法涉及的棋子
- **数据来源**: Pikafish引擎

### engine_forcing_sequence
- **描述**: 强制序列 - 走法后形成强制应着序列
- **检测逻辑**: 分析后续N步是否都是强制应着
- **绑定棋子**: 序列涉及的棋子
- **数据来源**: Pikafish引擎

---

## 棋子绑定格式

### 标准格式
```
{颜色}{兵种}-({x},{y})
```

### 示例
- `红车-(5,8)` - 红方车，位于第5列第8行
- `黑马-(7,6)` - 黑方马，位于第7列第6行
- `红帅-(5,1)` - 红方帅，位于第5列第1行

### 坐标说明
- x: 1-9，从左到右
- y: 1-10，从红方底线到黑方底线

---

## 检测器使用示例

```python
from core.rules.tactical_detector import TacticalDetector

detector = TacticalDetector()
fen = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"

# 静态检测
result = detector.detect_static(fen)
for tag in result.get_detected_tags():
    print(f"{tag.tag.name}: {tag.bind_pieces}")

# 动态检测（走法质量）
move_result = detector.detect_move_quality(fen, "h2e2")
for tag in move_result:
    if tag.detected:
        print(f"{tag.tag.name}: {tag.metadata}")
```
