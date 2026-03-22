"""
象棋知识库 - 张力导向检索

职责: 根据张力类型检索相关棋理原则
原则: 知识库不是用来"丰富输出"，而是参与假设的生成和验证

文档依据: docs/communication/GLM5_COACH_INTELLIGENCE_GUIDE.md
设计者: Claude Sonnet（诸葛先生）
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class Principle:
    """棋理原则"""
    content: str                    # 原则内容
    applies_when: str               # 适用条件
    counter_case: str = ""          # 反例/例外情况
    source: str = "经典棋理"         # 来源

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "applies_when": self.applies_when,
            "counter_case": self.counter_case,
            "source": self.source
        }


class ChessKnowledgeBase:
    """
    按张力类型组织的棋理知识库

    不是通用的 RAG，而是"张力导向检索"
    """

    # 张力类型 → 对应的棋理原则
    TENSION_PRINCIPLES = {
        "material_vs_initiative": [
            Principle(
                content="多子一方应主动兑换，简化局面，消除对方攻势",
                applies_when="当对方有攻势但己方子力占优时",
                counter_case="若对方攻势已形成直接将杀威胁，被动防守可能更优",
                source="《象棋战术》"
            ),
            Principle(
                content="攻势方应保持局面复杂，避免简化",
                applies_when="当己方子力处于劣势但有攻势时",
                counter_case="若自身也有子力损失风险，需谨慎",
                source="《象棋中局战术》"
            ),
            Principle(
                content="子力优势需要时间兑现，攻势优势需要速度",
                applies_when="判断谁的计划更快时",
                counter_case="无",
                source="《象棋战略》"
            ),
            Principle(
                content="有攻势的一方应该攻击，而不是防守",
                applies_when="当有明确进攻线路时",
                counter_case="若进攻会导致自身防守崩溃，需先稳固",
                source="《象棋进攻艺术》"
            ),
        ],
        "hidden_imbalance": [
            Principle(
                content="子力不协调往往比明显的子力劣势更危险",
                applies_when="当引擎评分差但战术标签少时",
                counter_case="有时评分差异来自引擎的深层计算，人类难以即时判断",
                source="《象棋局面评估》"
            ),
            Principle(
                content="位置优势会随时间转化为子力优势",
                applies_when="局面平稳但一方有明显位置优势时",
                counter_case="无",
                source="《象棋战略》"
            ),
            Principle(
                content="空间优势允许更灵活的子力调动",
                applies_when="一方控制更多空间时",
                counter_case="空间过大可能导致子力分散",
                source="《象棋空间控制》"
            ),
        ],
        "crisis_with_resources": [
            Principle(
                content="被将时优先考虑反击而非被动防守",
                applies_when="有反击机会时",
                counter_case="若反击会导致更大的子力损失，需谨慎",
                source="《象棋防守艺术》"
            ),
            Principle(
                content="无根子是战术组合的潜在目标",
                applies_when="有无根子存在时",
                counter_case="有时无根子是进攻的必要代价",
                source="《象棋战术》"
            ),
            Principle(
                content="活跃的子力可以弥补局部的薄弱",
                applies_when="子力活跃但存在薄弱点时",
                counter_case="若薄弱点是将帅本身，必须优先处理",
                source="《象棋攻防》"
            ),
        ],
        "sleeping_piece": [
            Principle(
                content="每步棋都应激活一个消极棋子，或改善其位置",
                applies_when="当存在明显消极棋子时",
                counter_case="有时消极棋子是防守的必要代价",
                source="《象棋开局原理》"
            ),
            Principle(
                content="车的活跃度决定局面的动态性",
                applies_when="车处于消极位置时",
                counter_case="无",
                source="《车的作用》"
            ),
            Principle(
                content="炮需要架子，没有架子的炮价值减半",
                applies_when="炮没有炮架时",
                counter_case="残局中炮可以独立作战",
                source="《炮的用法》"
            ),
        ],
        "tag_contradiction": [
            Principle(
                content="主动权必须建立在安全的基础上",
                applies_when="同时有主动权和安全威胁时",
                counter_case="无",
                source="《象棋攻防》"
            ),
            Principle(
                content="虚假的主动权比没有主动权更危险",
                applies_when="主动权可能不真实时",
                counter_case="无",
                source="《象棋战略》"
            ),
        ],
        "phase_mismatch": [
            Principle(
                content="开局阶段的意外子力损失需要改变策略",
                applies_when="开局阶段子力严重失衡时",
                counter_case="无",
                source="《象棋开局》"
            ),
            Principle(
                content="残局原则不适用于有大量棋子的局面",
                applies_when="阶段判断模糊时",
                counter_case="无",
                source="《象棋阶段理论》"
            ),
        ],
    }

    # 通用棋理原则（不针对特定张力）
    GENERAL_PRINCIPLES = [
        Principle(
            content="将帅安全是第一位的",
            applies_when="任何局面",
            counter_case="无",
            source="《象棋基本原理》"
        ),
        Principle(
            content="先手是宝贵的，不要轻易放弃",
            applies_when="握有先手时",
            counter_case="有时弃先争先更重要",
            source="《象棋先手理论》"
        ),
        Principle(
            content="控制中路是战略优势",
            applies_when="中路控制权争夺时",
            counter_case="侧翼进攻可能绕过中路",
            source="《象棋中路控制》"
        ),
    ]

    def query_for_tension(self, tension_type: str, phase: str = "中局") -> List[Principle]:
        """
        根据张力类型检索相关原则

        Args:
            tension_type: 张力类型
            phase: 局面阶段

        Returns:
            相关原则列表
        """
        principles = self.TENSION_PRINCIPLES.get(tension_type, [])
        return principles

    def query_general_principles(self, count: int = 3) -> List[Principle]:
        """
        获取通用原则

        Args:
            count: 返回数量

        Returns:
            通用原则列表
        """
        return self.GENERAL_PRINCIPLES[:count]

    def get_principles_for_prompt(self, tension_type: str, phase: str = "中局") -> str:
        """
        获取用于Prompt的原则文本

        Args:
            tension_type: 张力类型
            phase: 局面阶段

        Returns:
            格式化的原则文本
        """
        principles = self.query_for_tension(tension_type, phase)

        if not principles:
            return ""

        lines = ["【相关棋理原则】"]
        for i, p in enumerate(principles[:3], 1):  # 最多3条
            lines.append(f"{i}. {p.content}")
            lines.append(f"   适用：{p.applies_when}")
            if p.counter_case and p.counter_case != "无":
                lines.append(f"   例外：{p.counter_case}")

        return "\n".join(lines)


def get_knowledge_base() -> ChessKnowledgeBase:
    """获取知识库实例"""
    return ChessKnowledgeBase()


def query_principles_for_tension(tension_type: str, phase: str = "中局") -> List[Dict[str, Any]]:
    """
    便捷函数：根据张力类型查询原则

    Args:
        tension_type: 张力类型
        phase: 局面阶段

    Returns:
        原则字典列表
    """
    kb = ChessKnowledgeBase()
    principles = kb.query_for_tension(tension_type, phase)
    return [p.to_dict() for p in principles]


def get_principles_prompt(tension_type: str, phase: str = "中局") -> str:
    """
    便捷函数：获取用于Prompt的原则文本

    Args:
        tension_type: 张力类型
        phase: 局面阶段

    Returns:
        格式化的原则文本
    """
    kb = ChessKnowledgeBase()
    return kb.get_principles_for_prompt(tension_type, phase)
