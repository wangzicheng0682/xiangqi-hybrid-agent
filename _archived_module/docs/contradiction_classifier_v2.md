# 核心矛盾分类器设计草案 v2.0

## 更新日志

### v2.0 新增
1. **主次矛盾裁决逻辑**：不再是简单按强度排序，而是基于引擎首选着解释度、语义标签统一度、后续变化影响度
2. **证据绑定规范**：明确哪些矛盾只能由引擎支持、哪些可以由规则支持、哪些只能标成推断
3. **层级关系**：事实层 → 语义状态 → 矛盾裁决 → 解释模板

---

## 一、系统层级架构

```
┌─────────────────────────────────────────────────────────┐
│                      事实层                              │
│  FEN解析 + 引擎分析 + 规则检测 + 历史信息                 │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                     语义状态                             │
│  阶段 + 主动权 + 风险 + 结构 + 战术活跃度 + 子力协调       │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                     矛盾裁决                             │
│  矛盾检测 → 主次裁决 → 证据绑定 → 优先级排序              │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                     解释模板                             │
│  标题 + 核心解释 + 优先行动 + 证据来源                    │
└─────────────────────────────────────────────────────────┘
```

---

## 二、矛盾类型体系（6类）

| 类型 | 编号 | 描述 | 最低证据要求 |
|------|------|------|--------------|
| 中路争夺 | C01 | 双方争夺中路控制 | 规则检测 |
| 王安全 | C02 | 将/帅安全受威胁 | **引擎必须** |
| 子力协调 | C03 | 子力配合问题 | 规则检测 |
| 结构弱点 | C04 | 兵/卒结构问题 | 规则检测 |
| 优势转换 | C05 | 需要转换优势 | **引擎必须** |
| 抢先手 | C06 | 争夺主动权 | 推断 |

---

## 三、主次矛盾裁决逻辑

### 3.1 裁决原则（优先级从高到低）

```python
class ConflictArbiter:
    """矛盾裁决器"""
    
    def arbitrate(self, conflicts: List[ConflictResult], 
                  engine_analysis: dict,
                  semantic_state: dict) -> ArbitrationResult:
        
        scored_conflicts = []
        
        for conflict in conflicts:
            score = 0
            
            # 原则1: 能解释引擎首选着 (+40分)
            if self._explains_best_move(conflict, engine_analysis):
                score += 40
            
            # 原则2: 能统一最多语义标签 (+30分)
            unified_count = self._count_unified_labels(conflict, semantic_state)
            score += unified_count * 10
            
            # 原则3: 影响后续3-5步变化 (+20分)
            if self._affects_future_moves(conflict, engine_analysis):
                score += 20
            
            # 原则4: 证据强度 (+10-30分)
            score += self._evidence_strength_score(conflict)
            
            # 原则5: 基础强度 (+0-20分)
            score += conflict.intensity_value * 10
            
            scored_conflicts.append((conflict, score))
        
        scored_conflicts.sort(key=lambda x: x[1], reverse=True)
        
        if scored_conflicts:
            primary = scored_conflicts[0][0]
            primary_score = scored_conflicts[0][1]
            secondary = [c for c, s in scored_conflicts[1:4] if s > primary_score * 0.5]
            
            return ArbitrationResult(
                primary_conflict=primary,
                secondary_conflicts=secondary,
                arbitration_scores={c.type: s for c, s in scored_conflicts}
            )
        
        return ArbitrationResult(primary_conflict=None, secondary_conflicts=[])
    
    def _explains_best_move(self, conflict: ConflictResult, 
                           engine_analysis: dict) -> bool:
        best_move = engine_analysis.get('best_move', '')
        pv = engine_analysis.get('pv', [])
        
        if conflict.type == 'C02':  # 王安全
            return any(self._is_check_related(m) for m in pv[:3])
        
        if conflict.type == 'C01':  # 中路争夺
            return self._move_targets_middle(best_move)
        
        if conflict.type == 'C04':  # 结构弱点
            return self._move_fixes_weakness(best_move, conflict)
        
        return False
    
    def _count_unified_labels(self, conflict: ConflictResult, 
                             semantic_state: dict) -> int:
        count = 0
        
        if conflict.type == 'C02':
            if semantic_state.get('risk') == 'high':
                count += 1
            if semantic_state.get('tactics') == 'active':
                count += 1
        
        if conflict.type == 'C01':
            if semantic_state.get('phase') == 'middlegame':
                count += 1
            if semantic_state.get('initiative') != 'balanced':
                count += 1
        
        return count
    
    def _affects_future_moves(self, conflict: ConflictResult,
                             engine_analysis: dict) -> bool:
        pv = engine_analysis.get('pv', [])
        
        if conflict.type in ['C02', 'C05']:
            return len(pv) > 3
        
        return False
    
    def _evidence_strength_score(self, conflict: ConflictResult) -> int:
        evidence_scores = {
            'engine': 30,
            'rule': 20,
            'inference': 10
        }
        
        return max(evidence_scores.get(e, 0) for e in conflict.evidence_sources)
```

