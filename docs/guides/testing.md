---
name: 测试规范
type: guide
version: 1.0.0
date: 2026-04-01
owner: AI（自动维护）
changelog:
  - v1.0.0 (2026-04-01): 初始版本
---

# 测试规范

> 本文档定义项目的测试规范和最佳实践。

---

## 一、测试目录结构

```
tests/
├── test_tactical_detector.py    # 标签检测测试
├── test_golden_positions.py    # 黄金局面测试
├── test_agent.py               # Agent工作流测试
├── test_review.py               # 复盘报告测试
├── test_fewshot_examples.py    # Few-shot示例测试
├── test_handler_output.py     # Handler输出测试
├── golden_positions.py          # 测试数据
└── pytest.ini                   # pytest配置
```

---

## 二、运行测试

```bash
# 运行所有测试
pytest -q

# 运行特定测试文件
pytest tests/test_tactical_detector.py -v

# 运行特定测试类
pytest tests/test_agent.py::TestXiangqiAgent -v
```

---

## 三、测试规范

### 每个模块必须有测试

| 模块 | 测试文件 | 覆盖要求 |
|------|----------|----------|
| 规则引擎 | `test_tactical_detector.py` | 38个标签全覆盖 |
| Agent | `test_agent.py` | 工作流测试 |
| 复盘 | `test_review.py` | 功能测试 |
| Few-shot | `test_fewshot_examples.py` | 示例库测试 |

### 黄金局面测试

```python
def test_golden_position_GP001():
    """测试：将军局面"""
    fen = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"
    detector = TacticalDetector()
    result = detector.detect_static(fen)

    # 验证将军标签被检测
    assert has_tag(result, "is_check")
```

---

## 四、提交前检查

- [ ] `pytest -q` 全绿
- [ ] 新功能有对应测试
- [ ] 测试不依赖外部服务（Mock）

---

**文档版本**: v1.0.0
**最后更新**: 2026-04-01
