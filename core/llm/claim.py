"""
Phase 2: 结构化断言 (Claim) 与证据链 (Evidence Chain)

核心思想：
- 专家每个结论都是一个 Claim（断言）
- 每个 Claim 标注来源：tool_verified / reasoning / unverified
- 合成器基于 Claim 结构做裁决，而不是读自由文本猜共识
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional


# ═══════════════════════════════════════════════════════════════════════════════
# 数据结构
# ═══════════════════════════════════════════════════════════════════════════════

class ClaimSource:
    """断言来源分类"""
    TOOL_VERIFIED = "tool_verified"    # 经工具验证
    REASONING = "reasoning"            # 逻辑推理得出
    UNVERIFIED = "unverified"          # 未验证的判断


class ClaimConfidence:
    """断言置信度"""
    HIGH = "high"      # 工具直接验证
    MEDIUM = "medium"  # 逻辑推理，有部分工具支持
    LOW = "low"        # 未验证或推测


@dataclass
class EvidenceItem:
    """单条证据：一次工具调用的输入→输出"""
    tool_name: str
    arguments: dict
    result_summary: str  # 结果摘要（截断避免过长）
    success: bool = True


@dataclass
class Claim:
    """一个结构化断言"""
    statement: str                      # 断言内容
    source: str = ClaimSource.UNVERIFIED  # 来源
    confidence: str = ClaimConfidence.LOW  # 置信度
    evidence: List[EvidenceItem] = field(default_factory=list)  # 支持证据


@dataclass
class EvidenceChain:
    """专家的完整证据链"""
    tool_calls: List[EvidenceItem] = field(default_factory=list)

    def find_evidence_for(self, tool_name: str) -> List[EvidenceItem]:
        """查找特定工具的证据"""
        return [e for e in self.tool_calls if e.tool_name == tool_name]


# ═══════════════════════════════════════════════════════════════════════════════
# 解析器：从 LLM 输出中提取 Claim
# ═══════════════════════════════════════════════════════════════════════════════

# 匹配 [CLAIM] ... [EVIDENCE] ... [CONFIDENCE] ... 标记
_CLAIM_BLOCK_RE = re.compile(
    r"\[CLAIM\]\s*(.+?)(?=\[EVIDENCE\]|\[CONFIDENCE\]|\[CLAIM\]|\Z)",
    re.DOTALL,
)
_EVIDENCE_MARKER_RE = re.compile(
    r"\[EVIDENCE\]\s*(.+?)(?=\[CONFIDENCE\]|\[CLAIM\]|\Z)",
    re.DOTALL,
)
_CONFIDENCE_MARKER_RE = re.compile(
    r"\[CONFIDENCE\]\s*(高|中|低|high|medium|low)",
    re.IGNORECASE,
)

_CONFIDENCE_MAP = {
    "高": ClaimConfidence.HIGH,
    "中": ClaimConfidence.MEDIUM,
    "低": ClaimConfidence.LOW,
    "high": ClaimConfidence.HIGH,
    "medium": ClaimConfidence.MEDIUM,
    "low": ClaimConfidence.LOW,
}


def parse_claims(content: str, evidence_chain: EvidenceChain = None) -> List[Claim]:
    """
    从专家 LLM 输出中解析结构化 Claim。

    支持两种格式：
    1. 显式标记: [CLAIM] ... [EVIDENCE] ... [CONFIDENCE] ...
    2. 回退: 从【战术发现】/【战略评估】/【引擎解读】段落提取

    Args:
        content: LLM 输出文本
        evidence_chain: 工具调用证据链（用于关联 source）

    Returns:
        解析出的 Claim 列表
    """
    if not content:
        return []

    # 尝试显式标记格式
    claims = _parse_explicit_claims(content, evidence_chain)
    if claims:
        return claims

    # 回退：从传统节标题提取
    return _parse_fallback_claims(content, evidence_chain)


def _parse_explicit_claims(content: str, evidence_chain: EvidenceChain = None) -> List[Claim]:
    """解析 [CLAIM][EVIDENCE][CONFIDENCE] 标记格式"""
    # 按 [CLAIM] 分割
    claim_starts = list(_CLAIM_BLOCK_RE.finditer(content))
    if not claim_starts:
        return []

    claims = []
    for match in claim_starts:
        statement = match.group(1).strip()
        if not statement:
            continue

        # 从该 claim 位置之后查找对应的 EVIDENCE 和 CONFIDENCE
        after_claim = content[match.start():]

        # 提取 evidence 描述
        evidence_match = _EVIDENCE_MARKER_RE.search(after_claim)
        evidence_text = evidence_match.group(1).strip() if evidence_match else ""

        # 提取 confidence
        conf_match = _CONFIDENCE_MARKER_RE.search(after_claim)
        confidence = _CONFIDENCE_MAP.get(
            conf_match.group(1).strip() if conf_match else "",
            ClaimConfidence.LOW,
        )

        # 判断 source：有工具关键词 → tool_verified
        source = _infer_source(evidence_text, evidence_chain)

        claim = Claim(
            statement=statement[:200],  # 截断
            source=source,
            confidence=confidence,
            evidence=_match_evidence_items(evidence_text, evidence_chain),
        )
        claims.append(claim)

    return claims


def _parse_fallback_claims(content: str, evidence_chain: EvidenceChain = None) -> List[Claim]:
    """从传统【节标题】格式回退提取 Claim"""
    claims = []

    # 提取关键节标题的内容作为 claim
    finding_patterns = [
        (r"【战术发现】\s*(.+?)(?=【|$)", "tactics"),
        (r"【战略评估】\s*(.+?)(?=【|$)", "strategy"),
        (r"【引擎解读】\s*(.+?)(?=【|$)", "engine"),
        (r"【教练建议】\s*(.+?)(?=【|$)", "coach"),
    ]

    for pattern, tag in finding_patterns:
        match = re.search(pattern, content, re.DOTALL)
        if match:
            statement = match.group(1).strip()
            if not statement:
                continue

            # 从"结论可信度"段推断
            conf_match = re.search(r"【结论可信度】\s*(高|中|低)", content)
            confidence = _CONFIDENCE_MAP.get(
                conf_match.group(1) if conf_match else "",
                ClaimConfidence.MEDIUM,
            )

            # 有证据链 → 提升 source
            has_tool_evidence = bool(evidence_chain and evidence_chain.tool_calls)
            source = ClaimSource.TOOL_VERIFIED if has_tool_evidence else ClaimSource.REASONING

            claims.append(Claim(
                statement=statement[:200],
                source=source,
                confidence=confidence,
                evidence=evidence_chain.tool_calls[:3] if evidence_chain else [],
            ))

    # 如果连传统格式也没匹配到，取前200字作单条 claim
    if not claims and content.strip():
        first_line = content.strip().split("\n")[0][:200]
        has_tools = bool(evidence_chain and evidence_chain.tool_calls)
        claims.append(Claim(
            statement=first_line,
            source=ClaimSource.TOOL_VERIFIED if has_tools else ClaimSource.UNVERIFIED,
            confidence=ClaimConfidence.MEDIUM if has_tools else ClaimConfidence.LOW,
            evidence=evidence_chain.tool_calls[:3] if evidence_chain else [],
        ))

    return claims


def _infer_source(evidence_text: str, evidence_chain: EvidenceChain = None) -> str:
    """从证据描述推断 claim 来源"""
    if not evidence_text:
        if evidence_chain and evidence_chain.tool_calls:
            return ClaimSource.TOOL_VERIFIED
        return ClaimSource.UNVERIFIED

    # 提到了工具名 → tool_verified
    tool_keywords = [
        "get_piece_attacks", "get_piece_defenders", "get_threats_to_piece",
        "get_piece_relations", "analyze_move", "compare_moves",
        "get_forcing_sequence", "simulate_move", "engine_deep_analysis",
        "engine_alternatives", "get_move_candidates",
    ]
    for kw in tool_keywords:
        if kw in evidence_text:
            return ClaimSource.TOOL_VERIFIED

    # 提到"工具"/"验证" → tool_verified
    if re.search(r"工具|验证|tool|verify", evidence_text, re.IGNORECASE):
        return ClaimSource.TOOL_VERIFIED

    return ClaimSource.REASONING


def _match_evidence_items(evidence_text: str, evidence_chain: EvidenceChain = None) -> List[EvidenceItem]:
    """从证据文本中匹配对应的 EvidenceItem"""
    if not evidence_chain:
        return []

    matched = []
    for item in evidence_chain.tool_calls:
        # 如果证据文本提到了该工具名，关联上
        if item.tool_name in evidence_text:
            matched.append(item)

    # 没匹配到具体的就返回前3个
    return matched if matched else evidence_chain.tool_calls[:3]


# ═══════════════════════════════════════════════════════════════════════════════
# 格式化：Claim → 合成器可读格式
# ═══════════════════════════════════════════════════════════════════════════════

def format_claims_for_synthesis(claims: List[Claim], expert_name: str) -> str:
    """
    将 Claim 列表格式化为合成器可消费的结构化文本。

    格式：
    【战术专家断言】
    CLAIM-1: 红车控制将门线 [来源:工具验证] [置信:高]
      证据: get_piece_attacks(红车) → 攻击(0,4),(0,5)
    CLAIM-2: 黑马被牵制 [来源:推理] [置信:中]
    """
    if not claims:
        return f"【{expert_name}断言】\n（无结构化断言）"

    source_label = {
        ClaimSource.TOOL_VERIFIED: "工具验证",
        ClaimSource.REASONING: "推理",
        ClaimSource.UNVERIFIED: "未验证",
    }
    conf_label = {
        ClaimConfidence.HIGH: "高",
        ClaimConfidence.MEDIUM: "中",
        ClaimConfidence.LOW: "低",
    }

    lines = [f"【{expert_name}断言】"]
    for i, claim in enumerate(claims, 1):
        src = source_label.get(claim.source, claim.source)
        conf = conf_label.get(claim.confidence, claim.confidence)
        lines.append(f"CLAIM-{i}: {claim.statement} [来源:{src}] [置信:{conf}]")
        for ev in claim.evidence[:2]:
            args_str = str(ev.arguments)[:80]
            result_str = ev.result_summary[:80] if ev.result_summary else "N/A"
            lines.append(f"  证据: {ev.tool_name}({args_str}) → {result_str}")

    return "\n".join(lines)
