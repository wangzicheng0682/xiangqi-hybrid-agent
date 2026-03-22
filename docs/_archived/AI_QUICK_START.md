# AI全自动开发 - 快速开始指南

**版本**: v1.0
**最后更新**: 2026-03-09
**用途**: AI开发助手快速上手指南

---

## 🚀 AI全自动开发 - 3步快速开始

### 步骤1: 读取状态（唯一必读）
```bash
# AI每次会话开始时，只需读取1个文件
cat docs/STATE.md
```

**内容**:
- 当前版本和Sprint
- 当前任务列表
- 项目状态总结
- 技术债务清单

### 步骤2: 确认任务
```
根据STATE.md的"当前任务"确认要做什么
```

### 步骤3: 开始工作
```
直接执行任务，无需更多文档读取
```

---

## 🤖 AI开发工作流

### 开机流程
```python
# 伪代码
def ai_session_start():
    # 步骤1：读取状态（唯一必读）
    state = read_state("docs/STATE.md")

    # 步骤2：确认任务
    current_task = state.current_task

    # 步骤3：开始工作
    start_working(current_task)
```

### 关机流程
```python
# 伪代码
def ai_session_end():
    # 步骤1：更新状态
    update_state("docs/STATE.md", changes)

    # 步骤2：更新追溯（如有新功能）
    if new_features:
        update_traceability("docs/TRACEABILITY.md")

    # 步骤3：运行自动化门禁
    run_gates()

    # 步骤4：报告
    generate_report()
```

---

## 🛠️ 自动化工具

### 综合门禁检查
```bash
# 一键检查所有门禁
bash scripts/gates/check.sh
```

**检查项**:
- ✅ pytest测试
- ✅ 文档同步
- ⚠️  mypy类型检查
- ⚠️  black格式检查
- ⚠️  代码复杂度
- ⚠️  单文件大小

### 文档检查
```bash
# 单独检查文档
python scripts/gates/check_docs.py
```

### 代码检查
```bash
# 单独检查代码
python scripts/gates/check_code.py
```

---

## 📚 核心文档说明

### docs/STATE.md（AI必读）
**用途**: 当前项目状态
**内容**:
- 项目概况
- 当前Sprint和任务
- 技术债务清单
- 文档状态

**更新频率**: 每次会话结束时更新
**AI读取时机**: 每次会话开始必须读取

---

## ⚠️ 重要提醒

### 不要读取的文档
- ❌ **不要读取PRD.md、TECH.md** - 内容已合并到新文档
- ❌ **不要读取ITERATION_LOG.md** - 内容过长，已归档
- ❌ **不要读取AI_SUSTAINABLE_FRAMEWORK.md** - 内容已合并到新文档

### 必须读取的文档
- ✅ **只读取STATE.md** - 包含所有必要信息

### 更新文档的时机
- 每次会话结束前：更新docs/STATE.md
- 完成新功能后：更新docs/TRACEABILITY.md
- 每次Sprint开始：更新docs/ROADMAP.md

---

## 🎯 质量保证

### 提交前门禁
```bash
# 运行自动化门禁
bash scripts/gates/check.sh

# 如果所有强制门禁通过，可以提交
# 如果有门禁失败，修复后重试
```

### 人工检查清单（可选）
- [ ] 新功能有对应测试
- [ ] 代码符合规范
- [ ] 文档已更新

---

## 📞 常用命令

```bash
# 测试
pytest -q

# 启动服务
python apps/web-gradio/app.py

# 类型检查
mypy xiangqi/

# 代码格式化
black xiangqi/

# 代码检查
ruff check xiangqi/

# 综合门禁
bash scripts/gates/check.sh

# 文档检查
python scripts/gates/check_docs.py

# 代码检查
python scripts/gates/check_code.py
```

---

## 🔧 配置管理

### 统一配置
```python
# config/settings.py
from config.settings import settings

# 使用配置
engine_path = settings.engine_path
llm_api_key = settings.llm_api_key
```

### 环境变量
```bash
# 创建 .env 文件
cat > .env << EOF
ENGINE_PATH=data/engine/pikafish-avx2.exe
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
LLM_API_KEY=your_api_key
EOF
```

---

## 🎉 总结

### T0主路线
```
FEN/棋盘输入 → 局面结构解析 → 棋理检索 → 引擎分析 → LLM讲解 → 前端展示
```

### 核心原则
- 系统是否完整
- 讲解是否贴盘面
- 演示是否可信

---

**文档版本**: v1.0
**最后更新**: 2026-03-09
**维护者**: AI开发团队
