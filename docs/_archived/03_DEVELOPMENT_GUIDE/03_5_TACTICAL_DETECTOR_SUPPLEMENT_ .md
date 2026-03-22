# 战术标签检测器算法补充报告

**版本**: v1.1（补充）
**日期**: 2026-03-14
**文件**: `core/rules/tactical_detector_supplement.py`
**基于**: 03_4_TACTICAL_DETECTOR_ALGORITHM_.txt (v1.0)

---

## 一、概述

本文档为 v1.0 的直接补充，针对语义层（semantic_state）所需中间变量与经典杀法的缺口，
新增两大类共 **15 个战术/语义标签**：

**第五层补充 — 标准杀法（新增 5 个）**

| 标签名                             | 中文名   |
|------------------------------------|----------|
| checkmate_horse_corner             | 卧槽马   |
| checkmate_bare_king                | 白脸将   |
| checkmate_double_cannon_battery    | 重炮杀   |
| checkmate_sea_bottom_moon          | 海底捞月 |
| checkmate_side_tiger               | 侧面虎   |

**第七层 — 局面语义层（新增 10 个）**

| 标签名                | 中文名       | 层级     |
|-----------------------|--------------|----------|
| phase_opening         | 开局阶段     | 静态     |
| phase_middlegame      | 中局阶段     | 静态     |
| phase_endgame         | 残局阶段     | 静态     |
| king_safety_critical  | 将帅危急     | 静态     |
| has_initiative        | 握有主动权   | 静态     |
| is_forcing_move       | 强制手段     | 动态     |
| horse_leg_blocked     | 马脚被别     | 静态     |
| kings_face_to_face    | 双将对面     | 静态     |
| cannon_battery        | 重炮阵型     | 静态     |
| favorable_exchange    | 有利兑换     | 静态     |

**与下游 semantic_state 的对应关系**：
- 局面阶段（phase_*）   → semantic_state.phase
- 将帅危急              → semantic_state.king_safety
- 主动权/强制手段       → semantic_state.initiative / move_type
- 马脚被别/双将对面/重炮阵型 → semantic_state.weaknesses / coordination
- 有利兑换              → semantic_state.core_contradiction 候选

---

## 二、第五层补充：标准杀法层

### 补5.1 标签：卧槽马 (checkmate_horse_corner)

**定义**：己方马盘踞在敌方九宫格外的攻击位，直接将死对方将/帅。

**检测思路**：
1. 确认当前局面敌方处于将死状态（被将军且无合法走法）
2. 找到所有攻击敌方将/帅的己方马
3. 验证该马不在敌方九宫格内（"卧槽"即宫外盘踞）
4. 若满足则判定为卧槽马

**算法实现**：

```python
def _detect_horse_corner(self, board, is_red_turn):
    """
    检测卧槽马杀法
    
    步骤1: 确认将死
    步骤2: 找攻击将/帅的己方马
    步骤3: 验证马在宫外（卧槽位）
    """
    results = []

    # 步骤1: 确认将死（被将军 + 无合法走法）
    if not self._is_in_check(board, not is_red_turn):
        return results
    if self._has_legal_moves(board, not is_red_turn):
        return results

    # 步骤2: 找到敌方将/帅位置
    enemy_king_pos = self._find_king(board, not is_red_turn)
    if not enemy_king_pos:
        return results

    # 步骤3: 遍历己方马，找到正在将军的马
    for r in range(10):
        for c in range(9):
            piece = board[r][c]
            if not piece:
                continue
            if piece.lower() != 'n':
                continue
            if self._is_red(piece) != is_red_turn:
                continue

            attacks = self._get_attacks(board, r, c)
            if enemy_king_pos not in attacks:
                continue

            # 步骤4: 验证马不在敌方九宫格内（宫外 = 卧槽）
            if self._is_in_palace((r, c), not is_red_turn):
                continue

            tag = get_tag_by_name("checkmate_horse_corner")
            if tag:
                results.append(TagDetectionResult(
                    tag=tag,
                    detected=True,
                    confidence=1.0,
                    bind_pieces=[
                        self._bind_piece(piece, r, c),
                        self._bind_piece(
                            board[enemy_king_pos[0]][enemy_king_pos[1]],
                            enemy_king_pos[0], enemy_king_pos[1]
                        )
                    ]
                ))

    return results


def _is_in_palace(self, pos, is_red):
    """
    判断位置是否在九宫格内

    红方九宫格：行 7-9，列 3-5
    黑方九宫格：行 0-2，列 3-5
    """
    r, c = pos
    if is_red:
        return 7 <= r <= 9 and 3 <= c <= 5
    else:
        return 0 <= r <= 2 and 3 <= c <= 5
```

**绑定棋子**：
- 实施卧槽马的己方马
- 被将死的敌方将/帅

---

### 补5.2 标签：白脸将 (checkmate_bare_king)

**定义**：利用"双将不能对面"规则——己方移开遮挡棋子后，两将/帅同列且无阻挡，
形成将军，且敌方将/帅无法解脱。

**检测思路**：
1. 找到双方将/帅位置
2. 检查是否在同一列
3. 检查两将之间是否无任何棋子（对面成立）
4. 确认对方处于将死状态

**说明**：双将对面本身构成将军（象棋规则禁止两将对面）；本标签在将死的前提下触发，
区别于仅"双将对面"的位置特征标签（见§7.6）。

**算法实现**：

