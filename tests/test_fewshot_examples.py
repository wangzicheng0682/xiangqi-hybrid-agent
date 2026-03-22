"""
Few-shot示例库测试

测试内容:
1. 示例数量和结构
2. Prompt生成函数
3. 数据完整性
"""

import pytest
from core.llm.fewshot_examples import (
    FewshotExample,
    ToolCall,
    GamePhase,
    OPENING_EXAMPLES,
    MIDDLEGAME_EXAMPLES,
    ENDGAME_EXAMPLES,
    FEWSHOT_EXAMPLES,
    get_fewshot_prompt,
    get_all_examples,
    get_example_by_id,
    get_examples_by_phase,
    format_example_for_display,
)


class TestFewshotExamplesStructure:
    """测试Few-shot示例结构"""

    def test_opening_examples_count(self):
        """测试开局示例数量"""
        assert len(OPENING_EXAMPLES) == 3

    def test_middlegame_examples_count(self):
        """测试中局示例数量"""
        assert len(MIDDLEGAME_EXAMPLES) == 3

    def test_endgame_examples_count(self):
        """测试残局示例数量"""
        assert len(ENDGAME_EXAMPLES) == 3

    def test_total_examples_count(self):
        """测试总示例数量"""
        total = sum(len(v) for v in FEWSHOT_EXAMPLES.values())
        assert total == 9

    def test_all_examples_have_required_fields(self):
        """测试所有示例都有必需字段"""
        required_fields = ['id', 'name', 'phase', 'fen', 'move_count',
                          'description', 'features', 'thinking', 'tool_calls', 'summary']

        for phase_examples in FEWSHOT_EXAMPLES.values():
            for example in phase_examples:
                for field in required_fields:
                    assert hasattr(example, field) or field in example.__dict__


class TestFewshotExampleDataClass:
    """测试FewshotExample数据类"""

    def test_example_has_tool_calls(self):
        """测试示例包含工具调用"""
        example = OPENING_EXAMPLES[0]
        assert len(example.tool_calls) > 0

    def test_tool_call_has_required_fields(self):
        """测试工具调用有必需字段"""
        example = OPENING_EXAMPLES[0]
        tc = example.tool_calls[0]

        assert hasattr(tc, 'step')
        assert hasattr(tc, 'tool')
        assert hasattr(tc, 'input_params')
        assert hasattr(tc, 'output')
        assert hasattr(tc, 'reason')

    def test_example_phase_is_correct(self):
        """测试示例阶段正确"""
        for example in OPENING_EXAMPLES:
            assert example.phase == GamePhase.OPENING

        for example in MIDDLEGAME_EXAMPLES:
            assert example.phase == GamePhase.MIDDLEGAME

        for example in ENDGAME_EXAMPLES:
            assert example.phase == GamePhase.ENDGAME


class TestGetFewshotPrompt:
    """测试Prompt生成函数"""

    def test_get_opening_prompt(self):
        """测试获取开局Prompt"""
        prompt = get_fewshot_prompt("opening", count=1)

        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "示例" in prompt

    def test_get_middlegame_prompt(self):
        """测试获取中局Prompt"""
        prompt = get_fewshot_prompt("middlegame", count=1)

        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_get_endgame_prompt(self):
        """测试获取残局Prompt"""
        prompt = get_fewshot_prompt("endgame", count=1)

        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_get_multiple_examples(self):
        """测试获取多个示例"""
        prompt = get_fewshot_prompt("opening", count=2)

        # 应该包含两个示例的标识
        assert prompt.count("示例") >= 2

    def test_get_empty_for_invalid_phase(self):
        """测试无效阶段返回空"""
        prompt = get_fewshot_prompt("invalid_phase", count=1)

        assert prompt == ""


class TestGetAllExamples:
    """测试获取所有示例函数"""

    def test_get_all_examples_returns_list(self):
        """测试返回列表"""
        examples = get_all_examples()

        assert isinstance(examples, list)
        assert len(examples) == 9

    def test_all_examples_are_fewshot_example_type(self):
        """测试所有示例都是FewshotExample类型"""
        examples = get_all_examples()

        for example in examples:
            assert isinstance(example, FewshotExample)


