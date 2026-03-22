"""
战术标签检测器测试

测试六大层级标签检测功能
"""

import sys
sys.path.insert(0, 'd:/xiangqi-hybrid-agent')

from core.rules import (
    TacticalDetector,
    DetectionMode,
    generate_evidence_map,
    TAG_IS_CHECK,
    TAG_IS_CHECKMATE,
)


def test_initial_position():
    """测试初始局面"""
    print("=" * 60)
    print("测试1: 初始局面")
    print("=" * 60)
    
    fen = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"
    
    detector = TacticalDetector()
    result = detector.detect_static(fen)
    
    print(f"FEN: {fen}")
    print(f"检测到的标签数: {len(result.get_detected_tags())}")
    
    for tag_result in result.get_detected_tags():
        print(f"  - {tag_result.tag.name}: {tag_result.bind_pieces}")
    
    print()


def test_check_position():
    """测试将军局面"""
    print("=" * 60)
    print("测试2: 将军局面")
    print("=" * 60)
    
    # 红车将军黑将
    fen = "4k4/9/9/9/9/9/9/9/4R4/4K4 w - - 0 1"
    
    detector = TacticalDetector()
    result = detector.detect_static(fen)
    
    print(f"FEN: {fen}")
    print(f"检测到的标签数: {len(result.get_detected_tags())}")
    
    for tag_result in result.get_detected_tags():
        print(f"  - {tag_result.tag.name}: {tag_result.bind_pieces}")
    
    print()


def test_checkmate_position():
    """测试将死局面"""
    print("=" * 60)
    print("测试3: 将死局面")
    print("=" * 60)
    
    # 红车将死黑将
    fen = "3k5/4R4/9/9/9/9/9/9/9/4K4 w - - 0 1"
    
    detector = TacticalDetector()
    result = detector.detect_static(fen)
    
    print(f"FEN: {fen}")
    print(f"检测到的标签数: {len(result.get_detected_tags())}")
    
    for tag_result in result.get_detected_tags():
        print(f"  - {tag_result.tag.name}: {tag_result.bind_pieces}")
    
    print()


def test_evidence_map():
    """测试Evidence Map生成"""
    print("=" * 60)
    print("测试4: Evidence Map生成")
    print("=" * 60)
    
    fen = "4k4/9/9/9/9/9/9/9/4R4/4K4 w - - 0 1"
    
    evidence_map = generate_evidence_map(fen, include_dynamic=False)
    
    print(f"FEN: {fen}")
    print(f"Evidence Map:")
    
    import json
    print(json.dumps(evidence_map, ensure_ascii=False, indent=2))
    
    print()


def test_full_detection():
    """测试完整检测（静态+动态）"""
    print("=" * 60)
    print("测试5: 完整检测")
    print("=" * 60)
    
    # 闪将局面
    fen = "4k4/9/9/9/9/9/9/4N4/4C4/4K4 w - - 0 1"
    
    detector = TacticalDetector()
    result = detector.detect_full(fen)
    
    print(f"FEN: {fen}")
    print(f"静态检测标签数: {len(result.static_result.get_detected_tags())}")
    print(f"动态检测走法数: {len(result.dynamic_results)}")
    
    for tag_result in result.static_result.get_detected_tags():
        print(f"  [静态] {tag_result.tag.name}: {tag_result.bind_pieces}")
    
    for move, dyn_result in result.dynamic_results.items():
        for tag_result in dyn_result.get_detected_tags():
            print(f"  [动态:{move}] {tag_result.tag.name}: {tag_result.bind_pieces}")
    
    print()


def test_phase_detection():
    """测试局面阶段检测"""
    print("=" * 60)
    print("测试6: 局面阶段检测")
    print("=" * 60)
    
    detector = TacticalDetector()
    
    fen_opening = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"
    result = detector.detect_static(fen_opening)
    phase_tags = [t for t in result.get_detected_tags() if t.tag.name.startswith("phase_")]
    print(f"初始局面(32子): {[t.tag.name for t in phase_tags]}")
    assert any(t.tag.name == "phase_opening" for t in phase_tags), "应检测为开局阶段"
    
    fen_middlegame = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/9/9/9/RNBAKABNR w - - 0 1"
    result = detector.detect_static(fen_middlegame)
    phase_tags = [t for t in result.get_detected_tags() if t.tag.name.startswith("phase_")]
    print(f"中局局面(22子): {[t.tag.name for t in phase_tags]}")
    
    fen_endgame = "4k4/9/9/9/9/9/9/9/9/4K4 w - - 0 1"
    result = detector.detect_static(fen_endgame)
    phase_tags = [t for t in result.get_detected_tags() if t.tag.name.startswith("phase_")]
    print(f"残局局面(2子): {[t.tag.name for t in phase_tags]}")
    assert any(t.tag.name == "phase_endgame" for t in phase_tags), "应检测为残局阶段"
    
    print()


