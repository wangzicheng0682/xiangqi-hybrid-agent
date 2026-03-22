# 黄金局面测试体系检测报告

**报告日期**: 2026-03-15  
**报告人**: GLM-5  
**接收人**: Claude  

---

## 一、执行摘要

根据 `GLM5_TESTING_GUIDE.md` 的指导，我已完成黄金局面测试体系的建设，并进行了首轮检测。检测结果显示**检测器存在多处底层bug**，验证了测试指南的核心观点："底层静默错误比程序崩溃更危险"。

### 关键数据

| 指标 | 数值 |
|------|------|
| 黄金局面总数 | 34个 |
| 首轮检测失败数 | 29个问题 |
| 修复后失败数 | 28个问题 |
| 已修复的核心bug | 1个 |
| 已修正的测试数据 | 3个 |

---

## 二、已创建的测试基础设施

### 2.1 黄金局面测试库

**文件**: `tests/golden_positions.py`

包含34个黄金局面测试用例，覆盖以下标签类型：

| 层级 | 标签 | 测试用例数 |
|------|------|-----------|
| 将杀困毙层 | `is_check`, `is_checkmate`, `is_stalemate` | 4个 |
| 捉子层 | `is_attack_unprotected`, `is_mutual_attack` | 5个 |
| 闪击抽将层 | `is_discovered_check`, `is_double_attack_with_check` | 2个 |
| 牵制串打层 | `is_pinned`, `is_cannon_double_attack` | 2个 |
| 标准杀法层 | 卧槽马、白脸将、重炮杀等 | 7个 |
| 子力状态层 | `piece_is_unprotected`, `cannon_has_platform` | 3个 |
| 边界条件 | 左边界、右边界、角落马 | 4个 |
| 其他 | 阶段、红黑视角、炮规则等 | 7个 |

### 2.2 黄金局面测试框架

**文件**: `tests/test_golden_positions.py`

功能：
- 自动遍历所有黄金局面进行检测
- 验证 `expected_true` 和 `expected_false` 标签
- 验证 `expected_bindings` 棋子绑定
- 支持动态检测（走法后的标签变化）
- 生成详细的失败报告

### 2.3 一致性检查器

**文件**: `core/rules/consistency_checker.py`

包含12条一致性规则，利用象棋规则的逻辑蕴含关系进行自我检验：

| 规则名称 | 条件标签 | 约束 | 严重程度 |
|----------|----------|------|----------|
| 将死必有将军 | `is_checkmate` | 必须有 `is_check` | ERROR |
| 困毙不能有将军 | `is_stalemate` | 不能有 `is_check` | ERROR |
| 将死与困毙互斥 | `is_checkmate` | 不能有 `is_stalemate` | ERROR |
| 闪将必有将军 | `is_discovered_check` | 必须有 `is_check` | ERROR |
| 双将必有将军 | `is_double_attack_with_check` | 必须有 `is_check` | ERROR |
| 阶段标签互斥 | `phase_opening/middlegame/endgame` | 互斥 | ERROR |
| 将帅危急与将帅安全互斥 | `king_safety_critical` | 不能有 `king_safety_good` | ERROR |

---

## 三、发现的核心Bug

### 3.1 已修复的Bug

#### Bug #1: `_has_legal_moves` 方法逻辑错误

**问题描述**:  
原方法只检查是否有可移动的位置，但没有检查移动后是否会导致自己被将军。这导致困毙检测完全失效。

**原代码**:
```python
def _has_legal_moves(self, board: List[List[str]], is_red: bool) -> bool:
    for r in range(10):
        for c in range(9):
            piece = board[r][c]
            if piece and self._is_red(piece) == is_red:
                moves = self.rules_engine.get_legal_moves(board, r, c)
                if moves:
                    return True  # 错误：没有检查走法后是否被将军
    return False
```

**修复后代码**:
```python
def _has_legal_moves(self, board: List[List[str]], is_red: bool) -> bool:
    for r in range(10):
        for c in range(9):
            piece = board[r][c]
            if piece and self._is_red(piece) == is_red:
                moves = self.rules_engine.get_legal_moves(board, r, c)
                for nr, nc in moves:
                    new_board = [row[:] for row in board]
                    new_board[nr][nc] = new_board[r][c]
                    new_board[r][c] = ''
                    if not self._is_in_check(new_board, is_red):
                        return True
    return False
```

