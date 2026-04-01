# 前后端联合重构架构方案
## 商业级天天象棋级别实现

**版本**: v1.0
**日期**: 2026-03-09
**目标**: 从玩具级架构升级为商业级，保持后端graph/agent完整，重新设计前端交互

---

## 📋 执行摘要

### 重构目标
1. **后端保持完整**: 所有LangGraph节点（preprocess → engine → kg → rag → vision → explain）必须保留
2. **前端彻底重构**: 从单文件1037行app.py拆分为模块化架构
3. **商业级体验**: 实现天天象棋级别的UI/UX，包括：
   - 中国风设计（朱红/墨黑/鎏金/翠绿/宣纸白）
   - 60fps流畅动画（贝塞尔曲线）
   - 专业音效反馈（不同棋子不同声音）
   - 实时分析（热力图、最佳着法高亮）
   - 响应式布局（桌面/平板/手机）

### 关键约束
- ❌ **不能减少功能**: 所有agent节点必须保留
- ❌ **不能简化接口**: BaseEngine/BaseKG/BaseRAG接口必须完整
- ✅ **必须提升体验**: UI/UX要达到天天象棋水平
- ✅ **必须模块化**: 代码结构要清晰，AI易于维护

---

## 🏗️ 架构总览

### 系统分层架构

```
┌─────────────────────────────────────────────────────────┐
│                   表现层 (Presentation)            │
│                   Gradio Web Interface               │
│  ┌──────────────┬──────────────┬──────────────┐   │
│  │  棋盘组件   │  分析面板    │  控制面板    │   │
│  │  BoardUI     │  AnalysisUI  │  ControlsUI   │   │
│  └──────────────┴──────────────┴──────────────┘   │
└───────────────────────┬─────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────┐
│                 应用层 (Application)                │
│                业务逻辑与状态管理                   │
│  ┌──────────────┬──────────────┬──────────────┐   │
│  │  PGN模式     │  人机对战    │  复盘模式    │   │
│  │  PGNMode     │  PlayMode    │  ReviewMode   │   │
│  └──────────────┴──────────────┴──────────────┘   │
└───────────────────────┬─────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────┐
│                领域层 (Domain)                    │
│               游戏逻辑与规则引擎                   │
│  ┌──────────────┬──────────────┬──────────────┐   │
│  │  棋盘逻辑    │  象棋规则    │  走法生成    │   │
│  │  BoardLogic  │  Rules       │  MoveGen     │   │
│  └──────────────┴──────────────┴──────────────┘   │
└───────────────────────┬─────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────┐
│                代理层 (Agent)                      │
│               LangGraph工作流编排                  │
│                                                   │
│  START → preprocess → engine → kg → rag → vision    │
│         → explain → END                            │
│                                                   │
│  节点:                                           │
│  • PreprocessNode (输入预处理)                     │
│  • EngineNode (引擎分析)                           │
│  • KGNode (知识图谱查询)                          │
│  • RAGNode (棋书检索)                             │
│  • VisionNode (视觉识别)                           │
│  • ExplainNode (讲解生成)                          │
└───────────────────────┬─────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────┐
              基础设施层 (Infrastructure)            │
│  ┌──────────────┬──────────────┬──────────────┐   │
│  │  引擎组件    │  数据库      │  外部API     │   │
│  │  BaseEngine  │  Neo4j/FAISS │  Qwen-Max    │   │
│  └──────────────┴──────────────┴──────────────┘   │
└─────────────────────────────────────────────────────┘
```

### 核心设计原则

#### 1. 单一职责 (Single Responsibility)
- 每个模块只负责一个功能域
- BoardUI只负责棋盘渲染
- AnalysisUI只负责分析展示
- ControlsUI只负责用户交互

#### 2. 依赖倒置 (Dependency Inversion)
- 高层模块不依赖低层模块
- 都依赖于抽象（BaseEngine/BaseKG/BaseRAG）
- 通过依赖注入解耦

#### 3. 开闭原则 (Open/Closed)
- 对扩展开放，对修改关闭
- 新增模式（如残局挑战）不修改现有代码
- 通过继承和组合实现功能扩展

#### 4. 接口隔离 (Interface Segregation)
- 客户端不应依赖不需要的接口
- BaseEngine只有analyze/stop方法
- BaseKG只有query/get_similar_positions方法

---

## 🔧 后端架构（保持不变）

### LangGraph工作流（完整保留）

#### 工作流定义
```python
# core/agent/graph.py（不修改）

def create_agent() -> StateGraph:
    """创建LangGraph Agent工作流 - 完整保留"""
    workflow = StateGraph(AgentState)

    # 添加所有6个节点（不减少）
    workflow.add_node("preprocess", preprocess_node)
    workflow.add_node("engine", engine_node)
    workflow.add_node("kg", kg_node)
    workflow.add_node("rag", rag_node)
    workflow.add_node("vision", vision_node)
    workflow.add_node("explain", explain_node)

    # 定义边（不修改）
    workflow.set_entry_point("preprocess")
    workflow.add_edge("preprocess", "engine")
    workflow.add_edge("engine", "kg")
    workflow.add_edge("kg", "rag")
    workflow.add_edge("rag", "vision")
    workflow.add_edge("vision", "explain")
    workflow.add_edge("explain", END)

    return workflow.compile()
```

