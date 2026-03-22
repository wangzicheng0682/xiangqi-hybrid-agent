# 核心矛盾分类器设计草案

## 一、设计目标

将"解释主线"从自由发挥改成**结构化判断**。

输入：语义状态 + 引擎分析
输出：核心矛盾类型 + 关键区域 + 支撑理由

---

## 二、矛盾类型体系

### 2.1 第一版矛盾类型（6类）

| 类型 | 编号 | 描述 | 触发条件 |
|------|------|------|----------|
| 中路争夺 | C01 | 双方争夺中路控制 | 中路有多个子力对峙 |
| 王安全 | C02 | 将/帅安全受威胁 | 一方分数剧烈波动 |
| 子力协调 | C03 | 子力配合问题 | 协调度评估差异大 |
| 结构弱点 | C04 | 兵/卒结构问题 | 孤兵或叠兵存在 |
| 优势转换 | C05 | 需要转换优势 | 一方明显优势 |
| 抢先手 | C06 | 争夺主动权 | 分数接近但都有威胁 |

### 2.2 矛盾类型详细定义

#### C01：中路争夺
```python
class MiddleControlConflict:
    """中路争夺矛盾"""
    
    def detect(self, board_state: dict, engine_analysis: dict) -> ConflictResult:
        middle_zone = [(row, col) for row in range(3, 7) for col in range(3, 6)]
        
        red_in_middle = sum(1 for pos in middle_zone if board_state['red_pieces'].get(pos))
        black_in_middle = sum(1 for pos in middle_zone if board_state['black_pieces'].get(pos))
        
        if red_in_middle >= 2 and black_in_middle >= 2:
            return ConflictResult(
                type='C01',
                name='中路争夺',
                region='中路',
                intensity='high' if red_in_middle + black_in_middle >= 6 else 'medium',
                reason=f'红方{red_in_middle}子vs黑方{black_in_middle}子在中路对峙'
            )
        
        return None
```

#### C02：王安全
```python
class KingSafetyConflict:
    """王安全矛盾"""
    
    def detect(self, board_state: dict, engine_analysis: dict) -> ConflictResult:
        score = engine_analysis['score']
        pv = engine_analysis['pv']
        
        has_check = any('check' in move.lower() for move in pv[:3])
        
        king_exposed = board_state.get('king_safety') != 'both_safe'
        
        if has_check or (king_exposed and abs(score) > 100):
            return ConflictResult(
                type='C02',
                name='王安全',
                region='红方九宫' if score < 0 else '黑方九宫',
                intensity='high' if has_check else 'medium',
                reason='将/帅安全受威胁'
            )
        
        return None
```

#### C03：子力协调
```python
class PieceCoordinationConflict:
    """子力协调矛盾"""
    
    def detect(self, board_state: dict, engine_analysis: dict) -> ConflictResult:
        coordination = board_state.get('piece_coordination', 'balanced')
        
        if coordination != 'balanced':
            return ConflictResult(
                type='C03',
                name='子力协调',
                region='全局',
                intensity='medium',
                reason=f'{coordination.replace("_", "方")}子力协调更好'
            )
        
        return None
```

#### C04：结构弱点
```python
class StructureWeaknessConflict:
    """结构弱点矛盾"""
    
    def detect(self, board_state: dict, engine_analysis: dict) -> ConflictResult:
        weaknesses = board_state.get('weaknesses', [])
        
        if weaknesses:
            return ConflictResult(
                type='C04',
                name='结构弱点',
                region=weaknesses[0].get('region', '未知'),
                intensity='low',
                reason=f'存在{len(weaknesses)}个结构弱点'
            )
        
        return None
```

#### C05：优势转换
```python
class AdvantageConversionConflict:
    """优势转换矛盾"""
    
    def detect(self, board_state: dict, engine_analysis: dict) -> ConflictResult:
        score = engine_analysis['score']
        material = board_state.get('material_balance', 'balanced')
        
        if abs(score) > 150:
            advantaged = 'red' if score > 0 else 'black'
            return ConflictResult(
                type='C05',
                name='优势转换',
                region='全局',
                intensity='medium',
                reason=f'{advantaged}方需要技术性着法转换优势'
            )
        
        return None
```

