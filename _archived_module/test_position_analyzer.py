"""
局面分析器测试用例

测试三类局面：
1. 典型开局局面
2. 典型杀法局面
3. 边界异常局面
"""

import pytest
from core.semantic.position_analyzer import analyze_position, PositionAnalyzer
from core.semantic.position_analysis_schema import StandardizedPositionAnalysis


class TestOpeningPositions:
    """典型开局局面测试"""
    
    def test_initial_position(self):
        """测试初始局面"""
        fen = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"
        result = analyze_position(fen)
        
        assert result.turn == "red"
        assert len(result.pieces) == 32
        assert result.summary.red_piece_count == 16
        assert result.summary.black_piece_count == 16
        assert result.summary.red_material == result.summary.black_material
    
    def test_cannon_opening(self):
        """测试炮二平五开局"""
        fen = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"
        result = analyze_position(fen)
        
        cannons = [p for p in result.pieces if p.piece_type == 'cannon' and p.side == 'red']
        assert len(cannons) == 2
        
        for cannon in cannons:
            assert cannon.mobility is not None
            assert cannon.mobility.legal_count > 0
    
    def test_knight_opening(self):
        """测试马二进三开局"""
        fen = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"
        result = analyze_position(fen)
        
        knights = [p for p in result.pieces if p.piece_type == 'knight' and p.side == 'red']
        assert len(knights) == 2
        
        for knight in knights:
            blocked_constraints = [c for c in knight.constraints if c.kind == 'horse_leg_blocked']
            assert len(blocked_constraints) > 0


class TestTacticalPositions:
    """典型杀法局面测试"""
    
    def test_juocao_ma_check(self):
        """测试卧槽马将军"""
        fen = "4k4/9/9/9/9/9/9/9/4N4/4K4 w - - 0 1"
        result = analyze_position(fen)
        
        knights = [p for p in result.pieces if p.piece_type == 'knight']
        assert len(knights) == 1
        
        knight = knights[0]
        has_juocao = any("卧槽马" in p for p in knight.tactical_patterns)
        
        check_patterns = [p for p in result.global_patterns if p.pattern_type == 'check']
    
    def test_duijiang(self):
        """测试对将局面"""
        fen = "4k4/9/9/9/9/9/9/9/9/4K4 w - - 0 1"
        result = analyze_position(fen)
        
        duijiang_patterns = [p for p in result.global_patterns if p.pattern_type == 'duijiang']
        assert len(duijiang_patterns) == 1
        assert "对将" in duijiang_patterns[0].note
    
    def test_rook_check(self):
        """测试车将军"""
        fen = "4k4/9/9/9/9/9/9/9/4R4/4K4 w - - 0 1"
        result = analyze_position(fen)
        
        check_patterns = [p for p in result.global_patterns if p.pattern_type == 'check']
        assert len(check_patterns) > 0
    
    def test_cannon_check(self):
        """测试炮将军"""
        fen = "4k4/9/9/9/9/9/9/4C4/9/4K4 w - - 0 1"
        result = analyze_position(fen)
        
        cannons = [p for p in result.pieces if p.piece_type == 'cannon']
        assert len(cannons) == 1