class TestGetExampleById:
    """测试根据ID获取示例"""

    def test_get_example_by_id_1(self):
        """测试获取ID=1的示例"""
        example = get_example_by_id(1)

        assert example is not None
        assert example.id == 1
        assert "中炮" in example.name

    def test_get_example_by_id_4(self):
        """测试获取ID=4的示例（中局第一个）"""
        example = get_example_by_id(4)

        assert example is not None
        assert example.id == 4
        assert example.phase == GamePhase.MIDDLEGAME

    def test_get_example_by_invalid_id(self):
        """测试无效ID返回None"""
        example = get_example_by_id(999)

        assert example is None


class TestGetExamplesByPhase:
    """测试根据阶段获取示例"""

    def test_get_opening_examples(self):
        """测试获取开局示例"""
        examples = get_examples_by_phase("opening")

        assert len(examples) == 3
        for ex in examples:
            assert ex.phase == GamePhase.OPENING

    def test_get_middlegame_examples(self):
        """测试获取中局示例"""
        examples = get_examples_by_phase("middlegame")

        assert len(examples) == 3

    def test_get_endgame_examples(self):
        """测试获取残局示例"""
        examples = get_examples_by_phase("endgame")

        assert len(examples) == 3


class TestFormatExampleForDisplay:
    """测试格式化显示函数"""

    def test_format_example_returns_string(self):
        """测试返回字符串"""
        example = OPENING_EXAMPLES[0]
        formatted = format_example_for_display(example)

        assert isinstance(formatted, str)
        assert len(formatted) > 0

    def test_format_contains_example_name(self):
        """测试格式化包含示例名称"""
        example = OPENING_EXAMPLES[0]
        formatted = format_example_for_display(example)

        assert example.name in formatted

    def test_format_contains_thinking(self):
        """测试格式化包含思维链"""
        example = OPENING_EXAMPLES[0]
        formatted = format_example_for_display(example)

        # 应该包含思维链相关内容
        assert "思维" in formatted or "阶段" in formatted

    def test_format_contains_summary(self):
        """测试格式化包含总结"""
        example = OPENING_EXAMPLES[0]
        formatted = format_example_for_display(example)

        assert "总结" in formatted or "教练建议" in formatted


class TestExampleContent:
    """测试示例内容质量"""

    def test_all_fen_strings_valid(self):
        """测试所有FEN字符串格式有效"""
        for example in get_all_examples():
            fen = example.fen
            # 基本检查：FEN应该包含棋盘部分
            assert '/' in fen or ' ' in fen
            assert len(fen) > 20

    def test_all_thinking_not_empty(self):
        """测试所有思维链非空"""
        for example in get_all_examples():
            assert len(example.thinking) > 50

    def test_all_summary_not_empty(self):
        """测试所有总结非空"""
        for example in get_all_examples():
            assert len(example.summary) > 50

    def test_all_tool_calls_valid(self):
        """测试所有工具调用有效"""
        valid_tools = [
            "analyze_position_strategy",
            "engine_alternatives",
            "engine_deep_analysis",
            "get_piece_attacks",
            "get_piece_defenders",
            "get_threats_to_piece",
            "get_piece_relations",
            "analyze_move",
            "compare_moves",
            "get_forcing_sequence",
        ]

        for example in get_all_examples():
            for tc in example.tool_calls:
                assert tc.tool in valid_tools, f"Invalid tool: {tc.tool}"


class TestExampleUniqueness:
    """测试示例唯一性"""

    def test_all_ids_unique(self):
        """测试所有ID唯一"""
        examples = get_all_examples()
        ids = [ex.id for ex in examples]

        assert len(ids) == len(set(ids))

    def test_all_names_unique(self):
        """测试所有名称唯一"""
        examples = get_all_examples()
        names = [ex.name for ex in examples]

        assert len(names) == len(set(names))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
