"""
象棋资产审批台 — Gradio 轻量工具

功能：
- 浏览 scenario_examples / eval_set / failure_cases
- 渲染 FEN 棋盘图
- 显示思维步骤、标签、引擎答案、教学讲解
- 编辑教学讲解文字
- 审批：通过(gold) / 存疑(silver) / 否决(rejected)→进入重写队列
- 新建/导入局面
- 自动写回 JSONL

启动：python apps/web-gradio/reviewer.py
"""

import json
import os
import sys
import socket
from pathlib import Path
from datetime import datetime

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.render.board_renderer import render_board
from scripts.generate_asset_draft import generate_draft

# ── 数据路径 ────────────────────────────────────────────────────────────────

ASSETS_DIR = PROJECT_ROOT / "data" / "assets"

ASSET_FILES = {
    "情景示范 (scenario)": ASSETS_DIR / "scenario_examples.jsonl",
    "评测题集 (eval)": ASSETS_DIR / "eval_set.jsonl",
    "失败案例 (failure)": ASSETS_DIR / "failure_cases.jsonl",
    "待重写队列 (rewrite)": ASSETS_DIR / "rewrite_queue.jsonl",
}


# ── JSONL 读写 ───────────────────────────────────────────────────────────────

def load_jsonl(path: Path) -> list:
    """读取 JSONL 文件，返回字典列表。"""
    items = []
    if not path.exists():
        return items
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


