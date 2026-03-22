"""
引擎分析节点 - 调用Pikafish进行战术计算

文档依据: PRD.md 2.2 战术计算引擎 / TECH.md 2.1 Pikafish
"""

from typing import Dict, Any, Optional
from ..state import AgentState

_engine_instance = None


def get_engine():
    global _engine_instance
    if _engine_instance is None:
        from core.engine import PikafishEngine
        try:
            _engine_instance = PikafishEngine()
            _engine_instance.start()
        except Exception as e:
            print(f"[EngineNode] 引擎初始化失败: {e}")
            from core.engine import MockEngine
            _engine_instance = MockEngine()
    return _engine_instance


def engine_node(state: AgentState) -> AgentState:
    """
    引擎分析节点
    
    功能:
        1. 调用Pikafish引擎分析当前局面
        2. 获取最佳着法、评估分数、主要变例
        3. 将结果写入状态
    
    文档依据: PRD.md 3.系统工作流程 Step 3 / TECH.md 2.1.2 UCI协议通信
    """
    fen = state.get("fen", "")
    
    if not fen:
        state["engine_result"] = None
        state["error"] = "引擎分析失败: 缺少FEN"
        return state
    
    try:
        engine = get_engine()
        result = engine.analyze(fen, depth=15)
        
        state["engine_result"] = {
            "bestmove": result.bestmove,
            "score": result.score,
            "depth": result.depth,
            "pv": result.pv if hasattr(result, 'pv') else []
        }
        
        print(f"[EngineNode] 分析完成: bestmove={result.bestmove}, score={result.score}")
        
    except Exception as e:
        print(f"[EngineNode] 分析失败: {e}")
        state["engine_result"] = None
        state["error"] = f"引擎分析失败: {str(e)[:50]}"
    
    return state
