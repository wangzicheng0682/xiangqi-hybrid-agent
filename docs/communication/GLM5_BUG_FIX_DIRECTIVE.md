# 致 GLM5：底层 Bug 修复作战指令
## 基于测试报告的分步修复计划

**写给**：GLM5  
**优先级**：最高，阻塞其他所有开发  
**时间目标**：3天内将失败数从28降到0  
**核心原则**：一次只修一个根本原因，修完立刻回归测试，确认数字下降再继续

---

## 写在最前面

你的测试报告写得非常好。一天内建立34个测试用例、发现核心bug、修复并输出结构化报告——这是正确的工程做法。

现在我帮你把28个问题整理成5个根本原因，按顺序告诉你怎么修。不要同时开多条线，一件事做完，跑测试，看数字下降，再做下一件。

---

## 第一步：今天上午（2小时）— 修测试数据，不碰检测器

### 为什么先做这个

GP050-GP056、GP100 这8个失败，**不是检测器的问题，是测试数据的FEN写错了**。将帅没有在合法的九宫格位置，导致没有合法走法，被误判。

修这8个FEN，不改任何检测器代码，失败数会从28直接降到约20。先让考卷正确，再测真实能力。

### 九宫格规则（必须牢记）

```
红方九宫格：行 7-9，列 3-5   → 红帅 K 必须在这个范围内
黑方九宫格：行 0-2，列 3-5   → 黑将 k 必须在这个范围内
将帅不能在同一列直视（中间没有棋子时非法）
```

### GP050-GP056 杀法局面 FEN 重新设计原则

每个杀法局面的FEN必须满足：

```
条件1：黑将在行0-2，列3-5的九宫格内（通常放在 (0,3) 或 (0,4)）
条件2：红方棋子构成正确的将军（黑将当前被将）
条件3：黑方确实没有任何合法走法（将死，不是困毙）
条件4：红帅在行7-9，列3-5内（通常放在 (9,4)）
```

**逐个修复指导：**

#### GP050 马后炮将死

马后炮的标准形态：黑将在角落，红马控制逃跑格，红炮将军且无法阻挡。

```python
# 参考FEN设计
# 黑将在(0,3)，红炮在(0,7)将军，红马在(2,4)控制(0,3)周边逃跑格
# 验证：黑将能走哪里？每个候选格都被攻击或出九宫
"fen": "3k5/9/4N4/9/9/9/9/9/9/3K1C3 b - - 0 1"
# 注意：这只是示意，你需要验证黑将真的无路可走
# 建议：用规则引擎的 get_legal_moves 验证黑将的合法走法为空
```

#### GP051-GP056 其他杀法

每个杀法都用同样的方法：

```python
# 设计步骤
# 1. 确定杀法的核心形态（哪些棋子在哪里）
# 2. 把黑将放在 (0,3) 或 (0,4)
# 3. 放置红方关键棋子构成将军
# 4. 用代码验证：
test_board = fen_to_board(your_fen)
legal_moves = rules_engine.get_legal_moves_for_side(test_board, is_red=False)
assert len(legal_moves) == 0, f"黑方还有 {len(legal_moves)} 步合法走法，不是将死"
assert detector.detect(your_fen)["facts_rules"] 包含 is_checkmate
```

#### GP100 红黑视角测试

这个测试是验证黑方走棋时的标签检测。确保FEN里的走棋方标记是 `b`（黑方），不是 `w`。

```python
# FEN的第二个字段表示走棋方
# "...fen... w ..." 表示红方走
# "...fen... b ..." 表示黑方走
# GP100 应该用 b，让黑方来走
```

### 完成后

```bash
pytest tests/test_golden_positions.py -v
```

看着失败数从28降到约20，记录下来。

---

## 第二步：今天下午（3小时）— 修炮的攻击规则

### 问题定位

GP112 出现了 `SPURIOUS_TAG`：炮架在目标外侧，不应该攻击，但触发了攻击标签。