#### 状态定义（完整保留）
```python
# core/agent/state.py（不修改）

class AgentState(TypedDict, total=False):
    """Agent全局状态 - 完整保留所有字段"""
    # 输入
    input_type: str
    fen: str
    image_path: str
    board: List[List[str]]
    iccs_moves: List[str]
    last_move_info: Optional[Dict[str, Any]]

    # 中间结果（所有节点结果必须保留）
    visual_desc: str
    engine_result: Optional[Dict[str, Any]]
    kg_result: Optional[Dict[str, Any]]
    rag_results: List[Dict[str, Any]]
    vision_result: Optional[Dict[str, Any]]

    # 输出
    explanation: str
    error: str

    # 控制标志
    use_vision: bool
    red_to_move: bool
```

#### 接口定义（完整保留）
```python
# core/engine/base.py（不修改）
class BaseEngine(ABC):
    """引擎抽象基类 - 完整保留"""
    @abstractmethod
    def analyze(self, fen: str, depth: int = 20) -> Optional[EngineResult]:
        pass

    @abstractmethod
    def stop(self) -> None:
        pass

# core/kg/base.py（不修改）
class BaseKG(ABC):
    """知识图谱抽象基类 - 完整保留"""
    @abstractmethod
    def query(self, fen: str, moves: Optional[List[str]] = None) -> Optional[KGResult]:
        pass

    @abstractmethod
    def get_similar_positions(self, fen: str, limit: int = 5) -> List[dict]:
        pass

# core/rag/base.py（不修改）
class BaseRAG(ABC):
    """RAG检索抽象基类 - 完整保留"""
    @abstractmethod
    def search(self, query: str, top_k: int = 3) -> Optional[List[RAGResult]]:
        pass
```

---

## 🎨 前端架构（彻底重构）

### 项目结构

```
web/
├── app.py                     # 主入口（<100行，仅路由注册）
├── routes/                    # 路由层
│   ├── __init__.py
│   ├── pgn.py               # PGN模式路由
│   ├── play.py              # 人机对战路由
│   └── review.py           # 复盘模式路由
├── components/              # UI组件层
│   ├── __init__.py
│   ├── board.py            # 棋盘组件（300行）
│   ├── analysis.py         # 分析面板（200行）
│   ├── controls.py         # 控制面板（200行）
│   ├── move_list.py        # 走法列表（150行）
│   └── charts.py          # 图表组件（100行）
├── modes/                  # 模式层
│   ├── __init__.py
│   ├── pgn_mode.py        # PGN模式业务逻辑
│   ├── play_mode.py       # 人机对战业务逻辑
│   └── review_mode.py    # 复盘模式业务逻辑
├── state/                  # 状态管理
│   ├── __init__.py
│   ├── session.py         # 会话状态
│   └── board_state.py    # 棋盘状态
├── utils/                  # 工具层
│   ├── __init__.py
│   ├── animation.py       # 动画工具（已创建）
│   ├── audio.py          # 音效工具（已创建）
│   ├── ui_helpers.py     # UI辅助函数（已创建）
│   └── fen_renderer.py   # FEN渲染器
└── styles/                # 样式层
    ├── __init__.py
    ├── chinese_theme.py   # 中国风主题（已创建）
    └── gradio_styles.py  # Gradio样式（已创建）
```

### 核心组件设计

#### 1. 棋盘组件 (BoardUI)

**职责**: 棋盘渲染、走棋交互、动画展示

