"""开局识别模块"""
from .opening_book import (
    OpeningInfo,
    identify_opening,
    get_opening_evaluation,
    get_opening_name,
    identify_position_type,
    OPENING_BOOK,
)

__all__ = [
    "OpeningInfo",
    "identify_opening",
    "get_opening_evaluation",
    "get_opening_name",
    "identify_position_type",
    "OPENING_BOOK",
]