这是最经典的炮规则bug：把"至少一个棋子在中间"写成了"恰好一个棋子在中间"。

### 找到问题代码

在 `core/rules/tactical_detector.py` 或 `core/rules/xiangqi_rules.py` 中，找到炮的攻击范围计算逻辑。

通常长这样（错误版本）：

```python
# 错误版本——这会让炮打穿多个棋子
def get_cannon_attacks(board, r, c):
    attacks = []
    for direction in [(0,1),(0,-1),(1,0),(-1,0)]:
        dr, dc = direction
        platform_found = False  # 找到炮架了吗
        nr, nc = r + dr, c + dc
        while 0 <= nr < 10 and 0 <= nc < 9:
            piece = board[nr][nc]
            if piece:
                if platform_found:
                    attacks.append((nr, nc))  # 错误：没有break，会继续找
                    # 应该在这里break
                else:
                    platform_found = True
            nr += dr
            nc += dc
    return attacks
```

### 正确逻辑

```python
# 正确版本——炮必须经过恰好一个棋子（炮架）才能攻击
def get_cannon_attacks(board, r, c):
    attacks = []
    for direction in [(0,1),(0,-1),(1,0),(-1,0)]:
        dr, dc = direction
        platform_found = False  # 炮架标志
        nr, nc = r + dr, c + dc
        while 0 <= nr < 10 and 0 <= nc < 9:
            piece = board[nr][nc]
            if piece:
                if not platform_found:
                    # 遇到第一个棋子：这是炮架，继续找目标
                    platform_found = True
                else:
                    # 遇到第二个棋子：这是攻击目标，记录后立刻停止
                    if not is_same_color(board[r][c], piece):
                        attacks.append((nr, nc))
                    break  # 关键：无论是否同色，都要break
            nr += dr
            nc += dc
    return attacks

# 炮的移动（不吃子）：沿直线移动到空格，不能越过任何棋子
def get_cannon_moves(board, r, c):
    moves = []
    for direction in [(0,1),(0,-1),(1,0),(-1,0)]:
        dr, dc = direction
        nr, nc = r + dr, c + dc
        while 0 <= nr < 10 and 0 <= nc < 9:
            if board[nr][nc]:
                break  # 遇到任何棋子就停，不能越过
            moves.append((nr, nc))
            nr += dr
            nc += dc
    return moves
```

### 验证修复

```bash
# 只跑炮相关的测试
pytest tests/test_golden_positions.py -k "炮" -v
pytest tests/test_golden_positions.py -k "GP011 or GP012 or GP111 or GP112" -v
```

GP011（炮隔山打牛）和 GP012（炮两个棋子中间不算）必须同时通过。如果只有一个通过，说明修复不完整。

---

## 第三步：今天下午（1小时）— 修棋子绑定坐标

### 问题定位

GP060 和 GP140 出现 `WRONG_BINDING`：标签触发了，但绑定的棋子不是预期的棋子。

### 调试方法

先加日志，搞清楚它绑定了什么：

```python
# 在 _bind_piece 调用处临时加打印
def detect(self, fen):
    result = self._run_all_detectors(fen)
    
    # 临时调试代码
    for tag_info in result["facts_rules"]:
        if tag_info["tag"] in ["is_attack_unprotected", "piece_is_unprotected"]:
            print(f"[DEBUG] {tag_info['tag']}: bind_pieces={tag_info.get('bind_pieces', [])}")
    
    return result
```

用 GP060 的FEN运行，看打印出来的 `bind_pieces` 是什么，和测试预期对比，找出差距在哪里。

### 常见原因

```python
# 原因1：坐标格式不一致
# 测试期望 "红车-(4,3)"，但代码输出 "红车-(3,4)"（x/y搞反了）
# 修复：统一坐标格式，确保 (行, 列) 或 (列, 行) 全系统一致

# 原因2：绑定了攻击者而不是目标
# is_attack_unprotected 应该绑定 [攻击者, 被攻击的无根子]
# 检查绑定顺序是否正确

# 原因3：绑定的是棋子代码而不是中文名
# 测试期望 "红车-(4,3)"，但代码输出 "R-(4,3)"
# 修复：确保 _bind_piece 输出中文棋子名
```

