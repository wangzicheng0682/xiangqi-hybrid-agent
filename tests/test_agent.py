"""
LangGraph Agent 测试用例

文档依据: PRD.md 2.5 智能代理编排 / TECH.md 2.4 Agent框架
"""

import pytest
from unittest.mock import Mock, patch
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestAgentState:
    """测试AgentState状态定义"""
    
    def test_create_initial_state(self):
        """测试创建初始状态"""
        from core.agent.state import create_initial_state
        
        fen = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"
        state = create_initial_state(fen=fen)
        
        assert state["fen"] == fen
        assert state["input_type"] == "fen"
        assert state["engine_result"] is None
        assert state["kg_result"] is None
        assert state["explanation"] == ""
    
    def test_create_initial_state_with_board(self):
        """测试带棋盘的初始状态"""
        from core.agent.state import create_initial_state
        
        board = [['r', 'n', 'b'], ['', '', '']]
        iccs_moves = ["h2e2", "h9g7"]
        last_move_info = {"from_pos": "h2", "to_pos": "e2"}
        
        state = create_initial_state(
            fen="test_fen",
            board=board,
            iccs_moves=iccs_moves,
            last_move_info=last_move_info,
            use_vision=True,
            red_to_move=False
        )
        
        assert state["board"] == board
        assert state["iccs_moves"] == iccs_moves
        assert state["last_move_info"] == last_move_info
        assert state["use_vision"] is True
        assert state["red_to_move"] is False


class TestEngineNode:
    """测试引擎分析节点"""
    
    def test_engine_node_basic(self):
        """测试引擎节点基本功能"""
        from core.agent.nodes.engine_node import engine_node
        from core.agent.state import create_initial_state
        
        fen = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"
        state = create_initial_state(fen=fen)
        
        result = engine_node(state)
        
        assert "engine_result" in result
        if result["engine_result"]:
            assert "bestmove" in result["engine_result"]
            assert "score" in result["engine_result"]


class TestKGNode:
    """测试知识图谱节点"""
    
    def test_kg_node_basic(self):
        """测试知识图谱节点基本功能"""
        from core.agent.nodes.kg_node import kg_node
        from core.agent.state import create_initial_state
        
        fen = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"
        state = create_initial_state(fen=fen, iccs_moves=["h2e2"])
        
        result = kg_node(state)
        
        assert "kg_result" in result


class TestRAGNode:
    """测试RAG检索节点"""
    
    def test_rag_node_basic(self):
        """测试RAG节点基本功能"""
        from core.agent.nodes.rag_node import rag_node
        from core.agent.state import create_initial_state
        
        fen = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"
        state = create_initial_state(fen=fen)
        state["engine_result"] = {"bestmove": "h2e2", "score": 0.5}
        
        result = rag_node(state)
        
        assert "rag_results" in result


class TestVisionNode:
    """测试视觉分析节点"""
    
    def test_vision_node_skip_when_disabled(self):
        """测试禁用视觉分析时跳过"""
        from core.agent.nodes.vision_node import vision_node
        from core.agent.state import create_initial_state
        
        state = create_initial_state(fen="test", use_vision=False)
        
        result = vision_node(state)
        
        assert result["vision_result"] is None
    
    def test_vision_node_skip_when_no_board(self):
        """测试无棋盘数据时跳过"""
        from core.agent.nodes.vision_node import vision_node
        from core.agent.state import create_initial_state
        
        state = create_initial_state(fen="test", board=None, use_vision=True)
        
        result = vision_node(state)
        
        assert result["vision_result"] is None


class TestExplainNode:
    """测试讲解生成节点"""
    
    def test_explain_node_with_engine_result(self):
        """测试有引擎结果时的讲解生成"""
        from core.agent.nodes.explain_node import explain_node
        from core.agent.state import create_initial_state
        
        state = create_initial_state(fen="test_fen", red_to_move=True)
        state["engine_result"] = {
            "bestmove": "h2e2",
            "score": 0.5,
            "depth": 15,
            "pv": ["h2e2", "h9g7"]
        }
        state["kg_result"] = {
            "opening_name": "中炮开局",
            "win_rate": 60.0,
            "statistics": "红方胜率较高"
        }
        
        result = explain_node(state)
        
        assert "explanation" in result
        assert len(result["explanation"]) > 0


class TestXiangqiAgent:
    """测试XiangqiAgent类"""
    
    def test_agent_creation(self):
        """测试Agent创建"""
        from core.agent import XiangqiAgent
        
        agent = XiangqiAgent()
        
        assert agent.graph is not None
    
    def test_agent_analyze_basic(self):
        """测试Agent基本分析"""
        from core.agent import XiangqiAgent
        
        agent = XiangqiAgent()
        fen = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"
        
        result = agent.analyze(fen=fen, use_vision=False)
        
        assert "fen" in result
        assert "explanation" in result
        assert result["fen"] == fen


class TestAgentWorkflow:
    """测试完整工作流"""
    
    def test_full_workflow(self):
        """测试完整工作流"""
        from core.agent import create_agent
        from core.agent.state import create_initial_state
        
        graph = create_agent()
        
        fen = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"
        initial_state = create_initial_state(fen=fen, use_vision=False)
        
        final_state = graph.invoke(initial_state)
        
        assert "explanation" in final_state
        assert len(final_state["explanation"]) > 0
