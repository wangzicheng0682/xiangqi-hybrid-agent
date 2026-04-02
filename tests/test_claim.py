"""
Phase 2 - 证据裁决化测试

覆盖：
- Claim 数据结构
- Claim 解析器（显式标记 + 回退格式）
- 证据链构建
- 工具输出回填
- ExpertResult v2 字段
- 合成器断言格式化
"""

import pytest
from core.llm.claim import (
    Claim, ClaimSource, ClaimConfidence,
    EvidenceChain, EvidenceItem,
    parse_claims, format_claims_for_synthesis,
)
from core.llm.experts.base_expert import (
    ExpertResult, _build_evidence_chain, _backfill_tool_result,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Claim 解析 - 显式标记格式
# ═══════════════════════════════════════════════════════════════════════════════

class TestClaimParserExplicit:
    """测试 [CLAIM][EVIDENCE][CONFIDENCE] 标记解析"""

    def test_single_claim(self):
        content = """
## 3 总结
[CLAIM] 红车d8控制将门线，黑将无法逃离
[EVIDENCE] get_piece_attacks(红车) 显示攻击范围覆盖黑将所在行
[CONFIDENCE] 高
"""
        claims = parse_claims(content)
        assert len(claims) == 1
        assert "红车" in claims[0].statement
        assert claims[0].source == ClaimSource.TOOL_VERIFIED
        assert claims[0].confidence == ClaimConfidence.HIGH

    def test_multiple_claims(self):
        content = """
[CLAIM] 红车控制将门
[EVIDENCE] get_piece_attacks 验证
[CONFIDENCE] 高

[CLAIM] 黑马被牵制
[EVIDENCE] simulate_move 验证移动后被将军
[CONFIDENCE] 高

[CLAIM] 局面红方大优
[EVIDENCE] 推理得出
[CONFIDENCE] 中
"""
        claims = parse_claims(content)
        assert len(claims) == 3
        assert claims[0].source == ClaimSource.TOOL_VERIFIED
        assert claims[1].source == ClaimSource.TOOL_VERIFIED
        assert claims[2].source == ClaimSource.REASONING  # 没有工具关键词

    def test_chinese_confidence(self):
        """测试中文置信度标记"""
        content = "[CLAIM] 局面均势\n[EVIDENCE] 纯推理\n[CONFIDENCE] 低"
        claims = parse_claims(content)
        assert len(claims) == 1
        assert claims[0].confidence == ClaimConfidence.LOW

    def test_statement_truncated(self):
        """超长断言被截断"""
        long = "A" * 300
        content = f"[CLAIM] {long}\n[EVIDENCE] 无\n[CONFIDENCE] 中"
        claims = parse_claims(content)
        assert len(claims[0].statement) <= 200


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Claim 解析 - 回退格式
# ═══════════════════════════════════════════════════════════════════════════════

class TestClaimParserFallback:
    """测试从传统【节标题】格式回退提取"""

    def test_tactics_finding(self):
        content = "【战术发现】红车沉底将军形成绝杀\n【对手处境】无解\n【结论可信度】高"
        ev = EvidenceChain(tool_calls=[
            EvidenceItem("get_piece_attacks", {"piece": "红车"}, "攻击(0,4)", True),
        ])
        claims = parse_claims(content, ev)
        assert len(claims) >= 1
        assert "红车沉底" in claims[0].statement
        assert claims[0].source == ClaimSource.TOOL_VERIFIED

    def test_strategy_finding(self):
        content = "【战略评估】红方子力优势明显\n【结论可信度】中"
        claims = parse_claims(content)
        assert len(claims) >= 1
        assert claims[0].confidence == ClaimConfidence.MEDIUM

    def test_no_markers_fallback_to_first_line(self):
        """完全无标记时取第一行"""
        content = "这个局面红方大优，因为子力多一车"
        claims = parse_claims(content)
        assert len(claims) == 1
        assert "红方大优" in claims[0].statement
        assert claims[0].source == ClaimSource.UNVERIFIED

    def test_empty_content(self):
        claims = parse_claims("")
        assert claims == []

    def test_none_content(self):
        claims = parse_claims(None)
        assert claims == []


# ═══════════════════════════════════════════════════════════════════════════════
# 3. 证据链构建
# ═══════════════════════════════════════════════════════════════════════════════

class TestEvidenceChain:
    """测试 EvidenceChain 和 _build_evidence_chain"""

    def test_build_from_tool_calls_log(self):
        log = [
            {"name": "get_piece_attacks", "arguments": {"piece": "红车"}, "result_summary": "攻击3格", "success": True},
            {"name": "analyze_move", "arguments": {"move": "c2c7"}, "result_summary": "好棋", "success": True},
        ]
        chain = _build_evidence_chain(log)
        assert len(chain.tool_calls) == 2
        assert chain.tool_calls[0].tool_name == "get_piece_attacks"
        assert chain.tool_calls[0].result_summary == "攻击3格"

    def test_find_evidence_for(self):
        chain = EvidenceChain(tool_calls=[
            EvidenceItem("get_piece_attacks", {}, "x", True),
            EvidenceItem("analyze_move", {}, "y", True),
            EvidenceItem("get_piece_attacks", {}, "z", True),
        ])
        results = chain.find_evidence_for("get_piece_attacks")
        assert len(results) == 2

    def test_build_without_result_summary(self):
        """没有 result_summary 的旧格式也能构建"""
        log = [{"name": "get_piece_attacks", "arguments": {"piece": "红车"}}]
        chain = _build_evidence_chain(log)
        assert len(chain.tool_calls) == 1
        assert chain.tool_calls[0].result_summary == ""


# ═══════════════════════════════════════════════════════════════════════════════
# 4. 工具输出回填
# ═══════════════════════════════════════════════════════════════════════════════

class TestBackfillToolResult:
    """测试 _backfill_tool_result"""

    def test_backfill_basic(self):
        log = [
            {"name": "get_piece_attacks", "round": 0, "arguments": {"piece": "红车"}},
        ]
        result = {"success": True, "message": "攻击(0,4),(0,5),(1,4)"}
        _backfill_tool_result(log, "get_piece_attacks", result)
        assert log[0]["result_summary"] == "攻击(0,4),(0,5),(1,4)"
        assert log[0]["success"] is True

    def test_backfill_skips_already_filled(self):
        log = [
            {"name": "get_piece_attacks", "round": 0, "arguments": {}, "result_summary": "old"},
            {"name": "get_piece_attacks", "round": 1, "arguments": {}},
        ]
        _backfill_tool_result(log, "get_piece_attacks", {"success": True, "message": "new"})
        assert log[0]["result_summary"] == "old"  # 不覆盖
        assert log[1]["result_summary"] == "new"  # 回填最新

    def test_backfill_from_data_field(self):
        """当 message 为空时从 data 截取"""
        log = [{"name": "analyze_move", "round": 0, "arguments": {}}]
        result = {"success": True, "data": {"score": 320, "best": "c2c7"}}
        _backfill_tool_result(log, "analyze_move", result)
        assert "score" in log[0]["result_summary"]


# ═══════════════════════════════════════════════════════════════════════════════
# 5. ExpertResult v2 字段
# ═══════════════════════════════════════════════════════════════════════════════

class TestExpertResultV2:
    """测试 ExpertResult 新增的 claims 和 evidence_chain 字段"""

    def test_default_empty(self):
        r = ExpertResult(expert_name="tactics", finding="test", details="test")
        assert r.claims == []
        assert r.evidence_chain is None

    def test_with_claims(self):
        claim = Claim(statement="红车控制将门", source=ClaimSource.TOOL_VERIFIED, confidence=ClaimConfidence.HIGH)
        chain = EvidenceChain(tool_calls=[
            EvidenceItem("get_piece_attacks", {"piece": "红车"}, "攻击将门", True),
        ])
        r = ExpertResult(
            expert_name="tactics",
            finding="红车控制将门",
            details="详情...",
            claims=[claim],
            evidence_chain=chain,
        )
        assert len(r.claims) == 1
        assert r.claims[0].source == ClaimSource.TOOL_VERIFIED
        assert len(r.evidence_chain.tool_calls) == 1


# ═══════════════════════════════════════════════════════════════════════════════
# 6. 合成器格式化
# ═══════════════════════════════════════════════════════════════════════════════

class TestClaimFormatting:
    """测试 format_claims_for_synthesis"""

    def test_format_with_claims(self):
        claims = [
            Claim(
                statement="红车控制将门",
                source=ClaimSource.TOOL_VERIFIED,
                confidence=ClaimConfidence.HIGH,
                evidence=[EvidenceItem("get_piece_attacks", {"piece": "红车"}, "攻击(0,4)", True)],
            ),
            Claim(
                statement="黑马被牵制",
                source=ClaimSource.REASONING,
                confidence=ClaimConfidence.MEDIUM,
            ),
        ]
        text = format_claims_for_synthesis(claims, "战术专家")
        assert "【战术专家断言】" in text
        assert "CLAIM-1" in text
        assert "CLAIM-2" in text
        assert "工具验证" in text
        assert "推理" in text

    def test_format_empty(self):
        text = format_claims_for_synthesis([], "战术专家")
        assert "无结构化断言" in text

    def test_evidence_preview_truncated(self):
        """证据预览不会过长"""
        claim = Claim(
            statement="test",
            evidence=[EvidenceItem("tool", {"x": "A" * 200}, "R" * 200, True)],
        )
        text = format_claims_for_synthesis([claim], "test")
        # 每行不应超过合理长度
        for line in text.split("\n"):
            assert len(line) < 300
