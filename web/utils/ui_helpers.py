"""
UI辅助函数 - 商业级用户体验

用途：提供专业的UI反馈、提示、通知系统
"""

import gradio as gr
from typing import Tuple, Optional, List


# toast通知管理器（商业级体验）
_toast_queue = []

def show_success(message: str, duration: float = 3.0):
    """
    显示成功通知

    Args:
        message: 成功消息
        duration: 显示时长（秒）
    """
    _toast_queue.append({
        'type': 'success',
        'message': message,
        'duration': duration
    })
    return f"✅ {message}"


def show_error(message: str, duration: float = 5.0):
    """
    显示错误通知

    Args:
        message: 错误消息
        duration: 显示时长（秒）
    """
    _toast_queue.append({
        'type': 'error',
        'message': message,
        'duration': duration
    })
    return f"❌ {message}"


def show_warning(message: str, duration: float = 3.0):
    """
    显示警告通知

    Args:
        message: 警告消息
        duration: 显示时长（秒）
    """
    _toast_queue.append({
        'type': 'warning',
        'message': message,
        'duration': duration
    })
    return f"⚠️  {message}"


def show_info(message: str, duration: float = 3.0):
    """
    显示信息通知

    Args:
        message: 信息消息
        duration: 显示时长（秒）
    """
    _toast_queue.append({
        'type': 'info',
        'message': message,
        'duration': duration
    })
    return f"ℹ️  {message}"


def get_latest_toast() -> Optional[dict]:
    """
    获取最新的通知消息（用于Gradio更新）

    Returns:
        通知字典或None
    """
    if _toast_queue:
        return _toast_queue[-1]
    return None


def clear_toast():
    """清除所有待显示的通知"""
    _toast_queue.clear()


def format_eval_score(score: float) -> str:
    """
    格式化评估分数为胜率百分比

    Args:
        score: 引擎评分（红方优势为正，黑方优势为负）

    Returns:
        格式化的胜率字符串
    """
    # 使用tanh函数将分数转换为胜率
    import math
    winrate = 50 + 50 * math.tanh(score / 1000)

    return f"{winrate:+.1f}%"


def get_eval_color(score: float) -> str:
    """
    获取评估分数对应的颜色

    Args:
        score: 引擎评分

    Returns:
        颜色代码（#RRGGBB）
    """
    if abs(score) < 50:
        # 平衡局面 - 灰色
        return "#808080"
    elif score > 0:
        # 红方优势 - 红色
        if score < 200:
            return "#E63946"  # 轻微优势
        elif score < 500:
            return "#FF6B6B"  # 明显优势
        else:
            return "#DC2626"  # 压倒性优势
    else:
        # 黑方优势 - 绿色
        if abs(score) < 200:
            return "#4CAF50"  # 轻微劣势
        elif abs(score) < 500:
            return "#38B000"  # 明显劣势
        else:
            return "#145A32"  # 压倒性劣势


def format_move_iccs(iccs_move: str) -> str:
    """
    格式化ICCS走法为中文描述

    Args:
        iccs_move: ICCS格式走法（如h2e2）

    Returns:
        中文走法描述
    """
    if not iccs_move or len(iccs_move) != 4:
        return iccs_move

    # 解析ICCS走法
    from_col, from_row = iccs_move[0], iccs_move[1]
    to_col, to_row = iccs_move[2], iccs_move[3]

    # 棋子名称映射
    piece_names = {
        'r': '车', 'n': '马', 'b': '相', 'a': '仕', 'k': '帅', 'c': '炮', 'p': '兵',
        'R': '車', 'N': '馬', 'B': '象', 'A': '士', 'K': '将', 'C': '砲', 'P': '卒',
    }

    # 列/行映射（转换为中文）
    col_names = ['九', '八', '七', '六', '五', '四', '三', '二', '一']
    piece_name = piece_names.get(iccs_move[0], '车')

    return f"{piece_name}：{col_names[int(to_row)]}{col_names[int(to_col)]} → {col_names[int(to_row)]}{col_names[int(to_col)]}"


def format_move_list(moves: List[str], current_move: int = 0) -> str:
    """
    格式化走法列表

    Args:
        moves: 走法列表
        current_move: 当前走法步数

    Returns:
        格式化的走法字符串
    """
    if not moves:
        return "暂无走法"

    formatted_moves = []
    for i, move in enumerate(moves):
        prefix = "▶ " if i == current_move else "  "
        formatted = format_move_iccs(move)
        formatted_moves.append(f"{prefix} {i+1}. {formatted}")

    return "\n".join(formatted_moves)


def create_progress_bar(progress: float, total: int, width: int = 300) -> str:
    """
    创建进度条HTML

    Args:
        progress: 当前进度
        total: 总量
        width: 进度条宽度

    Returns:
        进度条HTML字符串
    """
    percentage = min(100, int(progress / total * 100)) if total > 0 else 100

    # 根据进度选择颜色
    if percentage >= 90:
        color = "#4CAF50"  # 绿色
    elif percentage >= 60:
        color = "#FFC107"  # 橙色
    else:
        color = "#FF9800"  # 黄色

    return f"""
    <div style="width: {width}px; height: 20px; background: #E0E0E0; border-radius: 10px; overflow: hidden;">
        <div style="height: 100%; background: {color}; border-radius: 5px; transition: width 0.5s ease-in-out; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold;">
            {percentage}%
        </div>
    </div>
    """


def create_badge(text: str, badge_type: str = "default") -> str:
    """
    创建徽章标签

    Args:
        text: 徽章文本
        badge_type: 徽章类型（default, success, warning, danger）

    Returns:
        徽章HTML字符串
    """
    colors = {
        'default': '#2196F3',
        'success': '#4CAF50',
        'warning': '#FF9800',
        'danger': '#F44336'
    }

    color = colors.get(badge_type, colors['default'])

    return f"""
    <span style="background: {color}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; margin-left: 8px;">
        {text}
    </span>
    """


def create_info_card(title: str, content: str, icon: str = "ℹ️") -> str:
    """
    创建信息卡片

    Args:
        title: 卡片标题
        content: 卡片内容
        icon: 图标emoji

    Returns:
        信息卡片HTML字符串
    """
    return f"""
    <div style="background: white; border: 2px solid #E0E0E0; border-radius: 8px; padding: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
        <div style="font-size: 24px; margin-bottom: 12px;">{icon}</div>
        <div style="font-weight: bold; font-size: 18px; color: #2C3E50; margin-bottom: 8px;">{title}</div>
        <div style="color: #666; font-size: 14px; line-height: 1.6;">{content}</div>
    </div>
    """


def format_game_time(seconds: int) -> str:
    """
    格式化游戏时间

    Args:
        seconds: 游戏时长（秒）

    Returns:
        格式化的时间字符串
    """
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        return f"{hours}小时{minutes}分钟"
    elif minutes > 0:
        return f"{minutes}分钟{secs}秒"
    else:
        return f"{secs}秒"