def save_jsonl(path: Path, items: list):
    """将字典列表写回 JSONL（原子覆盖）。"""
    tmp = path.with_suffix(".jsonl.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    tmp.replace(path)


# ── 渲染辅助 ─────────────────────────────────────────────────────────────────

def render_fen_image(fen: str):
    """将 FEN 渲染为 PIL Image。"""
    try:
        return render_board(fen, width=450, height=500)
    except Exception as e:
        from PIL import Image, ImageDraw
        img = Image.new("RGB", (450, 500), "#FFFFFF")
        draw = ImageDraw.Draw(img)
        draw.text((20, 20), f"渲染失败: {e}", fill="red")
        return img


def format_thinking_steps(item: dict) -> str:
    """将 thinking_steps 格式化为可读文本。"""
    steps = item.get("thinking_steps", [])
    if not steps:
        return "(无思维步骤)"
    lines = []
    for s in steps:
        lines.append(f"【第{s['step']}步】{s.get('thought', '')}")
        lines.append(f"  工具: {s.get('tool', '无')}")
        lines.append(f"  结果: {s.get('tool_result_summary', '')}")
        lines.append(f"  结论: {s.get('conclusion', '')}")
        lines.append("")
    return "\n".join(lines)


def format_item_info(item: dict) -> str:
    """格式化资产的元信息。"""
    parts = []
    parts.append(f"ID: {item.get('id', '?')}")
    parts.append(f"情景: {item.get('scenario', item.get('failure_type', '?'))}")
    parts.append(f"阶段: {item.get('phase', '?')}")
    parts.append(f"等级: {item.get('grade', 'draft')}")
    parts.append(f"创建: {item.get('created_by', '?')}")
    reviewed = item.get("reviewed_by")
    if reviewed:
        parts.append(f"审核: {reviewed}")
    review_note = item.get("review_note")
    if review_note:
        parts.append(f"审核备注: {review_note}")

    best_move = item.get("engine_best_move", item.get("engine_answer", {}).get("best_move"))
    if best_move:
        parts.append(f"引擎最佳: {best_move}")

    tags = item.get("tags_expected", item.get("tactical_tags", []))
    if tags:
        parts.append(f"预期标签: {', '.join(tags)}")

    engine_verified = item.get("engine_verified")
    tags_verified = item.get("tags_verified")
    if engine_verified is None and str(item.get("created_by", "")).startswith("ai"):
        engine_verified = False
    if tags_verified is None and str(item.get("created_by", "")).startswith("ai"):
        tags_verified = False

    if engine_verified is not None:
        parts.append(f"引擎数据: {'已验证' if engine_verified else 'AI草稿，待验证'}")
    if tags_verified is not None:
        parts.append(f"标签数据: {'已验证' if tags_verified else 'AI草稿，待验证'}")

    return "\n".join(parts)


def pick_launch_port(preferred_port: int = 7861, max_tries: int = 10) -> int:
    """从首选端口起寻找可用端口，避免旧进程占用导致审批台启动失败。"""
    for port in range(preferred_port, preferred_port + max_tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise OSError(f"从 {preferred_port} 开始连续 {max_tries} 个端口都被占用")


def format_contradiction(item: dict) -> str:
    """格式化主要矛盾和局面判断。"""
    parts = []
    sj = item.get("situation_judgment", "")
    if sj:
        parts.append(f"【局面判断】{sj}")
    pc = item.get("primary_contradiction", "")
    if pc:
        parts.append(f"【主要矛盾】{pc}")
    ft = item.get("failure_type", "")
    if ft:
        parts.append(f"【失败类型】{ft}")
    fd = item.get("failure_description", "")
    if fd:
        parts.append(f"【失败描述】{fd}")
    ca = item.get("correct_approach", "")
    if ca:
        parts.append(f"【正确做法】{ca}")
    return "\n".join(parts) if parts else "(无)"


def format_evidence_snapshot(item: dict) -> str:
    """格式化后端证据快照。"""
    evidence = item.get("evidence_snapshot") or {}
    if not evidence:
        return "(无后端证据快照)"

    engine = evidence.get("engine") or {}
    tags_resp = evidence.get("tags") or {}
    board_structure = evidence.get("board_structure") or {}
    position_analysis = evidence.get("position_analysis") or {}

    tag_names = [tag.get("name", "") for tag in tags_resp.get("tags", [])[:8]]
    summary = board_structure.get("structural_summary") or {}
    engine_result = position_analysis.get("analysis_structured", {}).get("engine_result", {})

    return "\n".join([
        f"引擎 bestmove: {engine.get('bestmove', '')}",
        f"引擎 score: {engine.get('score', 0):+.2f}",
        f"引擎 depth: {engine.get('depth', '')}",
        f"主变 PV: {' '.join(engine.get('pv', [])[:5]) if engine.get('pv') else '无'}",
        f"命中标签: {', '.join(tag_names) if tag_names else '无'}",
        f"轮到谁走: {board_structure.get('side_to_move', 'unknown')}",
        f"结构摘要: {summary if summary else '无'}",
        f"分析摘要: {engine_result if engine_result else '无'}",
    ])


def sync_rewrite_queue_status(original_id: str, target_id: str) -> None:
    """将对应原始条目的重写队列状态标记为已重写。"""
    rewrite_path = ASSET_FILES["待重写队列 (rewrite)"]
    rewrite_items = load_jsonl(rewrite_path)
    changed = False
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    for entry in rewrite_items:
        if entry.get("original_id") == original_id and entry.get("status") != "rewritten":
            entry["status"] = "rewritten"
            entry["rewritten_target_id"] = target_id
            entry["rewritten_at"] = now
            changed = True
    if changed:
        save_jsonl(rewrite_path, rewrite_items)


# ── 主界面构建 ────────────────────────────────────────────────────────────────

def build_app():
    import gradio as gr

    # 全局状态
    state = {
        "asset_type": "情景示范 (scenario)",
        "items": [],
        "index": 0,
    }

    def reload_items(asset_type):
        path = ASSET_FILES.get(asset_type)
        items = load_jsonl(path) if path else []
        state["asset_type"] = asset_type
        state["items"] = items
        state["index"] = 0
        if items:
            return show_item(0)
        return (
            None,  # board_image
            "该类别暂无数据",  # info
            "",  # contradiction
            "",  # thinking
            "",  # narrative (editable)
            "0 / 0",  # counter
            "",  # evidence
        )

    def show_item(idx):
        items = state["items"]
        if not items or idx < 0 or idx >= len(items):
            return (None, "无数据", "", "", "", "0 / 0", "")
        state["index"] = idx
        item = items[idx]
        fen = item.get("fen", "")
        img = render_fen_image(fen) if fen else None
        info = format_item_info(item)
        contradiction = format_contradiction(item)
        thinking = format_thinking_steps(item)
        evidence = format_evidence_snapshot(item)
        narrative = item.get(
            "teaching_narrative",
            item.get("system_output", item.get("reference_explanation", "")),
        )
        counter = f"{idx + 1} / {len(items)}"
        return img, info, contradiction, thinking, narrative, counter, evidence

    def go_prev():
        idx = max(0, state["index"] - 1)
        return show_item(idx)

    def go_next():
        idx = min(len(state["items"]) - 1, state["index"] + 1)
        return show_item(idx)

    def do_review(action, edited_narrative, note):
        items = state["items"]
        idx = state["index"]
        if not items or idx >= len(items):
            return "无数据可审批"

        item = items[idx]

        grade_map = {"✅ 通过 → gold": "gold", "⚠️ 存疑 → silver": "silver", "❌ 否决 → rejected": "rejected"}
        new_grade = grade_map.get(action, "draft")
        item["grade"] = new_grade
        item["reviewed_by"] = "human"
        item["review_date"] = datetime.now().strftime("%Y-%m-%d %H:%M")

        # 更新教学讲解（如编辑过）
        if "teaching_narrative" in item:
            item["teaching_narrative"] = edited_narrative
        elif "system_output" in item:
            item["system_output"] = edited_narrative
        elif "reference_explanation" in item:
            item["reference_explanation"] = edited_narrative

        if note and note.strip():
            item["review_note"] = note.strip()

        # 写回文件
        path = ASSET_FILES.get(state["asset_type"])
        save_jsonl(path, items)

        result_msg = f"已标记为 [{new_grade}]，已保存"

        # rejected → 写入重写队列 + failure_cases
        if new_grade == "rejected":
            rewrite_path = ASSET_FILES["待重写队列 (rewrite)"]
            rewrite_items = load_jsonl(rewrite_path)
            rewrite_entry = {
                "id": f"rewrite_{item.get('id', 'unknown')}",
                "original_id": item.get("id", "unknown"),
                "fen": item.get("fen", ""),
                "phase": item.get("phase", ""),
                "scenario": item.get("scenario", ""),
                "review_note": note.strip() if note else "人工审核否决",
                "original_narrative": edited_narrative,
                "status": "pending",
                "created_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            }
            rewrite_items.append(rewrite_entry)
            save_jsonl(rewrite_path, rewrite_items)

            if state["asset_type"] != "失败案例 (failure)":
                fail_path = ASSET_FILES["失败案例 (failure)"]
                failures = load_jsonl(fail_path)
                fail_entry = {
                    "id": f"fail_from_{item.get('id', 'unknown')}",
                    "fen": item.get("fen", ""),
                    "phase": item.get("phase", ""),
                    "scenario": item.get("scenario", ""),
                    "failure_type": "review_rejected",
                    "failure_description": note.strip() if note else "人工审核否决",
                    "grade": "gold",
                    "created_by": "human_review",
                    "date": datetime.now().strftime("%Y-%m-%d"),
                }
                failures.append(fail_entry)
                save_jsonl(fail_path, failures)

            result_msg += "\n→ 已加入重写队列，AI下次会重写此条"

        return result_msg

    # ── 新建局面 ──────────────────────────────────────────────────────────

    def preview_fen(fen_text):
        """预览 FEN 棋盘。"""
        fen_text = fen_text.strip()
        if not fen_text:
            return None, "请输入 FEN"
        try:
            img = render_fen_image(fen_text)
            position = fen_text.split()[0]
            ranks = position.split("/")
            if len(ranks) != 10:
                return img, f"⚠️ FEN 行数={len(ranks)}（应为10），请检查"
            return img, "✅ FEN 有效，棋盘已渲染"
        except Exception as e:
            return None, f"❌ 解析失败: {e}"

    def create_new_item(fen_text, phase, scenario, situation_judgment, primary_contradiction):
        """创建新的情景示范条目。"""
        fen_text = fen_text.strip()
        if not fen_text:
            return "❌ 请输入 FEN"
        scenario = scenario.strip()
        if not scenario:
            return "❌ 请输入情景名称"

        # 生成 ID
        existing = load_jsonl(ASSET_FILES["情景示范 (scenario)"])
        count = sum(1 for it in existing if it.get("scenario", "").startswith(scenario))
        new_id = f"scenario_{scenario}_{count + 1:03d}"

        new_item = {
            "id": new_id,
            "scenario": scenario,
            "fen": fen_text,
            "phase": phase,
            "move_count": 0,
            "situation_judgment": situation_judgment.strip() if situation_judgment else "",
            "primary_contradiction": primary_contradiction.strip() if primary_contradiction else "",
            "thinking_steps": [],
            "teaching_narrative": "",
            "tags_expected": [],
            "engine_best_move": "",
            "engine_verified": False,
            "tags_verified": False,
            "grade": "draft",
            "created_by": "human_import",
            "reviewed_by": None,
        }

        existing.append(new_item)
        save_jsonl(ASSET_FILES["情景示范 (scenario)"], existing)

        return f"✅ 已创建 [{new_id}]，共 {len(existing)} 条。\n切换到「情景示范」类别可看到新条目（在最后一条）。"

    def generate_api_draft(fen_text, phase, scenario, api_base):
        """调用后端 API 取真实证据并生成 scenario draft。"""
        fen_text = fen_text.strip()
        scenario = scenario.strip()
        api_base = api_base.strip() or "http://127.0.0.1:8002"

        if not fen_text:
            return "❌ 请输入 FEN", phase, "", "", "", "", None
        if not scenario:
            return "❌ 请输入情景名称", phase, "", "", "", "", None

        try:
            draft = generate_draft(
                fen=fen_text,
                scenario=scenario,
                phase=phase,
                base_url=api_base.rstrip("/"),
                created_by="copilot_api_bootstrap",
            )
        except Exception as exc:
            return f"❌ 后端取证据失败: {exc}", phase, "", "", "", "", None

        existing = load_jsonl(ASSET_FILES["情景示范 (scenario)"])
        existing.append(draft)
        save_jsonl(ASSET_FILES["情景示范 (scenario)"], existing)

        return (
            f"✅ 已根据后端证据生成并保存 [{draft['id']}]",
            draft.get("phase", phase),
            draft.get("situation_judgment", ""),
            draft.get("primary_contradiction", ""),
            ", ".join(draft.get("tags_expected", [])),
            draft.get("engine_best_move", ""),
            render_fen_image(fen_text),
        )

    def rewrite_current_from_api(api_base, edited_narrative, note):
        """对当前条目重取后端证据并重写。"""
        items = state["items"]
        idx = state["index"]
        if not items or idx >= len(items):
            return ("❌ 当前没有可重写条目",) + show_item(idx)

        item = items[idx]
        fen = (item.get("fen") or "").strip()
        scenario = (item.get("scenario") or item.get("failure_type") or "").strip()
        phase = (item.get("phase") or "middlegame").strip()
        api_base = (api_base or "http://127.0.0.1:8002").strip().rstrip("/")

        if not fen or not scenario:
            return ("❌ 当前条目缺少 FEN 或情景名，无法自动重写",) + show_item(idx)

        try:
            draft = generate_draft(
                fen=fen,
                scenario=scenario,
                phase=phase,
                base_url=api_base,
                created_by="copilot_api_rewrite",
            )
        except Exception as exc:
            return (f"❌ 后端取证据失败: {exc}",) + show_item(idx)

        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        if state["asset_type"] == "待重写队列 (rewrite)":
            scenario_items = load_jsonl(ASSET_FILES["情景示范 (scenario)"])
            target_id = item.get("original_id") or draft.get("id")
            draft["id"] = target_id
            draft["grade"] = "draft"
            draft["reviewed_by"] = None
            draft["teaching_narrative"] = edited_narrative or ""
            draft["rewrite_source_note"] = note.strip() if note and note.strip() else item.get("review_note", "")
            draft["rewrite_from_queue_id"] = item.get("id")
            draft["rewrite_date"] = now

            replaced = False
            for scenario_item in scenario_items:
                if scenario_item.get("id") == target_id:
                    scenario_item.update(draft)
                    replaced = True
                    break
            if not replaced:
                scenario_items.append(draft)
            save_jsonl(ASSET_FILES["情景示范 (scenario)"], scenario_items)

            item["status"] = "rewritten"
            item["rewritten_target_id"] = target_id
            item["rewritten_at"] = now
            save_jsonl(ASSET_FILES[state["asset_type"]], items)

            result = f"✅ 已从重写队列回填 [{target_id}] 到情景示范库，请切回 scenario 审批"
            return (result,) + show_item(idx)

        original_id = item.get("id")
        item["phase"] = draft.get("phase", phase)
        item["situation_judgment"] = draft.get("situation_judgment", "")
        item["primary_contradiction"] = draft.get("primary_contradiction", "")
        item["thinking_steps"] = draft.get("thinking_steps", [])
        item["tags_expected"] = draft.get("tags_expected", [])
        item["engine_best_move"] = draft.get("engine_best_move", "")
        item["engine_verified"] = True
        item["tags_verified"] = True
        item["evidence_snapshot"] = draft.get("evidence_snapshot", {})
        item["generated_at"] = draft.get("generated_at")
        item["created_by"] = "copilot_api_rewrite"
        item["grade"] = "draft"
        item["reviewed_by"] = None
        item["review_date"] = None
        item["teaching_narrative"] = edited_narrative or item.get("teaching_narrative", "")
        if note and note.strip():
            item["review_note"] = note.strip()
        item["rewrite_date"] = now

        path = ASSET_FILES.get(state["asset_type"])
        save_jsonl(path, items)
        sync_rewrite_queue_status(original_id, original_id)

        result = f"✅ 已基于后端证据重写当前条目 [{original_id}]，状态重置为 draft 待复审"
        return (result,) + show_item(idx)

    # ── 布局 ──────────────────────────────────────────────────────────────

    with gr.Blocks(title="象棋资产审批台") as app:
        gr.Markdown("# 🎯 象棋资产审批台")

        with gr.Tabs():
            # ──────── 审批 Tab ────────
            with gr.Tab("📋 审批"):
                gr.Markdown("浏览资产 → 看棋盘 + 思维步骤 → 编辑教学讲解 → 审批")
                gr.Markdown("**注意**：除非元信息里明确显示“已验证”，否则当前引擎着法、标签、思维步骤都按 AI 草稿处理，不算真值。")

                with gr.Row():
                    asset_type_dd = gr.Dropdown(
                        choices=list(ASSET_FILES.keys()),
                        value="情景示范 (scenario)",
                        label="资产类型",
                        interactive=True,
                    )
                    counter_text = gr.Textbox(label="当前", value="0 / 0", interactive=False, scale=0)

                with gr.Row():
                    prev_btn = gr.Button("← 上一条", size="sm")
                    next_btn = gr.Button("下一条 →", size="sm")

                with gr.Row():
                    with gr.Column(scale=1):
                        board_image = gr.Image(label="棋盘", type="pil", height=500)
                        info_box = gr.Textbox(label="元信息", lines=8, interactive=False)
                        evidence_box = gr.Textbox(label="后端证据摘要", lines=9, interactive=False)

                    with gr.Column(scale=2):
                        contradiction_box = gr.Textbox(label="局面判断 / 主要矛盾", lines=4, interactive=False)
                        thinking_box = gr.Textbox(label="思维步骤（推理节奏）", lines=10, interactive=False)
                        narrative_box = gr.Textbox(
                            label="📝 教学讲解（可编辑）",
                            lines=10,
                            interactive=True,
                            placeholder="在这里直接修改教学文字……",
                        )

                gr.Markdown("---")
                gr.Markdown("### 审批")

                with gr.Row():
                    review_note = gr.Textbox(
                        label="备注（可选，写几个字说明理由）",
                        placeholder="比如：'马的位置描述错了' 或 '这条讲得很好'",
                        lines=2,
                    )

                with gr.Row():
                    review_api_base = gr.Textbox(
                        label="重写使用的后端 API 地址",
                        value="http://127.0.0.1:8002",
                        lines=1,
                    )
                    rewrite_btn = gr.Button("♻️ 基于后端证据重写当前条目", variant="secondary")

                with gr.Row():
                    approve_btn = gr.Button("✅ 通过 → gold", variant="primary")
                    hold_btn = gr.Button("⚠️ 存疑 → silver", variant="secondary")
                    reject_btn = gr.Button("❌ 否决 → rejected", variant="stop")

                review_result = gr.Textbox(label="审批结果", interactive=False)

            # ──────── 新建局面 Tab ────────
            with gr.Tab("➕ 新建局面"):
                gr.Markdown("### 导入新局面到情景示范库")
                gr.Markdown("粘贴 FEN → 预览；或直接调用后端真实证据生成 draft")

                with gr.Row():
                    with gr.Column(scale=1):
                        fen_input = gr.Textbox(
                            label="FEN 字符串",
                            placeholder="例: rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1",
                            lines=2,
                        )
                        preview_btn = gr.Button("🔍 预览棋盘", variant="secondary")
                        preview_status = gr.Textbox(label="状态", interactive=False)
                        preview_img = gr.Image(label="预览", type="pil", height=450)
                        api_base_input = gr.Textbox(
                            label="后端 API 地址",
                            value="http://127.0.0.1:8002",
                            lines=1,
                        )

                    with gr.Column(scale=1):
                        phase_dd = gr.Dropdown(
                            choices=["opening", "middlegame", "endgame"],
                            value="middlegame",
                            label="阶段",
                        )
                        scenario_input = gr.Textbox(
                            label="情景名称（英文下划线）",
                            placeholder="例: midgame_fork / endgame_rook_pawn",
                        )
                        situation_input = gr.Textbox(
                            label="局面判断（可选，一句话描述）",
                            placeholder="例: 红方马炮联攻，黑方城门不稳",
                            lines=2,
                        )
                        contradiction_input = gr.Textbox(
                            label="主要矛盾（可选）",
                            placeholder="例: 红方进攻速度 vs 黑方防守弹性",
                            lines=2,
                        )
                        generated_tags = gr.Textbox(label="生成的标签", interactive=False)
                        generated_best_move = gr.Textbox(label="生成的引擎最佳着法", interactive=False)
                        generate_btn = gr.Button("⚡ 从后端证据生成 draft", variant="primary")
                        create_btn = gr.Button("✅ 创建条目", variant="primary")
                        create_result = gr.Textbox(label="创建结果", interactive=False)

        # ── 事件绑定 ──────────────────────────────────────────────────────

        outputs = [board_image, info_box, contradiction_box, thinking_box, narrative_box, counter_text, evidence_box]

        asset_type_dd.change(fn=reload_items, inputs=[asset_type_dd], outputs=outputs)
        prev_btn.click(fn=go_prev, outputs=outputs)
        next_btn.click(fn=go_next, outputs=outputs)

        approve_btn.click(
            fn=lambda n, note: do_review("✅ 通过 → gold", n, note),
            inputs=[narrative_box, review_note],
            outputs=[review_result],
        )
        hold_btn.click(
            fn=lambda n, note: do_review("⚠️ 存疑 → silver", n, note),
            inputs=[narrative_box, review_note],
            outputs=[review_result],
        )
        reject_btn.click(
            fn=lambda n, note: do_review("❌ 否决 → rejected", n, note),
            inputs=[narrative_box, review_note],
            outputs=[review_result],
        )
        rewrite_btn.click(
            fn=rewrite_current_from_api,
            inputs=[review_api_base, narrative_box, review_note],
            outputs=[review_result] + outputs,
        )

        # 新建局面事件
        preview_btn.click(
            fn=preview_fen,
            inputs=[fen_input],
            outputs=[preview_img, preview_status],
        )
        create_btn.click(
            fn=create_new_item,
            inputs=[fen_input, phase_dd, scenario_input, situation_input, contradiction_input],
            outputs=[create_result],
        )
        generate_btn.click(
            fn=generate_api_draft,
            inputs=[fen_input, phase_dd, scenario_input, api_base_input],
            outputs=[
                create_result,
                phase_dd,
                situation_input,
                contradiction_input,
                generated_tags,
                generated_best_move,
                preview_img,
            ],
        )

        # 启动时加载
        app.load(fn=lambda: reload_items("情景示范 (scenario)"), outputs=outputs)

    return app


# ── 入口 ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import gradio as _gr
    app = build_app()
    launch_port = pick_launch_port(int(os.getenv("GRADIO_SERVER_PORT", "7861")))
    print("=" * 50)
    print("象棋资产审批台启动中……")
    print(f"资产目录: {ASSETS_DIR}")
    print(f"启动端口: {launch_port}")
    print("=" * 50)
    app.launch(server_name="0.0.0.0", server_port=launch_port, share=False, theme=_gr.themes.Soft())