```python
# web/components/board.py（300行）

class BoardUI:
    """
    棋盘组件 - 天天象棋级别

    功能:
    - 棋盘渲染（楚河汉界、九宫格）
    - 棋子渲染（3D立体效果）
    - 走棋交互（点击、拖拽）
    - 动画效果（贝塞尔曲线移动）
    - 视觉反馈（高亮、脉冲）
    """

    def __init__(self, audio_manager, animation_manager):
        self.audio = audio_manager
        self.animation = animation_manager
        self.selected_piece = None
        self.valid_moves = []

    def render(self, board: List[List[str]], theme: str = "chinese") -> gr.HTML:
        """
        渲染棋盘

        Args:
            board: 棋盘二维数组
            theme: 主题样式

        Returns:
            Gradio HTML组件
        """
        html = self._build_board_html(board, theme)
        return gr.HTML(value=html)

    def _build_board_html(self, board: List[List[str]], theme: str) -> str:
        """
        构建棋盘HTML

        包含:
        - 楚河汉界（中间分割线）
        - 九宫格（虚线）
        - 棋子（3D立体效果）
        - 交互事件（点击、拖拽）
        """
        # 宣纸纹理背景
        background = "background: radial-gradient(circle at 30% 20%, #F5F5DC 0%, #E8E4D9 100%);"

        # 构建9x10网格
        grid = self._build_grid(board)

        # 楚河汉界
        river = self._build_river()

        # 九宫格
        palaces = self._build_palaces()

        # 棋子
        pieces = self._build_pieces(board)

        return f"""
        <div class="chess-board" style="{background}">
            {grid}
            {river}
            {palaces}
            {pieces}
        </div>
        """

    def _build_grid(self, board: List[List[str]]) -> str:
        """构建网格线"""
        # 9列10行的网格
        # 边框为鎏金 (#D4AF37)
        lines = []
        for row in range(10):
            for col in range(9):
                # 横线
                lines.append(f'<div class="grid-line h-line" style="top: {row * 11.11}%"></div>')
                # 竖线
                lines.append(f'<div class="grid-line v-line" style="left: {col * 12.5}%"></div>')

        return "\n".join(lines)

    def _build_river(self) -> str:
        """构建楚河汉界"""
        return """
        <div class="river">
            <span class="river-text">楚河</span>
            <span class="river-text">汉界</span>
        </div>
        """

    def _build_palaces(self) -> str:
        """构建九宫格（虚线）"""
        top_palace = """
        <div class="palace palace-top">
            <div class="palace-line-1"></div>
            <div class="palace-line-2"></div>
        </div>
        """
        bottom_palace = """
        <div class="palace palace-bottom">
            <div class="palace-line-1"></div>
            <div class="palace-line-2"></div>
        </div>
        """
        return top_palace + bottom_palace

    def _build_pieces(self, board: List[List[str]]) -> str:
        """构建棋子（3D立体效果）"""
        pieces = []
        for row in range(10):
            for col in range(9):
                piece = board[row][col]
                if piece:  # 有棋子
                    piece_html = self._build_piece(piece, row, col)
                    pieces.append(piece_html)

        return "\n".join(pieces)

    def _build_piece(self, piece: str, row: int, col: int) -> str:
        """
        构建单个棋子

        3D立体效果:
        - 径向渐变（白→米黄→米白）
        - 多层阴影（制造深度）
        - 文字阴影（提升可读性）
        """
        is_red = piece.isupper()
        piece_name = self._get_piece_name(piece)
        color_class = "red" if is_red else "black"

        return f"""
        <div class="chess-piece {color_class}"
             data-row="{row}"
             data-col="{col}"
             data-piece="{piece}">
            {piece_name}
        </div>
        """

    def _get_piece_name(self, piece: str) -> str:
        """获取棋子中文名称"""
        names = {
            'r': '车', 'n': '马', 'b': '相', 'a': '仕', 'k': '帅', 'c': '炮', 'p': '兵',
            'R': '車', 'N': '馬', 'B': '象', 'A': '士', 'K': '将', 'C': '砲', 'P': '卒',
        }
        return names.get(piece, piece)

    def highlight_valid_moves(self, moves: List[Tuple[int, int]]) -> str:
        """
        高亮可走位置

        视觉效果:
        - 绿色圆点（翠绿 #00A86B）
        - 脉冲动画
        """
        dots = []
        for row, col in moves:
            dots.append(f"""
            <div class="valid-move"
                 style="top: {row * 11.11 + 5.55}%;
                        left: {col * 12.5 + 6.25}%;"
                 data-row="{row}"
                 data-col="{col}">
            </div>
            """)

        return "\n".join(dots)

    def animate_move(self, from_pos: Tuple[int, int],
                   to_pos: Tuple[int, int],
                   piece_type: str) -> str:
        """
        走棋动画（60fps贝塞尔曲线）

        效果:
        - 贝塞尔曲线路径
        - 阴影跟随
        - 速度变化（缓入缓出）
        - 音效同步
        """
        # 播放音效
        audio_path = self.audio.play_move_sound(piece_type)

        # 生成贝塞尔曲线
        path_points = self.animation.calculate_bezier_curve(
            from_pos, to_pos, num_frames=18  # 18帧 @ 60fps = 300ms
        )

        # 构建动画CSS
        keyframes = []
        for i, (x, y) in enumerate(path_points):
            progress = i / 18
            keyframes.append(f"""
            {progress * 100:.1f}% {{
                transform: translate({x * 12.5}%, {y * 11.11}%);
                box-shadow: 0 {6 - progress * 6}px 12px rgba(0, 0, 0, {0.3 + progress * 0.2});
            }}
            """)

        animation_css = f"""
        @keyframes move-animation-{id(from_pos)}-{id(to_pos)} {{
            {''.join(keyframes)}
        }}

        .piece-moving-{id(from_pos)}-{id(to_pos)} {{
            animation: move-animation-{id(from_pos)}-{id(to_pos)} 0.3s cubic-bezier(0.4, 0, 0.2, 1) forwards;
        }}
        """

        return animation_css
```

#### 2. 分析面板组件 (AnalysisUI)

**职责**: 实时分析展示、热力图、胜率曲线