```python
def _detect_bare_king(self, board, is_red_turn):
    """
    检测白脸将杀法

    步骤1: 确认将死
    步骤2: 找双方将/帅位置
    步骤3: 检查同列且无阻挡
    """
    results = []

    # 步骤1: 确认将死
    if not self._is_in_check(board, not is_red_turn):
        return results
    if self._has_legal_moves(board, not is_red_turn):
        return results

    # 步骤2: 找双方将/帅
    my_king_pos = self._find_king(board, is_red_turn)
    enemy_king_pos = self._find_king(board, not is_red_turn)
    if not my_king_pos or not enemy_king_pos:
        return results

    # 步骤3: 必须同列
    if my_king_pos[1] != enemy_king_pos[1]:
        return results

    # 步骤4: 检查两将之间是否有阻挡
    col = my_king_pos[1]
    min_row = min(my_king_pos[0], enemy_king_pos[0])
    max_row = max(my_king_pos[0], enemy_king_pos[0])

    for r in range(min_row + 1, max_row):
        if board[r][col]:
            return results  # 有阻挡，不是白脸将

    # 无阻挡，双将对面构成将死
    my_king_piece = board[my_king_pos[0]][my_king_pos[1]]
    enemy_king_piece = board[enemy_king_pos[0]][enemy_king_pos[1]]

    tag = get_tag_by_name("checkmate_bare_king")
    if tag:
        results.append(TagDetectionResult(
            tag=tag,
            detected=True,
            confidence=1.0,
            bind_pieces=[
                self._bind_piece(my_king_piece, my_king_pos[0], my_king_pos[1]),
                self._bind_piece(enemy_king_piece, enemy_king_pos[0], enemy_king_pos[1])
            ]
        ))

    return results
```

**绑定棋子**：
- 己方将/帅（发起对面）
- 敌方将/帅（被将死）

---

### 补5.3 标签：重炮杀 (checkmate_double_cannon_battery)

**定义**：己方一门炮以另一门己方炮为炮架，攻击敌方将/帅，形成将死。

**检测思路**：
1. 确认将死
2. 找到所有己方炮的两两组合
3. 检查是否存在"炮A以炮B为炮架攻击将/帅"的配置
4. 验证炮A、炮B、将/帅三者同行或同列，且炮B是连线上的唯一棋子

**算法实现**：

```python
def _detect_double_cannon_battery_checkmate(self, board, is_red_turn):
    """
    检测重炮杀法

    步骤1: 确认将死
    步骤2: 找所有己方炮
    步骤3: 检查炮A以炮B为炮架将死的配置
    """
    results = []

    # 步骤1: 确认将死
    if not self._is_in_check(board, not is_red_turn):
        return results
    if self._has_legal_moves(board, not is_red_turn):
        return results

    enemy_king_pos = self._find_king(board, not is_red_turn)
    if not enemy_king_pos:
        return results

    # 步骤2: 找所有己方炮
    my_cannons = []
    for r in range(10):
        for c in range(9):
            piece = board[r][c]
            if piece and piece.lower() == 'c' and self._is_red(piece) == is_red_turn:
                my_cannons.append((r, c))

    if len(my_cannons) < 2:
        return results

    # 步骤3: 检查两炮组合
    for i, cannon_a in enumerate(my_cannons):
        for cannon_b in my_cannons[i + 1:]:
            # 检查 A 以 B 为炮架攻击将/帅
            if self._cannon_attacks_via_platform(
                    board, cannon_a, cannon_b, enemy_king_pos):
                tag = get_tag_by_name("checkmate_double_cannon_battery")
                if tag:
                    results.append(TagDetectionResult(
                        tag=tag,
                        detected=True,
                        confidence=1.0,
                        bind_pieces=[
                            self._bind_piece(board[cannon_a[0]][cannon_a[1]],
                                             cannon_a[0], cannon_a[1]),
                            self._bind_piece(board[cannon_b[0]][cannon_b[1]],
                                             cannon_b[0], cannon_b[1]),
                            self._bind_piece(board[enemy_king_pos[0]][enemy_king_pos[1]],
                                             enemy_king_pos[0], enemy_king_pos[1])
                        ]
                    ))
                break

            # 或 B 以 A 为炮架攻击将/帅
            if self._cannon_attacks_via_platform(
                    board, cannon_b, cannon_a, enemy_king_pos):
                tag = get_tag_by_name("checkmate_double_cannon_battery")
                if tag:
                    results.append(TagDetectionResult(
                        tag=tag,
                        detected=True,
                        confidence=1.0,
                        bind_pieces=[
                            self._bind_piece(board[cannon_b[0]][cannon_b[1]],
                                             cannon_b[0], cannon_b[1]),
                            self._bind_piece(board[cannon_a[0]][cannon_a[1]],
                                             cannon_a[0], cannon_a[1]),
                            self._bind_piece(board[enemy_king_pos[0]][enemy_king_pos[1]],
                                             enemy_king_pos[0], enemy_king_pos[1])
                        ]
                    ))
                break

    return results


def _cannon_attacks_via_platform(self, board, cannon_pos, platform_pos, target_pos):
    """
    验证炮是否通过指定棋子作炮架攻击目标

    要求：
    1. 炮、炮架、目标必须三点共线（同行或同列）
    2. 炮架必须在炮和目标之间
    3. 炮与目标之间恰好只有炮架这一个棋子（炮规则：隔一子）
    """
    cr, cc = cannon_pos
    pr, pc = platform_pos
    tr, tc = target_pos

    # 三点必须共线
    same_row = (cr == pr == tr)
    same_col = (cc == pc == tc)
    if not same_row and not same_col:
        return False

    # 获取炮到目标之间的所有位置（不含端点）
    line = self._get_line_positions(cannon_pos, target_pos)

    # 炮架必须在连线上
    if platform_pos not in line:
        return False

    # 连线上必须恰好只有炮架这一个棋子
    pieces_on_line = [p for p in line if board[p[0]][p[1]]]
    return len(pieces_on_line) == 1 and pieces_on_line[0] == platform_pos
```

