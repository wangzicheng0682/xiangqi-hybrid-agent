"""
Neo4j Knowledge Graph Interface for Xiangqi

Features:
- Position query (win rate, game count)
- Similar position search
- Player statistics

Reference: PRD 3.1, TECH 5.2
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from neo4j import GraphDatabase
from core.engine.base import BaseKG, KGResult
from core.opening.opening_book import get_opening_name as get_book_opening_name, identify_position_type
import hashlib


def stable_hash(fen: str) -> int:
    h = hashlib.md5(fen.encode()).hexdigest()
    return int(h[:8], 16)


@dataclass
class PositionStats:
    fen: str
    total_games: int = 0
    red_wins: int = 0
    black_wins: int = 0
    draws: int = 0
    red_win_rate: float = 0.0
    black_win_rate: float = 0.0
    draw_rate: float = 0.0


@dataclass
class GameInfo:
    game_id: int
    red: str
    black: str
    event: str
    date: str
    result: str
    moves: List[str]


class Neo4jKG(BaseKG):
    def __init__(self, uri: str = "bolt://localhost:7687", 
                 username: str = "neo4j", 
                 password: str = "xiangqi123",
                 database: str = "neo4j"):
        self.uri = uri
        self.username = username
        self.password = password
        self.database = database
        self._driver = None
    
    def connect(self) -> bool:
        try:
            self._driver = GraphDatabase.driver(
                self.uri, 
                auth=(self.username, self.password)
            )
            self._driver.verify_connectivity()
            return True
        except Exception as e:
            print(f"Neo4j connection error: {e}")
            return False
    
    def close(self):
        if self._driver:
            self._driver.close()
    
    def _get_session(self):
        return self._driver.session(database=self.database)
    
    def query(self, fen: str, moves: List[str] = None) -> Optional[KGResult]:
        """
        BaseKG接口实现：查询知识图谱
        
        Args:
            fen: FEN串
            moves: 走法序列（用于开局识别）
            
        Returns:
            KGResult: 知识图谱检索结果
        """
        if not self._driver:
            return None
        
        stats = self.query_position(fen)
        
        position_type, position_desc = identify_position_type(fen)
        
        if moves:
            opening_name = get_book_opening_name(moves)
        else:
            opening_name = self._get_opening_name_from_fen(fen)
        
        if stats:
            return KGResult(
                win_rate=stats.red_win_rate,
                opening_name=opening_name,
                statistics=f"历史对局{stats.total_games}局，红方胜率{stats.red_win_rate:.1f}%，黑方胜率{stats.black_win_rate:.1f}%，和棋{stats.draw_rate:.1f}%"
            )
        else:
            return KGResult(
                win_rate=0.0,
                opening_name=opening_name,
                statistics=f"局面阶段：{position_type} - {position_desc}"
            )
    
    def _get_opening_name_from_fen(self, fen: str) -> str:
        """根据FEN简单判断开局名称（后备方案）"""
        if not fen:
            return "未知开局"
        
        board = fen.split()[0] if " " in fen else fen
        
        if board == "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR":
            return "初始局面"
        
        if "1C2C4" in board or "4C2C1" in board:
            return "中炮开局"
        if "1C2B2C1" in board or "1C2N2C1" in board:
            return "中炮开局"
        
        if "9/RNBAKABNR" in board and "P1P1P1P1P" in board:
            if "1C5C1" in board:
                return "飞相局"
            if "9/9/RNBAKABNR" in board:
                return "起马局"
        
        position_type, _ = identify_position_type(fen)
        return position_type
    
    def query_position(self, fen: str) -> Optional[PositionStats]:
        if not self._driver:
            return None
        
        board_fen = fen.split()[0] if fen else ""
        
        with self._get_session() as session:
            result = session.run("""
                MATCH (p:Position)
                WHERE p.fen CONTAINS $board_fen AND p.total_games > 0 AND p.red_win_rate IS NOT NULL
                RETURN p.fen as fen, p.total_games as total_games,
                       p.red_wins as red_wins, p.black_wins as black_wins,
                       p.draws as draws, p.red_win_rate as red_win_rate,
                       p.black_win_rate as black_win_rate, p.draw_rate as draw_rate
                ORDER BY p.total_games DESC
                LIMIT 1
            """, board_fen=board_fen)
            
            record = result.single()
            if record and record["total_games"] and record["total_games"] > 0:
                return PositionStats(
                    fen=record["fen"] or fen,
                    total_games=record["total_games"] or 0,
                    red_wins=record["red_wins"] or 0,
                    black_wins=record["black_wins"] or 0,
                    draws=record["draws"] or 0,
                    red_win_rate=(record["red_win_rate"] or 0.0) * 100,
                    black_win_rate=(record["black_win_rate"] or 0.0) * 100,
                    draw_rate=(record["draw_rate"] or 0.0) * 100,
                )
        return None
    
    def get_next_moves(self, fen: str) -> List[Dict[str, Any]]:
        if not self._driver:
            return []
        
        fen_hash = stable_hash(fen)
        
        with self._get_session() as session:
            result = session.run("""
                MATCH (p:Position {fen_hash: $fen_hash})-[r:NEXT]->(next:Position)
                RETURN r.move as move, next.fen_hash as next_hash,
                       next.total_games as games, next.red_win_rate as red_rate
                ORDER BY games DESC
                LIMIT 10
            """, fen_hash=fen_hash)
            
            moves = []
            for record in result:
                moves.append({
                    "move": record["move"],
                    "next_hash": record["next_hash"],
                    "games": record["games"] or 0,
                    "red_win_rate": record["red_rate"] or 0.0,
                })
            return moves
    
    def search_games(self, player: str = None, event: str = None, 
                     limit: int = 20) -> List[GameInfo]:
        if not self._driver:
            return []
        
        with self._get_session() as session:
            if player:
                result = session.run("""
                    MATCH (g:Game)
                    WHERE g.red CONTAINS $player OR g.black CONTAINS $player
                    RETURN g.id as id, g.red as red, g.black as black,
                           g.event as event, g.date as date, g.result as result
                    ORDER BY g.date DESC
                    LIMIT $limit
                """, player=player, limit=limit)
            elif event:
                result = session.run("""
                    MATCH (g:Game)
                    WHERE g.event CONTAINS $event
                    RETURN g.id as id, g.red as red, g.black as black,
                           g.event as event, g.date as date, g.result as result
                    ORDER BY g.date DESC
                    LIMIT $limit
                """, event=event, limit=limit)
            else:
                return []
            
            games = []
            for record in result:
                games.append(GameInfo(
                    game_id=record["id"],
                    red=record["red"] or "",
                    black=record["black"] or "",
                    event=record["event"] or "",
                    date=record["date"] or "",
                    result=record["result"] or "",
                    moves=[],
                ))
            return games
    
    def get_statistics(self) -> Dict[str, int]:
        if not self._driver:
            return {}
        
        with self._get_session() as session:
            games = session.run("MATCH (g:Game) RETURN count(g) as cnt").single()["cnt"]
            positions = session.run("MATCH (p:Position) RETURN count(p) as cnt").single()["cnt"]
            players = session.run("MATCH (p:Player) RETURN count(p) as cnt").single()["cnt"]
            moves = session.run("MATCH ()-[r:HAS_POSITION]->() RETURN count(r) as cnt").single()["cnt"]
            
            return {
                "games": games,
                "positions": positions,
                "players": players,
                "moves": moves,
            }
