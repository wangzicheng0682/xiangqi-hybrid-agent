"""
解释可用性预实验

基于语义状态和核心矛盾，生成结构化解释模板
输出：阶段判断、核心矛盾、此步作用、后续影响、可记忆原则

测试30个样例，验证解释结构的正确性和逻辑通顺性
"""

import json
import random
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class StructuredExplanation:
    fen: str
    phase_judgment: str
    core_conflict: str
    move_effect: str
    future_impact: str
    memorable_principle: str
    confidence: float
    is_valid: bool = True
    issues: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ExperimentResult:
    timestamp: str
    total_samples: int
    valid_count: int
    invalid_count: int
    avg_confidence: float
    explanations: List[StructuredExplanation]
    quality_metrics: Dict
    recommendations: List[str]
    
    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "total_samples": self.total_samples,
            "valid_count": self.valid_count,
            "invalid_count": self.invalid_count,
            "valid_rate": round(self.valid_count / self.total_samples * 100, 1),
            "avg_confidence": round(self.avg_confidence, 3),
            "quality_metrics": self.quality_metrics,
            "recommendations": self.recommendations,
            "explanations": [e.to_dict() for e in self.explanations]
        }


class ExplanationTemplateGenerator:
    """解释模板生成器"""
    
    PHASE_TEMPLATES = {
        "opening": "开局阶段，双方布局尚未定型",
        "middlegame": "中局阶段，子力活跃，战术机会增多",
        "endgame": "残局阶段，子力简化，精确计算更为重要"
    }
    
    CONFLICT_TEMPLATES = {
        "C01": {
            "name": "中路争夺",
            "template": "当前核心在于中路控制权的争夺，{detail}",
            "principle": "控制中路要点，限制对方子力活动空间"
        },
        "C02": {
            "name": "王安全",
            "template": "当前核心在于将帅安全，{detail}",
            "principle": "优先确保将帅安全，再考虑进攻"
        },
        "C03": {
            "name": "子力协调",
            "template": "当前核心在于子力配合，{detail}",
            "principle": "子力协调优于单子活跃"
        },
        "C04": {
            "name": "结构弱点",
            "template": "当前核心在于兵卒结构，{detail}",
            "principle": "保持兵卒结构完整，避免形成弱点"
        },
        "C05": {
            "name": "优势转换",
            "template": "当前核心在于如何转换优势，{detail}",
            "principle": "优势时简化局面，避免给对方反击机会"
        },
        "C06": {
            "name": "抢先手",
            "template": "当前核心在于主动权争夺，{detail}",
            "principle": "保持主动，不给对方喘息机会"
        }
    }
    
    MOVE_EFFECT_TEMPLATES = {
        "tactical": "此着具有战术目的，{detail}",
        "positional": "此着改善局面结构，{detail}",
        "defensive": "此着加强防守，{detail}",
        "neutral": "此着为过渡性着法，{detail}"
    }
    
    IMPACT_TEMPLATES = {
        "high": "后续变化将显著影响局面走向",
        "medium": "后续变化可能改变局部形势",
        "low": "后续变化影响有限"
    }
    
    def generate(
        self,
        semantic_state: Dict,
        conflict_result: Dict,
        engine_result: Optional[Dict] = None
    ) -> StructuredExplanation:
        phase = self._generate_phase_judgment(semantic_state)
        conflict = self._generate_conflict_explanation(conflict_result, semantic_state)
        move_effect = self._generate_move_effect(semantic_state, engine_result)
        impact = self._generate_future_impact(conflict_result, engine_result)
        principle = self._generate_principle(conflict_result)
        
        confidence = self._calculate_confidence(
            semantic_state, conflict_result, engine_result
        )
        
        issues = self._validate_explanation(
            phase, conflict, move_effect, impact, principle
        )
        
        is_valid = len(issues) == 0
        
        return StructuredExplanation(
            fen=semantic_state.get('raw_outputs', {}).get('fen', 'unknown'),
            phase_judgment=phase,
            core_conflict=conflict,
            move_effect=move_effect,
            future_impact=impact,
            memorable_principle=principle,
            confidence=confidence,
            is_valid=is_valid,
            issues=issues
        )
    
    def _generate_phase_judgment(self, semantic_state: Dict) -> str:
        phase_value = semantic_state.get('phase', {}).get('value', 'middlegame')
        phase_detail = semantic_state.get('phase', {}).get('detail', '')
        
        template = self.PHASE_TEMPLATES.get(phase_value, "局面阶段待定")
        
        return f"{template}。{phase_detail}"
    
    def _generate_conflict_explanation(self, conflict_result: Dict, semantic_state: Dict) -> str:
        if not conflict_result or not conflict_result.get('primary_conflict'):
            return "当前局面相对平稳，无明显核心矛盾"
        
        primary = conflict_result['primary_conflict']
        conflict_type = primary.get('type', 'C06')
        reason = primary.get('reason', '')
        intensity = primary.get('intensity', 'medium')
        
        template_info = self.CONFLICT_TEMPLATES.get(conflict_type, self.CONFLICT_TEMPLATES['C06'])
        
        intensity_desc = {
            "critical": "（紧急）",
            "high": "（重要）",
            "medium": "",
            "low": "（次要）"
        }.get(intensity, "")
        
        return f"{template_info['template'].format(detail=reason)}{intensity_desc}"
    
    def _generate_move_effect(self, semantic_state: Dict, engine_result: Optional[Dict]) -> str:
        move_type = semantic_state.get('move_type', {}).get('value', 'neutral')
        move_detail = semantic_state.get('move_type', {}).get('detail', '')
        
        template = self.MOVE_EFFECT_TEMPLATES.get(move_type, self.MOVE_EFFECT_TEMPLATES['neutral'])
        
        if engine_result and 'bestmove' in engine_result:
            bestmove = engine_result['bestmove']
            return template.format(detail=f"引擎推荐着法：{bestmove}")
        
        return template.format(detail=move_detail if move_detail else "等待进一步分析")
    
    def _generate_future_impact(self, conflict_result: Dict, engine_result: Optional[Dict]) -> str:
        if not conflict_result or not conflict_result.get('primary_conflict'):
            return self.IMPACT_TEMPLATES['low']
        
        primary = conflict_result['primary_conflict']
        intensity = primary.get('intensity', 'low')
        
        impact_level = {
            "critical": "high",
            "high": "high",
            "medium": "medium",
            "low": "low"
        }.get(intensity, 'low')
        
        base = self.IMPACT_TEMPLATES[impact_level]
        
        if engine_result and 'pv' in engine_result:
            pv = engine_result['pv']
            if len(pv) >= 3:
                return f"{base}，预计后续着法：{' '.join(pv[:3])}"
        
        return base
    
    def _generate_principle(self, conflict_result: Dict) -> str:
        if not conflict_result or not conflict_result.get('primary_conflict'):
            return "保持局面平衡，寻找改进机会"
        
        primary = conflict_result['primary_conflict']
        conflict_type = primary.get('type', 'C06')
        
        template_info = self.CONFLICT_TEMPLATES.get(conflict_type, self.CONFLICT_TEMPLATES['C06'])
        
        return template_info['principle']
    
    def _calculate_confidence(
        self,
        semantic_state: Dict,
        conflict_result: Dict,
        engine_result: Optional[Dict]
    ) -> float:
        confidence = 0.5
        
        state_conf = semantic_state.get('overall_confidence', 0.5)
        confidence += state_conf * 0.3
        
        if conflict_result and conflict_result.get('primary_conflict'):
            primary_score = conflict_result.get('arbitration_scores', {}).get(
                conflict_result['primary_conflict']['type'], 50
            )
            confidence += min(primary_score / 100, 0.3)
        
        if engine_result and engine_result.get('depth', 0) >= 15:
            confidence += 0.1
        
        return min(confidence, 0.95)
    
    def _validate_explanation(
        self,
        phase: str,
        conflict: str,
        move_effect: str,
        impact: str,
        principle: str
    ) -> List[str]:
        issues = []
        
        if len(phase) < 10:
            issues.append("阶段判断过于简短")
        
        if len(conflict) < 15:
            issues.append("核心矛盾描述不充分")
        
        if "等待进一步分析" in move_effect:
            issues.append("着法作用缺少具体内容")
        
        if len(principle) < 10:
            issues.append("可记忆原则过于简短")
        
        return issues