```python
# web/components/analysis.py（200行）

class AnalysisUI:
    """
    分析面板 - 天天象棋级别

    功能:
    - 实时分析展示（引擎结果、知识图谱）
    - 胜率曲线（动态更新）
    - 最佳着法高亮
    - 劣着提示（评分变化>200）
    - 历史引用（棋书、对局数据）
    """

    def __init__(self):
        self.history = []  # 分析历史

    def render(self, engine_result: Optional[dict] = None,
              kg_result: Optional[dict] = None,
              rag_results: List[dict] = None) -> gr.HTML:
        """
        渲染分析面板

        Args:
            engine_result: 引擎分析结果
            kg_result: 知识图谱结果
            rag_results: 棋书检索结果

        Returns:
            Gradio HTML组件
        """
        html = self._build_analysis_html(engine_result, kg_result, rag_results)
        return gr.HTML(value=html)

    def _build_analysis_html(self, engine_result: Optional[dict],
                           kg_result: Optional[dict],
                           rag_results: List[dict]) -> str:
        """构建分析面板HTML"""

        # 评估条
        eval_bar = self._build_eval_bar(engine_result)

        # 最佳着法
        best_move = self._build_best_move(engine_result)

        # 历史胜率
        win_rate = self._build_win_rate(kg_result)

        # 棋书引用
        citations = self._build_citations(rag_results)

        return f"""
        <div class="analysis-panel">
            <h3>实时分析</h3>
            {eval_bar}
            {best_move}
            {win_rate}
            {citations}
        </div>
        """

    def _build_eval_bar(self, engine_result: Optional[dict]) -> str:
        """
        构建评估条

        效果:
        - 双向进度条（红方/黑方）
        - 颜色渐变（绿→黄→红）
        - 动画过渡（0.5s）
        """
        if not engine_result:
            return "<div class='eval-display'>等待分析...</div>"

        score = engine_result.get('score', 0)
        # 转换为胜率 (tanh函数)
        import math
        winrate = 50 + 50 * math.tanh(score / 1000)

        # 颜色
        color = self._get_eval_color(score)

        return f"""
        <div class="eval-bar">
            <div class="eval-bar-fill"
                 style="width: {winrate}%; background: {color};">
                <span class="eval-text">{score:+.0f}</span>
            </div>
        </div>
        <div class="eval-label">
            红方胜率: {winrate:.1f}%
        </div>
        """

    def _get_eval_color(self, score: float) -> str:
        """
        获取评估分数对应的颜色

        - 平衡（|score| < 50）: 灰色 #808080
        - 红方优势: 红色渐变 (#E63946 → #FF6B6B → #DC2626)
        - 黑方优势: 绿色渐变 (#4CAF50 → #38B000 → #145A32)
        """
        if abs(score) < 50:
            return "#808080"
        elif score > 0:
            if score < 200:
                return "#E63946"  # 轻微优势
            elif score < 500:
                return "#FF6B6B"  # 明显优势
            else:
                return "#DC2626"  # 压倒性优势
        else:
            abs_score = abs(score)
            if abs_score < 200:
                return "#4CAF50"  # 轻微劣势
            elif abs_score < 500:
                return "#38B000"  # 明显劣势
            else:
                return "#145A32"  # 压倒性劣势

    def _build_best_move(self, engine_result: Optional[dict]) -> str:
        """
        构建最佳着法展示

        效果:
        - 高亮显示（鎏金边框）
        - 主变化线（缩进显示）
        - 深度信息（右对齐）
        """
        if not engine_result:
            return "<div class='best-move'>等待分析...</div>"

        bestmove = engine_result.get('bestmove', '')
        pv = engine_result.get('pv', [])
        depth = engine_result.get('depth', 0)

        # 格式化走法
        formatted_pv = " ".join(pv) if pv else ""

        return f"""
        <div class="best-move">
            <div class="best-move-label">最佳着法</div>
            <div class="best-move-content">
                <span class="best-move-text">{bestmove}</span>
                <span class="best-move-depth">深度 {depth}</span>
            </div>
            <div class="best-move-pv">{formatted_pv}</div>
        </div>
        """

    def _build_win_rate(self, kg_result: Optional[dict]) -> str:
        """
        构建历史胜率展示

        效果:
        - 胜率百分比（大号字体）
        - 总对局数（小号字体）
        - 开局名称（中等字体）
        """
        if not kg_result:
            return "<div class='win-rate'>等待查询...</div>"

        win_rate = kg_result.get('win_rate', 0)
        total_games = kg_result.get('total_games', 0)
        opening_name = kg_result.get('opening_name', '未知')

        return f"""
        <div class="win-rate">
            <div class="win-rate-value">{win_rate:.1f}%</div>
            <div class="win-rate-label">红方胜率</div>
            <div class="win-rate-games">
                基于历史 {total_games} 局 {opening_name}
            </div>
        </div>
        """

    def _build_citations(self, rag_results: List[dict]) -> str:
        """
        构建棋书引用展示

        效果:
        - 引用列表（编号显示）
        - 书名 + 页码（粗体）
        - 相关性评分（星级显示）
        - 可点击跳转
        """
        if not rag_results:
            return "<div class='citations'>暂无引用</div>"

        citations = []
        for i, result in enumerate(rag_results, 1):
            book_name = result.get('book_name', '未知棋书')
            page = result.get('page', 0)
            relevance = result.get('relevance', 0)
            content = result.get('content', '')

            # 星级显示
            stars = "★" * int(relevance * 5)

            citations.append(f"""
            <div class="citation-item">
                <div class="citation-header">
                    <span class="citation-number">[{i}]</span>
                    <span class="citation-book">{book_name}</span>
                    <span class="citation-page">第{page}页</span>
                </div>
                <div class="citation-stars">{stars}</div>
                <div class="citation-content">{content[:100]}...</div>
            </div>
            """)

        return f"""
        <div class="citations">
            <div class="citations-header">棋书引用</div>
            {''.join(citations)}
        </div>
        """

    def update_eval_chart(self, history: List[Tuple[int, float]]) -> str:
        """
        更新胜率曲线图

        效果:
        - 折线图（动态更新）
        - 转折点标记（红色圆点）
        - 红色/绿色区域（红方/黑方优势）
        """
        # 使用Chart.js或Gradio的Plot组件
        # 返回图表配置JSON
        pass
```

