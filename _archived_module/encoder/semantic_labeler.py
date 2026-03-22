"""
语义标签生成器

基于PDF文档"语义监督的三种强落地方式"：
1. 规则弱监督：将军、牵制、兑子、弃子、悬子等
2. 引擎诱导伪标签：blunder、forcing_move、improving_move
3. LLM辅助标注+清洗：主动权、核心矛盾、节奏等
"""

from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass, field
import re
from pathlib import Path
import json

from core.rules.xiangqi_rules import XiangqiRulesEngine
from core.encoder.position_encoder import SEMANTIC_TAGS


SEMANTIC_TAG_INDEX = {tag: i for i, tag in enumerate(SEMANTIC_TAGS)}


@dataclass
class SemanticLabels:
    """语义标签结果"""
    fen: str
    tags: Dict[str, float] = field(default_factory=dict)
    sources: Dict[str, str] = field(default_factory=dict)
    
    def to_vector(self) -> List[float]:
        """转换为32维向量"""
        vector = [0.0] * len(SEMANTIC_TAGS)
        for tag, prob in self.tags.items():
            if tag in SEMANTIC_TAG_INDEX:
                vector[SEMANTIC_TAG_INDEX[tag]] = prob
        return vector
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'fen': self.fen,
            'tags': self.tags,
            'sources': self.sources,
            'vector': self.to_vector()
        }


