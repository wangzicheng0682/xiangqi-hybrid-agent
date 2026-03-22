"""
FEN Validator for Chinese Chess (Xiangqi).

Reference:
  - PRD: Sprint 1 / FEN解析
  - TECH: FEN解析与棋盘生成
"""

import re
from typing import Tuple


def validate_fen(fen: str) -> Tuple[bool, str]:
    """
    Validate a Xiangqi FEN string.

    Xiangqi FEN format: [position] [turn] [halfmoves] [fullmoves]
    Example: "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"

    Args:
        fen: FEN string to validate

    Returns:
        (is_valid, error_message)
    """
    if not fen or not fen.strip():
        return False, "FEN string is empty"

    parts = fen.strip().split()

    # Must have at least position and turn
    if len(parts) < 2:
        return False, "FEN must have at least position and turn fields"

    position, turn = parts[0], parts[1]

    # Validate turn
    if turn not in ['w', 'b']:
        return False, f"Invalid turn '{turn}', must be 'w' or 'b'"

    # Validate position
    ranks = position.split('/')
    if len(ranks) != 10:
        return False, f"Position must have 10 ranks, found {len(ranks)}"

    # Valid piece characters (including A for Advisor)
    valid_pieces = set('rnbakabcpRNBAKBCP')

    for rank_idx, rank in enumerate(ranks):
        # Check each rank
        file_count = 0
        i = 0
        while i < len(rank):
            char = rank[i]
            if char.isdigit():
                # Number indicates empty squares
                num = int(char)
                if num < 1 or num > 9:
                    return False, f"Invalid digit '{num}' in rank {rank_idx+1}"
                file_count += num
            elif char in valid_pieces:
                file_count += 1
            else:
                return False, f"Invalid character '{char}' in rank {rank_idx+1}"
            i += 1

        # Each rank must have exactly 9 files
        if file_count != 9:
            return False, f"Rank {rank_idx+1} must have 9 files, found {file_count}"

    return True, "Valid FEN"


def is_legal_fen(fen: str) -> bool:
    """
    Quick check if FEN is legal (syntactically valid).

    Args:
        fen: FEN string

    Returns:
        True if legal, False otherwise
    """
    is_valid, _ = validate_fen(fen)
    return is_valid
