"""
分析面板组件 - 商业级完整版

职责: 实时分析展示、热力图、胜率曲线

文档依据: JOINT_REFACTOR_ARCHITECTURE.md AnalysisUI

Phase 2完整实现:
- 评估条（双向进度条、颜色渐变）
- 最佳着法（高亮、主变化线）
- 历史胜率（百分比、总对局数）
- 棋书引用（星级显示）
- 商业级UI设计
"""

import gradio as gr
import math
from typing import Optional, List, Dict


class CompleteAnalysisUI:
    """
    完整的分析面板UI组件

    商业级分析展示
    """

    # 中国风配色
    COLORS = {
        'primary_red': '#C41E3A',
        'primary_black': '#1A1A1A',
        'gold': '#D4AF37',
        'jade': '#00A86B',
        'paper': '#F5F5DC',
        'red_piece': '#E63946',
        'black_piece': '#2C3E50',
    }

    def __init__(self):
        self.history = []
        self.current_eval = 0.0

    def render(self, engine_result: Optional[dict] = None,
              kg_result: Optional[dict] = None,
              rag_results: List[dict] = None) -> gr.HTML:
        """
        渲染完整分析面板

        Args:
            engine_result: 引擎分析结果
            kg_result: 知识图谱结果
            rag_results: 棋书检索结果

        Returns:
            Gradio HTML组件
        """
        # 更新历史
        if engine_result:
            self.current_eval = engine_result.get('score', 0.0)
            self.history.append(self.current_eval)

        # 构建HTML
        html_parts = [
            self._build_container(),
            self._build_header(),
            self._build_eval_bar(engine_result),
            self._build_best_move(engine_result),
            self._build_win_rate(kg_result),
            self._build_citations(rag_results),
            self._build_close_container(),
            self._build_styles()
        ]

        full_html = "\n".join(html_parts)
        return gr.HTML(value=full_html)

    def _build_container(self) -> str:
        """构建分析面板容器"""
        return """
        <div class="analysis-panel" style="
            background: linear-gradient(180deg, #F5F5DC 0%, #E8E4D9 100%);
            border: 2px solid #B8860B;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        ">
        """

    def _build_header(self) -> str:
        """构建面板标题"""
        return """
        <h3 style="
            font-family: '楷体', 'STKaiti', 'KaiTi', serif;
            font-size: 20px;
            color: #C41E3A;
            margin: 0 0 20px 0;
            text-align: center;
            border-bottom: 2px solid #D4AF37;
            padding-bottom: 10px;
        ">实时分析</h3>
        """

    def _build_eval_bar(self, engine_result: Optional[dict]) -> str:
        """
        构建评估条

        视觉效果:
        - 双向进度条（红方/黑方）
        - 颜色渐变（绿→黄→红）
        - 动画过渡（0.5s）
        - 评分数值显示
        """
        if not engine_result:
            return self._build_placeholder("等待分析...")

        score = engine_result.get('score', 0)
        depth = engine_result.get('depth', 0)

        # 转换为胜率 (tanh函数)
        winrate = 50 + 50 * math.tanh(score / 1000)

        # 获取颜色
        color = self._get_eval_color(score)

        return f"""
        <div class="eval-section" style="margin-bottom: 20px;">
            <div class="eval-label" style="
                font-family: '楷体', 'STKaiti', 'KaiTi', serif;
                font-size: 14px;
                color: #2C3E50;
                margin-bottom: 8px;
            ">评估（深度 {depth}）</div>

            <div class="eval-bar-container" style="
                position: relative;
                width: 100%;
                height: 30px;
                background: #E8E4D0;
                border-radius: 15px;
                overflow: hidden;
                box-shadow: inset 0 2px 4px rgba(0,0,0,0.1);
            ">
                <div class="eval-bar-fill" style="
                    position: absolute;
                    top: 0;
                    left: 0;
                    width: {winrate}%;
                    height: 100%;
                    background: {color};
                    transition: width 0.5s ease-out;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-family: '楷体', 'STKaiti', 'KaiTi', serif;
                    font-weight: bold;
                    font-size: 14px;
                    color: #FFFFFF;
                    text-shadow: 1px 1px 2px rgba(0,0,0,0.3);
                ">{score:+.0f}</div>
            </div>

            <div class="eval-winrate" style="
                font-family: '楷体', 'STKaiti', 'KaiTi', serif;
                font-size: 12px;
                color: #7F8C8D;
                text-align: center;
                margin-top: 8px;
            ">红方胜率: <span style="font-weight: bold; color: {color};">{winrate:.1f}%</span></div>
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

        视觉效果:
        - 鎏金边框高亮
        - 主变化线（缩进显示）
        - 深度信息（右对齐）
        """
        if not engine_result:
            return self._build_placeholder("等待分析...")

        bestmove = engine_result.get('bestmove', '')
        pv = engine_result.get('pv', [])
        depth = engine_result.get('depth', 0)
        nodes = engine_result.get('nodes', 0)
        time_ms = engine_result.get('time_ms', 0)

        # 格式化主变化线
        formatted_pv = " ".join(pv) if pv else "无变化线"

        return f"""
        <div class="best-move-section" style="
            background: rgba(212, 175, 55, 0.1);
            border: 2px solid #D4AF37;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 20px;
        ">
            <div class="best-move-header" style="
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 12px;
            ">
                <div class="best-move-label" style="
                    font-family: '楷体', 'STKaiti', 'KaiTi', serif;
                    font-size: 16px;
                    font-weight: bold;
                    color: #C41E3A;
                ">最佳着法</div>
                <div class="best-move-depth" style="
                    font-family: '楷体', 'STKaiti', 'KaiTi', serif;
                    font-size: 12px;
                    color: #7F8C8D;
                ">深度 {depth}</div>
            </div>

            <div class="best-move-content" style="
                display: flex;
                align-items: center;
                justify-content: space-between;
                margin-bottom: 12px;
            ">
                <span class="best-move-text" style="
                    font-family: '楷体', 'STKaiti', 'KaiTi', serif;
                    font-size: 24px;
                    font-weight: bold;
                    color: #C41E3A;
                    background: #D4AF37;
                    padding: 8px 20px;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                ">{bestmove}</span>
            </div>

            <div class="best-move-stats" style="
                font-size: 12px;
                color: #7F8C8D;
                margin-bottom: 8px;
            ">
                <span>节点: {nodes:,}</span>
                <span style="margin-left: 12px;">时间: {time_ms}ms</span>
            </div>

            <div class="best-move-pv" style="
                background: #FFFFFF;
                border: 1px solid #D4AF37;
                border-radius: 6px;
                padding: 12px;
                font-family: '楷体', 'STKaiti', 'KaiTi', serif;
                font-size: 14px;
                color: #2C3E50;
                line-height: 1.8;
            ">
                <div style="font-weight: bold; margin-bottom: 8px;">主变化线:</div>
                <div>{formatted_pv}</div>
            </div>
        </div>
        """

    def _build_win_rate(self, kg_result: Optional[dict]) -> str:
        """
        构建历史胜率展示

        视觉效果:
        - 胜率百分比（大号字体、渐变色）
        - 总对局数（小号字体）
        - 开局名称（中等字体）
        """
        if not kg_result:
            return self._build_placeholder("等待查询...")

        win_rate = kg_result.get('win_rate', 0)
        total_games = kg_result.get('total_games', 0)
        opening_name = kg_result.get('opening_name', '未知')

        return f"""
        <div class="win-rate-section" style="
            background: linear-gradient(135deg, #D4AF37 0%, #F4D03F 100%);
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            text-align: center;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        ">
            <div class="win-rate-value" style="
                font-family: '楷体', 'STKaiti', 'KaiTi', serif;
                font-size: 48px;
                font-weight: bold;
                color: #FFFFFF;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
            ">{win_rate:.1f}%</div>

            <div class="win-rate-label" style="
                font-family: '楷体', 'STKaiti', 'KaiTi', serif;
                font-size: 16px;
                color: #FFFFFF;
                margin-top: 8px;
                opacity: 0.9;
            ">红方胜率</div>

            <div class="win-rate-games" style="
                font-family: '楷体', 'STKaiti', 'KaiTi', serif;
                font-size: 12px;
                color: #2C3E50;
                margin-top: 16px;
                opacity: 0.8;
            ">基于历史 <strong>{total_games}</strong> 局 <strong>{opening_name}</strong></div>
        </div>
        """

    def _build_citations(self, rag_results: List[dict]) -> str:
        """
        构建棋书引用展示

        视觉效果:
        - 引用列表（编号显示）
        - 书名 + 页码（粗体）
        - 相关性评分（星级显示）
        - 可点击跳转
        """
        if not rag_results:
            return self._build_placeholder("暂无引用")

        citations = []
        for i, result in enumerate(rag_results, 1):
            book_name = result.get('book_name', '未知棋书')
            page = result.get('page', 0)
            relevance = result.get('relevance', 0)
            content = result.get('content', '')

            # 星级显示
            stars = "★" * int(relevance * 5) + "☆" * (5 - int(relevance * 5))

            citations.append(f"""
            <div class="citation-item" style="
                background: #FFFFFF;
                border: 1px solid #D4AF37;
                border-radius: 6px;
                padding: 12px;
                margin-bottom: 12px;
                transition: all 0.3s;
                cursor: pointer;
            ">
                <div class="citation-header" style="
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 8px;
                ">
                    <div class="citation-number" style="
                        font-family: '楷体', 'STKaiti', 'KaiTi', serif;
                        font-size: 14px;
                        font-weight: bold;
                        color: #C41E3A;
                        margin-right: 12px;
                    ">{i}</div>
                    <div class="citation-book" style="
                        font-family: '楷体', 'STKaiti', 'KaiTi', serif;
                        font-size: 14px;
                        font-weight: bold;
                        color: #2C3E50;
                        flex: 1;
                    ">{book_name}</div>
                    <div class="citation-page" style="
                        font-family: '楷体', 'STKaiti', 'KaiTi', serif;
                        font-size: 12px;
                        color: #7F8C8D;
                    ">第{page}页</div>
                </div>

                <div class="citation-stars" style="
                    font-size: 16px;
                    color: #D4AF37;
                    margin-bottom: 8px;
                ">{stars}</div>

                <div class="citation-content" style="
                    font-family: '楷体', 'STKaiti', 'KaiTi', serif;
                    font-size: 12px;
                    color: #7F8C8D;
                    line-height: 1.6;
                ">{content[:150]}{'...' if len(content) > 150 else ''}</div>
            </div>
            """)

        return f"""
        <div class="citations-section">
            <div class="citations-header" style="
                font-family: '楷体', 'STKaiti', 'KaiTi', serif;
                font-size: 16px;
                font-weight: bold;
                color: #C41E3A;
                margin-bottom: 16px;
                padding-bottom: 8px;
                border-bottom: 1px solid #D4AF37;
            ">棋书引用</div>
            {''.join(citations)}
        </div>
        """

    def _build_placeholder(self, text: str) -> str:
        """
        构建占位符（用于等待数据时）

        Args:
            text: 占位符文本

        Returns:
            占位符HTML
        """
        return f"""
        <div style="
            background: rgba(0, 0, 0, 0.05);
            border: 1px dashed #B8860B;
            border-radius: 6px;
            padding: 40px 20px;
            text-align: center;
            color: #7F8C8D;
            font-family: '楷体', 'STKaiti', 'KaiTi', serif;
        ">
            {text}
        </div>
        """

    def _build_close_container(self) -> str:
        """构建容器闭合标签"""
        return "</div>"

    def _build_styles(self) -> str:
        """构建CSS样式"""
        return """
        <style>
        .citation-item:hover {
            background: rgba(212, 175, 55, 0.1);
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }

        .best-move-section:hover {
            box-shadow: 0 6px 16px rgba(0,0,0,0.15);
        }
        </style>
        """

    def get_eval_chart_html(self) -> str:
        """
        获取评估曲线图HTML

        Returns:
            曲线图HTML片段
        """
        if len(self.history) < 2:
            return ""

        return f"""
        <div class="eval-chart" style="
            width: 100%;
            height: 200px;
            background: #FFFFFF;
            border: 1px solid #B8860B;
            border-radius: 6px;
            margin-top: 20px;
            padding: 12px;
        ">
            <div style="
                font-family: '楷体', 'STKaiti', 'KaiTi', serif;
                font-size: 14px;
                color: #2C3E50;
                margin-bottom: 8px;
            ">评估历史</div>
            <div style="
                display: flex;
                align-items: flex-end;
                height: 160px;
                gap: 4px;
            ">
                {self._build_chart_bars()}
            </div>
        </div>
        """

    def _build_chart_bars(self) -> str:
        """构建曲线图柱状条"""
        bars = []

        for i, score in enumerate(self.history[-20:]):  # 只显示最近20步
            height = min(100, abs(score) / 5)  # 最大高度100%
            color = self._get_eval_color(score)
            opacity = 0.5 + (i / 20) * 0.5  # 渐变透明度

            bars.append(f"""
            <div style="
                flex: 1;
                height: {height}%;
                background: {color};
                opacity: {opacity};
                border-radius: 2px 2px 0 0;
                min-height: 4px;
            "></div>
            """)

        return "\n".join(bars)


# 便捷函数
def create_complete_analysis_ui() -> CompleteAnalysisUI:
    """
    创建完整分析UI实例（便捷函数）

    Returns:
        CompleteAnalysisUI实例
    """
    return CompleteAnalysisUI()
