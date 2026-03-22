"""
视觉分析节点 - 使用Qwen-VL进行多模态分析

文档依据: PRD.md 2.4.2 Qwen2.5-VL视觉模型 / TECH.md 2.3 视觉优先原则
"""

from typing import Dict, Any, Optional
from ..state import AgentState

_vision_instance = None


def get_vision_analyzer():
    global _vision_instance
    if _vision_instance is None:
        try:
            from core.vision import VisionAnalyzer, VisionConfig
            config = VisionConfig()
            _vision_instance = VisionAnalyzer(config)
            print("[VisionNode] VisionAnalyzer初始化成功")
        except Exception as e:
            print(f"[VisionNode] VisionAnalyzer初始化失败: {e}")
            _vision_instance = None
    return _vision_instance


def vision_node(state: AgentState) -> AgentState:
    """
    视觉分析节点
    
    功能:
        1. 生成棋盘图片
        2. 调用Qwen-VL进行多模态分析
        3. 返回视觉描述和局面理解
    
    文档依据: PRD.md 3.系统工作流程 Step 5 / TECH.md 2.3 视觉优先原则
    """
    if not state.get("use_vision", True):
        print("[VisionNode] 跳过视觉分析 (use_vision=False)")
        state["vision_result"] = None
        return state
    
    board = state.get("board")
    engine_result = state.get("engine_result")
    last_move_info = state.get("last_move_info")
    
    if not board:
        print("[VisionNode] 缺少棋盘数据，跳过视觉分析")
        state["vision_result"] = None
        return state
    
    try:
        vision = get_vision_analyzer()
        
        if vision is None:
            print("[VisionNode] VisionAnalyzer不可用")
            state["vision_result"] = None
            return state
        
        board_img = _render_board(board)
        
        bestmove = engine_result.get("bestmove") if engine_result else None
        score = engine_result.get("score") if engine_result else None
        
        analysis = vision.analyze_board_image(
            board_img,
            bestmove=bestmove,
            score=score,
            last_move_info=last_move_info
        )
        
        if analysis:
            state["vision_result"] = {
                "description": analysis,
                "confidence": 0.9
            }
            print(f"[VisionNode] 分析成功: {analysis[:50]}...")
        else:
            state["vision_result"] = None
            
    except Exception as e:
        print(f"[VisionNode] 分析失败: {e}")
        state["vision_result"] = None
    
    return state


def _render_board(board):
    """渲染棋盘图片"""
    from PIL import Image, ImageDraw, ImageFont
    
    CELL_SIZE = 60
    BOARD_WIDTH = CELL_SIZE * 9
    BOARD_HEIGHT = CELL_SIZE * 10
    
    PIECE_NAMES = {
        'K': '帅', 'k': '将', 'A': '仕', 'a': '士',
        'B': '相', 'b': '象', 'R': '车', 'r': '車',
        'C': '炮', 'c': '砲', 'N': '马', 'n': '馬',
        'P': '兵', 'p': '卒',
    }
    
    img = Image.new('RGB', (BOARD_WIDTH, BOARD_HEIGHT), '#f0d9b5')
    draw = ImageDraw.Draw(img)
    
    for i in range(10):
        y = i * CELL_SIZE
        draw.line([(0, y), (BOARD_WIDTH - 1, y)], fill='#8b4513', width=1)
    
    for i in range(9):
        x = i * CELL_SIZE
        draw.line([(x, 0), (x, BOARD_HEIGHT - 1)], fill='#8b4513', width=1)
    
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/simhei.ttf", 28)
    except:
        font = ImageFont.load_default()
    
    for row_idx, row in enumerate(board):
        for col_idx, piece in enumerate(row):
            if piece:
                x = col_idx * CELL_SIZE + CELL_SIZE // 2
                y = row_idx * CELL_SIZE + CELL_SIZE // 2
                
                is_red = piece.isupper()
                color = '#c0392b' if is_red else '#2c3e50'
                bg_color = '#f5deb3' if is_red else '#d5d8dc'
                
                r = 24
                draw.ellipse([x-r, y-r, x+r, y+r], fill=bg_color, outline=color, width=2)
                
                piece_name = PIECE_NAMES.get(piece, piece)
                bbox = draw.textbbox((0, 0), piece_name, font=font)
                text_w = bbox[2] - bbox[0]
                text_h = bbox[3] - bbox[1]
                draw.text((x - text_w//2, y - text_h//2 - 2), piece_name, fill=color, font=font)
    
    return img