#### 3. 控制面板组件 (ControlsUI)

**职责**: 用户交互、模式切换、按钮操作

```python
# web/components/controls.py（200行）

class ControlsUI:
    """
    控制面板 - 天天象棋级别

    功能:
    - 模式切换（下棋谱/人机对战/复盘）
    - 难度选择（1-10级）
    - 走棋控制（上一步/下一步/跳转）
    - 播放控制（暂停/继续/速度）
    - 帮助按钮（规则说明/快捷键）
    """

    def __init__(self):
        self.current_mode = "pgn"  # pgn/play/review
        self.difficulty = 10
        self.playback_speed = 1.0

    def render(self) -> gr.Column:
        """
        渲染控制面板

        Returns:
            Gradio Column组件
        """
        with gr.Column() as controls:
            # 模式切换
            mode_tabs = self._build_mode_tabs()

            # PGN模式控制
            pgn_controls = self._build_pgn_controls()

            # 人机对战控制
            play_controls = self._build_play_controls()

            # 复盘模式控制
            review_controls = self._build_review_controls()

            # 通用控制
            common_controls = self._build_common_controls()

        return controls

    def _build_mode_tabs(self) -> gr.Tabs:
        """构建模式切换标签"""
        with gr.Tabs() as tabs:
            with gr.Tab("下棋谱"):
                pgn_content = gr.Column()
            with gr.Tab("人机对战"):
                play_content = gr.Column()
            with gr.Tab("复盘"):
                review_content = gr.Column()

        return tabs

    def _build_pgn_controls(self) -> gr.Row:
        """构建PGN模式控制"""
        with gr.Row() as controls:
            # 文件上传
            file_upload = gr.File(
                label="上传PGN文件",
                file_types=[".pgn"]
            )

            # 导航按钮
            with gr.Row():
                first_btn = gr.Button("⏮ 首局")
                prev_btn = gr.Button("◀ 上一步")
                next_btn = gr.Button("下一步 ▶")
                last_btn = gr.Button("尾局 ⏭")

            # 跳转输入
            jump_input = gr.Number(
                label="跳转到第几局",
                value=1,
                minimum=1
            )
            jump_btn = gr.Button("跳转")

        return controls

    def _build_play_controls(self) -> gr.Row:
        """构建人机对战控制"""
        with gr.Row() as controls:
            # 难度选择
            difficulty_slider = gr.Slider(
                label="难度等级",
                minimum=1,
                maximum=10,
                value=10,
                step=1,
                interactive=True
            )

            # 新局按钮
            new_game_btn = gr.Button("新对局", variant="primary")

            # 悔棋按钮
            undo_btn = gr.Button("悔棋")

            # 求和按钮
            draw_btn = gr.Button("求和")

        return controls

    def _build_review_controls(self) -> gr.Row:
        """构建复盘模式控制"""
        with gr.Row() as controls:
            # 导航按钮
            with gr.Row():
                first_btn = gr.Button("⏮ 开始")
                prev_btn = gr.Button("◀ 上一步")
                next_btn = gr.Button("下一步 ▶")
                last_btn = gr.Button("结束 ⏭")

            # 自动播放
            with gr.Row():
                play_btn = gr.Button("▶ 播放")
                pause_btn = gr.Button("⏸ 暂停")
                stop_btn = gr.Button("⏹ 停止")

            # 速度控制
            speed_slider = gr.Slider(
                label="播放速度",
                minimum=0.5,
                maximum=3.0,
                value=1.0,
                step=0.5
            )

        return controls

    def _build_common_controls(self) -> gr.Row:
        """构建通用控制"""
        with gr.Row() as controls:
            # 帮助按钮
            help_btn = gr.Button("❓ 帮助")

            # 设置按钮
            settings_btn = gr.Button("⚙️ 设置")

            # 音效开关
            audio_toggle = gr.Button("🔊 音效")

        return controls
```

---

## 🎮 模式层设计

### PGN模式业务逻辑

