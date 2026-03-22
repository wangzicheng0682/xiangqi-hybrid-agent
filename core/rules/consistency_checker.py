"""
标签一致性检查器

利用象棋规则的逻辑蕴含关系，让标签系统自我检验。
核心思想：如果 A 标签存在，则 B 标签必须/不能存在。违反这些关系，说明某个标签有 bug。
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any


@dataclass
class ConsistencyRule:
    """一致性规则定义"""
    name: str
    condition_tag: str
    required_tag: Optional[str]
    forbidden_tag: Optional[str]
    severity: str
    explanation: str


CONSISTENCY_RULES: List[ConsistencyRule] = [
    
    ConsistencyRule(
        name="将死必有将军",
        condition_tag="is_checkmate",
        required_tag="is_check",
        forbidden_tag=None,
        severity="ERROR",
        explanation=(
            "将死的定义是：处于将军且无法解除。因此将死时必然处于将军状态。"
            "如果 is_checkmate=True 但 is_check=False，将死检测逻辑有 bug。"
        )
    ),
    
    ConsistencyRule(
        name="困毙不能有将军",
        condition_tag="is_stalemate",
        required_tag=None,
        forbidden_tag="is_check",
        severity="ERROR",
        explanation=(
            "困毙的定义是：轮到自己走棋，没有任何合法走法，且不处于将军状态。"
            "如果同时出现 is_stalemate 和 is_check，两个检测至少有一个是错的。"
        )
    ),
    
    ConsistencyRule(
        name="将死与困毙互斥",
        condition_tag="is_checkmate",
        required_tag=None,
        forbidden_tag="is_stalemate",
        severity="ERROR",
        explanation="将死和困毙是两种不同的终局状态，不能同时成立。"
    ),
    
    ConsistencyRule(
        name="闪将必有将军",
        condition_tag="is_discovered_check",
        required_tag="is_check",
        forbidden_tag=None,
        severity="ERROR",
        explanation="闪将是将军的一种特殊形式，闪将必然导致将军状态。"
    ),
    
    ConsistencyRule(
        name="双将必有将军",
        condition_tag="is_double_attack_with_check",
        required_tag="is_check",
        forbidden_tag=None,
        severity="ERROR",
        explanation="双将是两个棋子同时将军，必然处于将军状态。"
    ),
    
    ConsistencyRule(
        name="开局阶段唯一",
        condition_tag="phase_opening",
        required_tag=None,
        forbidden_tag="phase_middlegame",
        severity="ERROR",
        explanation="开局和中局阶段不能同时存在。"
    ),
    
    ConsistencyRule(
        name="开局与残局互斥",
        condition_tag="phase_opening",
        required_tag=None,
        forbidden_tag="phase_endgame",
        severity="ERROR",
        explanation="开局和残局阶段不能同时存在。"
    ),
    
    ConsistencyRule(
        name="中局与残局互斥",
        condition_tag="phase_middlegame",
        required_tag=None,
        forbidden_tag="phase_endgame",
        severity="ERROR",
        explanation="中局和残局阶段不能同时存在。"
    ),
    
    ConsistencyRule(
        name="将死局面不应有战略评估",
        condition_tag="is_checkmate",
        required_tag=None,
        forbidden_tag="has_active_pieces",
        severity="WARNING",
        explanation=(
            "将死局面已经结束，战略评估标签在此没有意义。"
            "如果同时出现，说明标签的触发时机可能有问题。"
        )
    ),
    
    ConsistencyRule(
        name="困毙局面不应有战略评估",
        condition_tag="is_stalemate",
        required_tag=None,
        forbidden_tag="has_active_pieces",
        severity="WARNING",
        explanation="困毙局面已经结束，战略评估标签在此没有意义。"
    ),
    
    ConsistencyRule(
        name="将帅危急与将帅安全互斥",
        condition_tag="king_safety_critical",
        required_tag=None,
        forbidden_tag="king_safety_good",
        severity="ERROR",
        explanation="将帅危急和将帅安全是互斥状态，不能同时成立。"
    ),
    
    ConsistencyRule(
        name="被牵制棋子不能自由移动",
        condition_tag="is_pinned",
        required_tag=None,
        forbidden_tag=None,
        severity="INFO",
        explanation="被牵制的棋子移动受限，这是一个信息性提示。"
    ),
]


class ConsistencyError(Exception):
    """一致性检查错误"""
    pass


class ConsistencyChecker:
    """标签一致性检查器"""
    
    def __init__(self, rules: Optional[List[ConsistencyRule]] = None):
        """
        初始化检查器
        
        Args:
            rules: 自定义规则列表，默认使用 CONSISTENCY_RULES
        """
        self.rules = rules or CONSISTENCY_RULES
    
    def check(self, tags_dict: Dict[str, Any], fen: str) -> List[Dict[str, Any]]:
        """
        检查标签组合是否满足一致性规则
        
        Args:
            tags_dict: {tag_name: tag_info} 的字典
            fen: 当前局面（用于 bug 报告）
            
        Returns:
            违规列表，空列表表示一致
        """
        violations = []
        
        for rule in self.rules:
            if rule.condition_tag not in tags_dict:
                continue
            
            if rule.required_tag and rule.required_tag not in tags_dict:
                violations.append({
                    "severity": rule.severity,
                    "rule": rule.name,
                    "detail": (
                        f"标签 [{rule.condition_tag}] 存在，"
                        f"但必须同时存在的标签 [{rule.required_tag}] 不存在"
                    ),
                    "explanation": rule.explanation,
                    "fen": fen,
                })
            
            if rule.forbidden_tag and rule.forbidden_tag in tags_dict:
                violations.append({
                    "severity": rule.severity,
                    "rule": rule.name,
                    "detail": (
                        f"标签 [{rule.condition_tag}] 和 [{rule.forbidden_tag}] "
                        f"不能同时存在，但都出现了"
                    ),
                    "explanation": rule.explanation,
                    "fen": fen,
                })
        
        return violations
    
    def check_and_log(self, tags_dict: Dict[str, Any], fen: str) -> bool:
        """
        检查并打印结果
        
        Args:
            tags_dict: {tag_name: tag_info} 的字典
            fen: 当前局面
            
        Returns:
            True 表示通过（无ERROR级别违规），False 表示有ERROR级别违规
        """
        violations = self.check(tags_dict, fen)
        
        has_error = False
        for v in violations:
            icon = "🔴" if v["severity"] == "ERROR" else "🟡" if v["severity"] == "WARNING" else "ℹ️"
            print(f"{icon} [{v['severity']}] {v['rule']}: {v['detail']}")
            if v["severity"] == "ERROR":
                has_error = True
        
        return not has_error
    
    def check_and_raise(self, tags_dict: Dict[str, Any], fen: str) -> None:
        """
        检查并在有ERROR时抛出异常
        
        Args:
            tags_dict: {tag_name: tag_info} 的字典
            fen: 当前局面
            
        Raises:
            ConsistencyError: 有ERROR级别违规时抛出
        """
        violations = self.check(tags_dict, fen)
        
        error_violations = [v for v in violations if v["severity"] == "ERROR"]
        
        if error_violations:
            raise ConsistencyError(
                f"标签一致性检查失败：{len(error_violations)} 个 ERROR\n" +
                "\n".join(v["detail"] for v in error_violations)
            )


def check_position_consistency(detected_tags: List[Any], fen: str) -> List[Dict[str, Any]]:
    """
    便捷函数：检查检测结果的一致性
    
    Args:
        detected_tags: 检测到的标签列表（TagDetectionResult对象）
        fen: 当前局面FEN
        
    Returns:
        违规列表
    """
    checker = ConsistencyChecker()
    tags_dict = {t.tag.name: t for t in detected_tags if t.detected}
    return checker.check(tags_dict, fen)


def validate_detection_result(result: Any, fen: str, raise_on_error: bool = False) -> bool:
    """
    验证检测结果的一致性
    
    Args:
        result: PositionTacticalAnalysis 或类似对象
        fen: 当前局面FEN
        raise_on_error: 是否在出错时抛出异常
        
    Returns:
        True 表示通过，False 表示有违规
    """
    checker = ConsistencyChecker()
    
    detected_tags = result.get_detected_tags() if hasattr(result, 'get_detected_tags') else result
    tags_dict = {t.tag.name: t for t in detected_tags if t.detected}
    
    if raise_on_error:
        checker.check_and_raise(tags_dict, fen)
        return True
    else:
        return checker.check_and_log(tags_dict, fen)


if __name__ == "__main__":
    print("一致性规则列表：")
    print("=" * 60)
    for rule in CONSISTENCY_RULES:
        print(f"\n规则：{rule.name}")
        print(f"  条件标签：{rule.condition_tag}")
        if rule.required_tag:
            print(f"  必须存在：{rule.required_tag}")
        if rule.forbidden_tag:
            print(f"  不能存在：{rule.forbidden_tag}")
        print(f"  严重程度：{rule.severity}")
        print(f"  说明：{rule.explanation}")
