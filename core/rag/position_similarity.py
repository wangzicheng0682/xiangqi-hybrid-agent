"""本地相似局面检索。

使用 data/training/position_data.jsonl 中已有的 FEN + semantic_tags 样本，
通过局面结构、子力配置与语义标签做混合相似度检索。

目标：
- 不依赖外部服务
- 首次懒加载，后续极快
- 可直接为 AgentTools / RAG 主链路提供“相似局面”证据
"""

from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


_PROJECT_ROOT = Path(__file__).parent.parent.parent
_DEFAULT_DATA_PATH = _PROJECT_ROOT / "data" / "training" / "position_data.jsonl"

_INDEX_LOCK = threading.Lock()
_RETRIEVER: Optional["LocalPositionRetriever"] = None


@dataclass
class SimilarPosition:
    fen: str
    similarity: float
    phase: str
    best_move: Optional[str]
    score: Optional[float]
    total_games: int
    tags: Dict[str, float]


@dataclass
class _IndexedPosition:
    fen: str
    phase: str
    best_move: Optional[str]
    score: Optional[float]
    total_games: int
    tags: Dict[str, float]
    piece_tokens: set[str]
    material: Dict[str, int]


def get_position_retriever() -> "LocalPositionRetriever":
    global _RETRIEVER
    if _RETRIEVER is not None:
        return _RETRIEVER

    with _INDEX_LOCK:
        if _RETRIEVER is None:
            _RETRIEVER = LocalPositionRetriever()
    return _RETRIEVER


