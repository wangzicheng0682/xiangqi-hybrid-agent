"""
黄金局面测试框架

基于黄金局面测试库，验证标签检测器的正确性。
每个黄金局面是事先知道正确答案的测试局面。
"""

import pytest
import sys
from typing import List, Dict, Any

sys.path.insert(0, 'd:/xiangqi-hybrid-agent')

from core.rules.tactical_detector import TacticalDetector
from tests.golden_positions import (
    GOLDEN_POSITIONS,
    get_golden_position_by_id,
    get_golden_positions_by_tag,
)


detector = TacticalDetector()


class TestGoldenPositions:
    """黄金局面测试类"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前初始化检测器"""
        self.detector = TacticalDetector()
    
    def test_all_positions(self):
        """主测试：遍历所有黄金局面，报告所有失败"""
        all_failures = []
        
        for pos in GOLDEN_POSITIONS:
            failures = self._check_position(pos)
            all_failures.extend(failures)
        
        if all_failures:
            report = self._format_failure_report(all_failures)
            pytest.fail(report)
    
    def _check_position(self, pos: dict) -> list:
        """
        检查单个黄金局面
        
        Args:
            pos: 黄金局面定义
            
        Returns:
            失败列表，空列表表示通过
        """
        failures = []
        fen = pos["fen"]

        result = self.detector.detect_static(fen)
        # 使用列表存储同名标签，避免字典覆盖
        result_tags = {}
        for t in result.get_detected_tags():
            if t.tag.name not in result_tags:
                result_tags[t.tag.name] = []
            result_tags[t.tag.name].append(t)
        
        for tag in pos.get("expected_true", []):
            if tag not in result_tags:
                failures.append({
                    "position_id": pos["id"],
                    "position_name": pos["name"],
                    "type": "MISSING_TAG",
                    "detail": f"标签 [{tag}] 应该触发，但没有",
                    "description": pos["description"],
                })
        
        for tag in pos.get("expected_false", []):
            if tag in result_tags:
                failures.append({
                    "position_id": pos["id"],
                    "position_name": pos["name"],
                    "type": "SPURIOUS_TAG",
                    "detail": f"标签 [{tag}] 不应该触发，但触发了",
                    "description": pos["description"],
                })
        
        for tag, binding_spec in pos.get("expected_bindings", {}).items():
            if tag not in result_tags:
                continue

            # 获取该标签的所有绑定（列表）
            all_bindings = result_tags[tag]

            if "bind_pieces_must_contain" in binding_spec:
                for required_piece in binding_spec["bind_pieces_must_contain"]:
                    # 检查所有同名标签，只要有一个包含所需棋子就算通过
                    found = False
                    for binding in all_bindings:
                        actual_pieces = binding.bind_pieces
                        if any(required_piece in str(p) for p in actual_pieces):
                            found = True
                            break
                    if not found:
                        # 收集所有绑定的棋子用于错误报告
                        all_pieces = []
                        for binding in all_bindings:
                            all_pieces.extend(binding.bind_pieces)
                        failures.append({
                            "position_id": pos["id"],
                            "position_name": pos["name"],
                            "type": "WRONG_BINDING",
                            "detail": (
                                f"标签 [{tag}] 应该绑定棋子 [{required_piece}]，"
                                f"但实际绑定是 {all_pieces}"
                            ),
                            "description": pos["description"],
                        })

            if "attacker_type" in binding_spec:
                attacker_type = binding_spec["attacker_type"]
                attacker_found = False
                for binding in all_bindings:
                    actual_pieces = binding.bind_pieces
                    if any(attacker_type in str(p) for p in actual_pieces):
                        attacker_found = True
                        break
                if not attacker_found:
                    all_pieces = []
                    for binding in all_bindings:
                        all_pieces.extend(binding.bind_pieces)
                    failures.append({
                        "position_id": pos["id"],
                        "position_name": pos["name"],
                        "type": "WRONG_ATTACKER",
                        "detail": (
                            f"标签 [{tag}] 攻击者类型应为 [{attacker_type}]，"
                            f"但实际绑定是 {all_pieces}"
                        ),
                        "description": pos["description"],
                    })

            if "target_type" in binding_spec:
                target_type = binding_spec["target_type"]
                target_found = False
                for binding in all_bindings:
                    actual_pieces = binding.bind_pieces
                    if any(target_type in str(p) for p in actual_pieces):
                        target_found = True
                        break
                if not target_found:
                    all_pieces = []
                    for binding in all_bindings:
                        all_pieces.extend(binding.bind_pieces)
                    failures.append({
                        "position_id": pos["id"],
                        "position_name": pos["name"],
                        "type": "WRONG_TARGET",
                        "detail": (
                            f"标签 [{tag}] 目标类型应为 [{target_type}]，"
                            f"但实际绑定是 {all_pieces}"
                        ),
                        "description": pos["description"],
                    })
        
        dynamic_test = pos.get("dynamic_test")
        if dynamic_test:
            move = dynamic_test.get("move")
            if move:
                dyn_failures = self._check_dynamic_position(pos, fen, move, dynamic_test)
                failures.extend(dyn_failures)
        
        return failures
    
    def _check_dynamic_position(self, pos: dict, fen: str, move: str,
                                 dynamic_test: dict) -> list:
        """检查动态测试"""
        failures = []

        try:
            result = self.detector.detect_dynamic(fen, move)
            # 使用列表存储同名标签，避免字典覆盖
            result_tags = {}
            for t in result.get_detected_tags():
                if t.tag.name not in result_tags:
                    result_tags[t.tag.name] = []
                result_tags[t.tag.name].append(t)
            
            for tag in dynamic_test.get("expected_true", []):
                if tag not in result_tags:
                    failures.append({
                        "position_id": pos["id"],
                        "position_name": pos["name"],
                        "type": "MISSING_DYNAMIC_TAG",
                        "detail": f"动态检测：走法 [{move}] 后标签 [{tag}] 应该触发，但没有",
                        "description": pos["description"],
                    })
            
            for tag in dynamic_test.get("expected_false", []):
                if tag in result_tags:
                    failures.append({
                        "position_id": pos["id"],
                        "position_name": pos["name"],
                        "type": "SPURIOUS_DYNAMIC_TAG",
                        "detail": f"动态检测：走法 [{move}] 后标签 [{tag}] 不应该触发，但触发了",
                        "description": pos["description"],
                    })
        except Exception as e:
            failures.append({
                "position_id": pos["id"],
                "position_name": pos["name"],
                "type": "DYNAMIC_ERROR",
                "detail": f"动态检测执行失败：{str(e)}",
                "description": pos["description"],
            })
        
        return failures
    
    def _format_failure_report(self, failures: list) -> str:
        """格式化失败报告"""
        lines = [f"\n{'='*60}", f"测试失败：{len(failures)} 个问题", f"{'='*60}\n"]
        
        by_position = {}
        for f in failures:
            key = f"{f['position_id']} {f['position_name']}"
            by_position.setdefault(key, []).append(f)
        
        for pos_key, pos_failures in by_position.items():
            lines.append(f"📍 {pos_key}")
            lines.append(f"   说明：{pos_failures[0]['description']}")
            for f in pos_failures:
                icon = "❌" if f["type"] in ["MISSING_TAG", "WRONG_BINDING", 
                                              "WRONG_ATTACKER", "WRONG_TARGET",
                                              "MISSING_DYNAMIC_TAG", "DYNAMIC_ERROR"] else "⚠️"
                lines.append(f"   {icon} [{f['type']}] {f['detail']}")
            lines.append("")
        
        return "\n".join(lines)


