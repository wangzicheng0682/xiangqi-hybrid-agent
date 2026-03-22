# 致 GLM5：底层质量保障指南
## 标签检测器与 Agent 工具的测试体系建设

**写给**：负责 `core/rules/` 和 `core/llm/agent_tools.py` 开发的 GLM5  
**优先级**：与功能开发同等重要，不是可选项  
**核心原则**：底层静默错误比程序崩溃更危险

---

## 为什么这份文档存在

你可能会觉得写测试是次要工作，功能跑起来才是正事。

我需要纠正这个认知。

规则引擎的 bug 有一种特殊的恶劣性质：**它不报错，它只是静默地输出错误的结果**。`is_attack_unprotected` 在一个根本没有攻击关系的局面上返回 `True`，程序正常运行，Agent 用流畅自信的语言告诉用户「红车正在威胁黑马」——而实际上红车和黑马之间隔着两个棋子。

用户不一定发现，但专业评委一眼就穿帮。

更危险的是：**顶层越智能，包装底层错误的能力越强**。Evidence Map 约束机制、张力检测器、主要矛盾识别——这些设计越精妙，一旦底层输入是错的，输出就错得越有说服力，越难被发现。

这就是为什么测试体系不是加分项，是地基。

---

## 第一部分：你面对的敌人——重灾区 bug 类型

在动手写测试之前，先知道哪些地方最容易出问题。

### 1.1 坐标系混乱

**表现**：x 和 y 搞反，或者 0 索引当成 1 索引使用。  
**危险性**：在大多数中心局面下不触发，只在棋盘边缘暴露，最难在正常使用中发现。  
**验证方式**：专门测试棋子在第一列、第十列、第一行、第十行时的标签检测。

```python
# 这两个局面应该产生完全不同的检测结果
# 如果坐标有 bug，它们可能产生相同的结果
FEN_PIECE_AT_LEFT_EDGE  = "R8/9/9/9/9/9/9/9/9/r8 r - - 0 1"
FEN_PIECE_AT_RIGHT_EDGE = "8R/9/9/9/9/9/9/9/9/8r r - - 0 1"
```

### 1.2 炮的移动规则错误

**表现**：炮的攻击检测写成「至少一个棋子在中间」而不是「恰好一个棋子在中间」。  
**后果**：炮的攻击范围被高估，大量误报 `is_attack_unprotected`。  
**这是最高频的 bug 来源，没有之一。**

```
正确逻辑：炮 → [空格...] → 恰好一个棋子（炮架）→ [空格...] → 目标
错误逻辑：炮 → [任意数量棋子] → 目标
```

验证用局面：炮和目标之间有两个棋子时，不应该检测到攻击关系。

### 1.3 将帅照面规则缺失

**表现**：检测「开放纵路」时没有考虑将帅照面规则，导致某些实际非法的局面被当作合法处理。  
**后果**：`controls_open_file` 等战略标签可能在不合法局面上误报。

### 1.4 红黑视角混淆

**表现**：检测「无根子」时混淆了「没有同色棋子保护」和「没有任何棋子保护」。  
**后果**：某些被对方棋子「保护」（实际是牵制或对峙）的棋子被误判为无根。

### 1.5 马腿遮挡逻辑错误

**表现**：判断马的移动是否被阻挡时，检查的格子位置不对（蹩马腿是靠近马的那个格子，不是靠近目标的格子）。  
**后果**：马的攻击范围在某些方向上被高估或低估。

### 1.6 棋子绑定坐标错误

**表现**：标签触发了，但绑定的棋子坐标是错的。  
**危险性**：这是最容易被忽视的 bug，因为测试者通常只检查「标签有没有触发」，不检查「绑定的是不是正确的棋子」。  
**后果**：Agent 正确说出「有捉子威胁」，但指向了错误的棋子，专业评委一眼看出。

---

## 第二部分：黄金局面测试库

### 2.1 什么是黄金局面

