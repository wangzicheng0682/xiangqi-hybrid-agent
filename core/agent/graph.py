"""
LangGraph Agent 工作流图

文档依据: PRD.md 2.5 智能代理编排 / TECH.md 2.4 Agent框架

工作流程:
    START -> preprocess -> engine -> kg -> rag -> vision -> explain -> END
"""

from typing import TypedDict, Optional, List, Dict, Any
from langgraph.graph import StateGraph, END

from .state import AgentState, create_initial_state
from .nodes import (
    preprocess_node,
    engine_node,
    kg_node,
    rag_node,
    vision_node,
    explain_node
)


def create_agent() -> StateGraph:
    """
    创建LangGraph Agent工作流
    
    文档依据: PRD.md 2.5.1 ReAct架构设计
    
    节点说明:
        - preprocess: 预处理，判断输入类型
        - engine: 引擎分析，获取最佳着法
        - kg: 知识图谱查询，获取历史数据
        - rag: RAG检索，获取棋书引用
        - vision: 视觉分析，多模态理解
        - explain: 讲解生成，综合输出
    
    Returns:
        StateGraph: 编译后的工作流图
    """
    workflow = StateGraph(AgentState)
    
    workflow.add_node("preprocess", preprocess_node)
    workflow.add_node("engine", engine_node)
    workflow.add_node("kg", kg_node)
    workflow.add_node("rag", rag_node)
    workflow.add_node("vision", vision_node)
    workflow.add_node("explain", explain_node)
    
    workflow.set_entry_point("preprocess")
    
    workflow.add_edge("preprocess", "engine")
    workflow.add_edge("engine", "kg")
    workflow.add_edge("kg", "rag")
    workflow.add_edge("rag", "vision")
    workflow.add_edge("vision", "explain")
    workflow.add_edge("explain", END)
    
    return workflow.compile()


class XiangqiAgent:
    """
    象棋分析Agent
    
    文档依据: PRD.md 2.5 智能代理编排
    
    Usage:
        agent = XiangqiAgent()
        result = agent.analyze(fen, board, iccs_moves, last_move_info)
        print(result["explanation"])
    """
    
    def __init__(self):
        self.graph = create_agent()
        print("[XiangqiAgent] Agent初始化完成")
    
    def analyze(
        self,
        fen: str,
        board: List[List[str]] = None,
        iccs_moves: List[str] = None,
        last_move_info: Dict = None,
        use_vision: bool = True,
        red_to_move: bool = True
    ) -> Dict[str, Any]:
        """
        分析象棋局面
        
        Args:
            fen: 局面FEN字符串
            board: 棋盘二维数组（用于视觉分析）
            iccs_moves: ICCS格式走法历史
            last_move_info: 最后一步走法信息
            use_vision: 是否使用视觉分析
            red_to_move: 是否红方走棋
            
        Returns:
            Dict: 包含explanation和各项分析结果
        """
        initial_state = create_initial_state(
            fen=fen,
            board=board,
            iccs_moves=iccs_moves,
            last_move_info=last_move_info,
            use_vision=use_vision,
            red_to_move=red_to_move
        )
        
        print(f"[XiangqiAgent] 开始分析: {fen[:30]}...")
        
        final_state = self.graph.invoke(initial_state)
        
        return {
            "fen": final_state.get("fen", ""),
            "explanation": final_state.get("explanation", ""),
            "engine_result": final_state.get("engine_result"),
            "kg_result": final_state.get("kg_result"),
            "rag_results": final_state.get("rag_results", []),
            "vision_result": final_state.get("vision_result"),
            "error": final_state.get("error", "")
        }
    
    def stream_analyze(
        self,
        fen: str,
        board: List[List[str]] = None,
        iccs_moves: List[str] = None,
        last_move_info: Dict = None,
        use_vision: bool = True,
        red_to_move: bool = True
    ):
        """
        流式分析（返回每个节点的中间结果）
        
        Args:
            同analyze方法
            
        Yields:
            Tuple[str, AgentState]: (节点名称, 当前状态)
        """
        initial_state = create_initial_state(
            fen=fen,
            board=board,
            iccs_moves=iccs_moves,
            last_move_info=last_move_info,
            use_vision=use_vision,
            red_to_move=red_to_move
        )
        
        for node_name, state in self.graph.stream(initial_state):
            yield node_name, state


_agent_instance = None


def get_agent() -> XiangqiAgent:
    """获取全局Agent实例"""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = XiangqiAgent()
    return _agent_instance
