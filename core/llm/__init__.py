"""LLM module for Xiangqi analysis"""

from .client import LLMClient, LLMConfig
from .xiangqi_coach import XiangqiCoachAgent, CoachConfig, create_coach_agent
from .thinking_templates import (
    GamePhase,
    PhaseInfo,
    PhaseDetector,
    OpeningAnalyzer,
    ThinkingTemplateBuilder,
    ThinkingTemplate,
    get_phase_aware_prompt,
    detect_phase,
    analyze_opening,
    get_opening_summary,
)
from .opening_knowledge import (
    OPENING_PRINCIPLES,
    OpeningCategory,
    OpeningSystem,
    OPENING_SYSTEMS,
    DEFENSE_AGAINST_CANNON,
    OPENING_PATTERNS,
    evaluate_opening_development,
    detect_opening_pattern,
    get_opening_advice,
)
from .fewshot_examples import (
    FewshotExample,
    ToolCall,
    FEWSHOT_EXAMPLES,
    OPENING_EXAMPLES,
    MIDDLEGAME_EXAMPLES,
    ENDGAME_EXAMPLES,
    get_fewshot_prompt,
    get_all_examples,
    get_example_by_id,
    get_examples_by_phase,
    format_example_for_display,
)
from .knowledge_retriever import (
    Principle,
    ChessKnowledgeBase,
    get_knowledge_base,
    query_principles_for_tension,
    get_principles_prompt,
)

__all__ = [
    # LLM Client
    "LLMClient",
    "LLMConfig",
    # Coach Agent
    "XiangqiCoachAgent",
    "CoachConfig",
    "create_coach_agent",
    # Thinking Templates
    "GamePhase",
    "PhaseInfo",
    "PhaseDetector",
    "OpeningAnalyzer",
    "ThinkingTemplateBuilder",
    "ThinkingTemplate",
    "get_phase_aware_prompt",
    "detect_phase",
    "analyze_opening",
    "get_opening_summary",
    # Opening Knowledge
    "OPENING_PRINCIPLES",
    "OpeningCategory",
    "OpeningSystem",
    "OPENING_SYSTEMS",
    "DEFENSE_AGAINST_CANNON",
    "OPENING_PATTERNS",
    "evaluate_opening_development",
    "detect_opening_pattern",
    "get_opening_advice",
    # Few-shot Examples
    "FewshotExample",
    "ToolCall",
    "FEWSHOT_EXAMPLES",
    "OPENING_EXAMPLES",
    "MIDDLEGAME_EXAMPLES",
    "ENDGAME_EXAMPLES",
    "get_fewshot_prompt",
    "get_all_examples",
    "get_example_by_id",
    "get_examples_by_phase",
    "format_example_for_display",
    # Knowledge Retriever
    "Principle",
    "ChessKnowledgeBase",
    "get_knowledge_base",
    "query_principles_for_tension",
    "get_principles_prompt",
]