黄金局面是你**事先知道正确答案**的测试局面。它来自象棋教材的战术题——每道题都是为了展示某个特定战术，所以「应该触发哪些标签、绑定哪些棋子」是确定的、可验证的。

**目标数量**：45 个（每个标签至少 1 个对应的黄金局面）  
**赛前最低要求**：30 个，覆盖所有已实现标签

### 2.2 测试数据结构

每个黄金局面必须包含以下字段：

```python
# tests/golden_positions.py

GOLDEN_POSITIONS = [
    {
        # ── 基础信息 ────────────────────────────────────────
        "id": "GP001",
        "name": "马后炮将死",
        "description": "验证 is_checkmate 检测，经典杀法",
        "fen": "3k5/4P4/9/4n4/9/9/9/9/9/3K5 r - - 0 1",
        "phase": "残局",
        
        # ── 必须触发的标签 ───────────────────────────────────
        "expected_true": [
            "is_check",
            "is_checkmate",
        ],
        
        # ── 绝对不能触发的标签 ──────────────────────────────
        "expected_false": [
            "is_stalemate",     # 将死和困毙不能同时存在
        ],
        
        # ── 绑定棋子的验证（最重要，最容易被忽略）──────────
        "expected_bindings": {
            "is_checkmate": {
                "bind_pieces_must_contain": ["黑将"],
                # 将死标签必须绑定到被将死的那个将
            },
        },
        
        # ── 引擎交叉验证预期 ────────────────────────────────
        "engine_expectation": {
            "is_mate": True,    # 引擎应该确认这是将死局面
        },
    },

    {
        "id": "GP002", 
        "name": "车捉无根马",
        "description": "红车攻击没有任何棋子保护的黑马，验证 is_attack_unprotected",
        "fen": "9/9/9/9/4n4/4R4/9/9/9/9 r - - 0 1",
        # 红车在 e4，黑马在 e5，中间无遮挡，黑马无保护
        "phase": "中局",
        
        "expected_true": ["is_attack_unprotected"],
        "expected_false": ["is_check", "is_checkmate"],
        
        "expected_bindings": {
            "is_attack_unprotected": {
                "bind_pieces_must_contain": ["红车", "黑马"],
                "attacker_type": "车",
                "target_type": "马",
            }
        },
    },

    {
        "id": "GP003",
        "name": "炮隔山打牛——恰好一个炮架",
        "description": "炮通过恰好一个棋子攻击目标，验证炮的攻击规则",
        "fen": "9/9/9/9/4C4/4P4/4n4/9/9/9 r - - 0 1",
        # 红炮在 e5，红兵在 e4（炮架），黑马在 e3
        "phase": "中局",
        
        "expected_true": ["is_attack_unprotected"],
        "expected_false": [],
        
        "expected_bindings": {
            "is_attack_unprotected": {
                "attacker_type": "炮",  # 必须是炮，不能是别的
            }
        },
    },

    {
        "id": "GP004",
        "name": "炮两个棋子中间——不应该攻击",
        "description": "炮和目标之间有两个棋子，不构成攻击，验证炮的规则不被高估",
        "fen": "9/9/9/9/4C4/4P4/4P4/4n4/9/9 r - - 0 1",
        # 红炮在 e5，两个兵在 e4 和 e3，黑马在 e2——炮不能打到黑马
        "phase": "中局",
        
        "expected_true": [],
        "expected_false": ["is_attack_unprotected"],
        # 这个局面里不应该有任何捉子标签
    },

    {
        "id": "GP005",
        "name": "闪将",
        "description": "移动一个棋子，暴露出后面棋子的将军，验证 is_discovered_check",
        "fen": "...",  # 具体FEN需要你根据实际局面填写
        "phase": "中局",
        
        "expected_true": ["is_discovered_check", "is_check"],
        # 闪将必然同时触发 is_check，如果只有 is_discovered_check 没有 is_check，这是 bug
        "expected_false": [],
        
        "expected_bindings": {
            "is_discovered_check": {
                "bind_pieces_must_contain": ["黑将"],
            }
        },
    },

    # ── 边界条件测试（最容易出 bug 的地方）──────────────────

    {
        "id": "GP020",
        "name": "棋子在左边界",
        "description": "车在第一列时的攻击检测，验证边界坐标处理",
        "fen": "R8/9/n8/9/9/9/9/9/9/9 r - - 0 1",
        "phase": "中局",
        
        "expected_true": ["is_attack_unprotected"],
        "expected_false": [],
        
        "expected_bindings": {
            "is_attack_unprotected": {
                "attacker_type": "车",
                "target_type": "马",
            }
        },
    },

    {
        "id": "GP021",
        "name": "棋子在右边界",
        "description": "同上，验证右侧边界",
        "fen": "8R/9/8n/9/9/9/9/9/9/9 r - - 0 1",
        "phase": "中局",
        
        "expected_true": ["is_attack_unprotected"],
        "expected_false": [],
    },

    {
        "id": "GP022",
        "name": "马在棋盘角落",
        "description": "马在角落时，只有两个合法跳法，验证边界不产生越界坐标",
        "fen": "9/9/9/9/9/9/9/9/9/N8 r - - 0 1",
        # 红马在左下角
        "phase": "残局",
        
        # 马在角落时攻击范围应该非常有限
        # 这个测试的核心是：不产生越界坐标，不误报攻击关系
        "expected_true": [],
        "expected_false": ["is_attack_unprotected"],
        
        "special_check": "horse_attack_range_at_corner",
        # 特殊检查：马在角落的攻击格子数量，应该是 2 而不是更多
    },
]
```