### 3.2 裁决结果示例

```python
{
    "primary_conflict": {
        "type": "C02",
        "name": "王安全",
        "region": "黑方九宫",
        "intensity": "high",
        "reason": "红车威胁黑将，引擎首选着为防守"
    },
    "arbitration_scores": {
        "C02": 90,  # 解释首选着40 + 统一2标签20 + 影响后续20 + 引擎证据30 - 基础20
        "C01": 45,
        "C06": 30
    },
    "secondary_conflicts": [
        {
            "type": "C01",
            "name": "中路争夺",
            "region": "中路",
            "intensity": "medium"
        }
    ]
}
```

---

## 四、证据绑定规范

### 4.1 证据类型定义

| 证据类型 | 编号 | 可靠性 | 说明 |
|----------|------|--------|------|
| 引擎 | E01 | 高 | 来自Pikafish分析，depth>=12 |
| 规则 | E02 | 中 | 来自确定性规则检测 |
| 推断 | E03 | 低 | 基于模式的合理推断 |

### 4.2 矛盾-证据绑定矩阵

| 矛盾类型 | 引擎 | 规则 | 推断 | 最低要求 |
|----------|------|------|------|----------|
| C01 中路争夺 | ✓ | ✓ | ✗ | 至少规则 |
| C02 王安全 | **必须** | ✓ | ✗ | **必须引擎** |
| C03 子力协调 | ✗ | ✓ | ✓ | 至少规则 |
| C04 结构弱点 | ✗ | ✓ | ✓ | 至少规则 |
| C05 优势转换 | **必须** | ✗ | ✗ | **必须引擎** |
| C06 抢先手 | ✓ | ✗ | ✓ | 至少推断 |

### 4.3 证据绑定实现

```python
class EvidenceBinder:
    """证据绑定器"""
    
    EVIDENCE_REQUIREMENTS = {
        'C01': {'min_evidence': ['rule'], 'forbidden': []},
        'C02': {'min_evidence': ['engine'], 'forbidden': ['inference']},
        'C03': {'min_evidence': ['rule'], 'forbidden': []},
        'C04': {'min_evidence': ['rule'], 'forbidden': []},
        'C05': {'min_evidence': ['engine'], 'forbidden': ['rule', 'inference']},
        'C06': {'min_evidence': ['inference'], 'forbidden': []},
    }
    
    def bind_evidence(self, conflict: ConflictResult, 
                     engine_analysis: dict,
                     rule_results: dict) -> ConflictResult:
        
        req = self.EVIDENCE_REQUIREMENTS.get(conflict.type, {})
        evidence = []
        
        if req.get('min_evidence') == ['engine']:
            if not engine_analysis.get('depth', 0) >= 12:
                return None
            evidence.append('engine')
        
        if 'rule' in req.get('min_evidence', []):
            if rule_results.get(conflict.type):
                evidence.append('rule')
            else:
                return None
        
        if conflict.type == 'C06':
            evidence.append('inference')
        
        conflict.evidence_sources = evidence
        conflict.evidence_reliability = self._calc_reliability(evidence)
        
        return conflict
    
    def _calc_reliability(self, evidence: List[str]) -> str:
        if 'engine' in evidence:
            return 'high'
        elif 'rule' in evidence:
            return 'medium'
        else:
            return 'low'
```

### 4.4 证据在解释中的呈现

```python
EVIDENCE_TEMPLATES = {
    'engine': "引擎分析（depth={depth}）显示：{detail}",
    'rule': "根据{rule_name}规则：{detail}",
    'inference': "基于局面特征推断：{detail}"
}

def format_evidence(evidence_type: str, **kwargs) -> str:
    template = EVIDENCE_TEMPLATES.get(evidence_type, "{detail}")
    return template.format(**kwargs)
```

---

## 五、与解释系统的接口

### 5.1 接口定义

```python
@dataclass
class ExplanationInput:
    """解释系统输入"""
    fen: str
    primary_conflict: ConflictResult
    secondary_conflicts: List[ConflictResult]
    semantic_state: dict
    engine_analysis: dict
    arbitration_scores: dict

@dataclass
class ExplanationOutput:
    """解释系统输出"""
    title: str
    core_explanation: str
    priority_actions: List[str]
    evidence_chain: List[str]
    confidence: float
    related_knowledge: List[str]
```

### 5.2 解释生成器

