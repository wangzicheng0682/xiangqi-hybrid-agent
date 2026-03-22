"""
Pikafish 引擎测试

Reference:
  - PRD: Sprint 2 / 引擎集成
  - TECH: Pikafish(UCI)
"""

import pytest
from pathlib import Path

from core.engine import PikafishEngine, EngineResult


INITIAL_FEN = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"


class TestPikafishEngine:
    def test_engine_exists(self):
        engine = PikafishEngine()
        assert engine.engine_path.exists(), f"Engine not found at {engine.engine_path}"
    
    def test_engine_init(self):
        engine = PikafishEngine()
        try:
            engine.start()
            assert engine.is_ready()
        finally:
            engine.stop()
    
    def test_analyze_initial_position(self):
        engine = PikafishEngine()
        try:
            result = engine.analyze(INITIAL_FEN, depth=10)
            assert isinstance(result, EngineResult)
            assert result.bestmove, "Should have a bestmove"
            assert result.depth >= 10, f"Depth should be >= 10, got {result.depth}"
            assert len(result.pv) > 0, "Should have PV moves"
        finally:
            engine.stop()
    
    def test_context_manager(self):
        with PikafishEngine() as engine:
            assert engine.is_ready()
            result = engine.analyze(INITIAL_FEN, depth=8)
            assert result.bestmove
    
    def test_score_parsing(self):
        with PikafishEngine() as engine:
            result = engine.analyze(INITIAL_FEN, depth=12)
            assert isinstance(result.score, float)