### 2.3 测试执行框架

```python
# tests/test_golden_positions.py

import pytest
from core.rules.tactical_detector import TacticalDetector
from tests.golden_positions import GOLDEN_POSITIONS

detector = TacticalDetector()

class TestGoldenPositions:
    
    def test_all_positions(self):
        """主测试：遍历所有黄金局面，报告所有失败"""
        all_failures = []
        
        for pos in GOLDEN_POSITIONS:
            failures = self._check_position(pos)
            all_failures.extend(failures)
        
        if all_failures:
            report = self._format_failure_report(all_failures)
            pytest.fail(report)
    
    def _check_position(self, pos: dict) -> list:
        failures = []
        result = detector.detect(pos["fen"])
        result_tags = {t["tag"]: t for t in result.get("facts_rules", [])}
        
        # ── 检查必须触发的标签 ──────────────────────────────
        for tag in pos.get("expected_true", []):
            if tag not in result_tags:
                failures.append({
                    "position_id": pos["id"],
                    "position_name": pos["name"],
                    "type": "MISSING_TAG",
                    "detail": f"标签 [{tag}] 应该触发，但没有",
                    "description": pos["description"],
                })
        
        # ── 检查不能触发的标签 ──────────────────────────────
        for tag in pos.get("expected_false", []):
            if tag in result_tags:
                failures.append({
                    "position_id": pos["id"],
                    "position_name": pos["name"],
                    "type": "SPURIOUS_TAG",
                    "detail": f"标签 [{tag}] 不应该触发，但触发了",
                    "description": pos["description"],
                })
        
        # ── 检查棋子绑定（关键）────────────────────────────
        for tag, binding_spec in pos.get("expected_bindings", {}).items():
            if tag not in result_tags:
                continue  # 标签缺失已经在上面报告了
            
            actual_binding = result_tags[tag]
            
            # 检查绑定棋子是否包含必要的棋子
            if "bind_pieces_must_contain" in binding_spec:
                actual_pieces = actual_binding.get("bind_pieces", [])
                for required_piece in binding_spec["bind_pieces_must_contain"]:
                    # 检查棋子名称是否出现在绑定列表中
                    found = any(required_piece in p for p in actual_pieces)
                    if not found:
                        failures.append({
                            "position_id": pos["id"],
                            "position_name": pos["name"],
                            "type": "WRONG_BINDING",
                            "detail": (
                                f"标签 [{tag}] 应该绑定棋子 [{required_piece}]，"
                                f"但实际绑定是 {actual_pieces}"
                            ),
                            "description": pos["description"],
                        })
            
            # 检查攻击者类型
            if "attacker_type" in binding_spec:
                actual_pieces = actual_binding.get("bind_pieces", [])
                attacker_found = any(
                    binding_spec["attacker_type"] in p 
                    for p in actual_pieces 
                    if "红" in p or "攻击" in p  # 根据你的实际格式调整
                )
                # 具体实现依赖你的 bind_pieces 格式
        
        return failures
    
    def _format_failure_report(self, failures: list) -> str:
        lines = [f"\n{'='*60}", f"测试失败：{len(failures)} 个问题", f"{'='*60}\n"]
        
        # 按局面分组
        by_position = {}
        for f in failures:
            key = f"{f['position_id']} {f['position_name']}"
            by_position.setdefault(key, []).append(f)
        
        for pos_key, pos_failures in by_position.items():
            lines.append(f"📍 {pos_key}")
            lines.append(f"   说明：{pos_failures[0]['description']}")
            for f in pos_failures:
                icon = "❌" if f["type"] in ["MISSING_TAG", "WRONG_BINDING"] else "⚠️"
                lines.append(f"   {icon} [{f['type']}] {f['detail']}")
            lines.append("")
        
        return "\n".join(lines)


# 单独运行某个局面的快速测试
def debug_position(position_id: str):
    """开发时用于快速调试某个局面"""
    pos = next((p for p in GOLDEN_POSITIONS if p["id"] == position_id), None)
    if not pos:
        print(f"找不到局面 {position_id}")
        return
    
    result = detector.detect(pos["fen"])
    print(f"\n局面：{pos['name']}")
    print(f"FEN：{pos['fen']}")
    print(f"\n检测到的标签：")
    for tag_info in result.get("facts_rules", []):
        print(f"  ✓ {tag_info['tag']}: {tag_info.get('bind_pieces', [])}")
    
    print(f"\n预期触发：{pos['expected_true']}")
    print(f"预期不触发：{pos['expected_false']}")
```