```python
# web/modes/pgn_mode.py（200行）

class PGNMode:
    """
    PGN模式 - 专业棋谱打谱

    功能:
    - PGN文件解析
    - 局面导航（上一步/下一步/跳转）
    - 走法列表展示
    - 实时分析（可选）
    """

    def __init__(self, agent: XiangqiAgent):
        self.agent = agent
        self.pgn_data = None
        self.current_game = 0
        self.current_move = 0
        self.games = []

    def load_pgn(self, file_path: str) -> Tuple[List[dict], str]:
        """
        加载PGN文件

        Args:
            file_path: PGN文件路径

        Returns:
            (对局列表, 错误信息)
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 解析PGN
            games = self._parse_pgn(content)
            self.games = games

            if not games:
                return [], "PGN文件为空或格式错误"

            return games, ""
        except Exception as e:
            return [], f"加载PGN文件失败: {str(e)}"

    def _parse_pgn(self, content: str) -> List[dict]:
        """
        解析PGN内容

        返回格式:
        [
            {
                "event": "赛事名称",
                "date": "2024-01-01",
                "red": "红方",
                "black": "黑方",
                "result": "1-0",
                "moves": ["h2e2", "h9e9", ...],
                "fen": "初始FEN"
            },
            ...
        ]
        """
        # 简化版PGN解析
        # 实际实现需要完整的PGN解析器
        games = []

        # 按空行分割对局
        game_texts = content.split("\n\n")

        for game_text in game_texts:
            if not game_text.strip():
                continue

            # 解析元数据
            metadata = self._parse_metadata(game_text)

            # 解析走法
            moves = self._parse_moves(game_text)

            if metadata and moves:
                games.append({
                    "metadata": metadata,
                    "moves": moves
                })

        return games

    def _parse_metadata(self, game_text: str) -> dict:
        """解析对局元数据"""
        metadata = {}
        lines = game_text.split("\n")

        for line in lines:
            if line.startswith("["):
                # [Event "赛事名称"]
                match = re.match(r'\[(\w+)\s+"(.+)"\]', line)
                if match:
                    key, value = match.groups()
                    metadata[key.lower()] = value
            else:
                break

        return metadata

    def _parse_moves(self, game_text: str) -> List[str]:
        """解析走法"""
        # 提取走法部分
        lines = game_text.split("\n")
        move_text = ""

        in_moves = False
        for line in lines:
            if not line.startswith("["):
                in_moves = True
            if in_moves:
                move_text += line + " "

        # 解析ICCS走法
        moves = []
        # 简化版：按空格分割
        tokens = move_text.split()
        for token in tokens:
            if re.match(r'^[a-h][0-9][a-h][0-9]$', token):
                moves.append(token)

        return moves

    def get_game_count(self) -> int:
        """获取对局数量"""
        return len(self.games)

    def get_current_game(self) -> Optional[dict]:
        """获取当前对局"""
        if 0 <= self.current_game < len(self.games):
            return self.games[self.current_game]
        return None

    def get_move_count(self) -> int:
        """获取当前对局走法数"""
        game = self.get_current_game()
        if game:
            return len(game.get("moves", []))
        return 0

    def go_to_game(self, game_index: int) -> Tuple[int, str]:
        """
        跳转到指定对局

        Returns:
            (新对局索引, 错误信息)
        """
        if 0 <= game_index < len(self.games):
            self.current_game = game_index
            self.current_move = 0
            return game_index, ""
        return self.current_game, f"对局索引超出范围 (1-{len(self.games)})"

    def go_to_move(self, move_index: int) -> Tuple[int, str]:
        """
        跳转到指定走法

        Returns:
            (新走法索引, 错误信息)
        """
        game = self.get_current_game()
        if game:
            max_move = len(game.get("moves", []))
            if 0 <= move_index <= max_move:
                self.current_move = move_index
                return move_index, ""
            return self.current_move, f"走法索引超出范围 (0-{max_move})"
        return self.current_move, "没有当前对局"

    def next_move(self) -> Tuple[int, str]:
        """
        下一步

        Returns:
            (新走法索引, 错误信息)
        """
        return self.go_to_move(self.current_move + 1)

    def prev_move(self) -> Tuple[int, str]:
        """
        上一步

        Returns:
            (新走法索引, 错误信息)
        """
        return self.go_to_move(self.current_move - 1)

    def get_current_position(self) -> Optional[str]:
        """
        获取当前局面FEN

        Returns:
            当前局面FEN或None
        """
        game = self.get_current_game()
        if not game:
            return None

        # 从初始FEN应用走法
        fen = game.get("metadata", {}).get("fen", "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1")
        moves = game.get("moves", [])[:self.current_move]

        # 应用走法（需要棋盘逻辑）
        # 这里简化处理，实际需要完整的走法应用逻辑
        return fen

    def analyze_current_position(self) -> Optional[dict]:
        """
        分析当前局面（调用Agent）

        Returns:
            Agent分析结果
        """
        fen = self.get_current_position()
        if not fen:
            return None

        game = self.get_current_game()
        moves = game.get("moves", [])[:self.current_move] if game else []

        result = self.agent.analyze(
            fen=fen,
            iccs_moves=moves,
            use_vision=False  # PGN模式不需要视觉
        )

        return result
```

---

## 🔄 交互逻辑设计

### 核心交互流程

#### 场景1: 加载PGN文件并打谱

```
用户操作:
1. 点击"上传PGN文件"按钮
2. 选择PGN文件
3. 系统解析PGN
4. 显示对局列表
5. 用户点击"下一步"查看着法

系统行为:
1. 文件上传 → PGNMode.load_pgn()
2. 解析PGN → 返回对局列表
3. 渲染对局列表 → MoveListUI.render()
4. 用户点击"下一步" → PGNMode.next_move()
5. 获取当前局面 → PGNMode.get_current_position()
6. 渲染棋盘 → BoardUI.render()
7. 可选：分析局面 → PGNMode.analyze_current_position()
8. 显示分析 → AnalysisUI.render()
```

#### 场景2: 人机对战

