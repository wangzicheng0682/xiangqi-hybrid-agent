"""
知识图谱节点 - 查询历史数据和胜率统计

文档依据: PRD.md 2.3.1 知识图谱 / TECH.md 2.2.1 Neo4j与图谱构建
"""

from typing import Dict, Any, Optional
from ..state import AgentState

_kg_instance = None


def get_kg():
    global _kg_instance
    if _kg_instance is None:
        try:
            from core.kg import Neo4jKG
            _kg_instance = Neo4jKG()
        except Exception as e:
            print(f"[KGNode] Neo4j连接失败: {e}")
            from core.kg import MockKG
            _kg_instance = MockKG()
    return _kg_instance


def kg_node(state: AgentState) -> AgentState:
    """
    知识图谱节点
    
    功能:
        1. 查询知识图谱获取历史胜率
        2. 检索相似局面
        3. 获取开局识别结果
    
    文档依据: PRD.md 3.系统工作流程 Step 4 / TECH.md 2.2.1 Neo4j与图谱构建
    """
    fen = state.get("fen", "")
    iccs_moves = state.get("iccs_moves", [])
    
    try:
        kg = get_kg()
        
        if hasattr(kg, 'query'):
            result = kg.query(fen, iccs_moves)
            
            if result:
                state["kg_result"] = {
                    "opening_name": result.opening_name or "",
                    "win_rate": result.win_rate or 0.0,
                    "total_games": getattr(result, 'total_games', 0),
                    "statistics": result.statistics or "",
                    "similar_positions": getattr(result, 'similar_positions', [])
                }
                print(f"[KGNode] 查询成功: opening={result.opening_name}, win_rate={result.win_rate}")
            else:
                state["kg_result"] = None
        else:
            state["kg_result"] = None
            
    except Exception as e:
        print(f"[KGNode] 查询失败: {e}")
        state["kg_result"] = None
    
    return state