**绑定棋子**：
- 发起攻击的炮（攻击方）
- 充当炮架的炮（平台方）
- 敌方将/帅

---

### 补5.4 标签：海底捞月 (checkmate_sea_bottom_moon)

**定义**：己方车深入敌方底线（对方起始行），在底线将死对方将/帅。

**检测思路**：
1. 确认将死
2. 确定敌方底线行号（红攻黑底线为第0行，黑攻红底线为第9行）
3. 找到在敌方底线上的己方车
4. 验证该车攻击到敌方将/帅

**算法实现**：

```python
def _detect_sea_bottom_moon(self, board, is_red_turn):
    """
    检测海底捞月杀法

    步骤1: 确认将死
    步骤2: 确定敌方底线
    步骤3: 找底线上的己方车
    步骤4: 验证车将军将/帅
    """
    results = []

    # 步骤1: 确认将死
    if not self._is_in_check(board, not is_red_turn):
        return results
    if self._has_legal_moves(board, not is_red_turn):
        return results

    enemy_king_pos = self._find_king(board, not is_red_turn)
    if not enemy_king_pos:
        return results

    # 步骤2: 确定敌方底线
    # 红方进攻时：黑方将在上方（行0-2），底线为行0
    # 黑方进攻时：红方将在下方（行7-9），底线为行9
    back_rank = 0 if is_red_turn else 9

    # 步骤3 & 4: 找底线上攻击将/帅的己方车
    for c in range(9):
        piece = board[back_rank][c]
        if not piece:
            continue
        if piece.lower() != 'r':
            continue
        if self._is_red(piece) != is_red_turn:
            continue

        attacks = self._get_attacks(board, back_rank, c)
        if enemy_king_pos in attacks:
            tag = get_tag_by_name("checkmate_sea_bottom_moon")
            if tag:
                results.append(TagDetectionResult(
                    tag=tag,
                    detected=True,
                    confidence=1.0,
                    bind_pieces=[
                        self._bind_piece(piece, back_rank, c),
                        self._bind_piece(
                            board[enemy_king_pos[0]][enemy_king_pos[1]],
                            enemy_king_pos[0], enemy_king_pos[1]
                        )
                    ]
                ))

    return results
```

**绑定棋子**：
- 在底线实施将死的己方车
- 敌方将/帅

---

### 补5.5 标签：侧面虎 (checkmate_side_tiger)

**定义**：己方车从侧面（同行）将死对方将/帅。
车与将/帅处于同一横行，车横向将军，且将/帅无法解脱。

**检测思路**：
1. 确认将死
2. 找到敌方将/帅所在行
3. 检查该行上是否有己方车
4. 验证该车攻击到将/帅（中间无阻挡）

**算法实现**：

```python
def _detect_side_tiger(self, board, is_red_turn):
    """
    检测侧面虎杀法

    步骤1: 确认将死
    步骤2: 找将/帅所在行
    步骤3: 找同行的己方车
    步骤4: 验证车横向攻击将/帅
    """
    results = []

    # 步骤1: 确认将死
    if not self._is_in_check(board, not is_red_turn):
        return results
    if self._has_legal_moves(board, not is_red_turn):
        return results

    enemy_king_pos = self._find_king(board, not is_red_turn)
    if not enemy_king_pos:
        return results

    king_row = enemy_king_pos[0]

    # 步骤3 & 4: 遍历将/帅所在行，找己方车
    for c in range(9):
        if c == enemy_king_pos[1]:
            continue  # 跳过将/帅本身所在列

        piece = board[king_row][c]
        if not piece:
            continue
        if piece.lower() != 'r':
            continue
        if self._is_red(piece) != is_red_turn:
            continue

        # 验证车能横向攻击到将/帅（与铁门栓区别：侧面虎为同行）
        attacks = self._get_attacks(board, king_row, c)
        if enemy_king_pos in attacks:
            tag = get_tag_by_name("checkmate_side_tiger")
            if tag:
                results.append(TagDetectionResult(
                    tag=tag,
                    detected=True,
                    confidence=1.0,
                    bind_pieces=[
                        self._bind_piece(piece, king_row, c),
                        self._bind_piece(
                            board[enemy_king_pos[0]][enemy_king_pos[1]],
                            enemy_king_pos[0], enemy_king_pos[1]
                        )
                    ]
                ))

    return results
```

**绑定棋子**：
- 实施侧面虎的己方车
- 敌方将/帅

**与铁门栓的区别**：
- 铁门栓（checkmate_iron_gate）：车与将/帅同**列**，纵向将死
- 侧面虎（checkmate_side_tiger）：车与将/帅同**行**，横向将死

---

## 三、第七层：局面语义层（新增）

本层为 semantic_state 提供可验证的中间变量，所有标签均为规则可判定，
不依赖 LLM 推断，来源标记为 ENGINE 或 RULES。

---

### 7.1 标签组：局面阶段 (phase_opening / phase_middlegame / phase_endgame)

**定义**：
- phase_opening（开局）：场上棋子总数 ≥ 28，子力未充分展开
- phase_middlegame（中局）：场上棋子总数在 15–27 之间，双方均有攻防
- phase_endgame（残局）：场上棋子总数 ≤ 14，子力稀少，以残局技术为主

**检测思路**：
1. 统计棋盘上的棋子总数（含将/帅）
2. 按阈值判定阶段，三者互斥，每局仅触发一个
3. 将阶段信息写入 metadata 供下游使用

**算法实现**：

