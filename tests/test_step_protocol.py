"""步骤协议解析测试。"""

import sys
from pathlib import Path


project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_parse_step_blocks_splits_marked_sections():
    from core.llm.experts.base_expert import parse_step_blocks

    content = """[STEP: 扫描将军威胁]
红方中炮正在压制中路。

[STEP: 检查牵制关系]
黑方左马被牵制，暂时动不了。"""

    steps = parse_step_blocks(content)

    assert len(steps) == 2
    assert steps[0]["title"] == "扫描将军威胁"
    assert "中炮" in steps[0]["content"]
    assert steps[1]["title"] == "检查牵制关系"
    assert "左马" in steps[1]["content"]


def test_parse_step_blocks_returns_empty_without_markers():
    from core.llm.experts.base_expert import parse_step_blocks

    steps = parse_step_blocks("先观察局面，再调用工具验证。")

    assert steps == []


def test_parse_step_blocks_detects_section_headers():
    """专家输出中的【xxx】也应被识别为步骤"""
    from core.llm.experts.base_expert import parse_step_blocks

    content = """【子力关系】
红方双车对黑方单车双马。

【战术威胁】
红车有沉底威胁。"""

    steps = parse_step_blocks(content)
    assert len(steps) == 2
    assert steps[0]["title"] == "子力关系"
    assert steps[1]["title"] == "战术威胁"
    assert "沉底" in steps[1]["content"]


def test_parse_step_blocks_keeps_empty_body_step():
    from core.llm.experts.base_expert import parse_step_blocks

    steps = parse_step_blocks("[STEP: 读取引擎分数]\n")

    assert len(steps) == 1
    assert steps[0] == {"title": "读取引擎分数", "content": ""}


def test_synthesis_step_stream_parser_emits_structured_events():
    from core.llm.multi_agent_orchestrator import SynthesisStepStreamParser

    events = []

    def on_event(event_type, payload):
        events.append((event_type, payload))

    parser = SynthesisStepStreamParser(on_event)
    parser.feed("[STEP: 识别三位专家的共识]\n红方先手主动权")
    parser.feed("更强。\n[STEP: 解决战术与引擎分歧]\n引擎分数")
    parser.feed("略优，但战术上黑方更危险。")
    parser.finalize()

    structured_events = [event[0] for event in events if event[0] != "orchestrator_subtitle"]
    subtitle_events = [event for event in events if event[0] == "orchestrator_subtitle"]

    assert structured_events == [
        "synthesis_step_start",
        "synthesis_step_content",
        "synthesis_step_end",
        "synthesis_step_start",
        "synthesis_step_content",
        "synthesis_step_end",
    ]
    assert subtitle_events[0][1]["message"] == "识别三位专家的共识"
    assert subtitle_events[1][1]["message"] == "解决战术与引擎分歧"
    assert events[1][1]["title"] == "识别三位专家的共识"
    assert events[2][1]["content"] == "红方先手主动权更强。\n"
    assert events[5][1]["step_index"] == 1
    assert "战术上黑方更危险" in events[6][1]["content"]
    assert events[7][1]["duration_ms"] >= 250
    assert parser.saw_marker is True


def test_synthesis_step_stream_parser_tracks_plain_text_without_markers():
    from core.llm.multi_agent_orchestrator import SynthesisStepStreamParser

    events = []
    parser = SynthesisStepStreamParser(lambda event_type, payload: events.append((event_type, payload)))

    parser.feed("直接输出综合结论，不带步骤标记。")
    parser.finalize()

    assert events == []
    assert parser.saw_marker is False


def test_synthesis_parser_detects_section_headers_as_implicit_steps():
    """【综合评估】等中文节标题应自动触发步骤事件"""
    from core.llm.multi_agent_orchestrator import SynthesisStepStreamParser

    events = []
    parser = SynthesisStepStreamParser(lambda t, p: events.append((t, p)))

    parser.feed("【综合评估】\n红方优势明显。\n")
    parser.feed("【教练建议】\n建议走马八进七。\n")
    parser.finalize()

    starts = [e for e in events if e[0] == "synthesis_step_start"]
    contents = [e for e in events if e[0] == "synthesis_step_content"]
    ends = [e for e in events if e[0] == "synthesis_step_end"]

    assert len(starts) == 2
    assert starts[0][1]["title"] == "综合评估"
    assert starts[1][1]["title"] == "教练建议"
    assert len(contents) >= 2
    assert len(ends) == 2
    assert parser.saw_marker is True


def test_synthesis_parser_mixed_step_and_section():
    """[STEP:] 与 【section】 混合场景"""
    from core.llm.multi_agent_orchestrator import SynthesisStepStreamParser

    events = []
    parser = SynthesisStepStreamParser(lambda t, p: events.append((t, p)))

    parser.feed("[STEP: 汇总共识]\n三位专家一致认为...\n")
    parser.feed("【教练建议】\n走兵三进一。\n")
    parser.finalize()

    starts = [e for e in events if e[0] == "synthesis_step_start"]
    assert len(starts) == 2
    assert starts[0][1]["title"] == "汇总共识"
    assert starts[1][1]["title"] == "教练建议"
    assert parser.saw_marker is True