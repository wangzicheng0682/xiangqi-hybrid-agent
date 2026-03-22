"""
预处理节点 - 判断输入类型，准备数据

文档依据: PRD.md 2.5.1 ReAct架构设计 / TECH.md 3.系统工作流程
"""

from typing import Dict, Any
from ..state import AgentState


def preprocess_node(state: AgentState) -> AgentState:
    """
    预处理节点
    
    功能:
        1. 判断输入类型 (fen/image)
        2. 如果是图片，调用视觉模型提取FEN
        3. 初始化状态字段
    
    文档依据: PRD.md 3.系统工作流程 Step 1-2
    """
    if state.get("input_type") == "image" and state.get("image_path"):
        pass
    
    if not state.get("fen"):
        state["error"] = "缺少FEN字符串"
    
    if "iccs_moves" not in state:
        state["iccs_moves"] = []
    
    if "last_move_info" not in state:
        state["last_move_info"] = None
    
    if "use_vision" not in state:
        state["use_vision"] = True
    
    return state
