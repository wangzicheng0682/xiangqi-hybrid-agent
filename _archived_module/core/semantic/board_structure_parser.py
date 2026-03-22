"""
局面结构解析器 - T0核心组件

四层能力：
1. 棋子真实位置层 - 精确输出所有棋子位置、存活状态、当前行棋方
2. 棋子关系层 - 谁攻击谁、谁保护谁、谁受限、哪些线路打开
3. 结构摘要层 - 阶段、主动权、王安全、活跃子、受限子、关键冲突区域
4. LLM/检索可消费层 - 结构化上下文，供LLM和检索使用

研发原则：
- 规则优先：棋子位置、攻击、防守、争夺点、线路关系优先用规则精确计算
- 模型辅助：少量语义判断可用轻模型或规则混合
- LLM只负责表达，不负责重建棋盘空间
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set
from enum import Enum
import json


class PieceType(Enum):
    KING = "k"
    ADVISOR = "a"
    ELEPHANT = "b"
    ROOK = "r"
    CANNON = "c"
    KNIGHT = "n"
    PAWN = "p"


class RelationType(Enum):
    ATTACKS = "attacks"
    PROTECTS = "protects"
    BLOCKS = "blocks"
    PINNED_BY = "pinned_by"
    THREATENS = "threatens"


@dataclass
class PieceInfo:
    piece: str
    row: int
    col: int
    is_red: bool
    piece_type: str
    is_alive: bool = True
    
    def to_dict(self) -> dict:
        return {
            "piece": self.piece,
            "position": f"({self.row}, {self.col})",
            "is_red": self.is_red,
            "piece_type": self.piece_type,
            "is_alive": self.is_alive
        }
    
    def to_chinese(self) -> str:
        chinese_names = {
            'K': '帅', 'k': '将',
            'A': '仕', 'a': '士',
            'B': '相', 'b': '象',
            'R': '车', 'r': '车',
            'C': '炮', 'c': '炮',
            'N': '马', 'n': '马',
            'P': '兵', 'p': '卒'
        }
        return chinese_names.get(self.piece, self.piece)
    
    def position_name(self) -> str:
        col_names = ['一', '二', '三', '四', '五', '六', '七', '八', '九']
        row_names = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10']
        return f"{col_names[self.col]}{row_names[self.row]}"


@dataclass
class Relation:
    from_piece: str
    from_position: Tuple[int, int]
    to_piece: str
    to_position: Tuple[int, int]
    relation_type: RelationType
    description: str = ""
    
    def to_dict(self) -> dict:
        return {
            "from": f"{self.from_piece}@{self.from_position}",
            "to": f"{self.to_piece}@{self.to_position}",
            "type": self.relation_type.value,
            "description": self.description
        }
    
    def to_chinese_description(self) -> str:
        return self.description


@dataclass
class StructuralSummary:
    phase: str
    phase_detail: str
    initiative: str
    initiative_detail: str
    red_king_safety: str
    black_king_safety: str
    active_pieces: List[str]
    restricted_pieces: List[str]
    key_conflict_areas: List[str]
    
    def to_dict(self) -> dict:
        return {
            "phase": self.phase,
            "phase_detail": self.phase_detail,
            "initiative": self.initiative,
            "initiative_detail": self.initiative_detail,
            "red_king_safety": self.red_king_safety,
            "black_king_safety": self.black_king_safety,
            "active_pieces": self.active_pieces,
            "restricted_pieces": self.restricted_pieces,
            "key_conflict_areas": self.key_conflict_areas
        }


@dataclass
class LLMContext:
    position_summary: str
    key_relations: List[str]
    tactical_themes: List[str]
    strategic_advice: str
    search_keywords: List[str]
    
    def to_dict(self) -> dict:
        return {
            "position_summary": self.position_summary,
            "key_relations": self.key_relations,
            "tactical_themes": self.tactical_themes,
            "strategic_advice": self.strategic_advice,
            "search_keywords": self.search_keywords
        }


@dataclass
class BoardStructureOutput:
    pieces: List[PieceInfo]
    relations: List[Relation]
    structural_summary: StructuralSummary
    llm_context: LLMContext
    raw_fen: str
    side_to_move: str
    
    def to_dict(self) -> dict:
        return {
            "pieces": [p.to_dict() for p in self.pieces],
            "relations": [r.to_dict() for r in self.relations],
            "structural_summary": self.structural_summary.to_dict(),
            "llm_context": self.llm_context.to_dict(),
            "raw_fen": self.raw_fen,
            "side_to_move": self.side_to_move
        }
    
    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)


class BoardStructureParser:
    """
    局面结构解析器
    
    四层能力：
    1. 棋子真实位置层
    2. 棋子关系层
    3. 结构摘要层
    4. LLM/检索可消费层
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
    
    def __init__(self):
        pass
    
    def parse(self, fen: str) -> BoardStructureOutput:
        board, side_to_move = self._fen_to_board(fen)
        
        pieces = self._extract_pieces(board)
        
        relations = self._extract_relations(board, pieces)
        
        summary = self._extract_summary(board, pieces, relations, side_to_move)
        
        llm_context = self._build_llm_context(pieces, relations, summary)
        
        return BoardStructureOutput(
            pieces=pieces,
            relations=relations,
            structural_summary=summary,
            llm_context=llm_context,
            raw_fen=fen,
            side_to_move=side_to_move
        )
    
    def _fen_to_board(self, fen: str) -> Tuple[List[List[str]], str]:
        parts = fen.split()
        board_str = parts[0]
        side = parts[1] if len(parts) > 1 else 'w'
        
        board = []
        for row_str in board_str.split('/'):
            row = []
            for c in row_str:
                if c.isdigit():
                    row.extend([''] * int(c))
                else:
                    row.append(c)
            board.append(row)
        
        return board, 'red' if side == 'w' else 'black'
    
    def _extract_pieces(self, board: List[List[str]]) -> List[PieceInfo]:
        pieces = []
        for row in range(10):
            for col in range(9):
                piece = board[row][col]
                if piece:
                    pieces.append(PieceInfo(
                        piece=piece,
                        row=row,
                        col=col,
                        is_red=piece.isupper(),
                        piece_type=piece.lower()
                    ))
        return pieces
    
    def _extract_relations(self, board: List[List[str]], pieces: List[PieceInfo]) -> List[Relation]:
        relations = []
        
        for piece in pieces:
            attacks = self._find_attacks(board, piece)
            for target_pos, target_piece in attacks:
                relations.append(Relation(
                    from_piece=piece.piece,
                    from_position=(piece.row, piece.col),
                    to_piece=target_piece,
                    to_position=target_pos,
                    relation_type=RelationType.ATTACKS,
                    description=f"{piece.to_chinese()}攻击{self._piece_chinese(target_piece)}"
                ))
        
        for piece in pieces:
            protections = self._find_protections(board, piece)
            for target_pos, target_piece in protections:
                relations.append(Relation(
                    from_piece=piece.piece,
                    from_position=(piece.row, piece.col),
                    to_piece=target_piece,
                    to_position=target_pos,
                    relation_type=RelationType.PROTECTS,
                    description=f"{piece.to_chinese()}保护{self._piece_chinese(target_piece)}"
                ))
        
        return relations
    
    def _find_attacks(self, board: List[List[str]], piece: PieceInfo) -> List[Tuple[Tuple[int, int], str]]:
        attacks = []
        piece_type = piece.piece_type.lower()
        is_red = piece.is_red
        
        if piece_type == 'r':
            attacks.extend(self._rook_attacks(board, piece.row, piece.col, is_red))
        elif piece_type == 'c':
            attacks.extend(self._cannon_attacks(board, piece.row, piece.col, is_red))
        elif piece_type == 'n':
            attacks.extend(self._knight_attacks(board, piece.row, piece.col, is_red))
        elif piece_type == 'p':
            attacks.extend(self._pawn_attacks(board, piece.row, piece.col, is_red))
        elif piece_type == 'k':
            attacks.extend(self._king_attacks(board, piece.row, piece.col, is_red))
        
        return attacks
    
    def _rook_attacks(self, board: List[List[str]], row: int, col: int, is_red: bool) -> List[Tuple[Tuple[int, int], str]]:
        attacks = []
        for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nr, nc = row + dr, col + dc
            while 0 <= nr < 10 and 0 <= nc < 9:
                target = board[nr][nc]
                if target:
                    if self._is_enemy(target, is_red):
                        attacks.append(((nr, nc), target))
                    break
                nr += dr
                nc += dc
        return attacks
    
    def _cannon_attacks(self, board: List[List[str]], row: int, col: int, is_red: bool) -> List[Tuple[Tuple[int, int], str]]:
        attacks = []
        for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nr, nc = row + dr, col + dc
            jumped = False
            while 0 <= nr < 10 and 0 <= nc < 9:
                target = board[nr][nc]
                if target:
                    if not jumped:
                        jumped = True
                    else:
                        if self._is_enemy(target, is_red):
                            attacks.append(((nr, nc), target))
                        break
                nr += dr
                nc += dc
        return attacks
    
    def _knight_attacks(self, board: List[List[str]], row: int, col: int, is_red: bool) -> List[Tuple[Tuple[int, int], str]]:
        attacks = []
        knight_moves = [
            (2, 1, 1, 0), (2, -1, 1, 0),
            (-2, 1, -1, 0), (-2, -1, -1, 0),
            (1, 2, 0, 1), (1, -2, 0, -1),
            (-1, 2, 0, 1), (-1, -2, 0, -1),
        ]
        for dr, dc, br, bc in knight_moves:
            nr, nc = row + dr, col + dc
            block_r, block_c = row + br, col + bc
            if 0 <= nr < 10 and 0 <= nc < 9:
                if 0 <= block_r < 10 and 0 <= block_c < 9 and not board[block_r][block_c]:
                    target = board[nr][nc]
                    if target and self._is_enemy(target, is_red):
                        attacks.append(((nr, nc), target))
        return attacks
    
    def _pawn_attacks(self, board: List[List[str]], row: int, col: int, is_red: bool) -> List[Tuple[Tuple[int, int], str]]:
        attacks = []
        if is_red:
            if row > 0:
                target = board[row - 1][col]
                if target and self._is_enemy(target, is_red):
                    attacks.append(((row - 1, col), target))
            if row <= 4:
                for dc in [-1, 1]:
                    nc = col + dc
                    if 0 <= nc < 9:
                        target = board[row][nc]
                        if target and self._is_enemy(target, is_red):
                            attacks.append(((row, nc), target))
        else:
            if row < 9:
                target = board[row + 1][col]
                if target and self._is_enemy(target, is_red):
                    attacks.append(((row + 1, col), target))
            if row >= 5:
                for dc in [-1, 1]:
                    nc = col + dc
                    if 0 <= nc < 9:
                        target = board[row][nc]
                        if target and self._is_enemy(target, is_red):
                            attacks.append(((row, nc), target))
        return attacks
    
    def _king_attacks(self, board: List[List[str]], row: int, col: int, is_red: bool) -> List[Tuple[Tuple[int, int], str]]:
        attacks = []
        for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nr, nc = row + dr, col + dc
            if self._is_in_palace(nr, nc, is_red):
                target = board[nr][nc]
                if target and self._is_enemy(target, is_red):
                    attacks.append(((nr, nc), target))
        return attacks
    
    def _find_protections(self, board: List[List[str]], piece: PieceInfo) -> List[Tuple[Tuple[int, int], str]]:
        protections = []
        piece_type = piece.piece_type.lower()
        is_red = piece.is_red
        
        if piece_type == 'r':
            protections.extend(self._rook_protections(board, piece.row, piece.col, is_red))
        elif piece_type == 'c':
            protections.extend(self._cannon_protections(board, piece.row, piece.col, is_red))
        elif piece_type == 'n':
            protections.extend(self._knight_protections(board, piece.row, piece.col, is_red))
        
        return protections
    
    def _rook_protections(self, board: List[List[str]], row: int, col: int, is_red: bool) -> List[Tuple[Tuple[int, int], str]]:
        protections = []
        for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nr, nc = row + dr, col + dc
            while 0 <= nr < 10 and 0 <= nc < 9:
                target = board[nr][nc]
                if target:
                    if self._is_friendly(target, is_red):
                        protections.append(((nr, nc), target))
                    break
                nr += dr
                nc += dc
        return protections
    
    def _cannon_protections(self, board: List[List[str]], row: int, col: int, is_red: bool) -> List[Tuple[Tuple[int, int], str]]:
        protections = []
        for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nr, nc = row + dr, col + dc
            jumped = False
            while 0 <= nr < 10 and 0 <= nc < 9:
                target = board[nr][nc]
                if target:
                    if not jumped:
                        jumped = True
                    else:
                        if self._is_friendly(target, is_red):
                            protections.append(((nr, nc), target))
                        break
                nr += dr
                nc += dc
        return protections
    
    def _knight_protections(self, board: List[List[str]], row: int, col: int, is_red: bool) -> List[Tuple[Tuple[int, int], str]]:
        protections = []
        knight_moves = [
            (2, 1, 1, 0), (2, -1, 1, 0),
            (-2, 1, -1, 0), (-2, -1, -1, 0),
            (1, 2, 0, 1), (1, -2, 0, -1),
            (-1, 2, 0, 1), (-1, -2, 0, -1),
        ]
        for dr, dc, br, bc in knight_moves:
            nr, nc = row + dr, col + dc
            block_r, block_c = row + br, col + bc
            if 0 <= nr < 10 and 0 <= nc < 9:
                if 0 <= block_r < 10 and 0 <= block_c < 9 and not board[block_r][block_c]:
                    target = board[nr][nc]
                    if target and self._is_friendly(target, is_red):
                        protections.append(((nr, nc), target))
        return protections
    
    def _extract_summary(self, board: List[List[str]], pieces: List[PieceInfo], 
                        relations: List[Relation], side_to_move: str) -> StructuralSummary:
        phase, phase_detail = self._determine_phase(pieces)
        
        initiative, initiative_detail = self._determine_initiative(pieces, relations)
        
        red_king_safety = self._assess_king_safety(board, pieces, relations, is_red=True)
        black_king_safety = self._assess_king_safety(board, pieces, relations, is_red=False)
        
        active_pieces = self._find_active_pieces(pieces, relations)
        restricted_pieces = self._find_restricted_pieces(pieces, relations)
        
        key_conflict_areas = self._find_conflict_areas(board, relations)
        
        return StructuralSummary(
            phase=phase,
            phase_detail=phase_detail,
            initiative=initiative,
            initiative_detail=initiative_detail,
            red_king_safety=red_king_safety,
            black_king_safety=black_king_safety,
            active_pieces=active_pieces,
            restricted_pieces=restricted_pieces,
            key_conflict_areas=key_conflict_areas
        )
    
    def _determine_phase(self, pieces: List[PieceInfo]) -> Tuple[str, str]:
        piece_count = len(pieces)
        heavy_pieces = sum(1 for p in pieces if p.piece_type in ['r', 'c', 'n'])
        
        if piece_count >= 26 and heavy_pieces >= 4:
            return "开局", f"子力{piece_count}枚，重子{heavy_pieces}个"
        elif piece_count <= 14:
            return "残局", f"子力{piece_count}枚，进入残局"
        else:
            return "中局", f"子力{piece_count}枚，中局阶段"
    
    def _determine_initiative(self, pieces: List[PieceInfo], relations: List[Relation]) -> Tuple[str, str]:
        red_attacks = sum(1 for r in relations if r.from_piece.isupper() and r.relation_type == RelationType.ATTACKS)
        black_attacks = sum(1 for r in relations if r.from_piece.islower() and r.relation_type == RelationType.ATTACKS)
        
        red_material = sum(self.PIECE_VALUES.get(p.piece, 0) for p in pieces if p.is_red)
        black_material = sum(self.PIECE_VALUES.get(p.piece, 0) for p in pieces if not p.is_red)
        
        score = (red_attacks - black_attacks) * 0.5 + (red_material - black_material)
        
        if score > 2:
            return "红方优势", f"红方攻击{red_attacks}次，子力{red_material}分"
        elif score < -2:
            return "黑方优势", f"黑方攻击{black_attacks}次，子力{black_material}分"
        else:
            return "均势", "双方势均力敌"
    
    def _assess_king_safety(self, board: List[List[str]], pieces: List[PieceInfo], 
                           relations: List[Relation], is_red: bool) -> str:
        king_char = 'K' if is_red else 'k'
        king = next((p for p in pieces if p.piece == king_char), None)
        
        if not king:
            return "将帅不在棋盘"
        
        attacks_on_king = sum(1 for r in relations 
                             if r.to_piece == king_char 
                             and r.relation_type == RelationType.ATTACKS)
        
        if attacks_on_king >= 2:
            return "危险"
        elif attacks_on_king >= 1:
            return "受威胁"
        else:
            in_palace = self._is_in_palace(king.row, king.col, is_red)
            return "安全" if in_palace else "暴露"
    
    def _find_active_pieces(self, pieces: List[PieceInfo], relations: List[Relation]) -> List[str]:
        active = set()
        for r in relations:
            if r.relation_type == RelationType.ATTACKS:
                active.add(self._piece_chinese(r.from_piece))
        return list(active)[:5]
    
    def _find_restricted_pieces(self, pieces: List[PieceInfo], relations: List[Relation]) -> List[str]:
        restricted = set()
        for r in relations:
            if r.relation_type == RelationType.ATTACKS:
                restricted.add(self._piece_chinese(r.to_piece))
        return list(restricted)[:5]
    
    def _find_conflict_areas(self, board: List[List[str]], relations: List[Relation]) -> List[str]:
        areas = set()
        for r in relations:
            if r.relation_type == RelationType.ATTACKS:
                col = r.to_position[1]
                if 3 <= col <= 5:
                    areas.add("中路")
                elif col <= 2:
                    areas.add("左翼")
                else:
                    areas.add("右翼")
        return list(areas)
    
    def _build_llm_context(self, pieces: List[PieceInfo], relations: List[Relation], 
                           summary: StructuralSummary) -> LLMContext:
        position_summary = self._build_position_summary(pieces, summary)
        
        key_relations = [r.to_chinese_description() for r in relations[:10]]
        
        tactical_themes = self._extract_tactical_themes(relations, summary)
        
        strategic_advice = self._generate_strategic_advice(summary)
        
        search_keywords = self._generate_search_keywords(summary, relations)
        
        return LLMContext(
            position_summary=position_summary,
            key_relations=key_relations,
            tactical_themes=tactical_themes,
            strategic_advice=strategic_advice,
            search_keywords=search_keywords
        )
    
    def _build_position_summary(self, pieces: List[PieceInfo], summary: StructuralSummary) -> str:
        red_pieces = [p for p in pieces if p.is_red]
        black_pieces = [p for p in pieces if not p.is_red]
        
        return f"当前处于{summary.phase}，{summary.initiative}。" \
               f"红方{len(red_pieces)}子，黑方{len(black_pieces)}子。" \
               f"红帅{summary.red_king_safety}，黑将{summary.black_king_safety}。"
    
    def _extract_tactical_themes(self, relations: List[Relation], summary: StructuralSummary) -> List[str]:
        themes = []
        
        attack_count = sum(1 for r in relations if r.relation_type == RelationType.ATTACKS)
        if attack_count >= 5:
            themes.append("战术活跃")
        
        if "危险" in summary.red_king_safety or "危险" in summary.black_king_safety:
            themes.append("攻防关键")
        
        if "中路" in summary.key_conflict_areas:
            themes.append("中路争夺")
        
        return themes if themes else ["局面平稳"]
    
    def _generate_strategic_advice(self, summary: StructuralSummary) -> str:
        if "危险" in summary.red_king_safety:
            return "红方需要优先防守将帅安全"
        elif "危险" in summary.black_king_safety:
            return "红方可以继续加强攻势"
        elif summary.initiative == "均势":
            return "双方应寻找局面突破点"
        else:
            return "优势方应稳步扩大优势"
    
    def _generate_search_keywords(self, summary: StructuralSummary, relations: List[Relation]) -> List[str]:
        keywords = []
        
        keywords.append(summary.phase)
        
        if summary.key_conflict_areas:
            keywords.extend(summary.key_conflict_areas)
        
        for theme in self._extract_tactical_themes(relations, summary):
            keywords.append(theme)
        
        return keywords[:5]
    
    def _is_in_palace(self, row: int, col: int, is_red: bool) -> bool:
        if is_red:
            return 7 <= row <= 9 and 3 <= col <= 5
        else:
            return 0 <= row <= 2 and 3 <= col <= 5
    
    def _is_enemy(self, piece: str, is_red: bool) -> bool:
        if not piece:
            return False
        return piece.islower() if is_red else piece.isupper()
    
    def _is_friendly(self, piece: str, is_red: bool) -> bool:
        if not piece:
            return False
        return piece.isupper() if is_red else piece.islower()
    
    def _piece_chinese(self, piece: str) -> str:
        chinese_names = {
            'K': '帅', 'k': '将',
            'A': '仕', 'a': '士',
            'B': '相', 'b': '象',
            'R': '车', 'r': '车',
            'C': '炮', 'c': '炮',
            'N': '马', 'n': '马',
            'P': '兵', 'p': '卒'
        }
        return chinese_names.get(piece, piece)


