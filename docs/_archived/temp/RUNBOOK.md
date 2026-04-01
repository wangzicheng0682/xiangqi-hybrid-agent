# Sprint 1 运行手册 (RUNBOOK)

## 验收命令清单

### 1. 运行测试套件

```bash
python -m pytest tests/ -q
```

**预期输出**:
```
.....................                                                    [100%]
21 passed in 0.10s
```

**测试覆盖**:
- FEN校验测试 (10个)
- 棋盘渲染测试 (5个)
- Handler输出结构测试 (6个)

---

### 2. 启动Gradio应用

```bash
python apps/web-gradio/app.py
```

**预期输出**:
```
Running on local URL:  http://0.0.0.0:7860

To create a public link, set `share=True` in `launch()`.
```

**使用步骤**:
1. 打开浏览器访问 http://localhost:7860
2. 在FEN输入框输入FEN串，例如:
   ```
   rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1
   ```
3. 点击"🔍 分析局面"按钮
4. 查看生成的棋盘图片和分析讲解

---

### 3. 验证文档更新

```bash
cat docs/ITERATION_LOG.md
cat docs/TRACEABILITY.md
```

**检查要点**:
- ✅ ITERATION_LOG.md 包含Sprint 1完成记录
- ✅ TRACEABILITY.md 包含功能到代码到测试的映射

---

## 已通过证据

### 门禁1: pytest全绿 ✅
```
21 passed in 0.10s
```

### 门禁2: Gradio启动成功 ✅
- Gradio服务运行在 http://0.0.0.0:7860
- 界面可访问
- FEN输入 → 棋盘渲染 → 讲解输出 流程正常

### 门禁3: ITERATION_LOG已更新 ✅
- 记录了v0.1 Sprint 1完成
- 列出了所有交付物
- 包含验证命令

### 门禁4: TRACEABILITY已更新 ✅
- 6条可追溯记录
- 每条记录包含PRD/TECH引用、代码文件、测试证据
- Sprint 1验收门禁已记录

---

## 项目结构验证

```bash
# 检查核心文件存在
ls -la core/types/state.py
ls -la core/utils/fen_validator.py
ls -la core/render/board_renderer.py
ls -la apps/web-gradio/app.py
ls -la tests/test_*.py
```

**预期**: 所有文件存在且非空

---

## 依赖检查

```bash
pip list | grep -E "pytest|pillow|gradio"
```

**预期输出**:
```
gradio        X.X.X
Pillow        X.X.X
pytest        X.X.X
```

---

## 故障排查

### 问题1: ModuleNotFoundError: No module named 'core'
**解决**: 确保在项目根目录运行命令，或使用 `python apps/web-gradio/app.py` (已添加sys.path修复)

### 问题2: pytest找不到测试
**解决**: 确保使用 `python -m pytest tests/ -q` (指定tests目录)

### 问题3: Gradio无法启动
**解决**: 检查端口7860是否被占用，或修改app.py中的server_port参数

---

## 下一步

Sprint 1 MVP已完成，可以开始Sprint 2:
- 集成Pikafish引擎 (UCI协议)
- 集成Neo4j知识图谱
- 集成RAG向量检索
- 实现LangGraph Agent编排

参考: `docs/PRD.md` Sprint 2章节
