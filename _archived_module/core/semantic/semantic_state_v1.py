"""
语义状态生成器 v1

基于59M语义骨干模型 + 规则检测 + 引擎分析
输出完整的语义状态，每个字段标明来源

字段来源标注：
- [RULE] 规则检测
- [ENGINE] 引擎分析
- [MODEL] 59M模型输出
- [HYBRID] 多源融合
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
import torch
import numpy as np


class GamePhase(Enum):
    OPENING = "opening"
    MIDDLEGAME = "middlegame"
    ENDGAME = "endgame"


class Initiative(Enum):
    RED_ADVANTAGE = "red_advantage"
    BLACK_ADVANTAGE = "black_advantage"
    BALANCED = "balanced"


class SafetyLevel(Enum):
    SAFE = "safe"
    EXPOSED = "exposed"
    CRITICAL = "critical"


class CoordinationLevel(Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    MODERATE = "moderate"
    POOR = "poor"


class WeaknessType(Enum):
    ISOLATED_PAWN = "isolated_pawn"
    WEAK_SQUARE = "weak_square"
    BACKWARD_PAWN = "backward_pawn"
    EXPOSED_KING = "exposed_king"
    NONE = "none"


class MoveType(Enum):
    TACTICAL = "tactical"
    POSITIONAL = "positional"
    DEFENSIVE = "defensive"
    NEUTRAL = "neutral"


@dataclass
class FieldSource:
    value: any
    source: str
    confidence: float = 1.0
    detail: str = ""

    def to_dict(self) -> dict:
        return {
            "value": self.value if not isinstance(self.value, Enum) else self.value.value,
            "source": self.source,
            "confidence": round(self.confidence, 3),
            "detail": self.detail
        }


@dataclass
class SemanticStateV1:
    phase: FieldSource
    initiative: FieldSource
    red_king_safety: FieldSource
    black_king_safety: FieldSource
    red_coordination: FieldSource
    black_coordination: FieldSource
    long_term_weaknesses: FieldSource
    move_type: FieldSource
    overall_confidence: float = 0.0
    raw_outputs: Dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "phase": self.phase.to_dict(),
            "initiative": self.initiative.to_dict(),
            "red_king_safety": self.red_king_safety.to_dict(),
            "black_king_safety": self.black_king_safety.to_dict(),
            "red_coordination": self.red_coordination.to_dict(),
            "black_coordination": self.black_coordination.to_dict(),
            "long_term_weaknesses": self.long_term_weaknesses.to_dict(),
            "move_type": self.move_type.to_dict(),
            "overall_confidence": round(self.overall_confidence, 3),
            "raw_outputs": self.raw_outputs
        }


class SemanticStateGeneratorV1:
    """
    语义状态生成器 v1
    
    数据流：
    1. 规则层 → 基础特征（子力计数、位置分析）
    2. 引擎层 → 分数、PV线、威胁检测
    3. 模型层 → embedding、语义标签
    4. 融合层 → 最终语义状态
    """
    
    PIECE_VALUES = {
        'K': 0, 'k': 0,
        'R': 9, 'r': 9,
        'C': 4.5, 'c': 4.5,
        'N': 4, 'n': 4,
        'B': 2, 'b': 2,
        'A': 2, 'a': 2,
        'P': 1, 'p': 1,
    }
    
    def __init__(self, model=None, tokenizer=None, engine=None):
        self.model = model
        self.tokenizer = tokenizer
        self.engine = engine
    
    def generate(
        self,
        fen: str,
        engine_result: Optional[Dict] = None,
        model_output: Optional[Dict] = None
    ) -> SemanticStateV1:
        board = fen.split()[0]
        
        rule_features = self._extract_rule_features(board)
        
        if engine_result is None and self.engine:
            engine_result = self._get_engine_analysis(fen)
        
        if model_output is None and self.model and self.tokenizer:
            model_output = self._get_model_output(fen)
        
        phase = self._determine_phase(board, rule_features, model_output)
        initiative = self._determine_initiative(engine_result, model_output)
        red_safety = self._determine_king_safety(board, 'red', engine_result, rule_features)
        black_safety = self._determine_king_safety(board, 'black', engine_result, rule_features)
        red_coord = self._determine_coordination(board, 'red', rule_features)
        black_coord = self._determine_coordination(board, 'black', rule_features)
        weaknesses = self._detect_weaknesses(board, rule_features, engine_result)
        move_type = self._determine_move_type(engine_result, model_output)
        
        confidence = self._calculate_confidence(
            phase, initiative, red_safety, black_safety,
            red_coord, black_coord, weaknesses, move_type
        )
        
        return SemanticStateV1(
            phase=phase,
            initiative=initiative,
            red_king_safety=red_safety,
            black_king_safety=black_safety,
            red_coordination=red_coord,
            black_coordination=black_coord,
            long_term_weaknesses=weaknesses,
            move_type=move_type,
            overall_confidence=confidence,
            raw_outputs={
                "rule_features": {k: v for k, v in rule_features.items() if not isinstance(v, dict)},
                "engine_score": engine_result.get('score') if engine_result else None,
                "model_semantic_tags": model_output.get('semantic_tags') if model_output else None
            }
        )
    
    def _extract_rule_features(self, board: str) -> Dict:
        features = {}
        
        piece_count = sum(1 for c in board if c.isalpha())
        features['piece_count'] = piece_count
        
        heavy_pieces = sum(board.count(p) for p in 'RrCcNn')
        features['heavy_pieces'] = heavy_pieces
        
        rows = board.split('/')
        features['board_rows'] = rows
        
        red_pieces = []
        black_pieces = []
        for row_idx, row in enumerate(rows):
            col_idx = 0
            for c in row:
                if c.isdigit():
                    col_idx += int(c)
                elif c.isalpha():
                    if c.isupper():
                        red_pieces.append((c, row_idx, col_idx))
                    else:
                        black_pieces.append((c, row_idx, col_idx))
                    col_idx += 1
        
        features['red_pieces'] = red_pieces
        features['black_pieces'] = black_pieces
        
        material = 0
        for c in board:
            if c in self.PIECE_VALUES:
                val = self.PIECE_VALUES[c]
                if c.isupper():
                    material += val
                else:
                    material -= val
        features['material_balance'] = material
        
        pawn_structure = self._analyze_pawn_structure(rows)
        features['pawn_structure'] = pawn_structure
        
        return features
    
    def _analyze_pawn_structure(self, rows: List[str]) -> Dict:
        structure = {
            'red_pawns': [],
            'black_pawns': [],
            'isolated_red': 0,
            'isolated_black': 0,
            'passed_red': 0,
            'passed_black': 0
        }
        
        for row_idx, row in enumerate(rows):
            col_idx = 0
            for c in row:
                if c.isdigit():
                    col_idx += int(c)
                elif c == 'P':
                    structure['red_pawns'].append((row_idx, col_idx))
                    col_idx += 1
                elif c == 'p':
                    structure['black_pawns'].append((row_idx, col_idx))
                    col_idx += 1
                elif c.isalpha():
                    col_idx += 1
        
        return structure
    
    def _get_engine_analysis(self, fen: str) -> Dict:
        if not self.engine:
            return {}
        
        try:
            result = self.engine.analyze(fen, depth=15)
            return {
                'score': result.score,
                'depth': result.depth,
                'pv': result.pv,
                'bestmove': result.bestmove
            }
        except Exception as e:
            return {'error': str(e)}
    
    def _get_model_output(self, fen: str) -> Dict:
        if not self.model or not self.tokenizer:
            return {}
        
        try:
            tokens = self.tokenizer.tokenize(fen)
            tokens_tensor = torch.tensor([tokens], dtype=torch.long)
            
            with torch.no_grad():
                outputs = self.model(tokens_tensor)
            
            return {
                'embedding': outputs['embedding'].numpy().tolist(),
                'semantic_tags': outputs['semantic_tags'].numpy().tolist(),
                'state_value': outputs['state_value'].item()
            }
        except Exception as e:
            return {'error': str(e)}
    
    def _determine_phase(
        self,
        board: str,
        rule_features: Dict,
        model_output: Optional[Dict]
    ) -> FieldSource:
        piece_count = rule_features['piece_count']
        heavy_pieces = rule_features['heavy_pieces']
        
        if piece_count >= 26 and heavy_pieces >= 4:
            phase = GamePhase.OPENING
            detail = f"子力{piece_count}枚，重子{heavy_pieces}个"
        elif piece_count <= 14:
            phase = GamePhase.ENDGAME
            detail = f"子力{piece_count}枚，进入残局"
        else:
            phase = GamePhase.MIDDLEGAME
            detail = f"子力{piece_count}枚，中局阶段"
        
        model_phase = None
        if model_output and 'semantic_tags' in model_output:
            tags = model_output['semantic_tags'][0]
            if len(tags) >= 3:
                opening_prob = tags[0]
                middle_prob = tags[1]
                end_prob = tags[2]
                
                probs = [opening_prob, middle_prob, end_prob]
                model_phase_idx = probs.index(max(probs))
                model_phase = [GamePhase.OPENING, GamePhase.MIDDLEGAME, GamePhase.ENDGAME][model_phase_idx]
                model_confidence = max(probs)
        
        if model_phase and model_confidence > 0.7:
            if model_phase == phase:
                return FieldSource(
                    value=phase,
                    source="[HYBRID] 规则+模型一致",
                    confidence=0.9,
                    detail=detail
                )
            else:
                return FieldSource(
                    value=model_phase,
                    source="[MODEL] 模型判断",
                    confidence=model_confidence,
                    detail=f"模型判断为{model_phase.value}，规则判断为{phase.value}"
                )
        
        return FieldSource(
            value=phase,
            source="[RULE] 子力计数规则",
            confidence=0.85,
            detail=detail
        )
    
    def _determine_initiative(
        self,
        engine_result: Optional[Dict],
        model_output: Optional[Dict]
    ) -> FieldSource:
        if engine_result and 'score' in engine_result:
            score = engine_result['score']
            
            if score > 100:
                initiative = Initiative.RED_ADVANTAGE
                detail = f"引擎评分+{score:.1f}"
            elif score < -100:
                initiative = Initiative.BLACK_ADVANTAGE
                detail = f"引擎评分{score:.1f}"
            elif score > 30:
                initiative = Initiative.RED_ADVANTAGE
                detail = f"引擎评分+{score:.1f}，红方略优"
            elif score < -30:
                initiative = Initiative.BLACK_ADVANTAGE
                detail = f"引擎评分{score:.1f}，黑方略优"
            else:
                initiative = Initiative.BALANCED
                detail = f"引擎评分{score:.1f}，均势"
            
            return FieldSource(
                value=initiative,
                source="[ENGINE] 引擎评分",
                confidence=min(0.95, 0.7 + abs(score) / 500),
                detail=detail
            )
        
        if model_output and 'state_value' in model_output:
            state_val = model_output['state_value']
            
            if state_val > 0.3:
                initiative = Initiative.RED_ADVANTAGE
            elif state_val < -0.3:
                initiative = Initiative.BLACK_ADVANTAGE
            else:
                initiative = Initiative.BALANCED
            
            return FieldSource(
                value=initiative,
                source="[MODEL] 模型状态值",
                confidence=0.6,
                detail=f"模型状态值{state_val:.3f}"
            )
        
        return FieldSource(
            value=Initiative.BALANCED,
            source="[DEFAULT] 无数据",
            confidence=0.3,
            detail="缺少引擎和模型数据"
        )
    
    def _determine_king_safety(
        self,
        board: str,
        side: str,
        engine_result: Optional[Dict],
        rule_features: Dict
    ) -> FieldSource:
        king_char = 'K' if side == 'red' else 'k'
        rows = rule_features['board_rows']
        
        king_pos = None
        for row_idx, row in enumerate(rows):
            col_idx = 0
            for c in row:
                if c.isdigit():
                    col_idx += int(c)
                elif c == king_char:
                    king_pos = (row_idx, col_idx)
                    break
                elif c.isalpha():
                    col_idx += 1
            if king_pos:
                break
        
        if not king_pos:
            return FieldSource(
                value=SafetyLevel.CRITICAL,
                source="[RULE] 规则检测",
                confidence=1.0,
                detail=f"未找到{side}方将/帅"
            )
        
        king_row, king_col = king_pos
        
        in_palace = self._is_in_palace(king_row, king_col, side)
        
        attacker_count = self._count_king_attackers(board, king_pos, side, rows)
        
        if side == 'red':
            expected_row_range = (7, 9)
        else:
            expected_row_range = (0, 2)
        
        in_home = expected_row_range[0] <= king_row <= expected_row_range[1]
        
        if attacker_count >= 2:
            safety = SafetyLevel.CRITICAL
            detail = f"将/帅受{attacker_count}子攻击"
            confidence = 0.9
        elif attacker_count >= 1:
            safety = SafetyLevel.EXPOSED
            detail = f"将/帅受{attacker_count}子威胁"
            confidence = 0.8
        elif not in_home:
            safety = SafetyLevel.EXPOSED
            detail = f"将/帅离开本阵"
            confidence = 0.7
        else:
            safety = SafetyLevel.SAFE
            detail = f"将/帅位置安全"
            confidence = 0.85
        
        if engine_result and 'score' in engine_result:
            score = engine_result['score']
            if side == 'red' and score < -150:
                safety = SafetyLevel.CRITICAL
                detail += f"，引擎评分{score:.0f}"
                confidence = 0.95
            elif side == 'black' and score > 150:
                safety = SafetyLevel.CRITICAL
                detail += f"，引擎评分+{score:.0f}"
                confidence = 0.95
        
        return FieldSource(
            value=safety,
            source="[RULE] 位置检测" + (" + [ENGINE]" if engine_result else ""),
            confidence=confidence,
            detail=detail
        )
    
    def _is_in_palace(self, row: int, col: int, side: str) -> bool:
        if col < 3 or col > 5:
            return False
        
        if side == 'red':
            return 7 <= row <= 9
        else:
            return 0 <= row <= 2
    
    def _count_king_attackers(
        self,
        board: str,
        king_pos: Tuple[int, int],
        side: str,
        rows: List[str]
    ) -> int:
        attackers = 0
        king_row, king_col = king_pos
        
        enemy_pieces = 'rnc' if side == 'red' else 'RNC'
        
        for row_idx, row in enumerate(rows):
            col_idx = 0
            for c in row:
                if c.isdigit():
                    col_idx += int(c)
                elif c in enemy_pieces:
                    if self._can_attack_king(c, row_idx, col_idx, king_row, king_col, rows):
                        attackers += 1
                    col_idx += 1
                elif c.isalpha():
                    col_idx += 1
        
        return attackers
    
    def _can_attack_king(
        self,
        piece: str,
        piece_row: int,
        piece_col: int,
        king_row: int,
        king_col: int,
        rows: List[str]
    ) -> bool:
        piece_type = piece.upper()
        
        if piece_type == 'R':
            if piece_row == king_row or piece_col == king_col:
                return self._is_path_clear(piece_row, piece_col, king_row, king_col, rows)
        
        elif piece_type == 'C':
            if piece_row == king_row or piece_col == king_col:
                return True
        
        elif piece_type == 'N':
            knight_moves = [
                (-2, -1), (-2, 1), (-1, -2), (-1, 2),
                (1, -2), (1, 2), (2, -1), (2, 1)
            ]
            for dr, dc in knight_moves:
                if piece_row + dr == king_row and piece_col + dc == king_col:
                    return True
        
        return False
    
    def _is_path_clear(
        self,
        r1: int, c1: int,
        r2: int, c2: int,
        rows: List[str]
    ) -> bool:
        if r1 == r2:
            start, end = min(c1, c2), max(c1, c2)
            row = rows[r1]
            col_idx = 0
            for c in row:
                if c.isdigit():
                    col_idx += int(c)
                elif col_idx > start and col_idx < end:
                    return False
                elif c.isalpha():
                    col_idx += 1
            return True
        
        if c1 == c2:
            for r in range(min(r1, r2) + 1, max(r1, r2)):
                row = rows[r]
                col_idx = 0
                for c in row:
                    if c.isdigit():
                        col_idx += int(c)
                    elif col_idx == c1:
                        return False
                    elif c.isalpha():
                        col_idx += 1
            return True
        
        return False
    
    def _determine_coordination(
        self,
        board: str,
        side: str,
        rule_features: Dict
    ) -> FieldSource:
        pieces = rule_features['red_pieces'] if side == 'red' else rule_features['black_pieces']
        
        if len(pieces) < 2:
            return FieldSource(
                value=CoordinationLevel.POOR,
                source="[RULE] 子力计数",
                confidence=0.9,
                detail=f"仅{len(pieces)}枚棋子"
            )
        
        coordination_score = 0
        detail_parts = []
        
        for i, (p1, r1, c1) in enumerate(pieces):
            for p2, r2, c2 in pieces[i+1:]:
                dist = abs(r1 - r2) + abs(c1 - c2)
                if dist <= 2:
                    coordination_score += 3
                elif dist <= 4:
                    coordination_score += 1
        
        max_possible = len(pieces) * (len(pieces) - 1) / 2 * 3
        if max_possible > 0:
            normalized = coordination_score / max_possible
        else:
            normalized = 0
        
        if normalized >= 0.7:
            level = CoordinationLevel.EXCELLENT
        elif normalized >= 0.5:
            level = CoordinationLevel.GOOD
        elif normalized >= 0.3:
            level = CoordinationLevel.MODERATE
        else:
            level = CoordinationLevel.POOR
        
        detail = f"协调度{normalized:.2f}，{len(pieces)}子配合"
        
        return FieldSource(
            value=level,
            source="[RULE] 子力距离分析",
            confidence=0.75,
            detail=detail
        )
    
    def _detect_weaknesses(
        self,
        board: str,
        rule_features: Dict,
        engine_result: Optional[Dict]
    ) -> FieldSource:
        weaknesses = []
        detail_parts = []
        
        pawn_struct = rule_features.get('pawn_structure', {})
        
        red_pawns = pawn_struct.get('red_pawns', [])
        black_pawns = pawn_struct.get('black_pawns', [])
        
        isolated_red = self._count_isolated_pawns(red_pawns)
        isolated_black = self._count_isolated_pawns(black_pawns)
        
        if isolated_red > 0:
            weaknesses.append(f"红方{isolated_red}个孤兵")
            detail_parts.append(f"红孤兵:{isolated_red}")
        
        if isolated_black > 0:
            weaknesses.append(f"黑方{isolated_black}个孤兵")
            detail_parts.append(f"黑孤兵:{isolated_black}")
        
        if engine_result and 'score' in engine_result:
            score = engine_result['score']
            if abs(score) > 200:
                weaknesses.append("局面失衡")
                detail_parts.append(f"评分偏差:{abs(score):.0f}")
        
        if not weaknesses:
            weaknesses.append("无明显弱点")
            detail_parts.append("结构正常")
        
        return FieldSource(
            value=weaknesses,
            source="[RULE] 结构分析" + (" + [ENGINE]" if engine_result else ""),
            confidence=0.7,
            detail="; ".join(detail_parts)
        )
    
    def _count_isolated_pawns(self, pawns: List[Tuple[int, int]]) -> int:
        if len(pawns) <= 1:
            return 0
        
        isolated = 0
        for r1, c1 in pawns:
            has_neighbor = False
            for r2, c2 in pawns:
                if (r1, c1) != (r2, c2):
                    if abs(c1 - c2) <= 1:
                        has_neighbor = True
                        break
            if not has_neighbor:
                isolated += 1
        
        return isolated
    
    def _determine_move_type(
        self,
        engine_result: Optional[Dict],
        model_output: Optional[Dict]
    ) -> FieldSource:
        if engine_result and 'score' in engine_result:
            score = engine_result['score']
            pv = engine_result.get('pv', [])
            
            if abs(score) > 150:
                move_type = MoveType.TACTICAL
                detail = f"战术性着法，评分{score:.0f}"
            elif abs(score) > 50:
                move_type = MoveType.POSITIONAL
                detail = f"局面性着法，评分{score:.0f}"
            else:
                move_type = MoveType.NEUTRAL
                detail = f"中性着法，评分{score:.0f}"
            
            if pv and len(pv) > 0:
                detail += f"，PV: {' '.join(pv[:3])}"
            
            return FieldSource(
                value=move_type,
                source="[ENGINE] 引擎分析",
                confidence=0.8,
                detail=detail
            )
        
        if model_output and 'semantic_tags' in model_output:
            tags = model_output['semantic_tags'][0]
            
            tactical_idx = 28
            if len(tags) > tactical_idx:
                tactical_score = tags[tactical_idx]
                if tactical_score > 0.6:
                    return FieldSource(
                        value=MoveType.TACTICAL,
                        source="[MODEL] 模型判断",
                        confidence=tactical_score,
                        detail=f"模型判断为战术局面"
                    )
        
        return FieldSource(
            value=MoveType.NEUTRAL,
            source="[DEFAULT] 默认值",
            confidence=0.3,
            detail="缺少分析数据"
        )
    
    def _calculate_confidence(self, *fields: FieldSource) -> float:
        confidences = [f.confidence for f in fields if f.confidence > 0]
        if not confidences:
            return 0.0
        return sum(confidences) / len(confidences)


def generate_semantic_state(
    fen: str,
    model=None,
    tokenizer=None,
    engine=None,
    engine_result: Optional[Dict] = None,
    model_output: Optional[Dict] = None
) -> Dict:
    """
    便捷函数：生成语义状态
    
    返回完整的语义状态字典，每个字段标明来源
    """
    generator = SemanticStateGeneratorV1(model, tokenizer, engine)
    state = generator.generate(fen, engine_result, model_output)
    return state.to_dict()


if __name__ == "__main__":
    test_fens = [
        "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1",
        "2baka3/9/2R6/p8/4PP3/3p5/9/4r4/4A4/3AK4 b - - 40 40",
        "4k4/9/9/9/9/9/9/9/9/4K4 w - - 0 1",
    ]
    
    print("=" * 70)
    print("语义状态生成器 v1 测试")
    print("=" * 70)
    
    generator = SemanticStateGeneratorV1()
    
    for i, fen in enumerate(test_fens, 1):
        print(f"\n【测试 {i}】")
        print(f"FEN: {fen[:50]}...")
        
        state = generator.generate(fen)
        result = state.to_dict()
        
        print(f"\n阶段: {result['phase']['value']} [{result['phase']['source']}]")
        print(f"  置信度: {result['phase']['confidence']}")
        print(f"  详情: {result['phase']['detail']}")
        
        print(f"\n主动权: {result['initiative']['value']} [{result['initiative']['source']}]")
        print(f"  详情: {result['initiative']['detail']}")
        
        print(f"\n红方王安全: {result['red_king_safety']['value']}")
        print(f"黑方王安全: {result['black_king_safety']['value']}")
        
        print(f"\n红方协调: {result['red_coordination']['value']}")
        print(f"黑方协调: {result['black_coordination']['value']}")
        
        print(f"\n弱点: {result['long_term_weaknesses']['value']}")
        
        print(f"\n着法类型: {result['move_type']['value']}")
        
        print(f"\n总体置信度: {result['overall_confidence']}")
        print("-" * 70)
