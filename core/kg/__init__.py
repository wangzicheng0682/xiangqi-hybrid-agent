"""知识图谱模块"""
from core.engine.base import KGResult, BaseKG
from .mock_kg import MockKG
from .neo4j_kg import Neo4jKG

__all__ = ['KGResult', 'BaseKG', 'MockKG', 'Neo4jKG']