#### C06：抢先手
```python
class TempoConflict:
    """抢先手矛盾"""
    
    def detect(self, board_state: dict, engine_analysis: dict) -> ConflictResult:
        score = engine_analysis['score']
        pv = engine_analysis['pv']
        
        if abs(score) < 50 and len(pv) > 2:
            return ConflictResult(
                type='C06',
                name='抢先手',
                region='多变',
                intensity='low',
                reason='双方分数接近，都在争夺主动权'
            )
        
        return None
```

---

## 三、矛盾分类器架构

```python
class ContradictionClassifier:
    """核心矛盾分类器"""
    
    def __init__(self):
        self.detectors = [
            MiddleControlConflict(),
            KingSafetyConflict(),
            PieceCoordinationConflict(),
            StructureWeaknessConflict(),
            AdvantageConversionConflict(),
            TempoConflict(),
        ]
    
    def classify(self, fen: str, engine_analysis: dict) -> List[ConflictResult]:
        board_state = self._parse_board(fen)
        
        conflicts = []
        for detector in self.detectors:
            result = detector.detect(board_state, engine_analysis)
            if result:
                conflicts.append(result)
        
        conflicts.sort(key=lambda x: x.intensity_value, reverse=True)
        
        return conflicts
    
    def get_primary_conflict(self, fen: str, engine_analysis: dict) -> Optional[ConflictResult]:
        conflicts = self.classify(fen, engine_analysis)
        return conflicts[0] if conflicts else None
```

---

## 四、输入输出 Schema

### 4.1 输入

```python
{
    "fen": "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1",
    "semantic_labels": {
        "phase": "opening",
        "initiative": "balanced",
        "risk": "low",
        "structure": "closed",
        "tactics": "quiet"
    },
    "engine_analysis": {
        "score": 15.0,
        "best_move": "c3c4",
        "pv": ["c3c4", "c6c5", "h0g2", "h9g7"],
        "depth": 20
    }
}
```

### 4.2 输出

```python
{
    "primary_conflict": {
        "type": "C01",
        "name": "中路争夺",
        "region": "中路",
        "intensity": "medium",
        "reason": "红方3子vs黑方3子在中路对峙"
    },
    "secondary_conflicts": [
        {
            "type": "C06",
            "name": "抢先手",
            "region": "多变",
            "intensity": "low",
            "reason": "双方分数接近，都在争夺主动权"
        }
    ],
    "evidence_sources": ["engine", "rule"]
}
```

---

## 五、与解释系统对接

### 5.1 解释模板

```python
EXPLANATION_TEMPLATES = {
    'C01': {
        'title': '当前核心矛盾：中路争夺',
        'template': '局面核心在于{region}的争夺。{reason}。建议关注中路子力调动。',
        'priority_actions': ['控制中路要点', '调整子力位置', '防止对方突破']
    },
    'C02': {
        'title': '当前核心矛盾：王安全',
        'template': '局面核心在于{region}的攻防。{reason}。需要优先处理王的安全问题。',
        'priority_actions': ['加强防守', '兑子减轻压力', '寻找反击机会']
    },
    # ...
}
```

### 5.2 对接接口

```python
class ExplanationInterface:
    """与解释系统的对接接口"""
    
    def generate_explanation(self, fen: str, conflict_result: ConflictResult) -> str:
        template = EXPLANATION_TEMPLATES.get(conflict_result.type)
        
        if template:
            explanation = template['template'].format(
                region=conflict_result.region,
                reason=conflict_result.reason
            )
            return {
                'title': template['title'],
                'explanation': explanation,
                'priority_actions': template['priority_actions'],
                'intensity': conflict_result.intensity
            }
        
        return {'title': '分析中', 'explanation': '正在分析局面核心矛盾...'}
```

---

## 六、评估指标

### 6.1 准确率指标

| 指标 | 定义 | 目标 |
|------|------|------|
| 矛盾识别准确率 | 人工标注 vs 模型预测 | > 80% |
| 主矛盾正确率 | 主矛盾识别正确 | > 70% |
| 解释一致性 | 矛盾类型与解释一致 | > 90% |

### 6.2 测试集设计

- 100 个标注过的典型局面
- 覆盖 6 种矛盾类型
- 每种类型至少 10 个样本

---

## 七、开发计划

### Week 1：基础框架
- [ ] 实现 6 个矛盾检测器
- [ ] 实现分类器主类
- [ ] 单元测试

### Week 2：对接与优化
- [ ] 与语义标签生成器对接
- [ ] 与解释系统对接
- [ ] 评估与调优

### Week 3：集成测试
- [ ] 端到端测试
- [ ] 准确率评估
- [ ] 文档完善