class RuleBasedLabeler:
    """
    规则弱监督标签生成器
    
    零成本，纯规则判定
    标签：将军、牵制、兑子、弃子、悬子、兵形等
    """
    
    def __init__(self):
        self.rules_engine = XiangqiRulesEngine()
    
    def parse_fen_to_board(self, fen: str) -> Tuple[List[List[str]], str]:
        """解析FEN为棋盘"""
        board_str = fen.split()[0]
        side_to_move = fen.split()[1] if len(fen.split()) > 1 else 'w'
        
        board = []
        for row_str in board_str.split('/'):
            row = []
            for char in row_str:
                if char.isdigit():
                    row.extend([''] * int(char))
                else:
                    row.append(char)
            board.append(row)
        
        return board, side_to_move
    
    def label(self, fen: str) -> SemanticLabels:
        """生成规则弱监督标签"""
        labels = SemanticLabels(fen=fen)
        board, side = self.parse_fen_to_board(fen)
        is_red_turn = side == 'w'
        
        labels.tags['opening'] = self._is_opening(board)
        labels.tags['middlegame'] = self._is_middlegame(board)
        labels.tags['endgame'] = self._is_endgame(board)
        labels.sources['phase'] = 'RULE'
        
        check_red, check_black = self._detect_check(board)
        if check_red:
            labels.tags['king_safety_red'] = 0.3
        if check_black:
            labels.tags['king_safety_black'] = 0.3
        if check_red or check_black:
            labels.sources['check'] = 'RULE'
        
        pinned_red, pinned_black = self._detect_pinned_pieces(board)
        if pinned_red:
            labels.tags['pinned_piece'] = max(labels.tags.get('pinned_piece', 0), 0.8)
        if pinned_black:
            labels.tags['pinned_piece'] = max(labels.tags.get('pinned_piece', 0), 0.8)
        if pinned_red or pinned_black:
            labels.sources['pinned'] = 'RULE'
        
        hanging = self._detect_hanging_pieces(board, is_red_turn)
        if hanging:
            labels.tags['hanging_piece'] = 0.9
            labels.sources['hanging'] = 'RULE'
        
        mat_adv = self._calculate_material_advantage(board)
        if mat_adv > 100:
            labels.tags['material_advantage'] = min(1.0, mat_adv / 500)
            labels.sources['material'] = 'RULE'
        elif mat_adv < -100:
            labels.tags['material_disadvantage'] = min(1.0, abs(mat_adv) / 500)
            labels.sources['material'] = 'RULE'
        
        passed_pawns, isolated_pawns = self._detect_pawn_structure(board)
        if passed_pawns > 0:
            labels.tags['passed_pawn'] = min(1.0, passed_pawns / 3)
            labels.sources['pawn_structure'] = 'RULE'
        if isolated_pawns > 0:
            labels.tags['isolated_pawn'] = min(1.0, isolated_pawns / 3)
            labels.sources['pawn_structure'] = 'RULE'
        
        open_files = self._detect_open_files(board)
        if open_files > 0:
            labels.tags['open_file'] = min(1.0, open_files / 3)
            labels.sources['files'] = 'RULE'
        
        active_rooks = self._detect_active_rooks(board)
        if active_rooks['red'] > active_rooks['black']:
            labels.tags['active_rook'] = 0.7
        elif active_rooks['black'] > active_rooks['red']:
            labels.tags['passive_rook'] = 0.7
        if active_rooks['red'] > 0 or active_rooks['black'] > 0:
            labels.sources['rook_activity'] = 'RULE'
        
        return labels
    
    def _count_pieces(self, board: List[List[str]]) -> Tuple[int, int]:
        """统计双方棋子数量"""
        red_count = 0
        black_count = 0
        for row in board:
            for piece in row:
                if piece:
                    if piece.isupper():
                        red_count += 1
                    else:
                        black_count += 1
        return red_count, black_count
    
    def _is_opening(self, board: List[List[str]]) -> float:
        """判断是否开局（棋子>=28）"""
        red, black = self._count_pieces(board)
        total = red + black
        if total >= 28:
            return 0.9
        return 0.1
    
    def _is_middlegame(self, board: List[List[str]]) -> float:
        """判断是否中局（棋子16-27）"""
        red, black = self._count_pieces(board)
        total = red + black
        if 16 <= total < 28:
            return 0.9
        return 0.1
    
    def _is_endgame(self, board: List[List[str]]) -> float:
        """判断是否残局（棋子<16）"""
        red, black = self._count_pieces(board)
        total = red + black
        if total < 16:
            return 0.9
        return 0.1
    
    def _detect_check(self, board: List[List[str]]) -> Tuple[bool, bool]:
        """检测将军状态"""
        check_red = False
        check_black = False
        
        red_king_pos = self._find_king(board, is_red=True)
        black_king_pos = self._find_king(board, is_red=False)
        
        if red_king_pos:
            for r in range(10):
                for c in range(9):
                    piece = board[r][c]
                    if piece and piece.islower():
                        moves = XiangqiRulesEngine.get_legal_moves(board, r, c)
                        if red_king_pos in moves:
                            check_red = True
                            break
        
        if black_king_pos:
            for r in range(10):
                for c in range(9):
                    piece = board[r][c]
                    if piece and piece.isupper():
                        moves = XiangqiRulesEngine.get_legal_moves(board, r, c)
                        if black_king_pos in moves:
                            check_black = True
                            break
        
        return check_red, check_black
    
    def _find_king(self, board: List[List[str]], is_red: bool) -> Optional[Tuple[int, int]]:
        """查找将/帅位置"""
        king = 'K' if is_red else 'k'
        for r in range(10):
            for c in range(9):
                if board[r][c] == king:
                    return (r, c)
        return None
    
    def _detect_pinned_pieces(self, board: List[List[str]]) -> Tuple[int, int]:
        """检测牵制棋子（简化版：检测炮的牵制）"""
        pinned_red = 0
        pinned_black = 0
        
        for r in range(10):
            for c in range(9):
                piece = board[r][c]
                if piece and piece.lower() == 'c':
                    is_red = piece.isupper()
                    king_pos = self._find_king(board, is_red=not is_red)
                    if king_pos:
                        if is_red:
                            pinned_black += self._check_pin_along_line(board, r, c, king_pos)
                        else:
                            pinned_red += self._check_pin_along_line(board, r, c, king_pos)
        
        return pinned_red, pinned_black
    
    def _check_pin_along_line(self, board: List[List[str]], 
                               cannon_r: int, cannon_c: int,
                               king_pos: Tuple[int, int]) -> int:
        """检查炮是否牵制了棋子"""
        kr, kc = king_pos
        if cannon_r == kr or cannon_c == kc:
            return 1
        return 0
    
    def _detect_hanging_pieces(self, board: List[List[str]], is_red_turn: bool) -> bool:
        """检测悬子（简化版）"""
        return False
    
    def _calculate_material_advantage(self, board: List[List[str]]) -> int:
        """计算子力优势"""
        piece_values = {
            'k': 0, 'a': 20, 'b': 20, 'n': 40, 'r': 90, 'c': 45, 'p': 10,
            'K': 0, 'A': 20, 'B': 20, 'N': 40, 'R': 90, 'C': 45, 'P': 10
        }
        
        red_value = 0
        black_value = 0
        
        for row in board:
            for piece in row:
                if piece:
                    value = piece_values.get(piece, 0)
                    if piece.isupper():
                        red_value += value
                    else:
                        black_value += value
        
        return red_value - black_value
    
    def _detect_pawn_structure(self, board: List[List[str]]) -> Tuple[int, int]:
        """检测兵形：过河兵、孤兵"""
        passed_pawns = 0
        isolated_pawns = 0
        
        for r in range(10):
            for c in range(9):
                piece = board[r][c]
                if piece == 'P' and r <= 4:
                    passed_pawns += 1
                elif piece == 'p' and r >= 5:
                    passed_pawns += 1
        
        return passed_pawns, isolated_pawns
    
    def _detect_open_files(self, board: List[List[str]]) -> int:
        """检测开放线路"""
        open_files = 0
        for c in range(9):
            has_pawn = False
            for r in range(10):
                if board[r][c] in ['P', 'p']:
                    has_pawn = True
                    break
            if not has_pawn:
                open_files += 1
        return open_files
    
    def _detect_active_rooks(self, board: List[List[str]]) -> Dict[str, int]:
        """检测活跃的车"""
        active = {'red': 0, 'black': 0}
        
        for r in range(10):
            for c in range(9):
                piece = board[r][c]
                if piece == 'R':
                    if r <= 4 or c in [0, 8]:
                        active['red'] += 1
                elif piece == 'r':
                    if r >= 5 or c in [0, 8]:
                        active['black'] += 1
        
        return active