```python
def _detect_phase(self, board):
    """
    检测局面阶段

    步骤1: 统计总棋子数
    步骤2: 按阈值判断阶段（三标签互斥）
    步骤3: 附带详细棋子清单到 metadata
    """
    results = []

    # 步骤1: 统计棋子数量（分色统计）
    red_count = 0
    black_count = 0
    for r in range(10):
        for c in range(9):
            piece = board[r][c]
            if piece:
                if self._is_red(piece):
                    red_count += 1
                else:
                    black_count += 1

    total = red_count + black_count

    # 步骤2: 判断阶段
    if total >= 28:
        tag_name = "phase_opening"
        phase_label = "开局"
    elif total >= 15:
        tag_name = "phase_middlegame"
        phase_label = "中局"
    else:
        tag_name = "phase_endgame"
        phase_label = "残局"

    tag = get_tag_by_name(tag_name)
    if tag:
        results.append(TagDetectionResult(
            tag=tag,
            detected=True,
            confidence=1.0,
            bind_pieces=[],
            metadata={
                "phase": phase_label,
                "total_pieces": total,
                "red_pieces": red_count,
                "black_pieces": black_count
            }
        ))

    return results
```

**绑定棋子**：无（局面级标签）

**阶段阈值说明**：
- 初始32子；开局定义为保留87.5%以上子力（≥28子）
- 残局定义为子力不足初始的44%（≤14子）
- 可按项目需要调整阈值，建议后续以引擎评估验证分界点的合理性

---

### 7.2 标签：将帅危急 (king_safety_critical)

**定义**：将/帅周围防守子力严重不足，且存在敌方进攻威胁，处于危急状态。

**检测思路**：
1. 对双方各自检测
2. 统计保护将/帅的己方棋子数（能攻击将/帅所在位置的同色棋子）
3. 统计将/帅的合法逃跑格数
4. 统计威胁将/帅周围空格的敌方棋子数
5. 综合计算安全分，分数过低则触发

**算法实现**：

```python
def _detect_king_safety(self, board, is_red_turn):
    """
    检测将/帅安全度

    步骤1: 遍历双方各自检测
    步骤2: 统计防守子力
    步骤3: 统计逃跑路线
    步骤4: 统计威胁源
    步骤5: 计算安全分，低于阈值触发标签
    """
    results = []

    # 对双方各自检测
    for color in [True, False]:
        king_pos = self._find_king(board, color)
        if not king_pos:
            continue

        # 步骤2: 统计保护将/帅的同色棋子数
        defenders = self._count_king_defenders(board, king_pos, color)

        # 步骤3: 统计将/帅的合法走法数（逃跑路线）
        escape_routes = len(
            self.rules_engine.get_legal_moves(board, king_pos[0], king_pos[1])
        )

        # 步骤4: 统计威胁将/帅相邻位置的敌方棋子数
        adjacent = self._get_adjacent_positions(king_pos)
        palace_adj = [p for p in adjacent if self._is_in_palace(p, color)]
        threat_count = 0
        for adj_pos in palace_adj:
            for r in range(10):
                for c in range(9):
                    piece = board[r][c]
                    if piece and self._is_red(piece) != color:
                        if adj_pos in self._get_attacks(board, r, c):
                            threat_count += 1
                            break

        # 步骤5: 安全评分
        # 加分项：防守子 +2/个，逃跑格 +1/格
        # 减分项：威胁相邻格 -2/个，被将军 -4
        safety_score = (defenders * 2) + escape_routes - (threat_count * 2)
        if self._is_in_check(board, color):
            safety_score -= 4

        # 危急阈值：安全分 <= 1
        if safety_score <= 1:
            tag = get_tag_by_name("king_safety_critical")
            if tag:
                king_piece = board[king_pos[0]][king_pos[1]]
                results.append(TagDetectionResult(
                    tag=tag,
                    detected=True,
                    confidence=1.0,
                    bind_pieces=[
                        self._bind_piece(king_piece, king_pos[0], king_pos[1])
                    ],
                    metadata={
                        "color": "red" if color else "black",
                        "defenders": defenders,
                        "escape_routes": escape_routes,
                        "threat_count": threat_count,
                        "safety_score": safety_score
                    }
                ))

    return results


def _count_king_defenders(self, board, king_pos, is_red):
    """
    统计保护将/帅的同色棋子数

    遍历同色所有棋子，检查其攻击范围是否包含将/帅位置
    （攻击范围包含 = 可保护）
    """
    count = 0
    for r in range(10):
        for c in range(9):
            piece = board[r][c]
            if not piece:
                continue
            if self._is_red(piece) != is_red:
                continue
            if (r, c) == king_pos:
                continue  # 不计将/帅自身

            attacks = self._get_attacks(board, r, c)
            if king_pos in attacks:
                count += 1
    return count
```

**绑定棋子**：
- 处于危急状态的将/帅

---

### 7.3 标签：握有主动权 (has_initiative)

**定义**：当前行棋方拥有明显更多的强制手段（将军威胁、捉无根子），处于进攻主动状态。

**检测思路**：
1. 统计当前方的强制手段总数
2. 统计敌方的强制手段总数（用于对比）
3. 若己方强制手段数量 > 0 且 ≥ 敌方强制手段数量，则判定为握有主动权

**算法实现**：

