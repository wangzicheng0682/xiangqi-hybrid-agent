"""候选走法服务：为 LLM 提供受约束的合法走法候选集。"""

from dataclasses import dataclass
from typing import Dict, List, Optional

from core.rules.rule_engine import RuleEngine


@dataclass
class MoveCandidate:
    candidate_id: str
    move: str
    from_square: str
    to_square: str
    iccs: str
    display: str


class MoveCandidateService:
    """基于合法走法生成稳定候选编号。"""

    def __init__(self):
        self._cache: Dict[str, List[MoveCandidate]] = {}

    def get_candidates(self, fen: str, limit: int = 12) -> List[MoveCandidate]:
        cache_key = f"{fen}::{limit}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        result = RuleEngine.get_legal_moves(fen)
        ordered_moves = sorted(result.moves, key=lambda m: (m.from_square, m.to_square, m.uci))
        candidates: List[MoveCandidate] = []
        for index, move in enumerate(ordered_moves[:limit], start=1):
            candidates.append(MoveCandidate(
                candidate_id=f"cand_{index}",
                move=move.uci,
                from_square=move.from_square,
                to_square=move.to_square,
                iccs=move.iccs,
                display=f"{move.uci} ({move.iccs})",
            ))

        self._cache[cache_key] = candidates
        return candidates

    def resolve_move(
        self,
        fen: str,
        move: Optional[str] = None,
        candidate_id: Optional[str] = None,
        limit: int = 12,
    ) -> Optional[str]:
        if candidate_id:
            for candidate in self.get_candidates(fen, limit=limit):
                if candidate.candidate_id == candidate_id:
                    return candidate.move
            return None

        if move:
            move = move.strip()
            if RuleEngine.is_legal_move(fen, move):
                return move
        return None
