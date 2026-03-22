# Gemini前端设计协作请求

**发送者**: Kimi-K2.5 (后端开发)  
**接收者**: Gemini (前端设计)  
**日期**: 2026-03-09  
**主题**: 象棋AI混合代理系统 - 前端设计请求

---

## 一、项目概述

### 项目名称
象棋AI混合代理教学与对弈系统

### 项目目标
参加2026年中国大学生计算机设计大赛，打造天天象棋级别的商业级象棋AI应用。

### 核心特性
1. **战术精确计算** - Pikafish引擎（象棋Stockfish）
2. **知识图谱** - Neo4j存储790万+历史对局
3. **智能讲解** - Qwen-Max大模型
4. **多模态分析** - Qwen-VL-Max视觉模型

---

## 二、后端API（已完成）

### 2.1 Agent分析API
```python
from core.agent import XiangqiAgent

agent = XiangqiAgent()
result = agent.analyze(
    fen="rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1",
    board=[['r','n','b',...],  # 10x9棋盘数组
    iccs_moves=["h2e2", "h9g7"],  # 走法历史
    last_move_info={"from_pos": "h2", "to_pos": "e2"},  # 最后一步
    use_vision=True  # 是否使用视觉分析
)

# 返回结果
{
    "fen": "局面FEN",
    "explanation": "Markdown格式的讲解",
    "engine_result": {"bestmove": "h2e2", "score": 0.5, "depth": 15},
    "kg_result": {"opening_name": "中炮开局", "win_rate": 60.0},
    "vision_result": {"description": "多模态分析结果"}
}
```

### 2.2 夣盘报告API
```python
from core.review import (
    generate_review_report,
    generate_score_chart,
    GameRecord
)

# 生成复盘报告
game = GameRecord(
    red_player="红方",
    black_player="黑方",
    result="1-0",
    iccs_moves=["h2e2", "h9g7", "c3c4"]
)
report = generate_review_report(game, scores=[0, 100, -200, 300])

# 生成胜率曲线图
chart_image = generate_score_chart(
    scores=[0, 100, -200, 300],
    turning_points=[2, 4],  # 转折点
    blunders=[2]  # 劣着
)
```

### 2.3 规则引擎API
```python
from core.rules.xiangqi_rules import get_legal_moves, is_in_check

# 获取合法走法
legal_moves = get_legal_moves(board, row, col)
# 返回: [(to_row1, to_col1), (to_row2, to_col2), ...]

# 检查是否被将军
in_check = is_in_check(board, red_to_move=True)
```

### 2.4 数据格式

**棋盘数组** (10行9列):
```python
board = [
    ['r', 'n', 'b', 'a', 'k', 'a', 'b', 'n', 'r'],  # 第0行（黑方底线）
    ['', '', '', '', '', '', '', '', ''],  # 第1行
    ['', 'c', '', '', '', '', '', 'c', ''],  # 第2行
    ['p', '', 'p', '', 'p', '', 'p', '', 'p'],  # 第3行
    ['', '', '', '', '', '', '', '', ''],  # 第4行（楚河）
    ['', '', '', '', '', '', '', '', ''],  # 第5行（汉界）
    ['P', '', 'P', '', 'P', '', 'P', '', 'P'],  # 第6行
    ['', 'C', '', '', '', '', '', 'C', ''],  # 第7行
    ['', '', '', '', '', '', '', '', ''],  # 第8行
    ['R', 'N', 'B', 'A', 'K', 'A', 'B', 'N', 'R'],  # 第9行（红方底线）
]

# 大写=红方棋子, 小写=黑方棋子
# K/k=将帅, A/a=士, B/b=象, R/r=车, C/c=炮, N/n=马, P/p=兵卒
```

**ICCS走法格式**:
- `h2e2` = 从h2走到e2（炮二平五）
- 列号: a-i（从左到右）
- 行号: 0-9（从下到上，红方视角）

---

## 三、前端需求

### 3.1 三大模式

#### 模式1: 下棋谱 (PGN模式)
**功能**:
- 上传PGN文件
- 显示对局列表
- 逐步浏览对局
- 每步显示AI分析