```
用户操作:
1. 选择难度（1-10级）
2. 点击"新对局"按钮
3. 用户点击棋子（选中）
4. 系统显示可走位置
5. 用户点击目标位置（走棋）
6. 系统播放动画
7. 引擎思考
8. 系统走棋（AI）
9. 用户继续...

系统行为:
1. 初始化对局 → PlayMode.new_game()
2. 渲染初始棋盘 → BoardUI.render()
3. 用户点击棋子 → BoardUI.on_piece_click()
4. 生成走法 → Rules.get_valid_moves()
5. 高亮可走位置 → BoardUI.highlight_valid_moves()
6. 用户点击目标 → BoardUI.on_target_click()
7. 验证走法 → Rules.is_valid_move()
8. 应用走法 → BoardLogic.apply_move()
9. 播放动画 → BoardUI.animate_move()
10. 播放音效 → AudioManager.play_move_sound()
11. 引擎分析 → Engine.analyze()
12. AI走棋 → PlayMode.ai_move()
13. 显示AI走棋 → BoardUI.render()
```

#### 场景3: 复盘分析

```
用户操作:
1. 选择对局（PGN或历史）
2. 点击"开始复盘"
3. 系统显示胜率曲线
4. 用户点击"下一步"
5. 系统显示转折点
6. 用户点击"下一步"
7. 系统显示劣着提示
8. 用户点击"下一步"
9. ...

系统行为:
1. 加载对局 → ReviewMode.load_game()
2. 分析整个对局 → ReviewMode.analyze_full_game()
3. 生成胜率曲线 → ReviewMode.generate_eval_curve()
4. 识别转折点 → ReviewMode.find_turning_points()
5. 识别劣着 → ReviewMode.find_blunders()
6. 渲染图表 → ChartsUI.render()
7. 用户导航 → ReviewMode.next_move()
8. 显示分析 → AnalysisUI.render()
9. 高亮关键着法 → BoardUI.highlight_move()
```

---

## 🎨 中国风设计规范

### 配色方案

```python
# web/styles/chinese_theme.py（已创建）

CHINESE_THEME = {
    # 主色调
    'primary_red': '#C41E3A',      # 朱红 - 红方主色
    'primary_black': '#1A1A1A',     # 墨黑 - 黑方主色
    'gold': '#D4AF37',              # 鎏金 - 装饰色
    'jade': '#00A86B',               # 翠绿 - 状态色
    'paper': '#F5F5DC',             # 宣纸白 - 背景色

    # 辅助色
    'red_light': '#E85A6C',
    'black_light': '#333333',
    'gold_light': '#F4D03F',
    'jade_light': '#00B894',

    # 棋子色
    'piece_red': '#E63946',
    'piece_black': '#2C3E50',
    'piece_text_red': '#FFFFFF',
    'piece_text_black': '#FFFFFF',

    # 边框色
    'border': '#B8860B',             # 木纹框
    'shadow': 'rgba(0, 0, 0, 0.2)',  # 柔和阴影

    # 文本色
    'text_primary': '#2C3E50',
    'text_secondary': '#7F8C8D',
    'text_highlight': '#C0392B',
}
```

### 设计元素

#### 1. 棋盘
- 背景：宣纸纹理（径向渐变）
- 网格线：鎏金色（#D4AF37）
- 楚河汉界：渐变分割线
- 九宫格：虚线显示

#### 2. 棋子
- 形状：圆形（50px直径）
- 背景：径向渐变（白→米黄→米白）
- 阴影：多层阴影制造3D效果
- 边框：朱红/墨黑
- 文字：楷体/宋体
- 动画：悬停浮起、选中脉冲

#### 3. 按钮
- 主按钮：朱红渐变
- 次要按钮：翠绿渐变
- 危险按钮：红色渐变
- 悬停：上浮2px
- 点击：下沉效果

#### 4. 面板
- 背景：宣纸渐变
- 边框：鎏金边框
- 圆角：8px
- 阴影：柔和阴影

---

## 🎭 动画与音效

### 动画系统（已创建）

```python
# web/utils/animation.py（已创建）

class AnimationManager:
    """
    动画管理器 - 60fps流畅动画

    动画类型:
    - 走棋动画（贝塞尔曲线）
    - 吃子动画（缩放+淡出）
    - 选中动画（脉冲效果）
    - 将军动画（闪烁警报）
    """

    def calculate_bezier_curve(self, from_pos, to_pos, num_frames=18):
        """计算贝塞尔曲线路径"""
        pass

    def create_move_animation(self, piece_element, from_pos, to_pos):
        """创建走棋动画（300ms @ 60fps）"""
        pass

    def create_capture_animation(self, captured_element):
        """创建吃子动画（200ms @ 60fps）"""
        pass

    def create_selected_animation(self, piece_element):
        """创建选中动画（1.5s循环）"""
        pass

    def create_check_alert_animation(self, check_element):
        """创建将军警报动画（1s循环）"""
        pass
```

### 音效系统（已创建）

```python
# web/utils/audio.py（已创建）

class AudioManager:
    """
    音效管理器 - 专业音效系统

    音效类型:
    - 走棋音效（不同棋子不同声音）
    - 吃子音效
    - 将军音效
    - 胜利音效
    - 失败音效
    - UI音效（点击、通知）
    """

    def __init__(self):
        self.sounds = {}
        self.enabled = True
        self.volume = 0.7

    def play_move_sound(self, piece_type: str):
        """播放走棋音效"""
        pass

    def play_capture_sound(self):
        """播放吃子音效"""
        pass

    def play_check_sound(self):
        """播放将军音效"""
        pass

    def play_win_sound(self):
        """播放胜利音效"""
        pass

    def play_lose_sound(self):
        """播放失败音效"""
        pass

    def set_volume(self, volume: float):
        """设置音量"""
        pass

    def toggle_sound(self):
        """切换音效开关"""
        pass
```