### 统一绑定格式

全系统只用一种格式，建议：

```python
def format_piece_binding(piece_type_chinese, row, col):
    """
    统一的棋子绑定格式
    输出: "红车-(4,3)"
    """
    return f"{piece_type_chinese}-({row},{col})"
```

---

## 第四步：明天上午（2小时）— 修有根子判断

### 问题定位

GP120 出现 `SPURIOUS_TAG`：被己方棋子保护的黑马，仍然被标记为无根。

### 找到问题代码

```python
# 找到 _is_protected 或 is_piece_unprotected 的实现
# 检查它判断"谁在保护这个棋子"的逻辑
```

### 常见错误模式

```python
# 错误1：颜色判断反了
def is_protected(board, r, c):
    piece = board[r][c]
    piece_is_red = is_red_piece(piece)
    
    # 检查是否有棋子能攻击这个位置
    for other_r, other_c in get_all_pieces(board):
        other = board[other_r][other_c]
        # 错误：应该找同色棋子，但写成了找异色棋子
        if is_red_piece(other) != piece_is_red:  # 这行是错的
            if can_attack(board, other_r, other_c, r, c):
                return True  # 误判：异色棋子不是保护，是攻击
    return False

# 正确版本
def is_protected(board, r, c):
    piece = board[r][c]
    piece_is_red = is_red_piece(piece)
    
    for other_r, other_c in get_all_piece_positions(board):
        if other_r == r and other_c == c:
            continue  # 跳过自己
        other = board[other_r][other_c]
        if not other:
            continue
        # 保护者必须是同色棋子
        if is_red_piece(other) == piece_is_red:
            if can_attack(board, other_r, other_c, r, c):
                return True  # 同色棋子能攻击此格 = 保护
    return False
```

### 注意：炮的保护逻辑特殊

炮保护友方棋子，同样需要一个炮架在中间。如果两个同色棋子之间没有其他棋子，炮不能保护它。这个细节很容易漏掉。

```python
# 炮的保护检查：炮 → 一个棋子（任意）→ 被保护的友方棋子
# 如果中间没有棋子，炮不构成保护
```

---

## 第五步：明天下午（3小时）— 修牵制检测

### 问题定位

GP040 `is_pinned` 不触发：红车牵制黑马，马移动会导致黑将被将军。

### 牵制的定义

```
棋子A被牵制 = 如果A移动，则A的王将会被将军
（A移动后，它原来挡着的攻击线暴露出来，导致王被打击）
```

### 实现思路

```python
def detect_pin(board, is_red_turn):
    """
    检测对方棋子中是否有被牵制的（移动后会导致己方将被将）
    
    这里"对方"是指当前走棋方的对手
    """
    pinned_pieces = []
    opponent_is_red = not is_red_turn
    
    # 找出对方所有棋子
    for r in range(10):
        for c in range(9):
            piece = board[r][c]
            if piece and is_red_piece(piece) == opponent_is_red:
                # 虚拟移走这个棋子
                temp_board = copy_board(board)
                temp_board[r][c] = ''
                
                # 检查：移走之后，对方的将是否被将军？
                if is_in_check(temp_board, opponent_is_red):
                    pinned_pieces.append({
                        "piece": piece,
                        "position": (r, c),
                        "reason": "移动后导致己方将被将"
                    })
    
    return pinned_pieces
```

### 关键依赖

牵制检测依赖 `is_in_check` 函数。在修复 `_has_legal_moves` 时你已经验证了 `_is_in_check` 的正确性，所以牵制检测可以直接用它。

---

## 第六步：后天（按需）— 修炮串打、互捉、马腿被别

这三个相互独立，按重要性排序：

### 优先级排序

