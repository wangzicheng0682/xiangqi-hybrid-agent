---
name: 新人入门指南
type: guide
version: 1.0.0
date: 2026-04-01
owner: AI（自动维护）
changelog:
  - v1.0.0 (2026-04-01): 初始版本
---

# 新人入门指南

> 本文档帮助新开发者快速上手项目。

---

## 一、必读文档

按顺序阅读以下文档：

1. **本文档** - 快速了解项目
2. [DNA.md](../DNA.md) - 项目架构全貌
3. [STATE.md](../STATE.md) - 当前状态和待办
4. [前端指南](./frontend.md) - 如果你要做前端开发
5. [测试规范](./testing.md) - 如何运行测试

---

## 二、项目简介

### 是什么

象棋AI混合代理教学系统，让AI像教练一样**读懂棋局**、**讲解棋局**。

### 核心特性

- **零幻觉**：规则标签100%准确
- **教练式讲解**：基于事实的因果分析
- **Liquid Glass UI**：安静的、克制的设计语言
- **多专家并行**：战术/战略/引擎三专家协作

---

## 三、技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React 18 + TypeScript + Vite |
| 后端 | FastAPI + uvicorn |
| 棋盘规则 | python-xq + 自研规则引擎 |
| 引擎 | Pikafish (UCI协议) |
| 图数据库 | Neo4j 5.x |
| LLM | 通义千问 GLM-5 |

---

## 四、快速启动

### 1. 克隆项目

```bash
git clone <repo-url>
cd xiangqi-hybrid-agent
```

### 2. 安装后端依赖

```bash
pip install -r requirements.txt
```

### 3. 安装前端依赖

```bash
cd frontend
npm install
```

### 4. 启动服务

```bash
# 后端（端口8002）
python -m uvicorn api.main:app --host 0.0.0.0 --port 8002

# 前端（新窗口，端口3000/3001）
cd frontend && npm run dev
```

### 5. 访问

```
前端: http://localhost:3000
后端: http://localhost:8002
```

### 6. 运行测试

```bash
pytest -q
```

---

## 五、常见任务

### 添加新标签

1. 在 `core/rules/tactical_tags.py` 添加标签定义
2. 在 `core/rules/tactical_detector.py` 添加检测逻辑
3. 添加测试用例到 `tests/test_tactical_detector.py`
4. 更新 `docs/reference/tag_reference.md`

### 添加新API端点

1. 在 `api/main.py` 添加端点
2. 更新 `docs/reference/api_contract.md`
3. 前端在 `frontend/src/services/api.ts` 添加调用

### 添加新组件

1. 在 `frontend/src/components/` 创建组件
2. 使用Zustand管理状态
3. 更新本文档的组件列表

---

## 六、代码规范

### Python

- 使用类型注解
- 遵循PEP 8
- 每个函数有docstring

### TypeScript/React

- 使用TypeScript类型
- 组件使用函数式组件
- 优先内联样式

---

## 七、获取帮助

- 查看 [STATE.md](../STATE.md) 了解当前进度
- 查看 [plans/](../plans/) 了解未来的想法
- 查看 `tests/` 了解现有功能的测试方式

---

**文档版本**: v1.0.0
**最后更新**: 2026-04-01
