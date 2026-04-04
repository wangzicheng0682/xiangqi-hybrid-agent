"""
RAG检索节点 - 从棋书向量库检索相关内容

文档依据: PRD.md 2.3.2 书籍向量库 / TECH.md 2.2.2 向量数据库与RAG
"""

from typing import Dict, Any, List
from ..state import AgentState

_rag_instance = None


def get_rag():
    global _rag_instance
    if _rag_instance is None:
        try:
            from core.rag import ChromaRAG
            _rag_instance = ChromaRAG()
        except Exception:
            from core.rag import MockRAG
            _rag_instance = MockRAG()
    return _rag_instance


def rag_node(state: AgentState) -> AgentState:
    """
    RAG检索节点
    
    功能:
        1. 根据当前局面构建查询
        2. 从棋书向量库检索相关内容
        3. 返回相关棋书引用
    
    文档依据: PRD.md 3.系统工作流程 Step 4 / TECH.md 2.2.2 向量数据库与RAG
    """
    fen = state.get("fen", "")
    engine_result = state.get("engine_result")
    
    query_parts = []
    
    if engine_result and engine_result.get("bestmove"):
        query_parts.append(f"着法 {engine_result['bestmove']}")
    
    if state.get("iccs_moves"):
        opening_name = _identify_opening_from_moves(state["iccs_moves"])
        if opening_name:
            query_parts.append(opening_name)
    
    query = " ".join(query_parts) if query_parts else fen[:30]
    
    try:
        rag = get_rag()
        
        if hasattr(rag, 'retrieve'):
            results = rag.retrieve(query, top_k=3)
            
            rag_results = []
            for r in results:
                rag_results.append({
                    "book_name": r.book_name,
                    "content": r.content,
                    "relevance": r.relevance
                })
            
            state["rag_results"] = rag_results
            print(f"[RAGNode] 检索成功: {len(rag_results)} 条结果")
        else:
            state["rag_results"] = []
            
    except Exception as e:
        print(f"[RAGNode] 检索失败: {e}")
        state["rag_results"] = []
    
    return state


def _identify_opening_from_moves(moves: List[str]) -> str:
    """根据走法识别开局"""
    from core.opening import get_opening_name
    return get_opening_name(moves)
