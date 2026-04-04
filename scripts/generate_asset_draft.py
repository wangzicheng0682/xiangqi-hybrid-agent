"""
从后端 API 取真实证据，生成情景资产初稿。

用法：
    python scripts/generate_asset_draft.py \
        --fen "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1" \
        --scenario opening_center_cannon \
        --phase opening \
        --save
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests


PROJECT_ROOT = Path(__file__).resolve().parent.parent
ASSET_FILE = PROJECT_ROOT / "data" / "assets" / "scenario_examples.jsonl"


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    if not path.exists():
        return items
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


def save_jsonl(path: Path, items: List[Dict[str, Any]]) -> None:
    tmp = path.with_suffix(".jsonl.tmp")
    with open(tmp, "w", encoding="utf-8") as handle:
        for item in items:
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")
    tmp.replace(path)


def post_json(base_url: str, api_path: str, payload: Dict[str, Any], timeout: int = 30) -> Dict[str, Any]:
    response = requests.post(f"{base_url}{api_path}", json=payload, timeout=timeout)
    response.raise_for_status()
    return response.json()


def make_asset_id(existing: List[Dict[str, Any]], scenario: str) -> str:
    count = sum(1 for item in existing if item.get("scenario") == scenario)
    return f"scenario_{scenario}_{count + 1:03d}"


def summarize_position(board_structure: Dict[str, Any], phase: str) -> str:
    summary = board_structure.get("structural_summary", {})
    side_to_move = board_structure.get("side_to_move", "unknown")
    material = summary.get("material_balance") or summary.get("material_summary") or "子力格局待人工补写"
    initiative = summary.get("initiative") or summary.get("initiative_side") or "主动权待人工确认"
    return f"{phase}阶段，轮到{side_to_move}走。{material}。当前主动权判断：{initiative}。"


def summarize_contradiction(tags_resp: Dict[str, Any], engine_resp: Dict[str, Any]) -> str:
    tag_names = [tag.get("name", "") for tag in tags_resp.get("tags", [])][:3]
    bestmove = engine_resp.get("bestmove") or "待确认"
    score = engine_resp.get("score")
    tag_part = " / ".join(tag_names) if tag_names else "暂无显著战术标签"
    if score is None:
        return f"局面主矛盾待围绕 {tag_part} 展开；引擎主张进一步确认。"
    return f"局面主矛盾应围绕 {tag_part} 展开；引擎当前首选为 {bestmove}，评分 {score:+.2f}。"


def build_thinking_steps(
    board_structure: Dict[str, Any],
    tags_resp: Dict[str, Any],
    engine_resp: Dict[str, Any],
    position_analysis: Dict[str, Any],
) -> List[Dict[str, Any]]:
    retrieval_hints = position_analysis.get("analysis_text", {}).get("retrieval_hints", [])
    top_tags = [tag.get("name", "") for tag in tags_resp.get("tags", [])[:5]]
    engine_result = position_analysis.get("analysis_structured", {}).get("engine_result", {})
    pv = engine_result.get("pv", [])[:5]

    return [
        {
            "step": 1,
            "thought": "先读取后端返回的局面结构，确认阶段、轮次方与结构摘要。",
            "tool": "backend_api:/api/board-structure",
            "tool_input": {"fen": board_structure.get("raw_fen", "")},
            "tool_result_summary": summarize_position(board_structure, board_structure.get("llm_context", {}).get("phase", "unknown")),
            "conclusion": "初稿应先围绕真实结构信息展开，而不是先写口水话。",
        },
        {
            "step": 2,
            "thought": "读取规则标签，确认当前局面的战术/语义焦点。",
            "tool": "backend_api:/api/tactical-tags",
            "tool_input": {"fen": tags_resp.get("fen", "")},
            "tool_result_summary": f"命中标签: {', '.join(top_tags) if top_tags else '无'}",
            "conclusion": "初稿叙述重点必须和已检出的标签一致。",
        },
        {
            "step": 3,
            "thought": "读取引擎评估和主变，确认候选走法与分数。",
            "tool": "backend_api:/api/position-analysis",
            "tool_input": {"fen": position_analysis.get('analysis_structured', {}).get('board_fen', '')},
            "tool_result_summary": f"bestmove={engine_resp.get('bestmove', '')}, score={engine_resp.get('score', 0):+.2f}, pv={' '.join(pv) if pv else '无'}",
            "conclusion": f"检索提示: {'; '.join(retrieval_hints) if retrieval_hints else '无'}",
        },
    ]


def generate_draft(
    fen: str,
    scenario: str,
    phase: str,
    base_url: str,
    created_by: str = "ai_api_bootstrap",
) -> Dict[str, Any]:
    position_analysis = post_json(base_url, "/api/position-analysis", {"fen": fen})
    engine_resp = post_json(base_url, "/api/engine/evaluate", {"fen": fen, "depth": 15})
    tags_resp = post_json(base_url, "/api/tactical-tags", {"fen": fen})
    board_structure = post_json(base_url, "/api/board-structure", {"fen": fen})

    existing = load_jsonl(ASSET_FILE)
    asset_id = make_asset_id(existing, scenario)
    tags = [tag.get("name", "") for tag in tags_resp.get("tags", [])]
    bestmove = engine_resp.get("bestmove", "")
    phase_from_api = board_structure.get("llm_context", {}).get("phase") or phase

    draft = {
        "id": asset_id,
        "scenario": scenario,
        "fen": fen,
        "phase": phase_from_api,
        "move_count": 0,
        "situation_judgment": summarize_position(board_structure, phase_from_api),
        "primary_contradiction": summarize_contradiction(tags_resp, engine_resp),
        "thinking_steps": build_thinking_steps(board_structure, tags_resp, engine_resp, position_analysis),
        "teaching_narrative": "",
        "tags_expected": tags,
        "engine_best_move": bestmove,
        "engine_verified": True,
        "tags_verified": True,
        "grade": "draft",
        "created_by": created_by,
        "reviewed_by": None,
        "review_note": "初稿已预取后端真实证据，但教学讲解仍需人工审批。",
        "evidence_snapshot": {
            "engine": engine_resp,
            "tags": tags_resp,
            "board_structure": board_structure,
            "position_analysis": position_analysis,
        },
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    return draft


def main() -> None:
    parser = argparse.ArgumentParser(description="基于后端 API 生成情景资产初稿")
    parser.add_argument("--fen", required=True, help="局面 FEN")
    parser.add_argument("--scenario", required=True, help="情景名，例如 midgame_pin")
    parser.add_argument("--phase", default="middlegame", help="阶段 opening/middlegame/endgame")
    parser.add_argument("--api-base", default="http://127.0.0.1:8002", help="后端 API 基地址")
    parser.add_argument("--save", action="store_true", help="是否直接写入 scenario_examples.jsonl")
    args = parser.parse_args()

    draft = generate_draft(
        fen=args.fen,
        scenario=args.scenario,
        phase=args.phase,
        base_url=args.api_base.rstrip("/"),
    )

    if args.save:
        items = load_jsonl(ASSET_FILE)
        items.append(draft)
        save_jsonl(ASSET_FILE, items)
        print(f"已写入 {ASSET_FILE}")

    print(json.dumps(draft, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()