def test_horse_leg_blocked():
    """测试马脚被别检测"""
    print("=" * 60)
    print("测试7: 马脚被别检测")
    print("=" * 60)
    
    detector = TacticalDetector()
    
    fen = "4k4/9/9/9/9/9/9/3N5/4P4/4K4 w - - 0 1"
    result = detector.detect_static(fen)
    
    blocked_tags = [t for t in result.get_detected_tags() if t.tag.name == "horse_leg_blocked"]
    print(f"马脚被别检测数: {len(blocked_tags)}")
    for t in blocked_tags:
        print(f"  - {t.bind_pieces}, metadata: {t.metadata}")
    
    print()


def test_kings_face_to_face():
    """测试双将对面检测"""
    print("=" * 60)
    print("测试8: 双将对面检测")
    print("=" * 60)
    
    detector = TacticalDetector()
    
    fen = "4k4/9/9/9/9/9/9/9/9/4K4 w - - 0 1"
    result = detector.detect_static(fen)
    
    face_tags = [t for t in result.get_detected_tags() if t.tag.name == "kings_face_to_face"]
    print(f"双将对面检测数: {len(face_tags)}")
    for t in face_tags:
        print(f"  - {t.bind_pieces}, metadata: {t.metadata}")
    
    print()


def test_cannon_battery():
    """测试重炮阵型检测"""
    print("=" * 60)
    print("测试9: 重炮阵型检测")
    print("=" * 60)
    
    detector = TacticalDetector()
    
    fen = "4k4/9/9/9/9/9/9/9/4CC3/4K4 w - - 0 1"
    result = detector.detect_static(fen)
    
    battery_tags = [t for t in result.get_detected_tags() if t.tag.name == "cannon_battery"]
    print(f"重炮阵型检测数: {len(battery_tags)}")
    for t in battery_tags:
        print(f"  - {t.bind_pieces}, metadata: {t.metadata}")
    
    print()


def test_favorable_exchange():
    """测试有利兑换检测"""
    print("=" * 60)
    print("测试10: 有利兑换检测")
    print("=" * 60)
    
    detector = TacticalDetector()
    
    fen = "4k4/9/9/9/9/9/9/9/4p1R2/4K4 w - - 0 1"
    result = detector.detect_static(fen)
    
    exchange_tags = [t for t in result.get_detected_tags() if t.tag.name == "favorable_exchange"]
    print(f"有利兑换检测数: {len(exchange_tags)}")
    for t in exchange_tags:
        print(f"  - {t.bind_pieces}, metadata: {t.metadata}")
    
    print()


def test_king_safety_critical():
    """测试将帅危急检测"""
    print("=" * 60)
    print("测试11: 将帅危急检测")
    print("=" * 60)
    
    detector = TacticalDetector()
    
    fen = "4k4/9/9/9/9/9/4R4/9/9/4K4 w - - 0 1"
    result = detector.detect_static(fen)
    
    safety_tags = [t for t in result.get_detected_tags() if t.tag.name == "king_safety_critical"]
    print(f"将帅危急检测数: {len(safety_tags)}")
    for t in safety_tags:
        print(f"  - {t.bind_pieces}, metadata: {t.metadata}")
    
    print()


def test_initiative():
    """测试主动权检测"""
    print("=" * 60)
    print("测试12: 主动权检测")
    print("=" * 60)
    
    detector = TacticalDetector()
    
    fen = "4k4/9/9/9/9/9/4R4/9/9/4K4 w - - 0 1"
    result = detector.detect_static(fen)
    
    initiative_tags = [t for t in result.get_detected_tags() if t.tag.name == "has_initiative"]
    print(f"主动权检测数: {len(initiative_tags)}")
    for t in initiative_tags:
        print(f"  - metadata: {t.metadata}")
    
    print()