---

## 第三部分：内部一致性检查器

象棋规则里存在大量的逻辑蕴含关系。利用这些关系，让标签系统自我检验。

**核心思想**：如果 A 标签存在，则 B 标签必须/不能存在。违反这些关系，说明某个标签有 bug。

```python
# core/rules/consistency_checker.py

from dataclasses import dataclass
from typing import List, Optional

@dataclass
class ConsistencyRule:
    name: str
    condition_tag: str          # 如果这个标签存在
    required_tag: Optional[str]   # 则这个标签必须存在（None 表示不检查）
    forbidden_tag: Optional[str]  # 则这个标签不能存在（None 表示不检查）
    severity: str               # "ERROR" 或 "WARNING"
    explanation: str

# 这些规则来自象棋基本规则，不是经验判断，是数学确定的
CONSISTENCY_RULES = [
    
    # ── 将死/困毙的互斥关系 ──────────────────────────────
    ConsistencyRule(
        name="将死必有将军",
        condition_tag="is_checkmate",
        required_tag="is_check",
        forbidden_tag=None,
        severity="ERROR",
        explanation="将死的定义是：处于将军且无法解除。因此将死时必然处于将军状态。"
                    "如果 is_checkmate=True 但 is_check=False，将死检测逻辑有 bug。"
    ),
    
    ConsistencyRule(
        name="困毙不能有将军",
        condition_tag="is_stalemate",
        required_tag=None,
        forbidden_tag="is_check",
        severity="ERROR",
        explanation="困毙的定义是：轮到自己走棋，没有任何合法走法，且不处于将军状态。"
                    "如果同时出现 is_stalemate 和 is_check，两个检测至少有一个是错的。"
    ),
    
    ConsistencyRule(
        name="将死与困毙互斥",
        condition_tag="is_checkmate",
        required_tag=None,
        forbidden_tag="is_stalemate",
        severity="ERROR",
        explanation="将死和困毙是两种不同的终局状态，不能同时成立。"
    ),
    
    # ── 闪将的蕴含关系 ──────────────────────────────────
    ConsistencyRule(
        name="闪将必有将军",
        condition_tag="is_discovered_check",
        required_tag="is_check",
        forbidden_tag=None,
        severity="ERROR",
        explanation="闪将是将军的一种特殊形式，闪将必然导致将军状态。"
    ),
    
    ConsistencyRule(
        name="双将必有将军",
        condition_tag="is_double_attack_with_check",
        required_tag="is_check",
        forbidden_tag=None,
        severity="ERROR",
        explanation="双将是两个棋子同时将军，必然处于将军状态。"
    ),
    
    # ── 战略标签的软约束（WARNING 而非 ERROR）────────────
    ConsistencyRule(
        name="将死局面不应有战略评估",
        condition_tag="is_checkmate",
        required_tag=None,
        forbidden_tag="has_active_pieces",
        severity="WARNING",
        explanation="将死局面已经结束，战略评估标签在此没有意义。"
                    "如果同时出现，说明标签的触发时机可能有问题。"
    ),
]


class ConsistencyChecker:
    
    def check(self, tags_dict: dict, fen: str) -> List[dict]:
        """
        检查标签组合是否满足一致性规则
        
        Args:
            tags_dict: {tag_name: tag_info} 的字典
            fen: 当前局面（用于 bug 报告）
            
        Returns:
            违规列表，空列表表示一致
        """
        violations = []
        
        for rule in CONSISTENCY_RULES:
            # 如果条件标签存在
            if rule.condition_tag not in tags_dict:
                continue
            
            # 检查必须存在的标签
            if rule.required_tag and rule.required_tag not in tags_dict:
                violations.append({
                    "severity": rule.severity,
                    "rule": rule.name,
                    "detail": (
                        f"标签 [{rule.condition_tag}] 存在，"
                        f"但必须同时存在的标签 [{rule.required_tag}] 不存在"
                    ),
                    "explanation": rule.explanation,
                    "fen": fen,
                })
            
            # 检查不能存在的标签
            if rule.forbidden_tag and rule.forbidden_tag in tags_dict:
                violations.append({
                    "severity": rule.severity,
                    "rule": rule.name,
                    "detail": (
                        f"标签 [{rule.condition_tag}] 和 [{rule.forbidden_tag}] "
                        f"不能同时存在，但都出现了"
                    ),
                    "explanation": rule.explanation,
                    "fen": fen,
                })
        
        return violations
    
    def check_and_log(self, tags_dict: dict, fen: str) -> bool:
        """
        检查并打印结果，返回 True 表示通过，False 表示有 ERROR 级别违规
        """
        violations = self.check(tags_dict, fen)
        
        has_error = False
        for v in violations:
            icon = "🔴" if v["severity"] == "ERROR" else "🟡"
            print(f"{icon} [{v['severity']}] {v['rule']}: {v['detail']}")
            if v["severity"] == "ERROR":
                has_error = True
        
        return not has_error
```