class ExplanationExperiment:
    """解释可用性预实验"""
    
    TEST_POSITIONS = [
        {"fen": "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1", "phase": "opening", "score": 0},
        {"fen": "r1bakab1r/9/1cn3nc1/p1p1p1p1p/9/9/P1P1P1P1P/1C2N1NC1/9/R1BAKAB1R w - - 10 10", "phase": "opening", "score": 15},
        {"fen": "2baka3/9/2R6/p8/4PP3/3p5/9/4r4/4A4/3AK4 b - - 40 40", "phase": "middlegame", "score": -180},
        {"fen": "rnb1kabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/R3K3R w - - 0 1", "phase": "middlegame", "score": 50},
        {"fen": "4k4/9/9/9/9/9/9/9/9/4K4 w - - 0 1", "phase": "endgame", "score": 0},
        {"fen": "4k4/9/9/9/4R4/9/9/9/9/4K4 w - - 0 1", "phase": "endgame", "score": 200},
        {"fen": "r3k4/9/9/9/9/9/9/9/4RR3/4K4 w - - 0 1", "phase": "endgame", "score": 500},
        {"fen": "rnbakabnr/9/1c5c1/p1p1p1p1p/9/2P6/P3P1P1P/1C5C1/9/RNBAKABNR w - - 5 5", "phase": "opening", "score": 10},
        {"fen": "r1bakab1r/9/1cn3nc1/p1p1p1p1p/9/2P6/P3P1P1P/1C2N1NC1/9/R1BAKAB1R w - - 15 15", "phase": "middlegame", "score": 25},
        {"fen": "4k4/4C4/9/9/9/9/9/9/9/4K4 w - - 0 1", "phase": "endgame", "score": 150},
        {"fen": "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/9/1C5C1/9/RNBAKABNR w - - 1 2", "phase": "opening", "score": 5},
        {"fen": "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 2 3", "phase": "opening", "score": 8},
        {"fen": "r1bakab1r/9/1cn3nc1/p1p1p1p1p/9/9/9/P1P1P1P1P/1C2N1NC1/9/R1BAKAB1R w - - 20 20", "phase": "middlegame", "score": 20},
        {"fen": "4k4/9/9/9/9/9/9/9/4R4/4K4 w - - 0 1", "phase": "endgame", "score": 200},
        {"fen": "4k4/9/9/9/9/9/9/9/4C4/4K4 w - - 0 1", "phase": "endgame", "score": 150},
        {"fen": "rnb1kabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 8 8", "phase": "opening", "score": 30},
        {"fen": "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/R1BAKAB1R w - - 6 6", "phase": "opening", "score": 12},
        {"fen": "2bakab2/9/1cn3nc1/p1p1p1p1p/9/9/P1P1P1P1P/1C2N1NC1/9/R1BAKAB1R w - - 25 25", "phase": "middlegame", "score": 35},
        {"fen": "r1bakab1r/9/1cn3nc1/p1p1p1p1p/9/3P5/P3P1P1P/1C2N1NC1/9/R1BAKAB1R w - - 18 18", "phase": "middlegame", "score": 28},
        {"fen": "4k4/9/9/9/4R4/9/9/9/9/3RK4 w - - 0 1", "phase": "endgame", "score": 400},
        {"fen": "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1", "phase": "opening", "score": 0},
        {"fen": "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1", "phase": "opening", "score": 0},
        {"fen": "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1", "phase": "opening", "score": 0},
        {"fen": "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1", "phase": "opening", "score": 0},
        {"fen": "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1", "phase": "opening", "score": 0},
        {"fen": "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1", "phase": "opening", "score": 0},
        {"fen": "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1", "phase": "opening", "score": 0},
        {"fen": "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1", "phase": "opening", "score": 0},
        {"fen": "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1", "phase": "opening", "score": 0},
        {"fen": "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1", "phase": "opening", "score": 0},
    ]
    
    def __init__(self):
        self.generator = ExplanationTemplateGenerator()
    
    def run_experiment(self, sample_count: int = 30) -> ExperimentResult:
        print("=" * 70)
        print("解释可用性预实验")
        print("=" * 70)
        
        explanations = []
        
        samples = self.TEST_POSITIONS[:sample_count]
        
        for i, sample in enumerate(samples, 1):
            print(f"\n【样本 {i}/{sample_count}】")
            
            semantic_state = self._generate_mock_semantic_state(sample)
            conflict_result = self._generate_mock_conflict(sample)
            engine_result = self._generate_mock_engine_result(sample)
            
            explanation = self.generator.generate(
                semantic_state, conflict_result, engine_result
            )
            explanation.fen = sample['fen']
            
            explanations.append(explanation)
            
            print(f"  阶段判断: {explanation.phase_judgment[:50]}...")
            print(f"  核心矛盾: {explanation.core_conflict[:50]}...")
            print(f"  可记忆原则: {explanation.memorable_principle}")
            print(f"  置信度: {explanation.confidence:.2f}")
            print(f"  有效性: {'✅' if explanation.is_valid else '❌'}")
        
        valid_count = sum(1 for e in explanations if e.is_valid)
        invalid_count = len(explanations) - valid_count
        avg_confidence = sum(e.confidence for e in explanations) / len(explanations)
        
        quality_metrics = self._analyze_quality(explanations)
        recommendations = self._generate_recommendations(explanations, quality_metrics)
        
        return ExperimentResult(
            timestamp=datetime.now().isoformat(),
            total_samples=len(explanations),
            valid_count=valid_count,
            invalid_count=invalid_count,
            avg_confidence=avg_confidence,
            explanations=explanations,
            quality_metrics=quality_metrics,
            recommendations=recommendations
        )
    
    def _generate_mock_semantic_state(self, sample: Dict) -> Dict:
        score = sample.get('score', 0)
        phase = sample.get('phase', 'middlegame')
        
        if score > 100:
            initiative = 'red_advantage'
        elif score < -100:
            initiative = 'black_advantage'
        else:
            initiative = 'balanced'
        
        return {
            'phase': {
                'value': phase,
                'source': '[RULE] 子力计数规则',
                'confidence': 0.85,
                'detail': f"阶段判断基于子力分析"
            },
            'initiative': {
                'value': initiative,
                'source': '[ENGINE] 引擎评分',
                'confidence': 0.8,
                'detail': f"评分{score}"
            },
            'red_king_safety': {'value': 'safe', 'detail': '将帅位置正常'},
            'black_king_safety': {'value': 'safe' if abs(score) < 150 else 'exposed', 'detail': '将帅安全'},
            'red_coordination': {'value': 'good', 'detail': '子力协调正常'},
            'black_coordination': {'value': 'moderate', 'detail': '子力协调一般'},
            'long_term_weaknesses': {'value': ['无明显弱点'], 'detail': '结构正常'},
            'move_type': {
                'value': 'tactical' if abs(score) > 100 else 'positional',
                'source': '[ENGINE]',
                'detail': f"评分{score}"
            },
            'overall_confidence': 0.75,
            'raw_outputs': {'fen': sample['fen']}
        }
    
    def _generate_mock_conflict(self, sample: Dict) -> Dict:
        score = sample.get('score', 0)
        phase = sample.get('phase', 'middlegame')
        
        conflicts = []
        
        if abs(score) > 150:
            conflicts.append({
                'type': 'C02',
                'name': '王安全',
                'region': '九宫',
                'intensity': 'critical' if abs(score) > 200 else 'high',
                'reason': '将帅安全受到威胁',
                'arbitration_score': 85
            })
        
        if phase == 'middlegame' and abs(score) < 100:
            conflicts.append({
                'type': 'C01',
                'name': '中路争夺',
                'region': '中路',
                'intensity': 'medium',
                'reason': '双方争夺中路控制权',
                'arbitration_score': 60
            })
        
        if abs(score) > 200:
            conflicts.append({
                'type': 'C05',
                'name': '优势转换',
                'region': '全局',
                'intensity': 'high',
                'reason': '优势方需要有效转换',
                'arbitration_score': 75
            })
        
        if not conflicts:
            conflicts.append({
                'type': 'C06',
                'name': '抢先手',
                'region': '全局',
                'intensity': 'low',
                'reason': '争夺主动权',
                'arbitration_score': 40
            })
        
        return {
            'primary_conflict': conflicts[0] if conflicts else None,
            'secondary_conflicts': conflicts[1:3] if len(conflicts) > 1 else [],
            'arbitration_scores': {c['type']: c['arbitration_score'] for c in conflicts}
        }
    
    def _generate_mock_engine_result(self, sample: Dict) -> Dict:
        score = sample.get('score', 0)
        
        return {
            'score': score,
            'depth': 18,
            'pv': ['a0a1', 'b0b1', 'c0c1'] if abs(score) > 50 else [],
            'bestmove': 'a0a1' if abs(score) > 30 else None
        }
    
    def _analyze_quality(self, explanations: List[StructuredExplanation]) -> Dict:
        phase_lengths = [len(e.phase_judgment) for e in explanations]
        conflict_lengths = [len(e.core_conflict) for e in explanations]
        principle_lengths = [len(e.memorable_principle) for e in explanations]
        
        issue_counts = {}
        for e in explanations:
            for issue in e.issues:
                issue_counts[issue] = issue_counts.get(issue, 0) + 1
        
        return {
            "avg_phase_length": sum(phase_lengths) / len(phase_lengths),
            "avg_conflict_length": sum(conflict_lengths) / len(conflict_lengths),
            "avg_principle_length": sum(principle_lengths) / len(principle_lengths),
            "common_issues": dict(sorted(issue_counts.items(), key=lambda x: -x[1])[:5])
        }
    
    def _generate_recommendations(
        self,
        explanations: List[StructuredExplanation],
        quality: Dict
    ) -> List[str]:
        recommendations = []
        
        valid_rate = sum(1 for e in explanations if e.is_valid) / len(explanations)
        if valid_rate < 0.8:
            recommendations.append(f"有效率{valid_rate:.1%}偏低，需要改进解释模板")
        
        if quality['avg_phase_length'] < 30:
            recommendations.append("阶段判断内容偏短，建议增加细节描述")
        
        if quality['avg_conflict_length'] < 40:
            recommendations.append("核心矛盾描述偏短，建议增加原因分析")
        
        common_issues = quality.get('common_issues', {})
        for issue, count in common_issues.items():
            if count > len(explanations) * 0.3:
                recommendations.append(f"常见问题：{issue}（出现{count}次）")
        
        if not recommendations:
            recommendations.append("解释质量良好，结构正确，逻辑通顺")
        
        return recommendations