---

## 📱 响应式设计

### 断点设置

```css
/* 平板 - 768px-1024px */
@media (max-width: 1024px) {
    .chess-piece {
        width: 40px;
        height: 40px;
        font-size: 22px;
    }

    .nav-button {
        padding: 8px 16px;
        font-size: 12px;
    }
}

/* 手机 - <768px */
@media (max-width: 768px) {
    .chess-piece {
        width: 35px;
        height: 35px;
        font-size: 18px;
    }

    .river {
        font-size: 18px;
        letter-spacing: 0.5rem;
    }

    .chinese-button {
        padding: 8px 16px;
        font-size: 14px;
    }
}
```

### 布局适配

```
桌面布局（>1024px）:
┌─────────────────────────────────────────────┐
│  [棋盘 600px]  │  [分析面板 400px]    │
│  [600x660]      │  [400x660]          │
└─────────────────────────────────────────────┘
  [控制面板 1000px]

平板布局（768px-1024px）:
┌──────────────────────┐
│  [棋盘 500px]       │
│  [500x550]           │
└──────────────────────┘
  [分析面板 500px]
  [控制面板 500px]

手机布局（<768px）:
┌──────────────────┐
│  [棋盘 350px]    │
│  [350x385]       │
└──────────────────┘
  [分析面板 350px]
  [控制面板 350px]
```

---

## 🚀 实施计划

### Phase 1: 架构拆分（2天）

**任务**:
1. 拆分app.py为模块化结构
2. 创建routes/目录（pgn.py, play.py, review.py）
3. 创建components/目录（board.py, analysis.py, controls.py）
4. 创建modes/目录（pgn_mode.py, play_mode.py, review_mode.py）
5. 创建state/目录（session.py, board_state.py）

**验收标准**:
- app.py < 100行
- 每个模块 < 300行
- 所有功能可正常运行

### Phase 2: 组件实现（3天）

**任务**:
1. 实现BoardUI（棋盘渲染、动画）
2. 实现AnalysisUI（分析面板、热力图）
3. 实现ControlsUI（控制面板、按钮）
4. 集成中国风主题（CSS）
5. 集成动画系统（贝塞尔曲线）
6. 集成音效系统（走棋音效）

**验收标准**:
- 棋盘渲染正确（楚河汉界、九宫格）
- 动画流畅（60fps）
- 音效正常播放
- 中国风样式一致

### Phase 3: 模式实现（3天）

**任务**:
1. 实现PGNMode（PGN解析、导航）
2. 实现PlayMode（人机对战、AI走棋）
3. 实现ReviewMode（复盘、胜率曲线）
4. 实现模式切换逻辑
5. 实现跨模式功能（如：人机对战结束后复盘）

**验收标准**:
- 三大模式可切换
- PGN文件可加载并打谱
- 人机对战可正常对弈
- 复盘可显示胜率曲线

### Phase 4: 联调测试（2天）

**任务**:
1. 端到端测试（PGN模式）
2. 端到端测试（人机对战）
3. 端到端测试（复盘）
4. 跨模式测试
5. 性能测试（响应<3秒）
6. 兼容性测试（Chrome、Firefox、Edge）

**验收标准**:
- 所有测试通过
- 响应时间<3秒
- 无明显bug

### Phase 5: 优化完善（1天）

**任务**:
1. UI细节调整
2. 性能优化
3. 文档完善
4. 演示准备

**验收标准**:
- UI达到天天象棋水平
- 性能满足要求
- 文档完整

---

## 📊 验收标准

### 功能验收
- [ ] 三大模式可切换（下棋谱/人机对战/复盘）
- [ ] PGN文件可加载并解析
- [ ] PGN模式可导航（上一步/下一步/跳转）
- [ ] 人机对战可正常对弈
- [ ] 复盘可显示胜率曲线
- [ ] 复盘可识别转折点
- [ ] 复盘可识别劣着

### 性能验收
- [ ] 页面加载时间<2秒
- [ ] 走棋响应时间<1秒
- [ ] 分析响应时间<3秒
- [ ] 动画流畅度>50fps

### UI/UX验收
- [ ] 中国风样式一致
- [ ] 动画流畅（60fps）
- [ ] 音效正常播放
- [ ] 响应式布局（桌面/平板/手机）
- [ ] 无明显bug

### 代码质量验收
- [ ] 代码符合架构设计
- [ ] 模块职责清晰
- [ ] 单个文件<300行
- [ ] 测试覆盖率>70%

---

## 🎯 下一步行动

### 立即执行（本周）
1. **Phase 1: 架构拆分**（2天）
   - 拆分app.py
   - 创建routes/目录
   - 创建components/目录
   - 创建modes/目录

2. **Phase 2: 组件实现**（3天）
   - 实现BoardUI
   - 实现AnalysisUI
   - 实现ControlsUI

### 后续执行（下周）
3. **Phase 3: 模式实现**（3天）
4. **Phase 4: 联调测试**（2天）
5. **Phase 5: 优化完善**（1天）

---

**文档版本**: v1.0
**最后更新**: 2026-03-09
**维护者**: AI开发团队