class LocalPositionRetriever:
    """基于本地训练样本的快速相似局面检索器。"""

    def __init__(self, data_path: Optional[Path] = None, max_records: Optional[int] = None):
        self.data_path = data_path or _DEFAULT_DATA_PATH
        env_limit = os.getenv("XIANGQI_POSITION_INDEX_LIMIT")
        self.max_records = max_records or int(env_limit or "40000")
        self._loaded = False
        self._by_phase: Dict[str, List[_IndexedPosition]] = {
            "opening": [],
            "middlegame": [],
            "endgame": [],
            "unknown": [],
        }

    def retrieve(
        self,
        fen: str,
        semantic_tags: Optional[Dict[str, float]] = None,
        top_k: int = 3,
    ) -> List[SimilarPosition]:
        self._ensure_loaded()
        if not fen:
            return []

        query_phase = self._detect_phase(semantic_tags or {})
        query_tokens = self._extract_piece_tokens(fen)
        query_material = self._extract_material(fen)
        candidates = list(self._by_phase.get(query_phase, []))

        if len(candidates) < top_k * 4:
            for phase_name, bucket in self._by_phase.items():
                if phase_name == query_phase:
                    continue
                candidates.extend(bucket)

        ranked: List[Tuple[float, _IndexedPosition]] = []
        for candidate in candidates:
            if candidate.fen == fen:
                continue
            score = self._score_candidate(
                query_tokens=query_tokens,
                query_material=query_material,
                query_tags=semantic_tags or {},
                query_phase=query_phase,
                candidate=candidate,
            )
            if score <= 0:
                continue
            ranked.append((score, candidate))

        ranked.sort(key=lambda item: item[0], reverse=True)
        return [
            SimilarPosition(
                fen=item.fen,
                similarity=round(score, 3),
                phase=item.phase,
                best_move=item.best_move,
                score=item.score,
                total_games=item.total_games,
                tags=item.tags,
            )
            for score, item in ranked[:top_k]
        ]

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return

        with _INDEX_LOCK:
            if self._loaded:
                return

            if not self.data_path.exists():
                self._loaded = True
                return

            seen_fens = set()
            with self.data_path.open("r", encoding="utf-8") as handle:
                for line_index, raw_line in enumerate(handle):
                    if line_index >= self.max_records:
                        break
                    raw_line = raw_line.strip()
                    if not raw_line:
                        continue
                    try:
                        item = json.loads(raw_line)
                    except json.JSONDecodeError:
                        continue

                    fen = item.get("fen")
                    if not fen or fen in seen_fens:
                        continue
                    seen_fens.add(fen)

                    tags = item.get("semantic_tags") or {}
                    phase = self._detect_phase(tags)
                    indexed = _IndexedPosition(
                        fen=fen,
                        phase=phase,
                        best_move=item.get("best_move"),
                        score=item.get("score"),
                        total_games=int(item.get("total_games") or 0),
                        tags=tags,
                        piece_tokens=self._extract_piece_tokens(fen),
                        material=self._extract_material(fen),
                    )
                    self._by_phase.setdefault(phase, []).append(indexed)

            self._loaded = True

    def _score_candidate(
        self,
        query_tokens: set[str],
        query_material: Dict[str, int],
        query_tags: Dict[str, float],
        query_phase: str,
        candidate: _IndexedPosition,
    ) -> float:
        board_score = self._jaccard(query_tokens, candidate.piece_tokens)
        material_score = self._material_similarity(query_material, candidate.material)
        semantic_score = self._semantic_similarity(query_tags, candidate.tags)
        phase_bonus = 0.08 if query_phase == candidate.phase else 0.0
        popularity_bonus = min(candidate.total_games, 50) / 1000.0
        return 0.58 * board_score + 0.22 * material_score + 0.15 * semantic_score + phase_bonus + popularity_bonus

    def _detect_phase(self, semantic_tags: Dict[str, float]) -> str:
        phase_scores = {
            "opening": float(semantic_tags.get("opening", 0.0)),
            "middlegame": float(semantic_tags.get("middlegame", 0.0)),
            "endgame": float(semantic_tags.get("endgame", 0.0)),
        }
        phase, score = max(phase_scores.items(), key=lambda item: item[1])
        return phase if score > 0 else "unknown"

    def _extract_piece_tokens(self, fen: str) -> set[str]:
        board = fen.split()[0] if " " in fen else fen
        tokens: set[str] = set()
        for row_index, row in enumerate(board.split("/")):
            col_index = 0
            for char in row:
                if char.isdigit():
                    col_index += int(char)
                    continue
                tokens.add(f"{char}@{row_index},{col_index}")
                col_index += 1
        return tokens

    def _extract_material(self, fen: str) -> Dict[str, int]:
        board = fen.split()[0] if " " in fen else fen
        counts: Dict[str, int] = {}
        for char in board:
            if char.isalpha():
                key = char.lower()
                counts[key] = counts.get(key, 0) + 1
        return counts

    def _jaccard(self, left: set[str], right: set[str]) -> float:
        if not left and not right:
            return 1.0
        union = left | right
        if not union:
            return 0.0
        return len(left & right) / len(union)

    def _material_similarity(self, left: Dict[str, int], right: Dict[str, int]) -> float:
        all_keys = set(left) | set(right)
        if not all_keys:
            return 1.0
        total = sum(max(left.get(key, 0), right.get(key, 0)) for key in all_keys)
        if total == 0:
            return 1.0
        diff = sum(abs(left.get(key, 0) - right.get(key, 0)) for key in all_keys)
        return max(0.0, 1.0 - diff / total)

    def _semantic_similarity(self, left: Dict[str, float], right: Dict[str, float]) -> float:
        if not left or not right:
            return 0.0
        keys = set(left) | set(right)
        if not keys:
            return 0.0
        numerator = 0.0
        denominator = 0.0
        for key in keys:
            l_val = float(left.get(key, 0.0))
            r_val = float(right.get(key, 0.0))
            numerator += min(l_val, r_val)
            denominator += max(l_val, r_val)
        if denominator == 0:
            return 0.0
        return numerator / denominator


__all__ = ["SimilarPosition", "LocalPositionRetriever", "get_position_retriever"]