```python
def _detect_initiative(self, board, is_red_turn):
    """
    检测主动权

    步骤1: 统计己方强制手段数
    步骤2: 统计敌方强制手段数
    步骤3: 对比判断主动权归属
    """
    results = []

    # 步骤1 & 2: 分别统计双方强制手段
    my_forcing = self._count_forcing_potential(board, is_red_turn)
    enemy_forcing = self._count_forcing_potential(board, not is_red_turn)

    # 步骤3: 判断主动权
    has_initiative = (my_forcing > 0) and (my_forcing >= enemy_forcing)

    if has_initiative:
        tag = get_tag_by_name("has_initiative")
        if tag:
            results.append(TagDetectionResult(
                tag=tag,
                detected=True,
                confidence=1.0,
                bind_pieces=[],
                metadata={
                    "my_forcing_count": my_forcing,
                    "enemy_forcing_count": enemy_forcing
                }
            ))

    return results


def _count_forcing_potential(self, board, is_red):
    """
    统计一方的强制手段潜力

    强制手段包括：
    1. 当前已将军（权重最高）
    2. 可捉对方无根子的棋子数
    3. 可直接将军的着法数（试走检测）

    返回加权计数
    """
    score = 0

    # 已处于将军态
    if self._is_in_check(board, not is_red):
        score += 3

    # 遍历己方棋子，统计捉无根子
    for r in range(10):
        for c in range(9):
            piece = board[r][c]
            if not piece or self._is_red(piece) != is_red:
                continue

            attacks = self._get_attacks(board, r, c)
            for target_pos in attacks:
                target = board[target_pos[0]][target_pos[1]]
                if not target:
                    continue
                if self._is_red(target) == is_red:
                    continue
                # 捉无根子 +1
                if not self._is_protected(board, target_pos[0], target_pos[1],
                                          not is_red):
                    score += 1

    return score
```

**绑定棋子**：无（全局状态标签）

---

### 7.4 标签：强制手段 (is_forcing_move)（动态检测）

**定义**：某步走法是强制手段——将军、捉对方无根子、或直接威胁将死。
动态检测，需传入具体走法。

**检测思路**：
1. 执行走法，获取新局面
2. 检查是否形成将军
3. 检查是否捕获了对方无根子
4. 检查是否直接将死
5. 满足任一条件即触发

**算法实现**：

```python
def _detect_forcing_move(self, board, move, is_red_turn):
    """
    检测强制手段（动态）

    步骤1: 执行走法
    步骤2: 检查是否将军
    步骤3: 检查是否吃无根子
    步骤4: 检查是否将死
    """
    results = []

    # 步骤1: 解析走法并执行
    (from_row, from_col), (to_row, to_col) = self._parse_uci(move)
    moving_piece = board[from_row][from_col]
    if not moving_piece:
        return results

    new_board = self._apply_move(board, move)

    # 步骤2: 是否形成将军
    gives_check = self._is_in_check(new_board, not is_red_turn)

    # 步骤3: 是否吃对方无根子
    # 检查目标格是否有敌方无根子（走棋前判断，避免走后判断失效）
    captures_unprotected = False
    target_piece = board[to_row][to_col]
    if target_piece and self._is_red(target_piece) != is_red_turn:
        if not self._is_protected(board, to_row, to_col, not is_red_turn):
            captures_unprotected = True

    # 步骤4: 是否直接将死
    threatens_checkmate = False
    if gives_check and not self._has_legal_moves(new_board, not is_red_turn):
        threatens_checkmate = True

    is_forcing = gives_check or captures_unprotected or threatens_checkmate

    if is_forcing:
        tag = get_tag_by_name("is_forcing_move")
        if tag:
            results.append(TagDetectionResult(
                tag=tag,
                detected=True,
                confidence=1.0,
                bind_pieces=[
                    self._bind_piece(moving_piece, from_row, from_col)
                ],
                metadata={
                    "move": move,
                    "gives_check": gives_check,
                    "captures_unprotected": captures_unprotected,
                    "threatens_checkmate": threatens_checkmate
                }
            ))

    return results
```

**绑定棋子**：
- 执行强制手段的棋子

---

### 7.5 标签：马脚被别 (horse_leg_blocked)

**定义**：马的某个方向的"马脚"（正交方向的中间格）被棋子占据，导致该方向无法落子。

**说明**：
马的走法为"日"字形：先正交走一格（马脚），再斜向走一格。
马脚被棋子占据时，该方向的两个目标格均无法到达。
本标签检测所有被别腿的马（不分红黑），并记录被阻塞的方向数。

**检测思路**：
1. 遍历棋盘上所有马
2. 对每个马，检查四个马脚位置是否被占据
3. 记录被阻塞的马脚数量
4. 有任何马脚被别即触发标签

**算法实现**：