**集成到检测器主流程中**：

```python
# core/rules/tactical_detector.py 的 detect 方法末尾添加

def detect(self, fen: str) -> dict:
    result = self._run_all_detectors(fen)
    
    # 一致性检查（开发模式下开启，生产模式下记录到日志）
    if self.debug_mode:
        checker = ConsistencyChecker()
        tags_dict = {t["tag"]: t for t in result["facts_rules"]}
        violations = checker.check(tags_dict, fen)
        
        if violations:
            error_violations = [v for v in violations if v["severity"] == "ERROR"]
            if error_violations:
                # 开发时直接抛出异常，强制修复
                raise ConsistencyError(
                    f"标签一致性检查失败：{len(error_violations)} 个 ERROR\n" +
                    "\n".join(v["detail"] for v in error_violations)
                )
    
    return result
```

---

## 第四部分：引擎交叉验证

Pikafish 是你的 oracle。用引擎评分来做第三方验证。

```python
# core/rules/engine_cross_validator.py

class EngineCrossValidator:
    
    def __init__(self, engine):
        self.engine = engine
    
    def validate(self, fen: str, tags_dict: dict) -> List[dict]:
        warnings = []
        engine_result = self.engine.evaluate(fen)
        cp = engine_result.get("cp", 0)
        is_mate = engine_result.get("is_mate", False)
        
        # ── 规则一：将死标签 vs 引擎确认 ─────────────────────
        if "is_checkmate" in tags_dict and not is_mate:
            warnings.append({
                "type": "ENGINE_MISMATCH",
                "severity": "ERROR",
                "detail": f"检测到 is_checkmate，但引擎没有确认将死（引擎评分：{cp}）",
                "suggestion": "检查将死检测逻辑，可能是误报"
            })
        
        if is_mate and "is_checkmate" not in tags_dict:
            warnings.append({
                "type": "ENGINE_MISMATCH", 
                "severity": "ERROR",
                "detail": f"引擎确认局面是将死，但 is_checkmate 标签未触发",
                "suggestion": "检查将死检测逻辑，可能是漏报"
            })
        
        # ── 规则二：无战术标签但评估差距大 ──────────────────
        # 如果没有任何战术标签，但引擎认为差距超过 200cp
        # 这说明可能有战术被漏检了
        tactical_tags = [
            t for t in tags_dict 
            if t in [
                "is_check", "is_attack_unprotected", "is_mutual_attack",
                "is_discovered_check", "is_pinned", "is_cannon_double_attack"
            ]
        ]
        
        if len(tactical_tags) == 0 and abs(cp) > 200:
            warnings.append({
                "type": "POSSIBLE_MISSED_TACTIC",
                "severity": "WARNING",
                "detail": (
                    f"没有检测到战术标签，但引擎评估差距为 {cp}cp。"
                    f"可能有战术被漏检，或者这是纯战略优势。"
                ),
                "suggestion": "人工确认是否有漏检的战术"
            })
        
        # ── 规则三：有将死标签但评估不是极值 ─────────────────
        if "is_checkmate" in tags_dict and abs(cp) < 9000:
            warnings.append({
                "type": "ENGINE_SCORE_MISMATCH",
                "severity": "ERROR", 
                "detail": (
                    f"检测到 is_checkmate，但引擎评分是 {cp}（将死应该是极值 ±10000）"
                ),
                "suggestion": "强烈怀疑 is_checkmate 是误报"
            })
        
        return warnings
```