class TestEdgeCases:
    """边界异常局面测试"""
    
    def test_king_in_corner(self):
        """测试将在角落"""
        fen = "k7/9/9/9/9/9/9/9/9/K7 w - - 0 1"
        result = analyze_position(fen)
        
        kings = [p for p in result.pieces if p.piece_type == 'king']
        assert len(kings) == 2
        
        for king in kings:
            assert king.mobility is not None
    
    def test_pawn_at_edge(self):
        """测试兵在边线"""
        fen = "4k4/9/9/9/9/9/9/9/9/P3K4 w - - 0 1"
        result = analyze_position(fen)
        
        pawns = [p for p in result.pieces if p.piece_type == 'pawn']
        assert len(pawns) == 1
        
        pawn = pawns[0]
        assert "edge_pawn" in pawn.positional_tags
    
    def test_single_piece(self):
        """测试单子局面"""
        fen = "4k4/9/9/9/9/9/9/9/9/4K4 w - - 0 1"
        result = analyze_position(fen)
        
        assert len(result.pieces) == 2
        assert result.summary.red_piece_count == 1
        assert result.summary.black_piece_count == 1
    
    def test_empty_board(self):
        """测试空棋盘（异常情况）"""
        fen = "4k4/9/9/9/9/9/9/9/9/4K4 w - - 0 1"
        result = analyze_position(fen)
        
        assert result is not None
        assert len(result.pieces) == 2
    
    def test_pawn_crossed_river(self):
        """测试过河兵"""
        fen = "4k4/9/9/9/4P4/9/9/9/9/4K4 w - - 0 1"
        result = analyze_position(fen)
        
        pawns = [p for p in result.pieces if p.piece_type == 'pawn']
        assert len(pawns) == 1
        
        pawn = pawns[0]
        assert "cross_river" in pawn.geometric_tags
    
    def test_elephant_cannot_cross_river(self):
        """测试象不能过河"""
        fen = "4k4/9/9/9/4B4/9/9/9/9/4K4 w - - 0 1"
        result = analyze_position(fen)
        
        elephants = [p for p in result.pieces if p.piece_type == 'elephant']
        assert len(elephants) == 1
        
        elephant = elephants[0]
        for move in elephant.legal_moves:
            assert move.to[0] >= 5


class TestSemanticTags:
    """语义标签测试"""
    
    def test_geometric_tags(self):
        """测试几何层标签"""
        fen = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"
        result = analyze_position(fen)
        
        for piece in result.pieces:
            if piece.legal_moves:
                assert "legal_move" in piece.geometric_tags
    
    def test_positional_tags(self):
        """测试位置层标签"""
        fen = "4k4/9/9/9/9/9/9/9/4R4/4K4 w - - 0 1"
        result = analyze_position(fen)
        
        rooks = [p for p in result.pieces if p.piece_type == 'rook']
        assert len(rooks) == 1
        
        rook = rooks[0]
        assert "center_file" in rook.positional_tags
    
    def test_tactical_patterns(self):
        """测试战术层标签"""
        fen = "4k4/9/9/9/9/9/9/9/4N4/4K4 w - - 0 1"
        result = analyze_position(fen)
        
        knights = [p for p in result.pieces if p.piece_type == 'knight']
        assert len(knights) == 1


class TestRetrievalTags:
    """检索标签测试"""
    
    def test_retrieval_tags_generated(self):
        """测试检索标签生成"""
        fen = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"
        result = analyze_position(fen)
        
        assert result.retrieval_info is not None
        assert len(result.retrieval_info.tags) > 0
    
    def test_retrieval_query_hints(self):
        """测试检索查询提示"""
        fen = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"
        result = analyze_position(fen)
        
        assert result.retrieval_info is not None


class TestOutputFormat:
    """输出格式测试"""
    
    def test_structured_output(self):
        """测试结构化输出"""
        fen = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"
        result = analyze_position(fen)
        
        structured = result.to_structured()
        
        assert "board_fen" in structured
        assert "turn" in structured
        assert "pieces" in structured
        assert "global_patterns" in structured
        assert "summary" in structured
    
    def test_text_output(self):
        """测试文本输出"""
        fen = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"
        result = analyze_position(fen)
        
        text_output = result.to_text()
        
        assert "analysis_text" in text_output
        assert "retrieval_tags" in text_output
        assert "retrieval_hints" in text_output
    
    def test_dict_output(self):
        """测试字典输出"""
        fen = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"
        result = analyze_position(fen)
        
        output = result.to_dict()
        
        assert "analysis_structured" in output
        assert "analysis_text" in output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
