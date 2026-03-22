"""
分析面板组件 - 天天象棋级别

职责: 实时分析展示、热力图、胜率曲线

文档依据: JOINT_REFACTOR_ARCHITECTURE.md AnalysisUI

Phase 2将完整实现以下功能:
- 实时分析展示（引擎结果、知识图谱）
- 胜率曲线（动态更新）
- 最佳着法高亮
- 劣着提示（评分变化>200）
- 历史引用（棋书、对局数据）

当前: 框架版本，使用Markdown展示分析结果
"""

from typing import Optional, List, Dict


class AnalysisUI:
    """
    分析面板框架

    Phase 2将完整实现商业级HTML/CSS渲染
    当前版本使用Markdown展示
    """

    def __init__(self):
        self.history = []

    def render(self, engine_result: Optional[dict] = None,
              kg_result: Optional[dict] = None,
              rag_results: List[dict] = None) -> str:
        """
        渲染分析面板

        Args:
            engine_result: 引擎分析结果
            kg_result: 知识图谱结果
            rag_results: 棋书检索结果

        Returns:
            Markdown格式的分析内容
        """
        return self._build_analysis_markdown(engine_result, kg_result, rag_results)

    def _build_analysis_markdown(self, engine_result: Optional[dict],
                                 kg_result: Optional[dict],
                                 rag_results: List[dict]) -> str:
        """构建分析Markdown"""
        lines = ["## 实时分析\n"]

        # 引擎结果
        if engine_result:
            lines.append("### 引擎分析")
            lines.append(f"- **最佳着法**: {engine_result.get('bestmove', 'N/A')}")
            lines.append(f"- **评分**: {engine_result.get('score', 0):+.1f}")
            lines.append(f"- **深度**: {engine_result.get('depth', 0)}")
            lines.append("")

        # 知识图谱结果
        if kg_result:
            lines.append("### 历史数据")
            lines.append(f"- **开局名称**: {kg_result.get('opening_name', 'N/A')}")
            lines.append(f"- **胜率**: {kg_result.get('win_rate', 0):.1f}%")
            lines.append(f"- **总对局数**: {kg_result.get('total_games', 0)}")
            lines.append("")

        # 棋书引用
        if rag_results:
            lines.append("### 棋书引用")
            for i, result in enumerate(rag_results, 1):
                lines.append(f"{i}. **{result.get('book_name', 'N/A')}** (第{result.get('page', 0)}页)")
                lines.append(f"   {result.get('content', '')[:100]}...")
            lines.append("")

        if not engine_result and not kg_result and not rag_results:
            lines.append("等待分析...")

        return "\n".join(lines)
