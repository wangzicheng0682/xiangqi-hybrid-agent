"""
胜率曲线可视化模块

文档依据: PRD.md 3.3.3 复盘报告内容 - 胜率曲线

功能:
    - 绘制胜率变化曲线
    - 标注关键转折点
    - 支持导出图片
"""

from typing import List, Optional, Tuple
import io
from dataclasses import dataclass


@dataclass
class ScorePoint:
    move_number: int
    score: float
    is_turning_point: bool = False
    is_blunder: bool = False
    label: str = ""


def score_to_winrate(score: float) -> float:
    """
    将引擎评分转换为胜率
    
    Args:
        score: 引擎评分（红方视角，单位：百分之一兵）
        
    Returns:
        float: 红方胜率（0-100）
    """
    import math
    
    score_cp = score / 100.0
    
    k = 0.02
    winrate = 50 + 50 * math.tanh(k * score_cp)
    
    return max(0, min(100, winrate))


def generate_score_chart(
    scores: List[float],
    turning_points: List[int] = None,
    blunders: List[int] = None,
    title: str = "胜率曲线",
    width: int = 800,
    height: int = 400
):
    """
    生成胜率曲线图
    
    Args:
        scores: 每步后的评分列表
        turning_points: 转折点步数列表
        blunders: 劣着步数列表
        title: 图表标题
        width: 图片宽度
        height: 图片高度
        
    Returns:
        PIL.Image: 胜率曲线图
    """
    try:
        import matplotlib.pyplot as plt
        import matplotlib
        matplotlib.use('Agg')
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
        plt.rcParams['axes.unicode_minus'] = False
    except ImportError:
        return _generate_simple_chart(scores, width, height)
    
    fig, ax = plt.subplots(figsize=(width / 100, height / 100), dpi=100)
    
    moves = list(range(len(scores)))
    winrates = [score_to_winrate(s) for s in scores]
    
    ax.plot(moves, winrates, 'b-', linewidth=2, label='红方胜率')
    
    ax.axhline(y=50, color='gray', linestyle='--', alpha=0.5, label='均势线')
    
    ax.fill_between(moves, 50, winrates, where=[w >= 50 for w in winrates], 
                    color='red', alpha=0.2, label='红方优势区')
    ax.fill_between(moves, 50, winrates, where=[w < 50 for w in winrates], 
                    color='black', alpha=0.2, label='黑方优势区')
    
    if turning_points:
        tp_scores = [winrates[i] for i in turning_points if i < len(winrates)]
        tp_moves = [i for i in turning_points if i < len(winrates)]
        ax.scatter(tp_moves, tp_scores, color='orange', s=100, zorder=5, 
                   marker='*', label='转折点')
    
    if blunders:
        blunder_scores = [winrates[i] for i in blunders if i < len(winrates)]
        blunder_moves = [i for i in blunders if i < len(winrates)]
        ax.scatter(blunder_moves, blunder_scores, color='red', s=80, zorder=5,
                   marker='x', label='劣着')
    
    ax.set_xlabel('回合数', fontsize=12)
    ax.set_ylabel('红方胜率 (%)', fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    
    ax.set_ylim(0, 100)
    ax.set_xlim(0, max(len(scores) - 1, 1))
    
    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.3)
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', dpi=100)
    buf.seek(0)
    plt.close()
    
    from PIL import Image
    return Image.open(buf)


def _generate_simple_chart(scores: List[float], width: int, height: int):
    """
    使用PIL生成简单图表（无matplotlib时使用）
    """
    from PIL import Image, ImageDraw, ImageFont
    
    img = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/simhei.ttf", 14)
        small_font = ImageFont.truetype("C:/Windows/Fonts/simhei.ttf", 10)
    except:
        font = ImageFont.load_default()
        small_font = font
    
    margin = 60
    chart_width = width - 2 * margin
    chart_height = height - 2 * margin
    
    draw.rectangle([margin, margin, margin + chart_width, margin + chart_height], 
                   outline='black', width=1)
    
    draw.line([(margin, margin + chart_height // 2), 
               (margin + chart_width, margin + chart_height // 2)],
              fill='gray', width=1)
    
    if len(scores) > 1:
        max_score = max(abs(s) for s in scores) or 1
        scale = (chart_height // 2 - 10) / max_score
        
        points = []
        for i, score in enumerate(scores):
            x = margin + (i / (len(scores) - 1)) * chart_width
            y = margin + chart_height // 2 - score * scale
            y = max(margin, min(margin + chart_height, y))
            points.append((x, y))
        
        for i in range(len(points) - 1):
            draw.line([points[i], points[i + 1]], fill='blue', width=2)
    
    draw.text((width // 2 - 40, 10), "胜率曲线", fill='black', font=font)
    draw.text((10, margin + chart_height // 2 - 5), "50%", fill='gray', font=small_font)
    draw.text((10, margin - 5), "100%", fill='red', font=small_font)
    draw.text((10, margin + chart_height - 5), "0%", fill='black', font=small_font)
    
    return img


def generate_score_data(scores: List[float]) -> dict:
    """
    生成胜率数据（供前端图表库使用）
    
    Args:
        scores: 每步后的评分列表
        
    Returns:
        dict: 图表数据
    """
    winrates = [score_to_winrate(s) for s in scores]
    
    return {
        "labels": list(range(len(scores))),
        "datasets": [{
            "label": "红方胜率",
            "data": winrates,
            "borderColor": "rgb(75, 192, 192)",
            "fill": True,
            "backgroundColor": "rgba(75, 192, 192, 0.2)"
        }]
    }


def analyze_game_flow(scores: List[float]) -> dict:
    """
    分析对局走势
    
    Args:
        scores: 每步后的评分列表
        
    Returns:
        dict: 对局走势分析
    """
    if not scores:
        return {"phase": "unknown", "description": "无数据"}
    
    final_score = scores[-1]
    
    if len(scores) < 10:
        phase = "开局"
        description = "对局刚开始"
    elif len(scores) < 40:
        phase = "中局"
        description = "进入中局阶段"
    else:
        phase = "残局"
        description = "进入残局阶段"
    
    volatility = sum(abs(scores[i] - scores[i-1]) for i in range(1, len(scores))) / len(scores)
    
    if volatility > 100:
        pace = "激烈"
    elif volatility > 50:
        pace = "正常"
    else:
        pace = "平稳"
    
    if final_score > 300:
        advantage = "红方大优"
    elif final_score > 100:
        advantage = "红方稍优"
    elif final_score > -100:
        advantage = "均势"
    elif final_score > -300:
        advantage = "黑方稍优"
    else:
        advantage = "黑方大优"
    
    return {
        "phase": phase,
        "description": description,
        "pace": pace,
        "advantage": advantage,
        "volatility": volatility,
        "final_score": final_score
    }