def parse_board_structure(fen: str) -> Dict:
    """
    便捷函数：解析局面结构
    
    Args:
        fen: FEN字符串
        
    Returns:
        结构化局面信息（字典格式）
    """
    parser = BoardStructureParser()
    result = parser.parse(fen)
    return result.to_dict()


if __name__ == "__main__":
    test_fens = [
        "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1",
        "2baka3/9/2R6/p8/4PP3/3p5/9/4r4/4A4/3AK4 b - - 40 40",
        "4k4/9/9/9/9/9/9/9/9/4K4 w - - 0 1",
    ]
    
    parser = BoardStructureParser()
    
    for i, fen in enumerate(test_fens, 1):
        print(f"\n{'='*70}")
        print(f"测试 {i}: {fen[:50]}...")
        print('='*70)
        
        result = parser.parse(fen)
        
        print(f"\n【棋子位置】共{len(result.pieces)}枚")
        for p in result.pieces[:5]:
            print(f"  {p.to_chinese()} @ {p.position_name()}")
        
        print(f"\n【棋子关系】共{len(result.relations)}条")
        for r in result.relations[:5]:
            print(f"  {r.to_chinese_description()}")
        
        print(f"\n【结构摘要】")
        print(f"  阶段: {result.structural_summary.phase}")
        print(f"  主动权: {result.structural_summary.initiative}")
        print(f"  红帅安全: {result.structural_summary.red_king_safety}")
        print(f"  黑将安全: {result.structural_summary.black_king_safety}")
        
        print(f"\n【LLM上下文】")
        print(f"  {result.llm_context.position_summary}")
        print(f"  搜索关键词: {result.llm_context.search_keywords}")