```python
class ExplanationGenerator:
    """解释生成器"""
    
    CONFLICT_TEMPLATES = {
        'C01': {
            'title': '当前核心矛盾：中路争夺',
            'template': '局面核心在于{region}的争夺。{reason}。',
            'actions': ['控制中路要点', '调整子力位置', '防止对方突破']
        },
        'C02': {
            'title': '当前核心矛盾：王安全',
            'template': '局面核心在于{region}的攻防。{reason}。',
            'actions': ['加强防守', '兑子减轻压力', '寻找反击机会']
        },
        'C03': {
            'title': '当前核心矛盾：子力协调',
            'template': '局面核心在于{region}的子力配合。{reason}。',
            'actions': ['改善子力位置', '建立子力联系', '消除不协调子']
        },
        'C04': {
            'title': '当前核心矛盾：结构弱点',
            'template': '局面核心在于{region}的结构问题。{reason}。',
            'actions': ['加固弱点', '利用对方弱点', '简化局面']
        },
        'C05': {
            'title': '当前核心矛盾：优势转换',
            'template': '局面核心在于如何转换优势。{reason}。',
            'actions': ['简化优势', '扩大战果', '防止反扑']
        },
        'C06': {
            'title': '当前核心矛盾：抢先手',
            'template': '局面核心在于主动权的争夺。{reason}。',
            'actions': ['积极进取', '保持主动', '不给对方喘息']
        }
    }
    
    def generate(self, input_data: ExplanationInput) -> ExplanationOutput:
        conflict = input_data.primary_conflict
        
        if conflict is None:
            return self._default_explanation(input_data)
        
        template = self.CONFLICT_TEMPLATES.get(conflict.type)
        
        title = template['title']
        core = template['template'].format(
            region=conflict.region,
            reason=conflict.reason
        )
        
        evidence_chain = self._build_evidence_chain(
            conflict, 
            input_data.engine_analysis
        )
        
        confidence = self._calc_confidence(
            input_data.arbitration_scores,
            conflict.type
        )
        
        related = self._find_related_knowledge(conflict)
        
        return ExplanationOutput(
            title=title,
            core_explanation=core,
            priority_actions=template['actions'],
            evidence_chain=evidence_chain,
            confidence=confidence,
            related_knowledge=related
        )
    
    def _build_evidence_chain(self, conflict: ConflictResult, 
                             engine_analysis: dict) -> List[str]:
        chain = []
        
        for evidence in conflict.evidence_sources:
            if evidence == 'engine':
                chain.append(
                    f"引擎分析（depth={engine_analysis.get('depth', 'N/A')}）"
                    f"评分：{engine_analysis.get('score', 0):.1f}"
                )
            elif evidence == 'rule':
                chain.append(f"规则检测确认：{conflict.reason}")
            elif evidence == 'inference':
                chain.append(f"基于局面特征推断")
        
        return chain
    
    def _calc_confidence(self, scores: dict, primary_type: str) -> float:
        primary_score = scores.get(primary_type, 0)
        total_score = sum(scores.values())
        
        if total_score == 0:
            return 0.5
        
        return min(0.95, primary_score / 100)
    
    def _find_related_knowledge(self, conflict: ConflictResult) -> List[str]:
        knowledge_map = {
            'C01': ['中路控制原理', '中心化原则', '空间优势'],
            'C02': ['王安全原则', '防守技巧', '兑子简化'],
            'C03': ['子力协调', '双车配合', '马炮联攻'],
            'C04': ['兵卒结构', '弱点攻击', '叠兵孤兵'],
            'C05': ['优势转换', '技术性着法', '简化技巧'],
            'C06': ['主动权', '先手原则', '节奏控制']
        }
        
        return knowledge_map.get(conflict.type, [])
```

### 5.3 完整输出示例

```python
{
    "title": "当前核心矛盾：王安全",
    "core_explanation": "局面核心在于黑方九宫的攻防。红车威胁黑将，引擎首选着为防守。",
    "priority_actions": [
        "加强防守",
        "兑子减轻压力",
        "寻找反击机会"
    ],
    "evidence_chain": [
        "引擎分析（depth=20）评分：-156.3",
        "规则检测确认：红车直接威胁黑将"
    ],
    "confidence": 0.90,
    "related_knowledge": [
        "王安全原则",
        "防守技巧",
        "兑子简化"
    ],
    "secondary_summary": "次要矛盾：中路争夺（中等强度）"
}
```

---

## 六、系统流程图

```
输入FEN
    │
    ▼
┌─────────────────┐
│   事实层处理     │ ← 引擎分析 + 规则检测
└─────────────────┘
    │
    ▼
┌─────────────────┐
│   语义状态生成   │ ← 语义标签生成器
└─────────────────┘
    │
    ▼
┌─────────────────┐
│   矛盾检测      │ ← 6个矛盾检测器
└─────────────────┘
    │
    ▼
┌─────────────────┐
│   证据绑定      │ ← 检查最低证据要求
└─────────────────┘
    │
    ▼
┌─────────────────┐
│   主次裁决      │ ← 裁决器打分排序
└─────────────────┘
    │
    ▼
┌─────────────────┐
│   解释生成      │ ← 模板 + 证据链
└─────────────────┘
    │
    ▼
输出解释结果
```

---

## 七、开发计划

### Week 1：核心实现
- [ ] 实现裁决器（ConflictArbiter）
- [ ] 实现证据绑定器（EvidenceBinder）
- [ ] 实现解释生成器（ExplanationGenerator）

### Week 2：集成测试
- [ ] 与语义标签生成器集成
- [ ] 100个样本的端到端测试
- [ ] 准确率评估

### Week 3：优化与文档
- [ ] 根据测试结果调优
- [ ] 完善解释模板
- [ ] 编写API文档
