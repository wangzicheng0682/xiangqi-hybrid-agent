"""多专家分析的门控式调度策略。"""

import os
from typing import Dict, List

from core.llm.contracts import AnalysisPolicyDecision, DegradationLevel


TACTICAL_KEYWORDS = ("杀", "将军", "捉", "战术", "弃子", "应着", "对手")
ENGINE_KEYWORDS = ("引擎", "评分", "分数", "候选", "最佳着", "cp")
STRATEGIC_KEYWORDS = ("战略", "计划", "局面", "为什么", "整体", "思路")


def choose_analysis_policy(
    question: str,
    tensions: List[Dict],
    phase_name: str,
    engine_eval: Dict = None,
    force_full_team: bool = False,
) -> AnalysisPolicyDecision:
    """根据问题类型、张力数量和预算选择专家与并发度。"""
    text = question or ""
    tension_count = len(tensions or [])
    env_parallel = max(1, int(os.getenv("LLM_MAX_PARALLEL_REQUESTS", "2")))

    if force_full_team:
        selected = ["tactics", "strategy", "engine"]
        reason = "force_full_team"
    elif any(keyword in text for keyword in ENGINE_KEYWORDS):
        selected = ["engine", "strategy"]
        reason = "engine_focused_question"
    elif any(keyword in text for keyword in TACTICAL_KEYWORDS):
        selected = ["tactics", "engine"]
        reason = "tactical_question"
    elif phase_name == "开局":
        selected = ["strategy", "engine"]
        reason = "opening_phase_prefers_plan_and_eval"
    elif tension_count >= 3 or any(keyword in text for keyword in STRATEGIC_KEYWORDS):
        selected = ["tactics", "strategy", "engine"]
        reason = "high_complexity_or_strategic_question"
    else:
        selected = ["tactics", "strategy"]
        reason = "default_two_experts"

    if engine_eval and engine_eval.get("best") and "engine" not in selected:
        selected.append("engine")
        reason += "+engine_eval_present"

    parallelism = min(len(selected), env_parallel)
    degradation_level = DegradationLevel.NONE if parallelism == len(selected) else DegradationLevel.SERIALIZED

    return AnalysisPolicyDecision(
        mode="multi" if len(selected) > 1 else "single",
        selected_experts=selected,
        parallelism=parallelism,
        reason=reason,
        degradation_level=degradation_level,
    )