class EngineInducedLabeler:
    """
    引擎诱导伪标签生成器
    
    用PV差异与评估变化生成标签
    标签：blunder、forcing_move、improving_move、critical_position
    """
    
    def __init__(self, engine):
        self.engine = engine
        self.score_history = []
    
    def label(self, fen: str, prev_score: Optional[float] = None, 
              best_move: Optional[str] = None, pv: Optional[List[str]] = None) -> SemanticLabels:
        """生成引擎诱导标签"""
        labels = SemanticLabels(fen=fen)
        
        try:
            result = self.engine.analyze(fen, depth=15)
            current_score = result.score
            
            if prev_score is not None:
                score_change = current_score - prev_score
                
                if abs(score_change) > 1.0:
                    labels.tags['critical_position'] = 0.9
                    labels.sources['critical'] = 'ENGINE'
                
                if score_change < -1.5:
                    labels.tags['blunder'] = min(1.0, abs(score_change) / 3)
                    labels.sources['blunder'] = 'ENGINE'
                
                if score_change > 1.0:
                    labels.tags['improving_move'] = min(1.0, score_change / 2)
                    labels.sources['improving'] = 'ENGINE'
            
            if pv and len(pv) >= 3:
                if self._is_forcing_sequence(pv):
                    labels.tags['initiative'] = 0.8
                    labels.sources['initiative'] = 'ENGINE'
            
            if abs(current_score) < 0.3:
                labels.tags['quiet_position'] = 0.7
                labels.sources['quiet'] = 'ENGINE'
            elif abs(current_score) > 2.0:
                labels.tags['critical_position'] = 0.9
                labels.sources['critical'] = 'ENGINE'
            
            self.score_history.append(current_score)
            
        except Exception as e:
            labels.sources['error'] = f'ENGINE_ERROR: {str(e)}'
        
        return labels
    
    def _is_forcing_sequence(self, pv: List[str]) -> bool:
        """判断是否强制序列（将军、吃子等）"""
        forcing_count = 0
        for move in pv[:4]:
            if '+' in move or 'x' in move:
                forcing_count += 1
        return forcing_count >= 2
    
    def label_from_game(self, fens: List[str]) -> List[SemanticLabels]:
        """从整局棋生成标签"""
        all_labels = []
        prev_score = None
        
        for fen in fens:
            labels = self.label(fen, prev_score=prev_score)
            all_labels.append(labels)
            
            try:
                result = self.engine.analyze(fen, depth=15)
                prev_score = result.score
            except:
                pass
        
        return all_labels