**交互**:
- 文件上传 → 解析PGN → 显示对局列表
- 选择对局 → 显示棋盘
- 点击"下一步"/"上一步" → 更新棋盘和分析

#### 模式2: 人机对战 (Play模式)
**功能**:
- 点击棋盘走棋
- 显示可走位置
- AI分析当前局面
- AI对战模式（AI自动回应）

**交互**:
- 点击己方棋子 → 高亮显示可走位置
- 点击目标位置 → 移动棋子
- 点击"分析" → 显示AI分析结果
- 点击"新对局" → 重置棋盘

#### 模式3: 复盘分析 (Review模式)
**功能**:
- 输入走法记录
- 生成胜率曲线
- 生成复盘报告
- 标注转折点和失误

**交互**:
- 输入走法 → 点击分析 → 显示胜率曲线和报告

### 3.2 设计风格

**中国风主题**:
- 主色: 朱红 (#C41E3A)
- 辅色: 墨黑 (#2C3E50)
- 点缀: 鎏金 (#D4AF37)
- 背景: 宣纸白 (#F5F5DC)

**视觉元素**:
- 宣纸纹理背景
- 楚河汉界
- 3D立体棋子
- 鎏金边框

### 3.3 性能要求
- 响应时间 < 3秒
- 60fps流畅动画
- 支持桌面和平板

---

## 四、需要Gemini设计的内容

### 4.1 技术栈选择
请选择适合的前端技术栈，要求:
- **不使用Gradio**
- 支持复杂交互（棋盘点击、拖拽）
- 良好的动画性能
- 易于部署

建议考虑:
- React + TypeScript
- Vue 3 + TypeScript
- 或其他现代框架

### 4.2 需要输出的设计

#### A. 整体架构设计
- 目录结构
- 组件划分
- 状态管理方案
- 路由方案

#### B. 核心组件设计
1. **棋盘组件** (ChessBoard)
   - 如何渲染棋盘和棋子
   - 如何处理点击交互
   - 如何显示可走位置
   - 动画效果

2. **分析面板组件** (AnalysisPanel)
   - 如何展示引擎分析
   - 如何展示知识图谱数据
   - 如何展示多模态分析

3. **走法列表组件** (MoveList)
   - 如何展示走法历史
   - 如何支持点击跳转

4. **胜率曲线组件** (ScoreChart)
   - 用什么图表库
   - 如何标注转折点

#### C. 交互流程设计
- 走棋的完整交互流程
- 模式切换的交互流程
- 错误处理和提示

#### D. 样式设计
- CSS变量定义
- 响应式布局方案
- 动画效果实现

### 4.3 输出格式

请按以下格式输出:

```
## 1. 技术栈选择
[说明选择的框架和库]

## 2. 目录结构
[列出前端目录结构]

## 3. 核心组件代码
### 3.1 ChessBoard.tsx
[棋盘组件代码]

### 3.2 AnalysisPanel.tsx
[分析面板代码]

### 3.3 其他组件...
[代码]

## 4. 样式文件
[CSS/样式代码]

## 5. 状态管理
[状态管理代码]

## 6. API集成
[如何调用后端API]
```

---

## 五、后端服务信息

### 5.1 现有服务
- **Gradio服务**: http://localhost:7865 (旧版，可参考)
- **后端模块**: `core/` 目录下

### 5.2 API调用方式
可以直接调用Python模块:
```python
from core.agent import XiangqiAgent
from core.review import generate_review_report
from core.rules.xiangqi_rules import get_legal_moves
```

或者我可以创建REST API端点，请告诉我你的选择。

---

## 六、时间线

- **当前**: Week 4
- **提交截止**: 2026-04-09（约1个月后）
- **前端开发时间**: 建议3-5天

---

## 七、联系方式

- **后端开发者**: Kimi-K2.5 (Trae IDE)
- **前端开发者**: Gemini
- **协调人**: 用户

---

**Gemini, 请根据以上信息设计前端方案，输出代码。 我将负责执行你的设计。**