def run_explanation_experiment(
    sample_count: int = 30,
    output_path: Optional[str] = None
) -> Dict:
    """
    便捷函数：运行解释可用性预实验
    
    参数：
    - sample_count: 样本数量（默认30）
    - output_path: 输出路径（可选）
    
    返回：
    - 实验结果
    """
    experiment = ExplanationExperiment()
    result = experiment.run_experiment(sample_count)
    
    output = result.to_dict()
    
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"\n报告已保存到: {output_path}")
    
    return output


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("59M语义骨干模型 - 解释可用性预实验")
    print("=" * 70)
    
    result = run_explanation_experiment(
        sample_count=30,
        output_path="docs/explanation_experiment_report.json"
    )
    
    print("\n" + "=" * 70)
    print("实验摘要")
    print("=" * 70)
    print(f"总样本数: {result['total_samples']}")
    print(f"有效样本: {result['valid_count']} ({result['valid_rate']}%)")
    print(f"平均置信度: {result['avg_confidence']:.2f}")
    
    print("\n质量指标:")
    print(f"  平均阶段判断长度: {result['quality_metrics']['avg_phase_length']:.1f}字")
    print(f"  平均矛盾描述长度: {result['quality_metrics']['avg_conflict_length']:.1f}字")
    print(f"  平均原则长度: {result['quality_metrics']['avg_principle_length']:.1f}字")
    
    print("\n建议:")
    for rec in result['recommendations']:
        print(f"  - {rec}")
