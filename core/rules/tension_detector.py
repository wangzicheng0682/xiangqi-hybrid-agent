"""
张力检测器

职责: 检测局面中的"张力"——矛盾、异常、值得深挖的特征
原则: 张力驱动好奇心，好奇心驱动分析

文档依据: docs/communication/GLM5_COACH_INTELLIGENCE_GUIDE.md
设计者: Claude Sonnet（诸葛先生）
"""

from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
from enum import Enum


class TensionType(Enum):
    """张力类型"""
    HIDDEN_IMBALANCE = "hidden_imbalance"              # 评估异常：引擎差但标签少
    MATERIAL_VS_INITIATIVE = "material_vs_initiative"  # 子力vs攻势
    CRISIS_WITH_RESOURCES = "crisis_with_resources"    # 危机中的资源
    SLEEPING_PIECE = "sleeping_piece"                  # 沉睡的棋子
    TAG_CONTRADICTION = "tag_contradiction"            # 标签矛盾
    PHASE_MISMATCH = "phase_mismatch"                  # 阶段错位


class TensionPriority(Enum):
    """张力优先级"""
    CRITICAL = 3   # 必须立刻处理
    HIGH = 2       # 影响局面判断的核心张力
    MEDIUM = 1     # 值得注意但不影响全局
    LOW = 0        # 边缘信息


@dataclass
class Tension:
    """张力对象"""
    tension_type: str                    # 张力类型
    priority: TensionPriority            # 优先级
    question: str                        # 核心问题（驱动后续分析）
    evidence: List[str]                  # 支持证据
    hypothesis: str                      # 初始假设
    suggested_tools: List[str] = None    # 建议调用的工具

    def __post_init__(self):
        if self.suggested_tools is None:
            self.suggested_tools = []

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "tension_type": self.tension_type,
            "priority": self.priority.name,
            "question": self.question,
            "evidence": self.evidence,
            "hypothesis": self.hypothesis,
            "suggested_tools": self.suggested_tools
        }