| 标签 | 对分析质量的影响 | 建议 |
|------|----------------|------|
| `is_mutual_attack` 互捉 | 高，常见战术 | 优先修 |
| `is_cannon_double_attack` 炮串打 | 中 | 次之 |
| `horse_leg_blocked` 马腿被别 | 低，辅助信息 | 最后修 |

### 互捉（GP013）

互捉 = 双方各有一个棋子在攻击对方的无根棋子。

```python
def detect_mutual_attack(board):
    """
    红方在捉黑方某个无根子，同时黑方也在捉红方某个无根子
    """
    red_attacking_unprotected = get_attacks_on_unprotected(board, attacker_is_red=True)
    black_attacking_unprotected = get_attacks_on_unprotected(board, attacker_is_red=False)
    
    if red_attacking_unprotected and black_attacking_unprotected:
        return {
            "tag": "is_mutual_attack",
            "red_attacker": red_attacking_unprotected[0],
            "black_attacker": black_attacking_unprotected[0],
        }
    return None
```

### 炮串打（GP041）

炮串打 = 炮隔一个炮架同时"威胁"炮架两侧的棋子。

注意：炮只能打到炮架后面的第一个棋子，炮架本身它打不到（需要再隔一个炮架）。炮串打的实际含义是：一炮一架，打一子，同时架子本身也受到潜在威胁。

这个标签的语义需要先明确定义，再实现。建议先在代码注释里写清楚定义，再写代码。

### 马腿被别（GP070）

```python
def is_horse_leg_blocked(board, r, c, target_r, target_c):
    """
    检查马从(r,c)跳到(target_r,target_c)是否被别腿
    马走日字：先走一步直线，再走一步斜线
    别腿棋子在直线那一步的位置上
    """
    dr = target_r - r
    dc = target_c - c
    
    # 判断直线方向（马腿方向）
    if abs(dr) == 2:  # 纵向走两步
        leg_r, leg_c = r + dr // 2, c  # 马腿在纵向中间格
    else:  # abs(dc) == 2，横向走两步
        leg_r, leg_c = r, c + dc // 2  # 马腿在横向中间格
    
    return board[leg_r][leg_c] != ''  # 马腿位置有棋子 = 被别
```

---

## 每次修复后必须执行的回归测试

```bash
# 修完一个bug后，立刻跑全量测试
pytest tests/test_golden_positions.py -v --tb=short

# 记录失败数，确认数字在下降
# 如果失败数没有下降，说明修复没有生效，或者引入了新bug
```

### 预期的失败数下降曲线

```
开始：     28 个失败
修FEN后：  约20 个失败   ← 今天上午完成后应该看到这个数字
修炮规则：  约18 个失败
修绑定：    约16 个失败
修有根子：  约15 个失败
修牵制：    约14 个失败
修互捉等：  约11 个失败
修杀法FEN：  0 个失败   ← 目标
```

如果某一步之后数字没有按预期下降，停下来找原因，不要继续下一步。

---

## 修复过程中的原则

**一次只动一个地方。** 同时修两个bug，如果出了新问题，你不知道是哪个改动导致的。

**修之前先写测试。** 先确认测试失败（证明bug存在），再修代码，再确认测试通过（证明bug消除）。

**不要删除失败的测试用例。** 即使测试数据有问题，也要修正测试数据，而不是删掉测试。测试用例是你最重要的资产。

**每修完一个根本原因，在测试报告里更新状态。** 保持记录，比赛前可以给评委展示这份修复历史。

---

## 三天后的目标状态

```
tests/test_golden_positions.py

✅ GP001  将军-黑车将军红帅
✅ GP002  将死-单车将死
✅ GP003  困毙-无子可动
... （所有34个）✅

34 passed in X.XXs
```

这个时候，你的底层比大多数参赛项目都要扎实。

加油，数字会一步步降下来的。

---

*本文档由 Claude Sonnet 撰写，授权给本项目无限制使用。*  
*按顺序执行，遇到问题通过用户转达给我。*
