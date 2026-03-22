"""
复盘报告生成模块

文档依据: PRD.md 3.3.3 复盘报告内容

复盘报告包含:
    - 对局概览: 双方信息、对局结果、总步数
    - 胜率曲线: 展示胜率变化趋势
    - 关键局面: 标注关键转折点
    - 失误统计: 统计劣着数量和类型
    - 改进建议: 针对关键失误给出建议
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import json


@dataclass
class MoveRecord:
    move_number: int
    iccs_move: str
    fen_before: str
    fen_after: str
    score_before: float
    score_after: float
    score_change: float
    is_blunder: bool = False
    is_turning_point: bool = False
    piece: str = ""
    notation: str = ""


@dataclass
class GameRecord:
    red_player: str = "红方"
    black_player: str = "黑方"
    result: str = "*"  # "1-0", "0-1", "1/2-1/2", "*"
    moves: List[MoveRecord] = field(default_factory=list)
    iccs_moves: List[str] = field(default_factory=list)
    start_time: datetime = None
    end_time: datetime = None
    opening_name: str = ""


@dataclass
class TurningPoint:
    move_number: int
    score_change: float
    description: str
    is_red_move: bool
    fen: str


@dataclass
class ReviewReport:
    overview: str
    result_summary: str
    turning_points: List[TurningPoint]
    blunders_red: int
    blunders_black: int
    suggestions: List[str]
    score_history: List[float]
    move_analysis: List[Dict]


BLUNDER_THRESHOLD = 200  # 劣着阈值：2个兵的价值
TURNING_POINT_THRESHOLD = 300  # 胜负手阈值：3个兵的价值

PIECE_NAMES = {
    'K': '帅', 'k': '将', 'A': '仕', 'a': '士',
    'B': '相', 'b': '象', 'R': '车', 'r': '車',
    'C': '炮', 'c': '砲', 'N': '马', 'n': '馬',
    'P': '兵', 'p': '卒',
}


def identify_turning_points(scores: List[float], threshold: float = TURNING_POINT_THRESHOLD) -> List[TurningPoint]:
    """
    识别胜率曲线的转折点（胜负手）
    
    文档依据: PRD.md 3.3.4 胜负手识别算法
    
    Args:
        scores: 每步后的局面评分列表（红方视角）
        threshold: 转折点阈值（默认300 = 3个兵的价值）
        
    Returns:
        List[TurningPoint]: 转折点列表
    """
    turning_points = []
    
    for i in range(1, len(scores)):
        score_change = scores[i] - scores[i-1]
        
        if abs(score_change) > threshold:
            is_red_move = (i % 2 == 1)  # 奇数步是红方走
            
            if score_change > 0:
                description = f"红方{'扩大' if is_red_move else '挽回'}优势"
            else:
                description = f"黑方{'扩大' if not is_red_move else '挽回'}优势"
            
            turning_points.append(TurningPoint(
                move_number=i,
                score_change=score_change,
                description=description,
                is_red_move=is_red_move,
                fen=""  # 需要外部填充
            ))
    
    return turning_points


def identify_blunders(scores: List[float], threshold: float = BLUNDER_THRESHOLD) -> List[int]:
    """
    识别劣着
    
    Args:
        scores: 每步后的局面评分列表
        threshold: 劣着阈值
        
    Returns:
        List[int]: 劣着所在的步数列表
    """
    blunders = []
    
    for i in range(1, len(scores)):
        score_change = scores[i] - scores[i-1]
        is_red_move = (i % 2 == 1)
        
        # 红方走棋导致分数下降，或黑方走棋导致分数上升（对黑方不利）
        if is_red_move and score_change < -threshold:
            blunders.append(i)
        elif not is_red_move and score_change > threshold:
            blunders.append(i)
    
    return blunders


def generate_review_report(
    game: GameRecord,
    scores: List[float],
    fen_history: List[str] = None
) -> ReviewReport:
    """
    生成复盘报告
    
    文档依据: PRD.md 3.3.3 复盘报告内容
    
    Args:
        game: 对局记录
        scores: 每步后的评分列表
        fen_history: 每步后的FEN列表
        
    Returns:
        ReviewReport: 复盘报告
    """
    turning_points = identify_turning_points(scores)
    blunders = identify_blunders(scores)
    
    if fen_history:
        for i, tp in enumerate(turning_points):
            if tp.move_number < len(fen_history):
                tp.fen = fen_history[tp.move_number]
    
    blunders_red = sum(1 for b in blunders if b % 2 == 1)
    blunders_black = sum(1 for b in blunders if b % 2 == 0)
    
    suggestions = generate_suggestions(turning_points, blunders, scores)
    
    overview = generate_overview(game, len(scores) - 1)
    result_summary = generate_result_summary(scores, game.result)
    
    move_analysis = []
    for i, score in enumerate(scores):
        move_analysis.append({
            "move_number": i,
            "score": score,
            "is_turning_point": any(tp.move_number == i for tp in turning_points),
            "is_blunder": i in blunders
        })
    
    return ReviewReport(
        overview=overview,
        result_summary=result_summary,
        turning_points=turning_points,
        blunders_red=blunders_red,
        blunders_black=blunders_black,
        suggestions=suggestions,
        score_history=scores,
        move_analysis=move_analysis
    )


def generate_overview(game: GameRecord, total_moves: int) -> str:
    """生成对局概览"""
    lines = []
    lines.append(f"**对局双方**: {game.red_player} vs {game.black_player}")
    lines.append(f"**总步数**: {total_moves}步")
    
    if game.opening_name:
        lines.append(f"**开局**: {game.opening_name}")
    
    if game.result == "1-0":
        lines.append(f"**结果**: 红方胜")
    elif game.result == "0-1":
        lines.append(f"**结果**: 黑方胜")
    elif game.result == "1/2-1/2":
        lines.append(f"**结果**: 和棋")
    else:
        lines.append(f"**结果**: 未结束")
    
    return "\n".join(lines)


def generate_result_summary(scores: List[float], result: str) -> str:
    """生成结果摘要"""
    if not scores:
        return "无评分数据"
    
    final_score = scores[-1]
    
    if final_score > 500:
        return "红方大优，胜势已定"
    elif final_score > 200:
        return "红方明显优势"
    elif final_score > 50:
        return "红方稍优"
    elif final_score > -50:
        return "局面均势"
    elif final_score > -200:
        return "黑方稍优"
    elif final_score > -500:
        return "黑方明显优势"
    else:
        return "黑方大优，胜势已定"


def generate_suggestions(
    turning_points: List[TurningPoint],
    blunders: List[int],
    scores: List[float]
) -> List[str]:
    """生成改进建议"""
    suggestions = []
    
    if blunders:
        suggestions.append(f"本局共有{len(blunders)}步劣着，建议复盘时重点关注这些关键失误。")
    
    if turning_points:
        major_tp = [tp for tp in turning_points if abs(tp.score_change) > 500]
        if major_tp:
            suggestions.append(f"本局有{len(major_tp)}个重大转折点，这些时刻决定了胜负走向。")
    
    if not suggestions:
        suggestions.append("本局双方发挥稳定，无明显失误。")
    
    if scores and scores[-1] > 0:
        suggestions.append("红方整体表现较好，建议继续保持积极进攻的态势。")
    elif scores and scores[-1] < 0:
        suggestions.append("黑方整体表现较好，建议红方加强防守，寻找反击机会。")
    
    return suggestions


def format_report_markdown(report: ReviewReport) -> str:
    """
    将复盘报告格式化为Markdown
    
    Args:
        report: 复盘报告对象
        
    Returns:
        str: Markdown格式的报告
    """
    lines = []
    
    lines.append("# 📊 复盘报告\n")
    
    lines.append("## 📋 对局概览\n")
    lines.append(report.overview + "\n")
    
    lines.append("## 🎯 局势分析\n")
    lines.append(report.result_summary + "\n")
    
    lines.append("## 📈 关键转折点\n")
    if report.turning_points:
        for tp in report.turning_points:
            move_side = "红方" if tp.is_red_move else "黑方"
            direction = "↑" if tp.score_change > 0 else "↓"
            lines.append(f"- **第{tp.move_number}步** ({move_side}): {tp.description} ({direction}{abs(tp.score_change):.0f}分)")
    else:
        lines.append("- 本局无明显转折点\n")
    
    lines.append("\n## ⚠️ 失误统计\n")
    lines.append(f"- 红方劣着: {report.blunders_red}步")
    lines.append(f"- 黑方劣着: {report.blunders_black}步\n")
    
    lines.append("## 💡 改进建议\n")
    for i, suggestion in enumerate(report.suggestions, 1):
        lines.append(f"{i}. {suggestion}")
    
    return "\n".join(lines)


def format_report_html(report: ReviewReport) -> str:
    """
    将复盘报告格式化为HTML
    
    Args:
        report: 复盘报告对象
        
    Returns:
        str: HTML格式的报告
    """
    html = []
    
    html.append('<div class="review-report">')
    
    html.append('<h2>📋 对局概览</h2>')
    html.append(f'<p>{report.overview.replace(chr(10), "<br>")}</p>')
    
    html.append('<h2>🎯 局势分析</h2>')
    html.append(f'<p>{report.result_summary}</p>')
    
    html.append('<h2>📈 关键转折点</h2>')
    html.append('<ul>')
    for tp in report.turning_points:
        move_side = "红方" if tp.is_red_move else "黑方"
        html.append(f'<li>第{tp.move_number}步 ({move_side}): {tp.description}</li>')
    html.append('</ul>')
    
    html.append('<h2>⚠️ 失误统计</h2>')
    html.append(f'<p>红方劣着: {report.blunders_red}步 | 黑方劣着: {report.blunders_black}步</p>')
    
    html.append('<h2>💡 改进建议</h2>')
    html.append('<ol>')
    for suggestion in report.suggestions:
        html.append(f'<li>{suggestion}</li>')
    html.append('</ol>')
    
    html.append('</div>')
    
    return "".join(html)