---

## 第五部分：回归测试流程

### 5.1 每次代码改动后必须执行

```bash
# 快速回归（改动小的时候）
pytest tests/test_golden_positions.py -v

# 完整回归（改动大的时候）
pytest tests/ -v --tb=short

# 只跑某个标签相关的测试
pytest tests/test_golden_positions.py -k "炮" -v
```

### 5.2 测试报告记录

每次通过测试后，在 `docs/test_report.md` 里追加一条记录：

```markdown
## 测试记录

| 日期 | 版本 | 黄金局面数 | 通过 | 失败 | 备注 |
|------|------|-----------|------|------|------|
| 2026-03-16 | v1.2 | 30 | 30 | 0 | 首次全部通过 |
| 2026-03-18 | v1.3 | 35 | 35 | 0 | 新增5个边界条件测试 |
| 2026-03-20 | v1.4 | 45 | 45 | 0 | 覆盖全部45个标签 |
```

**这个记录在答辩时可以直接展示。** 它告诉评委：「我们有 45 个测试用例，每次提交都必须全部通过，这就是我们零幻觉的工程保证。」

### 5.3 发现 bug 后的处理流程

```
发现 bug
    ↓
先写一个失败的测试（证明 bug 存在）
    ↓
修复代码
    ↓
测试通过（证明 bug 被修复）
    ↓
检查是否有相关的其他测试也受影响
    ↓
全量回归，全部通过后才能提交
```