class TestTagConsistency:
    """标签一致性测试"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.detector = TacticalDetector()
    
    def test_checkmate_implies_check(self):
        """将死必然意味着将军"""
        for pos in GOLDEN_POSITIONS:
            if "is_checkmate" in pos.get("expected_true", []):
                assert "is_check" in pos.get("expected_true", []), \
                    f"{pos['id']}: 将死局面必须同时标记为将军"
    
    def test_stalemate_excludes_check(self):
        """困毙不能有将军"""
        for pos in GOLDEN_POSITIONS:
            if "is_stalemate" in pos.get("expected_true", []):
                assert "is_check" not in pos.get("expected_true", []), \
                    f"{pos['id']}: 困毙局面不能同时标记为将军"
                assert "is_check" in pos.get("expected_false", []), \
                    f"{pos['id']}: 困毙局面应该明确排除将军标签"
    
    def test_checkmate_stalemate_mutually_exclusive(self):
        """将死和困毙互斥"""
        for pos in GOLDEN_POSITIONS:
            true_tags = pos.get("expected_true", [])
            assert not ("is_checkmate" in true_tags and "is_stalemate" in true_tags), \
                f"{pos['id']}: 将死和困毙不能同时成立"


class TestBoundaryConditions:
    """边界条件专项测试"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.detector = TacticalDetector()
    
    def test_left_boundary(self):
        """左边界坐标测试"""
        pos = get_golden_position_by_id("GP020")
        assert pos is not None, "找不到左边界测试局面"
        
        result = self.detector.detect_static(pos["fen"])
        detected = [t.tag.name for t in result.get_detected_tags()]
        
        assert "is_attack_unprotected" in detected, \
            "左边界车攻击黑马应该触发is_attack_unprotected"
    
    def test_right_boundary(self):
        """右边界坐标测试"""
        pos = get_golden_position_by_id("GP021")
        assert pos is not None, "找不到右边界测试局面"
        
        result = self.detector.detect_static(pos["fen"])
        detected = [t.tag.name for t in result.get_detected_tags()]
        
        assert "is_attack_unprotected" in detected, \
            "右边界车攻击黑马应该触发is_attack_unprotected"
    
    def test_corner_horse(self):
        """角落马测试"""
        pos = get_golden_position_by_id("GP022")
        assert pos is not None, "找不到角落马测试局面"
        
        result = self.detector.detect_static(pos["fen"])
        detected = [t.tag.name for t in result.get_detected_tags()]
        
        assert "is_attack_unprotected" not in detected, \
            "角落马不应该触发攻击标签（攻击范围内没有敌方棋子）"


