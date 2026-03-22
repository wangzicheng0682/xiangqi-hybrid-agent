"""
语义标签生成器 - 第一版

功能：
1. 阶段识别（opening/middlegame/endgame）
2. 主动权判断（red/black/balanced）
3. 风险评估（high/medium/low）
4. 结构分析（open/closed/semi）
5. 战术活跃度（active/quiet）
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
import subprocess
import re


@dataclass
class SemanticLabels:
    """语义标签"""
    phase: str
    initiative: str
    risk: str
    structure: str
    tactics: str
    
    def to_dict(self) -> dict:
        return {
            'phase': self.phase,
            'initiative': self.initiative,
            'risk': self.risk,
            'structure': self.structure,
            'tactics': self.tactics
        }


class SemanticLabelGenerator:
    """语义标签生成器"""
    
    PHASE_OPENING = 'opening'
    PHASE_MIDDLE = 'middlegame'
    PHASE_END = 'endgame'
    
    INITIATIVE_RED = 'red'
    INITIATIVE_BLACK = 'black'
    INITIATIVE_BALANCED = 'balanced'
    
    RISK_HIGH = 'high'
    RISK_MEDIUM = 'medium'
    RISK_LOW = 'low'
    
    STRUCTURE_OPEN = 'open'
    STRUCTURE_CLOSED = 'closed'
    STRUCTURE_SEMI = 'semi'
    
    TACTICS_ACTIVE = 'active'
    TACTICS_QUIET = 'quiet'
    
    def __init__(self, engine_path: str = "data/engine/pikafish-avx2.exe"):
        self.engine_path = engine_path
        self.engine_proc = None
    
    def start_engine(self):
        if self.engine_proc is None:
            self.engine_proc = subprocess.Popen(
                [self.engine_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                bufsize=1
            )
            self.engine_proc.stdin.write("uci\n")
            self.engine_proc.stdin.flush()
            while "uciok" not in self.engine_proc.stdout.readline():
                pass
    
    def stop_engine(self):
        if self.engine_proc:
            self.engine_proc.kill()
            self.engine_proc = None
    
    def generate(self, fen: str, engine_score: Optional[float] = None) -> SemanticLabels:
        if engine_score is None:
            engine_score = self._get_engine_score(fen)
        
        phase = self._detect_phase(fen)
        initiative = self._detect_initiative(engine_score)
        risk = self._detect_risk(engine_score)
        structure = self._detect_structure(fen)
        tactics = self._detect_tactics(engine_score)
        
        return SemanticLabels(
            phase=phase,
            initiative=initiative,
            risk=risk,
            structure=structure,
            tactics=tactics
        )
    
    def generate_with_engine(self, fen: str, depth: int = 12) -> Dict:
        self.start_engine()
        
        self.engine_proc.stdin.write(f"position fen {fen}\ngo depth {depth}\n")
        self.engine_proc.stdin.flush()
        
        score = 0.0
        best_move = ""
        pv = []
        
        while True:
            line = self.engine_proc.stdout.readline()
            if 'score cp' in line and 'bound' not in line:
                try:
                    score = int(line.split('score cp')[1].split()[0]) / 100.0
                except:
                    pass
            elif 'score mate' in line:
                try:
                    mate_in = int(line.split('score mate')[1].split()[0])
                    score = 100.0 if mate_in > 0 else -100.0
                except:
                    pass
            elif ' pv ' in line:
                try:
                    pv_part = line.split(' pv ')[1].strip()
                    pv = pv_part.split()[:5]
                except:
                    pass
            if 'bestmove' in line:
                parts = line.split()
                if len(parts) >= 2:
                    best_move = parts[1]
                break
        
        labels = self.generate(fen, score)
        
        return {
            'fen': fen,
            'engine_score': score,
            'best_move': best_move,
            'pv': pv,
            'semantic_labels': labels.to_dict()
        }
    
    def _get_engine_score(self, fen: str, depth: int = 10) -> float:
        self.start_engine()
        
        self.engine_proc.stdin.write(f"position fen {fen}\ngo depth {depth}\n")
        self.engine_proc.stdin.flush()
        
        score = 0.0
        while True:
            line = self.engine_proc.stdout.readline()
            if 'score cp' in line and 'bound' not in line:
                try:
                    score = int(line.split('score cp')[1].split()[0]) / 100.0
                except:
                    pass
            elif 'score mate' in line:
                try:
                    mate_in = int(line.split('score mate')[1].split()[0])
                    score = 100.0 if mate_in > 0 else -100.0
                except:
                    pass
            if 'bestmove' in line:
                break
        
        return score
    
    def _detect_phase(self, fen: str) -> str:
        board = fen.split()[0]
        
        piece_count = sum(1 for c in board if c.isalpha())
        
        heavy_pieces = 0
        for piece in 'RrCcNn':
            heavy_pieces += board.count(piece)
        
        if piece_count >= 26 and heavy_pieces >= 4:
            return self.PHASE_OPENING
        elif piece_count <= 14:
            return self.PHASE_END
        else:
            return self.PHASE_MIDDLE
    
    def _detect_initiative(self, score: float) -> str:
        if score > 50:
            return self.INITIATIVE_RED
        elif score < -50:
            return self.INITIATIVE_BLACK
        else:
            return self.INITIATIVE_BALANCED
    
    def _detect_risk(self, score: float) -> str:
        abs_score = abs(score)
        if abs_score > 200:
            return self.RISK_HIGH
        elif abs_score > 50:
            return self.RISK_MEDIUM
        else:
            return self.RISK_LOW
    
    def _detect_structure(self, fen: str) -> str:
        board = fen.split()[0]
        
        pawn_count = board.count('P') + board.count('p')
        
        rows = board.split('/')
        center_pawns = 0
        for row in rows[3:7]:
            for c in row:
                if c in 'Pp':
                    center_pawns += 1
        
        if pawn_count <= 6:
            return self.STRUCTURE_OPEN
        elif center_pawns >= 4:
            return self.STRUCTURE_CLOSED
        else:
            return self.STRUCTURE_SEMI
    
    def _detect_tactics(self, score: float) -> str:
        abs_score = abs(score)
        if abs_score > 100:
            return self.TACTICS_ACTIVE
        else:
            return self.TACTICS_QUIET


class EnhancedSemanticGenerator(SemanticLabelGenerator):
    """增强版语义标签生成器"""
    
    def generate(self, fen: str, engine_score: Optional[float] = None) -> Dict:
        base_labels = super().generate(fen, engine_score)
        
        board = fen.split()[0]
        
        enhanced = {
            'phase': base_labels.phase,
            'initiative': base_labels.initiative,
            'risk': base_labels.risk,
            'structure': base_labels.structure,
            'tactics': base_labels.tactics,
            'king_safety': self._detect_king_safety(board),
            'piece_coordination': self._detect_piece_coordination(board),
            'material_balance': self._calculate_material(board),
        }
        
        return enhanced
    
    def _detect_king_safety(self, board: str) -> str:
        rows = board.split('/')
        
        red_king_row = None
        black_king_row = None
        
        for i, row in enumerate(rows):
            if 'K' in row:
                red_king_row = i
            if 'k' in row:
                black_king_row = i
        
        if red_king_row is None or black_king_row is None:
            return 'unknown'
        
        red_king_safe = red_king_row >= 7
        black_king_safe = black_king_row <= 2
        
        if red_king_safe and black_king_safe:
            return 'both_safe'
        elif red_king_safe:
            return 'red_safe'
        elif black_king_safe:
            return 'black_safe'
        else:
            return 'both_exposed'
    
    def _detect_piece_coordination(self, board: str) -> str:
        red_pieces = []
        black_pieces = []
        
        rows = board.split('/')
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
        
        red_coord = self._calc_coordination(red_pieces)
        black_coord = self._calc_coordination(black_pieces)
        
        if red_coord > black_coord + 2:
            return 'red_better'
        elif black_coord > red_coord + 2:
            return 'black_better'
        else:
            return 'balanced'
    
    def _calc_coordination(self, pieces: List) -> float:
        if len(pieces) < 2:
            return 0
        
        score = 0
        for i, (p1, r1, c1) in enumerate(pieces):
            for p2, r2, c2 in pieces[i+1:]:
                dist = abs(r1 - r2) + abs(c1 - c2)
                if dist <= 3:
                    score += 1
        
        return score / len(pieces)
    
    def _calculate_material(self, board: str) -> str:
        piece_values = {
            'K': 0, 'k': 0,
            'R': 9, 'r': -9,
            'C': 4.5, 'c': -4.5,
            'N': 4, 'n': -4,
            'B': 2, 'b': -2,
            'A': 2, 'a': -2,
            'P': 1, 'p': -1,
        }
        
        total = 0
        for c in board:
            if c in piece_values:
                total += piece_values[c]
        
        if total > 3:
            return 'red_ahead'
        elif total < -3:
            return 'black_ahead'
        else:
            return 'balanced'


if __name__ == "__main__":
    generator = EnhancedSemanticGenerator()
    
    test_fens = [
        "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1",
        "2baka3/9/2R6/p8/4PP3/3p5/9/4r4/4A4/3AK4 b - - 40 40",
        "4k4/9/9/9/9/9/9/9/9/4K4 w - - 0 1",
    ]
    
    print("语义标签生成器测试")
    print("=" * 60)
    
    for fen in test_fens:
        print(f"\nFEN: {fen[:50]}...")
        result = generator.generate_with_engine(fen)
        
        print(f"  引擎分数: {result['engine_score']:.1f}")
        print(f"  最佳着法: {result['best_move']}")
        print(f"  语义标签:")
        for key, value in result['semantic_labels'].items():
            print(f"    {key}: {value}")
    
    generator.stop_engine()