class LLMAssistedLabeler:
    """
    LLM辅助标注+清洗
    
    用于生成抽象语义标签：主动权、核心矛盾、节奏等
    需要verifier清洗
    """
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
    
    def label(self, fen: str, engine_info: Optional[Dict] = None) -> SemanticLabels:
        """生成LLM辅助标签"""
        labels = SemanticLabels(fen=fen)
        
        if not self.llm_client:
            labels.sources['llm'] = 'NOT_AVAILABLE'
            return labels
        
        try:
            prompt = self._build_prompt(fen, engine_info)
            response = self.llm_client.chat(prompt)
            
            parsed_tags = self._parse_llm_response(response)
            
            for tag, value in parsed_tags.items():
                if tag in SEMANTIC_TAG_INDEX:
                    labels.tags[tag] = value
                    labels.sources[tag] = 'INFERRED'
            
        except Exception as e:
            labels.sources['llm_error'] = f'LLM_ERROR: {str(e)}'
        
        return labels
    
    def _build_prompt(self, fen: str, engine_info: Optional[Dict]) -> str:
        """构建LLM提示"""
        prompt = f"""分析以下象棋局面，输出语义标签。

FEN: {fen}

"""
        if engine_info:
            prompt += f"""引擎信息:
- 评分: {engine_info.get('score', 'N/A')}
- 最佳着法: {engine_info.get('best_move', 'N/A')}
- 主要变例: {' '.join(engine_info.get('pv', [])[:5])}

"""
        
        prompt += """请输出以下标签的概率值（0.0-1.0），每行一个：
- initiative: 主动权（谁在主导局面）
- tempo_advantage: 节奏优势
- space_advantage: 空间优势
- mobility_advantage: 机动性优势
- attack_red/attack_black: 攻击态势
- defense_red/defense_black: 防守态势

格式示例：
initiative: 0.8
tempo_advantage: 0.6
"""
        return prompt
    
    def _parse_llm_response(self, response: str) -> Dict[str, float]:
        """解析LLM响应"""
        tags = {}
        for line in response.split('\n'):
            if ':' in line:
                parts = line.split(':')
                if len(parts) >= 2:
                    tag = parts[0].strip().lower()
                    try:
                        value = float(parts[1].strip())
                        if 0 <= value <= 1:
                            tags[tag] = value
                    except ValueError:
                        pass
        return tags


class SemanticLabelerPipeline:
    """
    语义标签生成流水线
    
    整合三种方法：规则弱监督 + 引擎诱导 + LLM辅助
    """
    
    def __init__(self, engine=None, llm_client=None):
        self.rule_labeler = RuleBasedLabeler()
        self.engine_labeler = EngineInducedLabeler(engine) if engine else None
        self.llm_labeler = LLMAssistedLabeler(llm_client)
        self.engine = engine
    
    def label(self, fen: str, prev_score: Optional[float] = None,
              engine_info: Optional[Dict] = None) -> SemanticLabels:
        """完整标签生成流程"""
        rule_labels = self.rule_labeler.label(fen)
        
        if self.engine_labeler:
            engine_labels = self.engine_labeler.label(fen, prev_score=prev_score)
            rule_labels.tags.update(engine_labels.tags)
            rule_labels.sources.update(engine_labels.sources)
        
        llm_labels = self.llm_labeler.label(fen, engine_info=engine_info)
        for tag, value in llm_labels.tags.items():
            if tag not in rule_labels.tags:
                rule_labels.tags[tag] = value
                rule_labels.sources[tag] = 'INFERRED'
        
        return rule_labels
    
    def label_batch(self, fens: List[str], output_path: Optional[str] = None) -> List[SemanticLabels]:
        """批量生成标签"""
        all_labels = []
        prev_score = None
        
        for fen in fens:
            labels = self.label(fen, prev_score=prev_score)
            all_labels.append(labels)
            
            if self.engine:
                try:
                    result = self.engine.analyze(fen, depth=12)
                    prev_score = result.score
                except:
                    pass
        
        if output_path:
            self._save_labels(all_labels, output_path)
        
        return all_labels
    
    def _save_labels(self, labels: List[SemanticLabels], output_path: str):
        """保存标签到文件"""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for label in labels:
                f.write(json.dumps(label.to_dict(), ensure_ascii=False) + '\n')
        
        print(f"保存 {len(labels)} 条标签到 {output_path}")


def demo():
    """演示语义标签生成"""
    print("=" * 50)
    print("语义标签生成器演示")
    print("=" * 50)
    
    rule_labeler = RuleBasedLabeler()
    
    test_fens = [
        "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1",
        "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 5",
    ]
    
    for fen in test_fens:
        print(f"\nFEN: {fen[:50]}...")
        labels = rule_labeler.label(fen)
        
        print("标签:")
        for tag, prob in sorted(labels.tags.items(), key=lambda x: -x[1]):
            if prob > 0.1:
                source = labels.sources.get(tag.split('_')[0], 'RULE')
                print(f"  {tag}: {prob:.2f} ({source})")


if __name__ == "__main__":
    demo()