def test_forcing_move():
    """测试强制手段检测（动态）"""
    print("=" * 60)
    print("测试13: 强制手段检测")
    print("=" * 60)
    
    detector = TacticalDetector()
    
    fen = "4k4/9/9/9/9/9/9/9/4R4/4K4 w - - 0 1"
    result = detector.detect_dynamic(fen, "e2e1")
    
    forcing_tags = [t for t in result.get_detected_tags() if t.tag.name == "is_forcing_move"]
    print(f"强制手段检测数: {len(forcing_tags)}")
    for t in forcing_tags:
        print(f"  - {t.bind_pieces}, metadata: {t.metadata}")
    
    print()


def test_checkmate_horse_corner():
    """测试卧槽马杀法检测"""
    print("=" * 60)
    print("测试14: 卧槽马杀法检测")
    print("=" * 60)
    
    detector = TacticalDetector()
    
    fen = "3k5/9/9/9/9/9/9/3N5/9/4K4 w - - 0 1"
    result = detector.detect_static(fen)
    
    horse_corner_tags = [t for t in result.get_detected_tags() if t.tag.name == "checkmate_horse_corner"]
    print(f"卧槽马检测数: {len(horse_corner_tags)}")
    for t in horse_corner_tags:
        print(f"  - {t.bind_pieces}")
    
    print()


def test_checkmate_bare_king():
    """测试白脸将杀法检测"""
    print("=" * 60)
    print("测试15: 白脸将杀法检测")
    print("=" * 60)
    
    detector = TacticalDetector()
    
    fen = "4k4/9/9/9/9/9/9/9/9/3RK4 w - - 0 1"
    result = detector.detect_static(fen)
    
    bare_king_tags = [t for t in result.get_detected_tags() if t.tag.name == "checkmate_bare_king"]
    print(f"白脸将检测数: {len(bare_king_tags)}")
    for t in bare_king_tags:
        print(f"  - {t.bind_pieces}")
    
    print()


def test_checkmate_double_cannon_battery():
    """测试重炮杀法检测"""
    print("=" * 60)
    print("测试16: 重炮杀法检测")
    print("=" * 60)
    
    detector = TacticalDetector()
    
    fen = "3k5/9/9/9/9/9/9/9/4CC3/4K4 w - - 0 1"
    result = detector.detect_static(fen)
    
    battery_tags = [t for t in result.get_detected_tags() if t.tag.name == "checkmate_double_cannon_battery"]
    print(f"重炮杀检测数: {len(battery_tags)}")
    for t in battery_tags:
        print(f"  - {t.bind_pieces}")
    
    print()


def test_checkmate_sea_bottom_moon():
    """测试海底捞月杀法检测"""
    print("=" * 60)
    print("测试17: 海底捞月杀法检测")
    print("=" * 60)
    
    detector = TacticalDetector()
    
    fen = "3kR4/9/9/9/9/9/9/9/9/4K4 w - - 0 1"
    result = detector.detect_static(fen)
    
    sea_bottom_tags = [t for t in result.get_detected_tags() if t.tag.name == "checkmate_sea_bottom_moon"]
    print(f"海底捞月检测数: {len(sea_bottom_tags)}")
    for t in sea_bottom_tags:
        print(f"  - {t.bind_pieces}")
    
    print()


def test_checkmate_side_tiger():
    """测试侧面虎杀法检测"""
    print("=" * 60)
    print("测试18: 侧面虎杀法检测")
    print("=" * 60)
    
    detector = TacticalDetector()
    
    fen = "3k5/3R5/9/9/9/9/9/9/9/4K4 w - - 0 1"
    result = detector.detect_static(fen)
    
    side_tiger_tags = [t for t in result.get_detected_tags() if t.tag.name == "checkmate_side_tiger"]
    print(f"侧面虎检测数: {len(side_tiger_tags)}")
    for t in side_tiger_tags:
        print(f"  - {t.bind_pieces}")
    
    print()


if __name__ == "__main__":
    test_initial_position()
    test_check_position()
    test_checkmate_position()
    test_evidence_map()
    test_full_detection()
    test_phase_detection()
    test_horse_leg_blocked()
    test_kings_face_to_face()
    test_cannon_battery()
    test_favorable_exchange()
    test_king_safety_critical()
    test_initiative()
    test_forcing_move()
    test_checkmate_horse_corner()
    test_checkmate_bare_king()
    test_checkmate_double_cannon_battery()
    test_checkmate_sea_bottom_moon()
    test_checkmate_side_tiger()
    
    print("=" * 60)
    print("所有测试完成！")
    print("=" * 60)