class TestCannonRules:
    """炮规则专项测试（最高频bug来源）"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.detector = TacticalDetector()
    
    def test_cannon_no_platform(self):
        """无炮架不能攻击"""
        pos = get_golden_position_by_id("GP110")
        assert pos is not None, "找不到无炮架测试局面"
        
        result = self.detector.detect_static(pos["fen"])
        detected = [t.tag.name for t in result.get_detected_tags()]
        
        assert "is_attack_unprotected" not in detected, \
            "无炮架时炮不应该攻击远处棋子"
    
    def test_cannon_one_platform(self):
        """恰好一个炮架可以攻击"""
        pos = get_golden_position_by_id("GP111")
        assert pos is not None, "找不到单炮架测试局面"
        
        result = self.detector.detect_static(pos["fen"])
        detected = [t.tag.name for t in result.get_detected_tags()]
        
        assert "is_attack_unprotected" in detected, \
            "恰好一个炮架时炮应该攻击目标"
    
    def test_cannon_two_pieces_between(self):
        """两个棋子中间不能攻击"""
        pos = get_golden_position_by_id("GP012")
        assert pos is not None, "找不到双棋子测试局面"
        
        result = self.detector.detect_static(pos["fen"])
        detected = [t.tag.name for t in result.get_detected_tags()]
        
        assert "is_attack_unprotected" not in detected, \
            "炮和目标之间有两个棋子时不应该攻击"


class TestRedBlackPerspective:
    """红黑视角测试"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.detector = TacticalDetector()
    
    def test_black_turn_check(self):
        """黑方走棋时的将军检测"""
        pos = get_golden_position_by_id("GP100")
        assert pos is not None, "找不到黑方走棋测试局面"
        
        result = self.detector.detect_static(pos["fen"])
        detected = [t.tag.name for t in result.get_detected_tags()]
        
        assert "is_check" in detected, \
            "黑车将军红帅应该触发is_check"
    
    def test_black_attack_unprotected(self):
        """黑方攻击无根子检测"""
        pos = get_golden_position_by_id("GP101")
        assert pos is not None, "找不到黑方攻无根测试局面"
        
        result = self.detector.detect_static(pos["fen"])
        detected = [t.tag.name for t in result.get_detected_tags()]
        
        assert "is_attack_unprotected" in detected, \
            "黑车攻击红马应该触发is_attack_unprotected"


def debug_position(position_id: str):
    """
    开发时用于快速调试某个局面
    
    Args:
        position_id: 黄金局面ID（如 "GP001"）
    """
    pos = get_golden_position_by_id(position_id)
    if not pos:
        print(f"找不到局面 {position_id}")
        return
    
    result = detector.detect_static(pos["fen"])
    print(f"\n局面：{pos['name']}")
    print(f"FEN：{pos['fen']}")
    print(f"\n检测到的标签：")
    for tag_info in result.get_detected_tags():
        print(f"  ✓ {tag_info.tag.name}: {tag_info.bind_pieces}")
    
    print(f"\n预期触发：{pos.get('expected_true', [])}")
    print(f"预期不触发：{pos.get('expected_false', [])}")


def run_all_tests():
    """运行所有黄金局面测试"""
    print("=" * 60)
    print("黄金局面测试")
    print("=" * 60)
    
    all_failures = []
    
    for pos in GOLDEN_POSITIONS:
        test = TestGoldenPositions()
        test.setup()
        failures = test._check_position(pos)
        
        if failures:
            all_failures.extend(failures)
            print(f"❌ {pos['id']} {pos['name']}: {len(failures)} 个问题")
        else:
            print(f"✓ {pos['id']} {pos['name']}")
    
    print()
    if all_failures:
        report = TestGoldenPositions()._format_failure_report(all_failures)
        print(report)
        return False
    else:
        print("所有黄金局面测试通过！")
        return True


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="黄金局面测试")
    parser.add_argument("--debug", type=str, help="调试指定局面，如 --debug GP001")
    parser.add_argument("--run", action="store_true", help="运行所有测试")
    parser.add_argument("--coverage", action="store_true", help="显示覆盖率报告")
    
    args = parser.parse_args()
    
    if args.debug:
        debug_position(args.debug)
    elif args.coverage:
        from tests.golden_positions import print_coverage_report
        print_coverage_report()
    else:
        success = run_all_tests()
        sys.exit(0 if success else 1)