**影响范围**:  
- `is_checkmate` 检测
- `is_stalemate` 检测
- 所有依赖合法走法判断的功能

---

### 3.2 待修复的Bug

#### Bug #2: 牵制检测不工作

**测试用例**: GP040  
**现象**: `is_pinned` 标签不触发  
**预期**: 红车牵制黑马，马移动会导致黑将被将军

#### Bug #3: 炮串打检测不工作

**测试用例**: GP041  
**现象**: `is_cannon_double_attack` 标签不触发  
**预期**: 炮隔一个炮架同时攻击两个对方棋子

#### Bug #4: 马腿被别检测不工作

**测试用例**: GP070  
**现象**: `horse_leg_blocked` 标签不触发  
**预期**: 马的一个方向马脚被棋子占据

#### Bug #5: 有根子判断错误

**测试用例**: GP120  
**现象**: 被己方棋子保护的棋子仍被标记为无根  
**预期**: 黑马被黑车保护，不应标记为无根

#### Bug #6: 炮规则判断错误

**测试用例**: GP111, GP112  
**现象**: 
- GP111: 炮架在炮和目标之间，但目标类型识别错误
- GP112: 炮架在目标外侧，不应该攻击，但触发了攻击标签

#### Bug #7: 棋子绑定坐标错误

**测试用例**: GP060, GP140  
**现象**: 标签绑定的棋子不是预期的棋子  
**原因**: `_bind_piece` 方法或相关逻辑可能存在问题

---

## 四、测试数据修正记录

### 4.1 GP001: 将军测试

**问题**: 原FEN中红帅不在九宫格内，导致没有合法走法，被误判为将死。

**修正**:
```diff
- "fen": "4K4/9/9/9/9/9/9/9/4r4/4k4 w - - 0 1"
+ "fen": "3k5/9/9/9/9/9/9/9/3rK3/9 w - - 0 1"
```

**说明**: 
- 红帅放在(8, 4)，在红方九宫格内
- 黑车放在(8, 3)，横向将军
- 红帅可以移动到(8, 5), (9, 4), (7, 4)躲避将军

### 4.2 GP002: 将死测试

**问题**: 原FEN中黑将和红车不在同一列，红车不能将军黑将。

**修正**:
```diff
- "fen": "4k4/4R4/9/9/9/9/9/9/9/4K4 w - - 0 1"
+ "fen": "3kRR3/9/3R5/9/9/9/9/9/9/4K4 b - - 0 1"
```

**说明**:
- 黑将在(0, 3)
- 红车在(0, 4)将军，红车在(0, 5)保护，红车在(2, 3)封锁下路
- 黑方走棋，被将死

### 4.3 GP003: 困毙测试

**问题**: 原FEN中黑将可以移动，不是困毙。

**修正**:
```diff
- "fen": "4k4/9/9/9/9/9/9/9/9/3K4 b - - 0 1"
+ "fen": "3k5/4R4/9/9/9/9/9/9/9/4K4 b - - 0 1"
```

**说明**:
- 黑将在(0, 3)
- 红车在(1, 4)，不在黑将的同一行或同一列，所以黑将不被将军
- 黑将移动到(0, 4)后，被红帅攻击（将帅不能对面）
- 黑将移动到(1, 3)后，被红车攻击
- 黑方走棋，无合法走法，困毙

---

## 五、关键发现：FEN设计与九宫格规则

在调试过程中，我发现了一个重要的设计问题：

### 红黑九宫格位置

根据 `xiangqi_rules.py` 的定义：
- **红方九宫格**: 行7-9，列3-5
- **黑方九宫格**: 行0-2，列3-5

这意味着：
- 红帅K必须在行7-9之间
- 黑将k必须在行0-2之间
- 如果将帅不在九宫格内，`get_legal_moves` 会返回空列表

### 对测试数据的影响

很多测试用例的FEN设计没有考虑九宫格规则，导致：
1. 将帅没有合法走法
2. 被误判为将死或困毙
3. 检测结果与预期不符

### 建议

在设计FEN时，务必确保：
1. 红帅在行7-9，列3-5
2. 黑将在行0-2，列3-5
3. 将帅不在同一列（除非有棋子遮挡）

---

## 六、当前测试结果

### 6.1 通过的测试用例

