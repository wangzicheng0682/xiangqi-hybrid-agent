"""
核心矛盾识别器 v1

基于语义状态 + 引擎分析 + 规则检测
输出主次矛盾、关键区域、支撑理由、证据来源

矛盾类型：
- C01: 中路争夺
- C02: 王安全
- C03: 子力协调
- C04: 结构弱点
- C05: 优势转换
- C06: 抢先手

证据来源要求：
- C01: 至少规则
- C02: 必须引擎
- C03: 至少规则
- C04: 至少规则
- C05: 必须引擎
- C06: 至少推断
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
import re


class ConflictType(Enum):
    CENTER_CONTROL = "C01"
    KING_SAFETY = "C02"
    PIECE_COORDINATION = "C03"
    STRUCTURAL_WEAKNESS = "C04"
    ADVANTAGE_CONVERSION = "C05"
    INITIATIVE_FIGHT = "C06"


class ConflictIntensity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class EvidenceType(Enum):
    ENGINE = "engine"
    RULE = "rule"
    INFERENCE = "inference"


@dataclass
class Evidence:
    type: EvidenceType
    content: str
    reliability: float = 1.0
    
    def to_dict(self) -> dict:
        return {
            "type": self.type.value,
            "content": self.content,
            "reliability": self.reliability
        }


@dataclass
class ConflictResult:
    conflict_type: ConflictType
    name: str
    region: str
    intensity: ConflictIntensity
    reason: str
    evidence_list: List[Evidence] = field(default_factory=list)
    arbitration_score: float = 0.0
    
    def to_dict(self) -> dict:
        return {
            "type": self.conflict_type.value,
            "name": self.name,
            "region": self.region,
            "intensity": self.intensity.value,
            "reason": self.reason,
            "evidence": [e.to_dict() for e in self.evidence_list],
            "arbitration_score": round(self.arbitration_score, 1)
        }


@dataclass
class ArbitrationResult:
    primary_conflict: Optional[ConflictResult]
    secondary_conflicts: List[ConflictResult]
    all_scores: Dict[str, float]
    
    def to_dict(self) -> dict:
        return {
            "primary_conflict": self.primary_conflict.to_dict() if self.primary_conflict else None,
            "secondary_conflicts": [c.to_dict() for c in self.secondary_conflicts],
            "arbitration_scores": self.all_scores,
            "summary": self._generate_summary()
        }
    
    def _generate_summary(self) -> str:
        if not self.primary_conflict:
            return "未检测到明显矛盾"
        
        summary = f"主矛盾：{self.primary_conflict.name}"
        if self.secondary_conflicts:
            secondary_names = [c.name for c in self.secondary_conflicts[:2]]
            summary += f"；次矛盾：{', '.join(secondary_names)}"
        return summary


class ConflictDetector:
    """矛盾检测器基类"""
    
    CONFLICT_TYPE: ConflictType = None
    CONFLICT_NAME: str = ""
    MIN_EVIDENCE: List[EvidenceType] = []
    FORBIDDEN_EVIDENCE: List[EvidenceType] = []
    
    def detect(
        self,
        semantic_state: Dict,
        engine_result: Optional[Dict],
        rule_features: Dict
    ) -> Optional[ConflictResult]:
        raise NotImplementedError
    
    def _check_evidence_requirements(self, evidence_list: List[Evidence]) -> bool:
        evidence_types = [e.type for e in evidence_list]
        
        for req in self.MIN_EVIDENCE:
            if req not in evidence_types:
                return False
        
        for forbidden in self.FORBIDDEN_EVIDENCE:
            if forbidden in evidence_types:
                return False
        
        return True


class CenterControlDetector(ConflictDetector):
    """C01: 中路争夺检测"""
    
    CONFLICT_TYPE = ConflictType.CENTER_CONTROL
    CONFLICT_NAME = "中路争夺"
    MIN_EVIDENCE = [EvidenceType.RULE]
    FORBIDDEN_EVIDENCE = []
    
    def detect(
        self,
        semantic_state: Dict,
        engine_result: Optional[Dict],
        rule_features: Dict
    ) -> Optional[ConflictResult]:
        board_rows = rule_features.get('board_rows', [])
        
        center_control = self._analyze_center_control(board_rows)
        
        if center_control['tension'] < 0.3:
            return None
        
        evidence_list = []
        
        evidence_list.append(Evidence(
            type=EvidenceType.RULE,
            content=f"中路子力密度：红方{center_control['red_center']}，黑方{center_control['black_center']}",
            reliability=0.8
        ))
        
        if engine_result and 'pv' in engine_result:
            pv = engine_result['pv']
            center_moves = self._count_center_moves(pv, board_rows)
            if center_moves > 0:
                evidence_list.append(Evidence(
                    type=EvidenceType.ENGINE,
                    content=f"引擎PV线包含{center_moves}步中路相关着法",
                    reliability=0.9
                ))
        
        if not self._check_evidence_requirements(evidence_list):
            return None
        
        intensity = self._determine_intensity(center_control['tension'])
        
        return ConflictResult(
            conflict_type=self.CONFLICT_TYPE,
            name=self.CONFLICT_NAME,
            region="中路（4-6列）",
            intensity=intensity,
            reason=f"双方在中路形成对峙，红方控制{center_control['red_center']}点，黑方控制{center_control['black_center']}点",
            evidence_list=evidence_list
        )
    
    def _analyze_center_control(self, board_rows: List[str]) -> Dict:
        red_center = 0
        black_center = 0
        
        for row_idx, row in enumerate(board_rows):
            if 3 <= row_idx <= 6:
                col_idx = 0
                for c in row:
                    if c.isdigit():
                        col_idx += int(c)
                    elif c.isalpha():
                        if 3 <= col_idx <= 5:
                            if c.isupper():
                                red_center += 1
                            else:
                                black_center += 1
                        col_idx += 1
        
        tension = min(red_center, black_center) / max(red_center + black_center, 1) * 2
        
        return {
            'red_center': red_center,
            'black_center': black_center,
            'tension': min(tension, 1.0)
        }
    
    def _count_center_moves(self, pv: List[str], board_rows: List[str]) -> int:
        center_moves = 0
        for move in pv[:5]:
            if len(move) >= 4:
                try:
                    dest_col = int(move[2])
                    if 3 <= dest_col <= 5:
                        center_moves += 1
                except:
                    pass
        return center_moves
    
    def _determine_intensity(self, tension: float) -> ConflictIntensity:
        if tension >= 0.7:
            return ConflictIntensity.HIGH
        elif tension >= 0.5:
            return ConflictIntensity.MEDIUM
        else:
            return ConflictIntensity.LOW


class KingSafetyDetector(ConflictDetector):
    """C02: 王安全检测"""
    
    CONFLICT_TYPE = ConflictType.KING_SAFETY
    CONFLICT_NAME = "王安全"
    MIN_EVIDENCE = [EvidenceType.ENGINE]
    FORBIDDEN_EVIDENCE = [EvidenceType.INFERENCE]
    
    def detect(
        self,
        semantic_state: Dict,
        engine_result: Optional[Dict],
        rule_features: Dict
    ) -> Optional[ConflictResult]:
        if not engine_result:
            return None
        
        red_safety = semantic_state.get('red_king_safety', {})
        black_safety = semantic_state.get('black_king_safety', {})
        
        red_status = red_safety.get('value', 'safe')
        black_status = black_safety.get('value', 'safe')
        
        if red_status not in ['critical', 'exposed'] and black_status not in ['critical', 'exposed']:
            return None
        
        evidence_list = []
        
        depth = engine_result.get('depth', 0)
        score = engine_result.get('score', 0)
        pv = engine_result.get('pv', [])
        
        evidence_list.append(Evidence(
            type=EvidenceType.ENGINE,
            content=f"引擎分析depth={depth}，评分{score:.1f}",
            reliability=0.95 if depth >= 15 else 0.8
        ))
        
        if red_status == 'critical':
            target_side = "红方"
            region = "红方九宫"
            intensity = ConflictIntensity.CRITICAL
        elif black_status == 'critical':
            target_side = "黑方"
            region = "黑方九宫"
            intensity = ConflictIntensity.CRITICAL
        elif red_status == 'exposed':
            target_side = "红方"
            region = "红方阵地"
            intensity = ConflictIntensity.HIGH
        else:
            target_side = "黑方"
            region = "黑方阵地"
            intensity = ConflictIntensity.HIGH
        
        check_related = self._has_check_related_moves(pv)
        if check_related:
            evidence_list.append(Evidence(
                type=EvidenceType.RULE,
                content=f"PV线包含将军或防守着法",
                reliability=0.9
            ))
        
        if not self._check_evidence_requirements(evidence_list):
            return None
        
        return ConflictResult(
            conflict_type=self.CONFLICT_TYPE,
            name=self.CONFLICT_NAME,
            region=region,
            intensity=intensity,
            reason=f"{target_side}将/帅安全受到威胁",
            evidence_list=evidence_list
        )
    
    def _has_check_related_moves(self, pv: List[str]) -> bool:
        return len(pv) > 0


class PieceCoordinationDetector(ConflictDetector):
    """C03: 子力协调检测"""
    
    CONFLICT_TYPE = ConflictType.PIECE_COORDINATION
    CONFLICT_NAME = "子力协调"
    MIN_EVIDENCE = [EvidenceType.RULE]
    FORBIDDEN_EVIDENCE = []
    
    def detect(
        self,
        semantic_state: Dict,
        engine_result: Optional[Dict],
        rule_features: Dict
    ) -> Optional[ConflictResult]:
        red_coord = semantic_state.get('red_coordination', {})
        black_coord = semantic_state.get('black_coordination', {})
        
        red_level = red_coord.get('value', 'moderate')
        black_level = black_coord.get('value', 'moderate')
        
        has_problem = red_level in ['poor'] or black_level in ['poor']
        
        if not has_problem:
            return None
        
        evidence_list = []
        
        if red_level == 'poor':
            problem_side = "红方"
            region = "红方阵地"
            detail = red_coord.get('detail', '')
        else:
            problem_side = "黑方"
            region = "黑方阵地"
            detail = black_coord.get('detail', '')
        
        evidence_list.append(Evidence(
            type=EvidenceType.RULE,
            content=f"{problem_side}子力协调度低：{detail}",
            reliability=0.75
        ))
        
        if engine_result and 'score' in engine_result:
            score = engine_result['score']
            if (problem_side == "红方" and score < -50) or (problem_side == "黑方" and score > 50):
                evidence_list.append(Evidence(
                    type=EvidenceType.ENGINE,
                    content=f"引擎评分与协调问题一致",
                    reliability=0.85
                ))
        
        if not self._check_evidence_requirements(evidence_list):
            return None
        
        return ConflictResult(
            conflict_type=self.CONFLICT_TYPE,
            name=self.CONFLICT_NAME,
            region=region,
            intensity=ConflictIntensity.MEDIUM,
            reason=f"{problem_side}子力协调存在问题",
            evidence_list=evidence_list
        )


class StructuralWeaknessDetector(ConflictDetector):
    """C04: 结构弱点检测"""
    
    CONFLICT_TYPE = ConflictType.STRUCTURAL_WEAKNESS
    CONFLICT_NAME = "结构弱点"
    MIN_EVIDENCE = [EvidenceType.RULE]
    FORBIDDEN_EVIDENCE = []
    
    def detect(
        self,
        semantic_state: Dict,
        engine_result: Optional[Dict],
        rule_features: Dict
    ) -> Optional[ConflictResult]:
        weaknesses = semantic_state.get('long_term_weaknesses', {})
        weakness_values = weaknesses.get('value', [])
        
        if isinstance(weakness_values, str):
            weakness_values = [weakness_values]
        
        significant_weaknesses = [w for w in weakness_values if '孤兵' in w or '失衡' in w]
        
        if not significant_weaknesses:
            return None
        
        evidence_list = []
        
        detail = weaknesses.get('detail', '')
        evidence_list.append(Evidence(
            type=EvidenceType.RULE,
            content=f"结构分析：{detail}",
            reliability=0.7
        ))
        
        if engine_result and 'pv' in engine_result:
            pv = engine_result.get('pv', [])
            if pv:
                evidence_list.append(Evidence(
                    type=EvidenceType.ENGINE,
                    content=f"引擎PV线可能针对弱点",
                    reliability=0.6
                ))
        
        if not self._check_evidence_requirements(evidence_list):
            return None
        
        return ConflictResult(
            conflict_type=self.CONFLICT_TYPE,
            name=self.CONFLICT_NAME,
            region="全局",
            intensity=ConflictIntensity.LOW,
            reason=f"存在结构性弱点：{', '.join(significant_weaknesses[:2])}",
            evidence_list=evidence_list
        )


class AdvantageConversionDetector(ConflictDetector):
    """C05: 优势转换检测"""
    
    CONFLICT_TYPE = ConflictType.ADVANTAGE_CONVERSION
    CONFLICT_NAME = "优势转换"
    MIN_EVIDENCE = [EvidenceType.ENGINE]
    FORBIDDEN_EVIDENCE = [EvidenceType.RULE, EvidenceType.INFERENCE]
    
    def detect(
        self,
        semantic_state: Dict,
        engine_result: Optional[Dict],
        rule_features: Dict
    ) -> Optional[ConflictResult]:
        if not engine_result:
            return None
        
        score = engine_result.get('score', 0)
        
        if abs(score) < 150:
            return None
        
        evidence_list = []
        
        depth = engine_result.get('depth', 0)
        evidence_list.append(Evidence(
            type=EvidenceType.ENGINE,
            content=f"引擎分析depth={depth}，评分{score:.1f}，优势方需要转换",
            reliability=0.9 if depth >= 15 else 0.75
        ))
        
        if not self._check_evidence_requirements(evidence_list):
            return None
        
        advantage_side = "红方" if score > 0 else "黑方"
        
        return ConflictResult(
            conflict_type=self.CONFLICT_TYPE,
            name=self.CONFLICT_NAME,
            region="全局",
            intensity=ConflictIntensity.HIGH if abs(score) > 300 else ConflictIntensity.MEDIUM,
            reason=f"{advantage_side}拥有显著优势，需要有效转换",
            evidence_list=evidence_list
        )


class InitiativeFightDetector(ConflictDetector):
    """C06: 抢先手检测"""
    
    CONFLICT_TYPE = ConflictType.INITIATIVE_FIGHT
    CONFLICT_NAME = "抢先手"
    MIN_EVIDENCE = [EvidenceType.INFERENCE]
    FORBIDDEN_EVIDENCE = []
    
    def detect(
        self,
        semantic_state: Dict,
        engine_result: Optional[Dict],
        rule_features: Dict
    ) -> Optional[ConflictResult]:
        initiative = semantic_state.get('initiative', {})
        initiative_value = initiative.get('value', 'balanced')
        
        if initiative_value == 'balanced':
            return None
        
        evidence_list = []
        
        detail = initiative.get('detail', '')
        source = initiative.get('source', '')
        
        if '[ENGINE]' in source:
            evidence_list.append(Evidence(
                type=EvidenceType.ENGINE,
                content=detail,
                reliability=0.85
            ))
        elif '[MODEL]' in source:
            evidence_list.append(Evidence(
                type=EvidenceType.INFERENCE,
                content=f"模型判断主动权：{detail}",
                reliability=0.6
            ))
        else:
            evidence_list.append(Evidence(
                type=EvidenceType.INFERENCE,
                content=f"推断主动权归属",
                reliability=0.5
            ))
        
        advantage_side = "红方" if initiative_value == 'red_advantage' else "黑方"
        
        return ConflictResult(
            conflict_type=self.CONFLICT_TYPE,
            name=self.CONFLICT_NAME,
            region="全局",
            intensity=ConflictIntensity.MEDIUM,
            reason=f"{advantage_side}掌握主动权",
            evidence_list=evidence_list
        )


class ConflictArbiter:
    """矛盾裁决器"""
    
    def __init__(self):
        self.detectors = [
            CenterControlDetector(),
            KingSafetyDetector(),
            PieceCoordinationDetector(),
            StructuralWeaknessDetector(),
            AdvantageConversionDetector(),
            InitiativeFightDetector(),
        ]
    
    def arbitrate(
        self,
        semantic_state: Dict,
        engine_result: Optional[Dict],
        rule_features: Dict
    ) -> ArbitrationResult:
        all_conflicts = []
        
        for detector in self.detectors:
            try:
                conflict = detector.detect(semantic_state, engine_result, rule_features)
                if conflict:
                    all_conflicts.append(conflict)
            except Exception as e:
                continue
        
        scored_conflicts = []
        for conflict in all_conflicts:
            score = self._calculate_score(conflict, semantic_state, engine_result)
            conflict.arbitration_score = score
            scored_conflicts.append((conflict, score))
        
        scored_conflicts.sort(key=lambda x: x[1], reverse=True)
        
        all_scores = {c.conflict_type.value: s for c, s in scored_conflicts}
        
        if not scored_conflicts:
            return ArbitrationResult(
                primary_conflict=None,
                secondary_conflicts=[],
                all_scores=all_scores
            )
        
        primary = scored_conflicts[0][0]
        primary_score = scored_conflicts[0][1]
        
        secondary = []
        for conflict, score in scored_conflicts[1:]:
            if score > primary_score * 0.4:
                secondary.append(conflict)
        
        return ArbitrationResult(
            primary_conflict=primary,
            secondary_conflicts=secondary[:3],
            all_scores=all_scores
        )
    
    def _calculate_score(
        self,
        conflict: ConflictResult,
        semantic_state: Dict,
        engine_result: Optional[Dict]
    ) -> float:
        score = 0.0
        
        if conflict.intensity == ConflictIntensity.CRITICAL:
            score += 40
        elif conflict.intensity == ConflictIntensity.HIGH:
            score += 25
        elif conflict.intensity == ConflictIntensity.MEDIUM:
            score += 15
        else:
            score += 5
        
        if self._explains_best_move(conflict, engine_result):
            score += 30
        
        unified = self._count_unified_labels(conflict, semantic_state)
        score += unified * 10
        
        if self._affects_future(conflict, engine_result):
            score += 15
        
        evidence_score = self._evidence_score(conflict)
        score += evidence_score
        
        return score
    
    def _explains_best_move(self, conflict: ConflictResult, engine_result: Optional[Dict]) -> bool:
        if not engine_result:
            return False
        
        if conflict.conflict_type == ConflictType.KING_SAFETY:
            pv = engine_result.get('pv', [])
            return len(pv) > 0
        
        if conflict.conflict_type == ConflictType.CENTER_CONTROL:
            best_move = engine_result.get('bestmove', '')
            if best_move and len(best_move) >= 4:
                try:
                    dest_col = int(best_move[2])
                    if 3 <= dest_col <= 5:
                        return True
                except:
                    pass
        
        return False
    
    def _count_unified_labels(self, conflict: ConflictResult, semantic_state: Dict) -> int:
        count = 0
        
        if conflict.conflict_type == ConflictType.KING_SAFETY:
            if semantic_state.get('red_king_safety', {}).get('value') in ['critical', 'exposed']:
                count += 1
            if semantic_state.get('black_king_safety', {}).get('value') in ['critical', 'exposed']:
                count += 1
        
        if conflict.conflict_type == ConflictType.INITIATIVE_FIGHT:
            initiative = semantic_state.get('initiative', {}).get('value', 'balanced')
            if initiative != 'balanced':
                count += 1
        
        return count
    
    def _affects_future(self, conflict: ConflictResult, engine_result: Optional[Dict]) -> bool:
        if not engine_result:
            return False
        
        if conflict.conflict_type in [ConflictType.KING_SAFETY, ConflictType.ADVANTAGE_CONVERSION]:
            pv = engine_result.get('pv', [])
            return len(pv) >= 3
        
        return False
    
    def _evidence_score(self, conflict: ConflictResult) -> float:
        score = 0.0
        
        for evidence in conflict.evidence_list:
            if evidence.type == EvidenceType.ENGINE:
                score += 20 * evidence.reliability
            elif evidence.type == EvidenceType.RULE:
                score += 10 * evidence.reliability
            else:
                score += 5 * evidence.reliability
        
        return min(score, 30)


def detect_core_conflicts(
    semantic_state: Dict,
    engine_result: Optional[Dict] = None,
    rule_features: Optional[Dict] = None
) -> Dict:
    """
    便捷函数：检测核心矛盾
    
    输入：
    - semantic_state: 语义状态（来自semantic_state_v1）
    - engine_result: 引擎分析结果
    - rule_features: 规则特征
    
    输出：
    - 主矛盾
    - 次矛盾列表
    - 裁决分数
    - 摘要
    """
    if rule_features is None:
        rule_features = {}
    
    arbiter = ConflictArbiter()
    result = arbiter.arbitrate(semantic_state, engine_result, rule_features)
    return result.to_dict()


if __name__ == "__main__":
    test_cases = [
        {
            "name": "开局局面",
            "semantic_state": {
                "phase": {"value": "opening"},
                "initiative": {"value": "balanced", "detail": "评分0.0"},
                "red_king_safety": {"value": "safe"},
                "black_king_safety": {"value": "safe"},
                "red_coordination": {"value": "good"},
                "black_coordination": {"value": "good"},
                "long_term_weaknesses": {"value": ["无明显弱点"]},
            },
            "engine_result": {"score": 0.0, "depth": 20, "pv": []},
            "rule_features": {"board_rows": ["rnbakabnr", "9", "1c5c1", "p1p1p1p1p", "9", "9", "P1P1P1P1P", "1C5C1", "9", "RNBAKABNR"]}
        },
        {
            "name": "王安全危机",
            "semantic_state": {
                "phase": {"value": "middlegame"},
                "initiative": {"value": "red_advantage", "detail": "评分+180"},
                "red_king_safety": {"value": "safe"},
                "black_king_safety": {"value": "critical"},
                "red_coordination": {"value": "excellent"},
                "black_coordination": {"value": "poor"},
                "long_term_weaknesses": {"value": ["黑方防守薄弱"]},
            },
            "engine_result": {"score": 180.0, "depth": 18, "pv": ["a0a1", "b0b1"]},
            "rule_features": {"board_rows": ["rnb1kabnr", "9", "1c5c1", "p1p1p1p1p", "9", "9", "P1P1P1P1P", "1C5C1", "9", "RNBAKABNR"]}
        },
        {
            "name": "优势转换",
            "semantic_state": {
                "phase": {"value": "endgame"},
                "initiative": {"value": "red_advantage", "detail": "评分+250"},
                "red_king_safety": {"value": "safe"},
                "black_king_safety": {"value": "safe"},
                "red_coordination": {"value": "good"},
                "black_coordination": {"value": "moderate"},
                "long_term_weaknesses": {"value": ["黑方少子"]},
            },
            "engine_result": {"score": 250.0, "depth": 22, "pv": ["a0a1", "b0b1", "c0c1"]},
            "rule_features": {"board_rows": ["4k4", "9", "9", "9", "9", "9", "9", "9", "9", "R3K4"]}
        }
    ]
    
    print("=" * 70)
    print("核心矛盾识别器 v1 测试")
    print("=" * 70)
    
    arbiter = ConflictArbiter()
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n【测试 {i}】{case['name']}")
        print("-" * 50)
        
        result = arbiter.arbitrate(
            case['semantic_state'],
            case.get('engine_result'),
            case.get('rule_features', {})
        )
        
        output = result.to_dict()
        
        if output['primary_conflict']:
            pc = output['primary_conflict']
            print(f"\n主矛盾: {pc['name']} [{pc['type']}]")
            print(f"  区域: {pc['region']}")
            print(f"  强度: {pc['intensity']}")
            print(f"  理由: {pc['reason']}")
            print(f"  裁决分数: {pc['arbitration_score']}")
            print(f"  证据:")
            for e in pc['evidence']:
                print(f"    - [{e['type']}] {e['content']}")
        else:
            print("\n未检测到主矛盾")
        
        if output['secondary_conflicts']:
            print(f"\n次矛盾:")
            for sc in output['secondary_conflicts']:
                print(f"  - {sc['name']} [{sc['intensity']}] 分数:{sc['arbitration_score']}")
        
        print(f"\n摘要: {output['summary']}")
        print("=" * 70)
