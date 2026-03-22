"""
GameState: Core data structure for Xiangqi position.

Reference:
  - PRD: Sprint 1 / System Architecture
  - TECH: Gradio/Web形态 / Tool-first原则
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class GameState:
    """
    Minimal game state for Sprint 1 MVP.

    Fields:
        fen: Current position in FEN notation
        bestmove: Best move from engine (e.g., "炮二平五")
        eval: Position evaluation (e.g., "+0.5" or "红方优势")
        citations: List of knowledge citations (from KG/Books)
    """
    fen: str
    bestmove: Optional[str] = None
    eval: Optional[str] = None
    citations: List[str] = field(default_factory=list)

    def is_valid(self) -> bool:
        """Check if state has minimum required fields."""
        return bool(self.fen and self.fen.strip())
