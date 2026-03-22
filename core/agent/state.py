"""
AgentState - LangGraph Agent 状态定义

文档依据: PRD.md 2.5.2 状态管理 / TECH.md 6.2 状态Schema扩展

状态流转:
    preprocess -> engine -> kg -> rag -> vision -> explain -> END
"""

from typing import TypedDict, Optional, List, Dict, Any
from dataclasses import dataclass, field


@dataclass
class EngineResult:
    bestmove: Optional[str] = None
    score: float = 0.0
    pv: List[str] = field(default_factory=list)
    depth: int = 0
    nodes: int = 0
    time_ms: int = 0


@dataclass
class KGResult:
    opening_name: str = ""
    win_rate: float = 0.0
    total_games: int = 0
    statistics: str = ""
    similar_positions: List[Dict] = field(default_factory=list)


@dataclass
class RAGResult:
    book_name: str = ""
    content: str = ""
    relevance: float = 0.0
    page: int = 0


@dataclass
class VisionResult:
    fen: str = ""
    description: str = ""
    pieces: List[Dict] = field(default_factory=list)
    confidence: float = 0.0


@dataclass
class LastMoveInfo:
    from_pos: str = ""
    to_pos: str = ""
    piece: str = ""
    captured: str = ""
    notation: str = ""


class AgentState(TypedDict, total=False):
    """
    Agent全局状态
    
    文档依据: PRD.md 2.5.2 状态管理
    
    状态字段说明:
        input_type: 输入类型 ("fen" 或 "image")
        fen: 当前局面FEN字符串
        image_path: 图片路径（如果是图片输入）
        board: 棋盘二维数组（用于视觉分析）
        iccs_moves: ICCS格式走法历史
        last_move_info: 最后一步走法信息
        
        visual_desc: 视觉描述（来自Qwen-VL）
        engine_result: 引擎分析结果
        kg_result: 知识图谱查询结果
        rag_results: RAG检索结果列表
        vision_result: 视觉分析结果
        
        explanation: 最终讲解文本
        error: 错误信息
        
        use_vision: 是否使用视觉分析
        red_to_move: 是否红方走棋
    """
    input_type: str
    fen: str
    image_path: str
    board: List[List[str]]
    iccs_moves: List[str]
    last_move_info: Optional[Dict[str, Any]]
    
    visual_desc: str
    engine_result: Optional[Dict[str, Any]]
    kg_result: Optional[Dict[str, Any]]
    rag_results: List[Dict[str, Any]]
    vision_result: Optional[Dict[str, Any]]
    
    explanation: str
    error: str
    
    use_vision: bool
    red_to_move: bool


def create_initial_state(
    fen: str,
    board: List[List[str]] = None,
    iccs_moves: List[str] = None,
    last_move_info: Dict = None,
    use_vision: bool = True,
    red_to_move: bool = True
) -> AgentState:
    """
    创建初始状态
    
    Args:
        fen: 局面FEN字符串
        board: 棋盘二维数组
        iccs_moves: ICCS格式走法历史
        last_move_info: 最后一步走法信息
        use_vision: 是否使用视觉分析
        red_to_move: 是否红方走棋
        
    Returns:
        AgentState: 初始化的状态字典
    """
    return AgentState(
        input_type="fen",
        fen=fen,
        image_path="",
        board=board or [],
        iccs_moves=iccs_moves or [],
        last_move_info=last_move_info,
        visual_desc="",
        engine_result=None,
        kg_result=None,
        rag_results=[],
        vision_result=None,
        explanation="",
        error="",
        use_vision=use_vision,
        red_to_move=red_to_move
    )