class TensionDetector:
    """
    张力检测器

    检测局面中的"张力"——即两种力量或价值之间的冲突，
    导致局面无法用简单结论描述。

    张力的存在触发"好奇心"，驱动后续的深度分析。
    """

    # 张力类型的中文名称
    TENSION_NAMES = {
        TensionType.HIDDEN_IMBALANCE: "评估异常",
        TensionType.MATERIAL_VS_INITIATIVE: "子力与攻势失衡",
        TensionType.CRISIS_WITH_RESOURCES: "危机中的资源",
        TensionType.SLEEPING_PIECE: "沉睡的强子",
        TensionType.TAG_CONTRADICTION: "标签矛盾",
        TensionType.PHASE_MISMATCH: "阶段错位",
    }

    def __init__(self):
        pass

    def detect_all(self, evidence_map: Dict[str, Any],
                   engine_eval: Dict[str, Any],
                   phase: str = "中局") -> List[Tension]:
        """
        检测所有张力

        Args:
            evidence_map: Evidence Map（包含facts_rules等）
            engine_eval: 引擎评估（包含cp、best等）
            phase: 局面阶段（开局/中局/残局）

        Returns:
            按优先级排序的张力列表
        """
        tensions = []

        # 提取标签集合
        tags = self._extract_tags(evidence_map)

        # 引擎评估
        cp = engine_eval.get('cp', 0) if engine_eval else 0

        # ── 张力一：评估异常 ──────────────────────────────────────
        tension = self._detect_hidden_imbalance(tags, cp, evidence_map)
        if tension:
            tensions.append(tension)

        # ── 张力二：危机中的资源 ─────────────────────────────────
        tension = self._detect_crisis_with_resources(tags, evidence_map)
        if tension:
            tensions.append(tension)

        # ── 张力三：子力 vs 攻势 ─────────────────────────────────
        tension = self._detect_material_vs_initiative(tags, cp, evidence_map)
        if tension:
            tensions.append(tension)

        # ── 张力四：沉睡的强子 ───────────────────────────────────
        tension = self._detect_sleeping_piece(tags, evidence_map)
        if tension:
            tensions.append(tension)

        # ── 张力五：标签矛盾 ─────────────────────────────────────
        tension = self._detect_tag_contradiction(tags, evidence_map)
        if tension:
            tensions.append(tension)

        # 按优先级排序（高优先级在前）
        tensions.sort(key=lambda t: t.priority.value, reverse=True)

        return tensions

    def get_primary_contradiction(self, tensions: List[Tension]) -> Optional[Tension]:
        """
        获取主要矛盾（优先级最高的张力）

        Args:
            tensions: 张力列表

        Returns:
            主要矛盾，如果没有则返回None
        """
        return tensions[0] if tensions else None

    def _extract_tags(self, evidence_map: Dict[str, Any]) -> Set[str]:
        """从Evidence Map中提取标签集合"""
        tags = set()
        facts_rules = evidence_map.get('facts_rules', [])
        for item in facts_rules:
            if isinstance(item, dict) and 'tag' in item:
                tags.add(item['tag'])
        return tags

    def _detect_hidden_imbalance(self, tags: Set[str], cp: int,
                                  evidence_map: Dict[str, Any]) -> Optional[Tension]:
        """
        检测评估异常张力

        触发条件：引擎认为差距大，但战术标签少 → 有隐藏的结构性问题
        """
        # 计算战术标签数量（排除基础标签）
        tactical_tags = [t for t in tags if t.startswith('is_')
                        and t not in ['is_check', 'is_checkmate', 'is_stalemate']]
        tactical_count = len(tactical_tags)

        # 引擎评估差距大（超过3兵），但战术标签少（<2个）
        # 注意：开局阶段小优势（cp<300）是正常的，不算"评估异常"
        if abs(cp) > 300 and tactical_count < 2:
            side = "红方" if cp > 0 else "黑方"
            return Tension(
                tension_type=TensionType.HIDDEN_IMBALANCE.value,
                priority=TensionPriority.HIGH,
                question=f"引擎评估{side}有明显优势（{cp}分），但可见的战术特征稀少。这个优势来自哪里？是子力协调、位置优势还是潜在威胁？",
                evidence=[
                    f"引擎评分: {cp}cp",
                    f"可见战术标签数: {tactical_count}",
                    f"标签列表: {list(tactical_tags) if tactical_tags else '无'}"
                ],
                hypothesis="局面存在非战术性的结构优势或劣势，需要战略层面的分析",
                suggested_tools=["analyze_position_strategy", "engine_deep_analysis"]
            )
        return None

    def _detect_crisis_with_resources(self, tags: Set[str],
                                       evidence_map: Dict[str, Any]) -> Optional[Tension]:
        """
        检测危机中的资源张力

        触发条件：被将同时有无根子，但己方子力活跃 → 真危机还是佯危机？
        """
        # 检查标签组合
        has_check = 'is_check' in tags
        has_unprotected = 'piece_is_unprotected' in tags or 'TAG_PIECE_IS_UNPROTECTED' in tags
        has_initiative = 'has_active_pieces' in tags or 'TAG_HAS_INITIATIVE' in tags

        if has_check and (has_unprotected or has_initiative):
            evidence_list = ["is_check（被将军）"]
            if has_unprotected:
                evidence_list.append("piece_is_unprotected（有无根子）")
            if has_initiative:
                evidence_list.append("has_active_pieces（子力活跃）")

            return Tension(
                tension_type=TensionType.CRISIS_WITH_RESOURCES.value,
                priority=TensionPriority.CRITICAL,
                question="我方正在被将，同时存在薄弱环节或活跃子力。这是真实的危机，还是对方在攻击的同时暴露了弱点？",
                evidence=evidence_list,
                hypothesis="需要判断应将方式：是否存在既解将又反击的着法",
                suggested_tools=["get_forcing_sequence", "analyze_move", "get_piece_relations"]
            )
        return None

    def _detect_material_vs_initiative(self, tags: Set[str], cp: int,
                                        evidence_map: Dict[str, Any]) -> Optional[Tension]:
        """
        检测子力vs攻势张力

        触发条件：一方子力占优但另一方有攻势 → 谁的计划更快？
        """
        # 判断子力优势（用引擎评分近似）
        material_up = cp > 100  # 红方多子
        material_down = cp < -100  # 黑方多子

        # 判断攻势（通过战术标签）
        attacking_tags = {'is_attack_unprotected', 'is_discovered_check',
                         'is_double_attack_with_check', 'TAG_IS_ATTACK_UNPROTECTED'}
        has_attack = bool(tags & attacking_tags)

        # 检查主动权标签
        has_initiative = 'TAG_HAS_INITIATIVE' in tags

        # 红方多子但黑方有攻势
        if material_up and (has_attack or has_initiative):
            return Tension(
                tension_type=TensionType.MATERIAL_VS_INITIATIVE.value,
                priority=TensionPriority.HIGH,
                question="红方子力占优，但黑方正在施压。这是速度的比拼：红方能否在被攻破前利用子力优势？",
                evidence=[
                    f"引擎评分倾向红方（{cp}cp）",
                    "黑方有进攻性标签",
                    f"攻势标签: {list(tags & attacking_tags)}"
                ],
                hypothesis="局面的关键不是子力数量，而是计划执行的速度",
                suggested_tools=["get_forcing_sequence", "engine_deep_analysis", "compare_moves"]
            )

        # 黑方多子但红方有攻势
        if material_down and (has_attack or has_initiative):
            return Tension(
                tension_type=TensionType.MATERIAL_VS_INITIATIVE.value,
                priority=TensionPriority.HIGH,
                question="黑方子力占优，但红方正在施压。这是速度的比拼：红方的攻势能否在黑方整合前突破？",
                evidence=[
                    f"引擎评分倾向黑方（{cp}cp）",
                    "红方有进攻性标签"
                ],
                hypothesis="攻势方需要加快进攻节奏，避免被对方简化局面",
                suggested_tools=["get_forcing_sequence", "engine_deep_analysis"]
            )

        return None

    def _detect_sleeping_piece(self, tags: Set[str],
                                evidence_map: Dict[str, Any]) -> Optional[Tension]:
        """
        检测沉睡的强子张力

        触发条件：车或炮处于消极位置，既不攻也不守

        注意：这个检测需要更详细的棋子信息，这里做简化版本
        """
        # 简化检测：如果有"子力不协调"但没有具体的攻击标签
        has_inactive = 'inactive_pieces' in tags or 'TAG_INACTIVE_PIECES' in tags

        if has_inactive:
            return Tension(
                tension_type=TensionType.SLEEPING_PIECE.value,
                priority=TensionPriority.MEDIUM,
                question="存在明显消极的强子。它的存在价值是什么？是否应该激活它？",
                evidence=["检测到消极棋子"],
                hypothesis="激活消极棋子可能是当前局面的关键改善方向",
                suggested_tools=["get_piece_attacks", "analyze_position_strategy"]
            )
        return None

    def _detect_tag_contradiction(self, tags: Set[str],
                                   evidence_map: Dict[str, Any]) -> Optional[Tension]:
        """
        检测标签矛盾张力

        触发条件：同时有主动权标签和安全威胁标签
        """
        # 主动权标签
        initiative_tags = {'has_active_pieces', 'TAG_HAS_INITIATIVE', 'TAG_FAVORABLE_EXCHANGE'}
        # 安全威胁标签
        safety_tags = {'is_check', 'is_checkmate', 'TAG_KING_SAFETY_CRITICAL'}

        has_initiative = bool(tags & initiative_tags)
        has_safety_issue = bool(tags & safety_tags)

        if has_initiative and has_safety_issue:
            return Tension(
                tension_type=TensionType.TAG_CONTRADICTION.value,
                priority=TensionPriority.HIGH,
                question="己方子力活跃，但同时存在安全威胁。主动权是真实的还是错觉？",
                evidence=[
                    f"主动权标签: {list(tags & initiative_tags)}",
                    f"安全威胁标签: {list(tags & safety_tags)}"
                ],
                hypothesis="主动权可能是表面的，实际局面可能更危险",
                suggested_tools=["get_threats_to_piece", "engine_deep_analysis"]
            )
        return None


def detect_tensions(evidence_map: Dict[str, Any],
                    engine_eval: Dict[str, Any],
                    phase: str = "中局") -> List[Dict[str, Any]]:
    """
    便捷函数：检测张力并返回字典列表

    Args:
        evidence_map: Evidence Map
        engine_eval: 引擎评估
        phase: 局面阶段

    Returns:
        张力字典列表
    """
    detector = TensionDetector()
    tensions = detector.detect_all(evidence_map, engine_eval, phase)
    return [t.to_dict() for t in tensions]


def get_primary_tension(evidence_map: Dict[str, Any],
                        engine_eval: Dict[str, Any],
                        phase: str = "中局") -> Optional[Dict[str, Any]]:
    """
    便捷函数：获取主要矛盾

    Args:
        evidence_map: Evidence Map
        engine_eval: 引擎评估
        phase: 局面阶段

    Returns:
        主要矛盾字典，如果没有则返回None
    """
    detector = TensionDetector()
    tensions = detector.detect_all(evidence_map, engine_eval, phase)
    primary = detector.get_primary_contradiction(tensions)
    return primary.to_dict() if primary else None