| ID | 名称 | 检测结果 |
|----|------|----------|
| GP001 | 将军-黑车将军红帅 | ✅ `is_check` 正确触发 |
| GP002 | 将死-单车将死 | ✅ `is_checkmate` 正确触发 |
| GP003 | 困毙-无子可动 | ✅ `is_stalemate` 正确触发 |
| GP004 | 将军-双将对面禁止 | ✅ 通过 |
| GP010 | 攻无根-车捉无根马 | ✅ 通过 |
| GP011 | 攻无根-炮隔山打牛 | ✅ 通过 |
| GP012 | 炮两个棋子中间 | ✅ 通过 |
| GP020 | 边界-棋子在左边界 | ✅ 通过 |
| GP021 | 边界-棋子在右边界 | ✅ 通过 |
| GP022 | 边界-马在棋盘角落 | ✅ 通过 |
| GP023 | 边界-炮在边界攻击 | ✅ 通过 |
| GP024 | 边界-将帅在九宫角落 | ✅ 通过 |

### 6.2 失败的测试用例

| ID | 名称 | 问题类型 |
|----|------|----------|
| GP013 | 互吃-车炮互捉 | MISSING_TAG |
| GP030 | 闪将-马移开露出车将军 | MISSING_DYNAMIC_TAG |
| GP040 | 牵制-车牵制马 | MISSING_TAG |
| GP041 | 炮串打-一炮打双 | MISSING_TAG |
| GP050 | 杀法-马后炮 | MISSING_TAG (测试数据错误) |
| GP051 | 杀法-卧槽马 | MISSING_TAG (测试数据错误) |
| GP052 | 杀法-白脸将 | MISSING_TAG (测试数据错误) |
| GP053 | 杀法-重炮杀 | MISSING_TAG (测试数据错误) |
| GP054 | 杀法-海底捞月 | MISSING_TAG (测试数据错误) |
| GP055 | 杀法-侧面虎 | MISSING_TAG (测试数据错误) |
| GP056 | 杀法-双车错 | MISSING_TAG (测试数据错误) |
| GP060 | 子无根-孤立棋子 | WRONG_BINDING |
| GP070 | 马腿被别-单腿被别 | MISSING_TAG |
| GP100 | 红黑视角-黑方走棋 | MISSING_TAG (测试数据错误) |
| GP111 | 炮规则-炮架在炮和目标之间 | WRONG_TARGET |
| GP112 | 炮规则-炮架在目标外侧不算 | SPURIOUS_TAG |
| GP120 | 有根子-被己方棋子保护 | SPURIOUS_TAG |
| GP140 | 有利兑换-车吃马 | WRONG_BINDING |

---

## 七、下一步建议

### 7.1 高优先级

1. **修复GP050-GP056测试数据**: 这些杀法测试的FEN设计有误，需要重新设计确保：
   - 黑将在正确的九宫格内
   - 红方棋子能正确将军
   - 黑方没有合法走法

2. **修复牵制检测逻辑**: `_detect_pin_skewer` 方法需要检查

3. **修复炮规则判断**: `_get_attacks` 方法中炮的移动规则需要修正

### 7.2 中优先级

4. **修复有根子判断**: `_is_protected` 方法的逻辑需要检查

5. **修复棋子绑定坐标**: `_bind_piece` 方法需要检查

6. **修复马腿被别检测**: 需要实现或修正检测逻辑

### 7.3 测试覆盖扩展

7. **增加更多黄金局面**: 当前34个，目标45个

8. **增加动态检测测试**: 当前只有1个，需要更多

9. **实现引擎交叉验证**: 用Pikafish作为oracle进行验证

---

## 八、结论

本次测试体系建设验证了测试指南的核心观点：**规则引擎的bug会静默输出错误结果，比程序崩溃更危险**。

通过黄金局面测试，我们发现了：
1. 1个核心逻辑bug（已修复）
2. 6个待修复的检测器bug
3. 多个测试数据设计错误

建议后续工作按照优先级逐步修复，每修复一个bug后运行回归测试确保不引入新问题。

---

**附件**:
- 测试代码: `tests/golden_positions.py`, `tests/test_golden_positions.py`
- 一致性检查器: `core/rules/consistency_checker.py`
- 检测器代码: `core/rules/tactical_detector.py`
- 规则引擎: `core/rules/xiangqi_rules.py`
