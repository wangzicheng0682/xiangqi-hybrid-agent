"""
讲解生成节点 - 综合所有结果生成自然语言讲解

文档依据: PRD.md 2.4.1 DeepSeek模型 / TECH.md 2.4 LLM核心
"""

from typing import Dict, Any, Optional
from ..state import AgentState

_llm_instance = None


def get_llm_client():
    global _llm_instance
    if _llm_instance is None:
        try:
            from core.llm import LLMClient, LLMConfig
            config = LLMConfig()
            _llm_instance = LLMClient(config)
            print("[ExplainNode] LLM客户端初始化成功")
        except Exception as e:
            print(f"[ExplainNode] LLM客户端初始化失败: {e}")
            _llm_instance = None
    return _llm_instance


def explain_node(state: AgentState) -> AgentState:
    """
    讲解生成节点
    
    功能:
        1. 综合引擎、知识图谱、RAG、视觉分析结果
        2. 调用LLM生成自然语言讲解
        3. 遵循"工具优先"和"引用优先"原则
    
    文档依据: PRD.md 3.系统工作流程 Step 6 / TECH.md 2.4 LLM核心
    """
    fen = state.get("fen", "")
    engine_result = state.get("engine_result")
    kg_result = state.get("kg_result")
    rag_results = state.get("rag_results", [])
    vision_result = state.get("vision_result")
    last_move_info = state.get("last_move_info")
    red_to_move = state.get("red_to_move", True)
    
    explanation_parts = []
    
    turn = "红方" if red_to_move else "黑方"
    explanation_parts.append(f"**当前回合**: {turn}走棋\n")
    
    if engine_result:
        explanation_parts.append(_format_engine_result(engine_result, red_to_move))
    
    if kg_result:
        explanation_parts.append(_format_kg_result(kg_result))
    
    if rag_results:
        explanation_parts.append(_format_rag_results(rag_results))
    
    if vision_result:
        explanation_parts.append(_format_vision_result(vision_result))
    
    try:
        llm = get_llm_client()
        
        if llm and engine_result and engine_result.get("bestmove"):
            llm_explanation = _generate_llm_explanation(
                llm, fen, engine_result, kg_result, 
                rag_results, vision_result, last_move_info, red_to_move
            )
            if llm_explanation:
                explanation_parts.append("\n### 🤖 AI讲解\n")
                explanation_parts.append(llm_explanation)
    except Exception as e:
        print(f"[ExplainNode] LLM生成失败: {e}")
    
    state["explanation"] = "\n".join(explanation_parts)
    print(f"[ExplainNode] 讲解生成完成，长度: {len(state['explanation'])}")
    
    return state


def _format_engine_result(result: Dict, red_to_move: bool) -> str:
    """格式化引擎结果"""
    parts = ["\n### 🤖 引擎分析\n"]
    
    if result.get("bestmove"):
        move_str = result["bestmove"]
        parts.append(f"- **推荐着法**: {move_str}\n")
    
    if result.get("score") is not None:
        score = result["score"]
        score_sign = "+" if (red_to_move and score > 0) or (not red_to_move and score < 0) else ""
        parts.append(f"- 评估分数: {score_sign}{score:.2f}\n")
    
    if result.get("depth"):
        parts.append(f"- 搜索深度: {result['depth']}\n")
    
    if result.get("pv"):
        parts.append(f"- 主要变例: {' → '.join(result['pv'][:5])}\n")
    
    return "".join(parts)


def _format_kg_result(result: Dict) -> str:
    """格式化知识图谱结果"""
    parts = ["\n### 📊 知识图谱统计\n"]
    
    if result.get("opening_name"):
        parts.append(f"- 开局: {result['opening_name']}\n")
    
    if result.get("win_rate", 0) > 0:
        parts.append(f"- 历史胜率: {result['win_rate']:.1f}%\n")
    
    if result.get("statistics"):
        parts.append(f"- {result['statistics']}\n")
    
    return "".join(parts)


def _format_rag_results(results: list) -> str:
    """格式化RAG检索结果"""
    if not results:
        return ""
    
    parts = ["\n### 📚 棋书引用\n"]
    
    for i, r in enumerate(results[:2], 1):
        if r.get("book_name") and r.get("content"):
            parts.append(f"{i}. [{r['book_name']}] {r['content'][:100]}...\n")
    
    return "".join(parts)


def _format_vision_result(result: Dict) -> str:
    """格式化视觉分析结果"""
    if not result or not result.get("description"):
        return ""
    
    parts = ["\n### 👁️ 多模态分析 (Qwen-VL-Max)\n"]
    parts.append(result["description"])
    parts.append("\n")
    
    return "".join(parts)


def _generate_llm_explanation(
    llm, fen: str, engine_result: Dict, 
    kg_result: Optional[Dict], rag_results: list,
    vision_result: Optional[Dict], last_move_info: Optional[Dict],
    red_to_move: bool
) -> Optional[str]:
    """调用LLM生成讲解"""
    try:
        from core.utils.board_text import create_llm_context
        
        context = create_llm_context(
            fen=fen,
            bestmove=engine_result.get("bestmove"),
            score=engine_result.get("score"),
            last_move_info=last_move_info
        )
        
        if hasattr(llm, 'explain_move'):
            explanation = llm.explain_move(
                fen=fen,
                bestmove=engine_result.get("bestmove"),
                score=engine_result.get("score"),
                last_move_info=last_move_info
            )
            return explanation
        
    except Exception as e:
        print(f"[ExplainNode] LLM调用失败: {e}")
    
    return None
