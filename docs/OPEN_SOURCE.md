---
name: 开源代码与组件使用说明
type: reference
version: 2.0
date: 2026-04-01
owner: AI（自动维护）
changelog:
  - v2.0 (2026-04-01): 改为"用在哪些组件"结构
  - v1.0 (2026-04-01): 初稿
---

# 开源代码与组件使用情况说明

> 本文档记录本项目使用的开源代码及其在各模块中的使用情况。

---

## 一、前端（React + TypeScript）

### 1.1 React 生态

| 开源组件 | 许可证 | 用在哪些模块 |
|----------|--------|--------------|
| **React** | MIT | 全局基础框架，所有UI组件依赖 |
| **React DOM** | MIT | 前端路由与DOM渲染 |
| **React Markdown** | MIT | `AgentThinkingPanel.tsx` — 渲染专家的Markdown格式思考内容 |
| **Framer Motion** | MIT | `AgentCardFlip.tsx`、`AgentDebutPanel.tsx`、`DeepAnalysisPanel.tsx`、`App.tsx` — 扑克牌翻面动画、专家登场动画、布局弹簧动画 |
| **Zustand** | MIT | `useGameStore.ts`、`useAgentStore.ts`、`useGlassParamsStore.ts` — 游戏状态、Agent动画状态、液态玻璃参数的三种状态管理 |

### 1.2 UI与样式

| 开源组件 | 许可证 | 用在哪些模块 |
|----------|--------|--------------|
| **Tailwind CSS** | MIT | `index.css` — 全局样式框架，提供基础样式原子类 |
| **Axios** | MIT | `services/api.ts` — 统一封装所有后端API调用（快速分析、深度分析、标签检测等） |
| **Leva** | MIT | `LiquidGlassApp.tsx` — 液态玻璃参数实时调参面板（折射强度、模糊半径、色散系数等） |

### 1.3 自研渲染引擎

> 以下模块为**完全自主研发**，未直接使用开源代码：

| 自研模块 | 文件 | 功能说明 |
|----------|------|----------|
| **Liquid Glass渲染引擎** | `LiquidGlassApp.tsx` + 4个GLSL着色器 | WebGL四步管线渲染苹果液态玻璃效果 |
| **专家扑克牌系统** | `AgentCardFlip.tsx`、`ExpertCard.tsx`、`ThinkingStream.tsx` | 三专家并行分析的卡片动画与流式思维展示 |
| **引擎评分图** | `EngineChart.tsx` | 纯SVG绘制Pikafish评分折线图，无外部图表库依赖 |

---

## 二、后端（Python + FastAPI）

### 2.1 Web框架

| 开源组件 | 许可证 | 用在哪些模块 |
|----------|--------|--------------|
| **FastAPI** | MIT | `api/main.py` — 所有REST API端点（`/api/analyze/*`、`/api/move`、`/api/tactical-tags`等），提供同步响应与SSE流式输出 |
| **Uvicorn** | BSD | 生产服务器，运行 `uvicorn api.main:app` 启动后端 |
| **python-multipart** | Apache 2.0 | `api/main.py` — PGN棋谱文件上传端点 |

### 2.2 Agent与LLM编排

| 开源组件 | 许可证 | 用在哪些模块 |
|----------|--------|--------------|
| **LangGraph** | MIT | `multi_agent_orchestrator.py` — 多专家协调器的状态机编排，支持三专家并行执行与结果合成 |
| **LangChain Core** | MIT | `base_expert.py`、`agent_tools.py` — 工具定义结构化、LLM调用封装 |

### 2.3 数据与图像

| 开源组件 | 许可证 | 用在哪些模块 |
|----------|--------|--------------|
| **Pillow** | HPND | `core/semantic/board_structure_parser.py` — 图片尺寸处理、棋盘截图处理 |
| **Matplotlib** | PSF | `api/main.py` — `/api/review` 复盘报告生成时的图表绘制 |
| **Neo4j** (社区版) | GPL v3 | `core/kg/neo4j_kg.py` — 19万局历史棋谱存储与相似局面检索 |
| **Pikafish** | GPL v3 | `core/engine/pikafish_engine.py` — UCI协议封装，提供局面评估、候选走法、深度分析 |

---

## 三、参考学习的开源项目

以下项目为**学习参考**，未直接复制代码，源码为自主实现：

| 项目 | 许可证 | 学习内容 | 实现方式 |
|------|--------|----------|----------|
| **liquid-glass-js** (dashersw) | MIT | WebGL折射模型数学原理（SDF形状、菲涅尔系数） | 完全自主实现着色器（617行GLSL） |
| **liquid-glass-studio** (charyyyyin) | MIT | 参数控制面板UI布局与预设持久化架构 | 自主实现Zustand+Leva持久化系统 |

---

## 四、许可证汇总

| 许可证 | 级别 | 组件 |
|--------|------|------|
| MIT | 宽松 | React, Framer Motion, Zustand, Axios, Leva, React Markdown, FastAPI, LangGraph, LangChain Core |
| Apache 2.0 | 中等 | python-multipart |
| BSD | 宽松 | Uvicorn |
| HPND | 宽松 | Pillow |
| PSF | 宽松 | Matplotlib |
| GPL v3 | 传染 | Neo4j (社区版), Pikafish |

---

## 五、开源声明（可直接复制）

```
本项目使用了以下开源代码与组件：

前端框架与UI：
- React (MIT License) — 全局基础框架
- Framer Motion (MIT License) — 扑克牌翻面动画、专家登场动画
- Zustand (MIT License) — 游戏状态、Agent状态、玻璃参数的状态管理
- Leva (MIT License) — 液态玻璃参数实时调参面板
- Axios (MIT License) — 后端API统一调用
- React Markdown (MIT License) — 专家思考内容渲染
- Tailwind CSS (MIT License) — 全局样式框架

后端框架：
- FastAPI (MIT License) — REST API与SSE流式响应
- Uvicorn (BSD License) — ASGI服务器
- LangGraph (MIT License) — 多专家Agent协调编排
- LangChain Core (MIT License) — LLM调用封装与工具定义

数据与服务：
- Neo4j社区版 (GPL v3) — 19万局棋谱知识图谱
- Pikafish (GPL v3) — 中国象棋UCI引擎
- Pillow (HPND) — 图像处理
- Matplotlib (PSF) — 数据可视化

液态玻璃渲染引擎：完全自主研发
（中国象棋规则引擎、标签检测系统、多专家Agent系统：完全自主研发）
```

---

**文档版本**: v2.0
**最后更新**: 2026-04-01