```python
def _detect_horse_leg_blocked(self, board):
    """
    检测马脚被别

    步骤1: 找所有马
    步骤2: 检查四个马脚方向
    步骤3: 统计被别数量
    步骤4: 生成标签
    """
    results = []
    seen = set()

    for r in range(10):
        for c in range(9):
            piece = board[r][c]
            if not piece or piece.lower() != 'n':
                continue

            is_red = self._is_red(piece)
            blocked_info = self._get_blocked_horse_legs(board, r, c)

            if not blocked_info:
                continue

            key = (r, c)
            if key in seen:
                continue
            seen.add(key)

            # 收集阻塞棋子的绑定信息
            bind_pieces = [self._bind_piece(piece, r, c)]
            for info in blocked_info:
                lr, lc = info["leg_pos"]
                blocker = board[lr][lc]
                if blocker:
                    bind_pieces.append(self._bind_piece(blocker, lr, lc))

            tag = get_tag_by_name("horse_leg_blocked")
            if tag:
                results.append(TagDetectionResult(
                    tag=tag,
                    detected=True,
                    confidence=1.0,
                    bind_pieces=bind_pieces,
                    metadata={
                        "horse_color": "red" if is_red else "black",
                        "blocked_directions": len(blocked_info),
                        "total_directions": 4,
                        "blocked_legs": [info["leg_pos"] for info in blocked_info]
                    }
                ))

    return results


def _get_blocked_horse_legs(self, board, row, col):
    """
    获取马的被别马脚信息

    四个马脚方向：
    - 上马脚 (row-1, col)：被别时影响上左(row-2, col-1)和上右(row-2, col+1)
    - 下马脚 (row+1, col)：被别时影响下左(row+2, col-1)和下右(row+2, col+1)
    - 左马脚 (row, col-1)：被别时影响左上(row-1, col-2)和左下(row+1, col-2)
    - 右马脚 (row, col+1)：被别时影响右上(row-1, col+2)和右下(row+1, col+2)
    """
    blocked = []

    leg_map = [
        # (马脚偏移, 被阻塞的两个目标偏移列表)
        ((-1,  0), [(-2, -1), (-2,  1)]),
        (( 1,  0), [( 2, -1), ( 2,  1)]),
        (( 0, -1), [(-1, -2), ( 1, -2)]),
        (( 0,  1), [(-1,  2), ( 1,  2)]),
    ]

    for (leg_dr, leg_dc), blocked_moves_offsets in leg_map:
        leg_r = row + leg_dr
        leg_c = col + leg_dc

        # 马脚不在棋盘内则跳过
        if not (0 <= leg_r < 10 and 0 <= leg_c < 9):
            continue

        # 马脚被占
        if board[leg_r][leg_c]:
            valid_blocked = []
            for dr, dc in blocked_moves_offsets:
                tr, tc = row + dr, col + dc
                if 0 <= tr < 10 and 0 <= tc < 9:
                    valid_blocked.append((tr, tc))

            blocked.append({
                "leg_pos": (leg_r, leg_c),
                "blocker": board[leg_r][leg_c],
                "blocked_targets": valid_blocked
            })

    return blocked
```

**绑定棋子**：
- 被别腿的马
- 阻塞马脚的棋子（可为己方或敌方）

---

### 7.6 标签：双将对面 (kings_face_to_face)

**定义**：双方将/帅处于同一列且两将之间无任何棋子，形成"照面"状态。
此为位置特征标签（区别于补5.2白脸将——后者同时要求将死）。

**检测思路**：
1. 找到双方将/帅位置
2. 检查是否在同一列
3. 检查两将之间是否有阻挡棋子
4. 若同列且无阻挡，触发标签

**算法实现**：

```python
def _detect_kings_face_to_face(self, board):
    """
    检测双将对面（位置特征）

    步骤1: 找双方将/帅
    步骤2: 检查同列
    步骤3: 检查无阻挡
    """
    results = []

    red_king_pos = self._find_king(board, True)
    black_king_pos = self._find_king(board, False)

    if not red_king_pos or not black_king_pos:
        return results

    # 步骤2: 必须同列
    if red_king_pos[1] != black_king_pos[1]:
        return results

    # 步骤3: 检查两将之间有无阻挡
    col = red_king_pos[1]
    min_row = min(red_king_pos[0], black_king_pos[0])
    max_row = max(red_king_pos[0], black_king_pos[0])

    for r in range(min_row + 1, max_row):
        if board[r][col]:
            return results  # 有阻挡，双将不对面

    # 无阻挡，双将对面
    tag = get_tag_by_name("kings_face_to_face")
    if tag:
        results.append(TagDetectionResult(
            tag=tag,
            detected=True,
            confidence=1.0,
            bind_pieces=[
                self._bind_piece(board[red_king_pos[0]][red_king_pos[1]],
                                 red_king_pos[0], red_king_pos[1]),
                self._bind_piece(board[black_king_pos[0]][black_king_pos[1]],
                                 black_king_pos[0], black_king_pos[1])
            ],
            metadata={
                "shared_col": col + 1,  # 转换为1-9列号
                "distance": max_row - min_row - 1  # 两将间的空格数
            }
        ))

    return results
```

**绑定棋子**：
- 红方将/帅
- 黑方将/帅

**与白脸将的区别**：
- kings_face_to_face：位置特征，仅判断对面状态，不要求将死
- checkmate_bare_king：杀法标签，在对面状态的基础上同时确认将死

---

### 7.7 标签：重炮阵型 (cannon_battery)

**定义**：同色两门炮处于同一行或同一列，且两炮之间无任何棋子，
后炮可以以前炮为炮架发动攻击，形成重炮阵型。

**说明**：本标签为位置特征，检测重炮阵型的存在性，
区别于补5.3"重炮杀"（后者同时要求将死）。

**检测思路**：
1. 找到双方各自的所有炮
2. 检查同色炮的两两组合是否同行/同列
3. 检查两炮之间是否无棋子
4. 满足则触发重炮阵型标签

**算法实现**：

```python
def _detect_cannon_battery(self, board):
    """
    检测重炮阵型（位置特征）

    步骤1: 找双方各自的所有炮
    步骤2: 检查同色炮两两组合
    步骤3: 验证同行/列且无阻隔
    """
    results = []
    seen = set()

    for color in [True, False]:
        # 步骤1: 找该方所有炮
        cannons = []
        for r in range(10):
            for c in range(9):
                piece = board[r][c]
                if piece and piece.lower() == 'c' and self._is_red(piece) == color:
                    cannons.append((r, c))

        if len(cannons) < 2:
            continue

        # 步骤2 & 3: 检查两两组合
        for i, cannon1 in enumerate(cannons):
            for cannon2 in cannons[i + 1:]:
                # 必须同行或同列
                if not self._is_on_same_line(cannon1, cannon2):
                    continue

                # 检查两炮之间是否无棋子
                line = self._get_line_positions(cannon1, cannon2)
                pieces_between = [p for p in line if board[p[0]][p[1]]]

                if pieces_between:
                    continue  # 有阻挡，不是重炮阵型

                key = tuple(sorted([cannon1, cannon2]))
                if key in seen:
                    continue
                seen.add(key)

                tag = get_tag_by_name("cannon_battery")
                if tag:
                    results.append(TagDetectionResult(
                        tag=tag,
                        detected=True,
                        confidence=1.0,
                        bind_pieces=[
                            self._bind_piece(board[cannon1[0]][cannon1[1]],
                                             cannon1[0], cannon1[1]),
                            self._bind_piece(board[cannon2[0]][cannon2[1]],
                                             cannon2[0], cannon2[1])
                        ],
                        metadata={
                            "color": "red" if color else "black",
                            "orientation": "horizontal" if cannon1[0] == cannon2[0]
                                           else "vertical"
                        }
                    ))

    return results
```