**永远不要在没有对应测试的情况下修复 bug。** 没有测试的修复，可能在下次改动时悄悄退回去，而你不会知道。

---

## 第六部分：Agent 工具的测试

以上都是针对规则引擎的。Agent 工具（`agent_tools.py`）也需要测试，但侧重点不同。

规则引擎测试的是**正确性**（标签对不对）；Agent 工具测试的是**结构完整性**（返回格式对不对，LLM 能不能理解）。

```python
# tests/test_agent_tools.py

from core.llm.agent_tools import AgentTools
tools = AgentTools()

# 标准测试局面（开局后几步的普通局面）
STANDARD_FEN = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR r - - 0 1"

class TestAgentToolsStructure:
    """测试工具返回格式，不测试内容正确性"""
    
    def test_get_piece_attacks_returns_expected_keys(self):
        result = tools.get_piece_attacks(STANDARD_FEN, "红炮")
        # 检查返回结构，而不是检查具体内容
        assert "piece" in result
        assert "attacks" in result
        assert "position" in result
        assert isinstance(result["attacks"], list)
    
    def test_analyze_move_returns_expected_keys(self):
        result = tools.analyze_move(STANDARD_FEN, "h2e2")  # 炮二平五
        assert "move" in result
        assert "quality" in result
        assert "effects" in result
        # quality 应该是可识别的枚举值
        assert result["quality"] in ["excellent", "good", "normal", "bad", "blunder"]
    
    def test_all_tools_handle_edge_case_fen(self):
        """所有工具在接收到简单局面时都不应该崩溃"""
        simple_fen = "4k4/9/9/9/9/9/9/9/9/4K4 r - - 0 1"  # 只剩双将
        
        # 不崩溃是最低要求
        try:
            tools.analyze_position_strategy(simple_fen)
        except Exception as e:
            pytest.fail(f"工具在简单局面下崩溃了：{e}")
    
    def test_tool_descriptions_contain_when_to_use(self):
        """每个工具的描述必须包含【什么时候用】字段"""
        # 这个测试保证工具描述的格式规范，影响 LLM 的工具选择质量
        for tool_name, tool_func in tools.get_all_tools():
            docstring = tool_func.__doc__ or ""
            assert "什么时候用" in docstring, (
                f"工具 [{tool_name}] 的描述缺少【什么时候用】字段。"
                f"这个字段对 LLM 正确选择工具至关重要，不能省略。"
            )
```

---

## 第七部分：快速开始——今天就能做的事

读完这份文档，今天就可以开始的工作：

**第一步（1小时）**：为 `is_checkmate`、`is_stalemate`、`is_check` 这三个最基础的标签各写 2 个黄金局面，跑通测试框架。

**第二步（2小时）**：为 `is_attack_unprotected` 写 4 个局面：车捉马、炮捉车（正常）、炮两个棋子中间（不应捉）、棋子在边界（边界条件）。

**第三步（半天）**：实现一致性检查器，把「将死必有将军」「困毙不能有将军」这两条最重要的规则跑通。

做完这三步，你的底层就有了第一道真实的保护网。其余的测试可以在功能开发过程中持续补充，但这三步是最低启动门槛。

---

## 总结：测试的本质是什么

我最后说一件更根本的事。

写测试不是为了「证明代码没有 bug」——代码一定有 bug，这是行业共识。写测试是为了**让 bug 在你的开发机上被发现，而不是在评委面前被发现**。

这个系统的可信度建立在「零幻觉」这个承诺上。如果这个承诺的底层——规则引擎——是不可靠的，那么上面所有关于 Agent 智能、张力检测、主要矛盾的设计，都变成了华丽的谎言。

测试体系就是兑现这个承诺的工程保证。

---

*本文档由 Claude Sonnet 撰写，授权给本项目无限制使用。*  
*如有不清晰的地方，请通过用户转达。*