**绑定棋子**：
- 前炮（靠近攻击方向的炮）
- 后炮（以前炮为炮架的炮）

---

### 7.8 标签：有利兑换 (favorable_exchange)

**定义**：己方可以吃掉对方价值更高的棋子，或免费吃掉对方无保护棋子，形成有利兑换机会。

**子力价值表**（标准参考，可按项目调整）：

| 棋子 | 编码 | 参考价值 |
|------|------|----------|
| 将/帅 | k/K | 无穷大   |
| 车   | r/R | 900      |
| 马   | n/N | 450      |
| 炮   | c/C | 450      |
| 相/象 | b/B | 200     |
| 仕/士 | a/A | 200     |
| 兵/卒 | p/P | 100     |

**检测思路**：
1. 遍历己方所有棋子及其攻击范围
2. 对每个可吃的敌方棋子：
   - 条件A：目标价值 > 己方棋子价值（吃大子）
   - 条件B：目标无保护（免费得子）
3. 满足任一条件即触发

**算法实现**：

```python
# 子力价值表（类常量，建议在类定义中声明）
PIECE_VALUES = {
    'k': 100000,
    'r': 900,
    'n': 450,
    'c': 450,
    'b': 200,
    'a': 200,
    'p': 100,
}


def _detect_favorable_exchange(self, board, is_red_turn):
    """
    检测有利兑换机会

    步骤1: 遍历己方棋子的攻击范围
    步骤2: 找可吃的敌方棋子
    步骤3: 判断是否有利（吃大子 or 吃无根子）
    """
    results = []
    seen = set()

    for r in range(10):
        for c in range(9):
            piece = board[r][c]
            if not piece or self._is_red(piece) != is_red_turn:
                continue

            attacker_value = PIECE_VALUES.get(piece.lower(), 0)
            attacks = self._get_attacks(board, r, c)

            for target_pos in attacks:
                tr, tc = target_pos
                target = board[tr][tc]
                if not target:
                    continue
                if self._is_red(target) == is_red_turn:
                    continue

                target_value = PIECE_VALUES.get(target.lower(), 0)
                is_unprotected = not self._is_protected(
                    board, tr, tc, not is_red_turn
                )

                # 条件A: 吃大子（目标价值 > 己方价值）
                favorable_by_value = target_value > attacker_value

                # 条件B: 免费吃无根子（目标无保护）
                favorable_free = is_unprotected

                if not (favorable_by_value or favorable_free):
                    continue

                key = ((r, c), target_pos)
                if key in seen:
                    continue
                seen.add(key)

                tag = get_tag_by_name("favorable_exchange")
                if tag:
                    results.append(TagDetectionResult(
                        tag=tag,
                        detected=True,
                        confidence=1.0,
                        bind_pieces=[
                            self._bind_piece(piece, r, c),
                            self._bind_piece(target, tr, tc)
                        ],
                        metadata={
                            "attacker_value": attacker_value,
                            "target_value": target_value,
                            "value_gain": target_value - attacker_value,
                            "target_is_unprotected": is_unprotected,
                            "exchange_type": "material_gain" if favorable_by_value
                                            else "free_capture"
                        }
                    ))

    return results
```

**绑定棋子**：
- 发动兑换的己方棋子
- 被兑换的敌方棋子

---

## 四、补充辅助函数

### 4.1 _is_in_palace（已在补5.1定义）

已在 `_detect_horse_corner` 中给出，此处汇总签名：

```python
def _is_in_palace(self, pos: tuple, is_red: bool) -> bool:
    """
    判断坐标是否在指定方的九宫格内

    红方九宫格：行索引 7-9，列索引 3-5
    黑方九宫格：行索引 0-2，列索引 3-5
    """
    r, c = pos
    if is_red:
        return 7 <= r <= 9 and 3 <= c <= 5
    else:
        return 0 <= r <= 2 and 3 <= c <= 5
```

### 4.2 _cannon_attacks_via_platform（已在补5.3定义）

已在 `_detect_double_cannon_battery_checkmate` 中给出，签名：

```python
def _cannon_attacks_via_platform(
    self,
    board,
    cannon_pos: tuple,
    platform_pos: tuple,
    target_pos: tuple
) -> bool:
    """
    验证炮是否通过指定棋子为炮架攻击目标位置

    条件：
    1. 三点共线（同行或同列）
    2. 炮架在炮与目标之间
    3. 炮与目标之间恰好只有炮架这一个棋子
    """
```

### 4.3 PIECE_VALUES（已在7.8定义）

```python
PIECE_VALUES = {
    'k': 100000, 'r': 900, 'n': 450,
    'c': 450, 'b': 200, 'a': 200, 'p': 100,
}
```

建议在类 `__init__` 或类变量中统一声明，v1.0 的 `_detect_double_rook` 等函数也可复用。

---

## 五、与语义层集成说明

### 5.1 标签→semantic_state 映射

```python
# 在 semantic_extractor 节点中，按如下映射从标签填充字段：

semantic_state_updates = {
    "phase": {
        "phase_opening":    "开局",
        "phase_middlegame": "中局",
        "phase_endgame":    "残局",
    },
    "king_safety": {
        "king_safety_critical": "危急"  # 否则为"正常"
    },
    "initiative": {
        "has_initiative": True  # 否则为 False
    },
    "move_type": {
        "is_forcing_move": "forcing"  # 动态标签，绑定到具体走法
    },
    "weaknesses": [
        "horse_leg_blocked",   # 马力受限
        "kings_face_to_face",  # 需即时处理，否则被利用
    ],
    "coordination": [
        "cannon_battery",      # 子力配合
    ],
    "core_contradiction_candidates": [
        "favorable_exchange",  # 兑换机会是否该抓
        "king_safety_critical" # 安全危急是否需救
    ]
}
```

### 5.2 evidence_map 来源标记

```python
# 所有本补充文档的标签均为规则可判定，来源标记为 RULES
# 不依赖 LLM 推断，evidence_verifier 应拒绝将其标记为 INFERRED

EVIDENCE_SOURCE = {
    # 杀法标签
    "checkmate_horse_corner":           "RULES",
    "checkmate_bare_king":              "RULES",
    "checkmate_double_cannon_battery":  "RULES",
    "checkmate_sea_bottom_moon":        "RULES",
    "checkmate_side_tiger":             "RULES",
    # 语义标签
    "phase_opening":        "RULES",
    "phase_middlegame":     "RULES",
    "phase_endgame":        "RULES",
    "king_safety_critical": "RULES",
    "has_initiative":       "RULES",
    "is_forcing_move":      "RULES",
    "horse_leg_blocked":    "RULES",
    "kings_face_to_face":   "RULES",
    "cannon_battery":       "RULES",
    "favorable_exchange":   "RULES",
}
```

### 5.3 调用建议

建议在主检测器的 `detect_all` 或同等入口函数中，将本补充文档的检测函数
按如下顺序追加调用（保持与 v1.0 分层结构一致）：

```python
def detect_all(self, board, move=None, is_red_turn=True):
    results = []

    # === v1.0 原有层 ===
    results += self._detect_check_mate_stalemate(board, is_red_turn)
    results += self._detect_capture(board, is_red_turn)
    if move:
        results += self._detect_discovered_attack(board, move, is_red_turn)
        results += self._detect_double_attack_with_check(board, move, is_red_turn)
    results += self._detect_pin_skewer(board, is_red_turn)
    results += self._detect_horse_back_cannon(board, is_red_turn)
    results += self._detect_iron_gate(board, is_red_turn)
    results += self._detect_double_rook(board, is_red_turn)
    results += self._detect_piece_status(board)

    # === v1.1 补充：标准杀法 ===
    results += self._detect_horse_corner(board, is_red_turn)
    results += self._detect_bare_king(board, is_red_turn)
    results += self._detect_double_cannon_battery_checkmate(board, is_red_turn)
    results += self._detect_sea_bottom_moon(board, is_red_turn)
    results += self._detect_side_tiger(board, is_red_turn)

    # === v1.1 补充：语义层（静态） ===
    results += self._detect_phase(board)
    results += self._detect_king_safety(board, is_red_turn)
    results += self._detect_initiative(board, is_red_turn)
    results += self._detect_horse_leg_blocked(board)
    results += self._detect_kings_face_to_face(board)
    results += self._detect_cannon_battery(board)
    results += self._detect_favorable_exchange(board, is_red_turn)

    # === v1.1 补充：语义层（动态，需走法） ===
    if move:
        results += self._detect_forcing_move(board, move, is_red_turn)

    return results
```

---

## 六、性能影响评估

| 新增函数                               | 额外复杂度  | 说明                                           |
|----------------------------------------|-------------|------------------------------------------------|
| _detect_horse_corner                   | O(n)        | 只遍历己方马，少量棋子                         |
| _detect_bare_king                      | O(1)        | 定位两将后只扫一列                             |
| _detect_double_cannon_battery_checkmate| O(k²)       | k=炮数≤2，实际近似O(1)                         |
| _detect_sea_bottom_moon                | O(9)        | 只扫底线一行                                   |
| _detect_side_tiger                     | O(9)        | 只扫将/帅所在行                                |
| _detect_phase                          | O(90)       | 全棋盘计数一遍                                 |
| _detect_king_safety                    | O(n × 90)   | 最重的新函数；内层循环可缓存攻击范围后优化     |
| _detect_initiative                     | O(n²)       | 与原有 _detect_capture 同量级，可复用攻击缓存  |
| _detect_forcing_move（动态）           | O(n)        | 仅在有走法时触发                               |
| _detect_horse_leg_blocked              | O(n)        | 只检查马，常数级操作                           |
| _detect_kings_face_to_face             | O(10)       | 只扫一列                                       |
| _detect_cannon_battery                 | O(k²)       | k=炮数≤2，近似O(1)                             |
| _detect_favorable_exchange             | O(n²)       | 与原有捉子检测同量级                           |

**优化建议**：`_detect_king_safety` 的内层"威胁相邻格"统计对每个相邻格都要遍历全棋盘，
建议在完成攻击范围缓存（v1.0 §9.1 优化方向1）后，直接查询缓存表，
可将该函数复杂度从 O(n × m) 降至 O(1)（m=相邻格数）。

---

**文档版本**: v1.1（补充）
**最后更新**: 2026-03-14
**配套文件**: 03_4_TACTICAL_DETECTOR_ALGORITHM_.txt (v1.0)
