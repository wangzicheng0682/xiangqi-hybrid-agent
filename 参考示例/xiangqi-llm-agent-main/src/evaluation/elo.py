"""
ELO评分系统
维护agent的ELO分数,支持多版本agent对比
"""
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import sqlite3
import json
import logging
import os

logger = logging.getLogger(__name__)


# ============ 数据类定义 ============

class GameResult(Enum):
    """对局结果"""
    WIN = "WIN"
    LOSS = "LOSS"
    DRAW = "DRAW"


@dataclass
class Agent:
    """Agent信息"""
    agent_id: str                          # Agent唯一标识
    name: str                              # Agent名称
    version: str                           # 版本号
    elo: float = 1500.0                   # ELO分数(默认1500)
    games_played: int = 0                  # 对局数
    wins: int = 0                          # 胜局数
    losses: int = 0                        # 负局数
    draws: int = 0                         # 和局数
    created_at: Optional[datetime] = None  # 创建时间
    updated_at: Optional[datetime] = None # 更新时间
    metadata: Optional[Dict[str, Any]] = None  # 额外元数据
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "version": self.version,
            "elo": self.elo,
            "games_played": self.games_played,
            "wins": self.wins,
            "losses": self.losses,
            "draws": self.draws,
            "win_rate": self.win_rate,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "metadata": self.metadata
        }
    
    @property
    def win_rate(self) -> float:
        """胜率"""
        if self.games_played == 0:
            return 0.0
        return self.wins / self.games_played
    
    @property
    def full_name(self) -> str:
        """完整名称(包含版本)"""
        return f"{self.name} v{self.version}"


@dataclass
class MatchRecord:
    """对局记录"""
    match_id: str                          # 对局ID
    agent1_id: str                         # Agent1 ID
    agent2_id: str                         # Agent2 ID
    agent1_elo_before: float               # Agent1对局前ELO
    agent2_elo_before: float               # Agent2对局前ELO
    agent1_elo_after: float                # Agent1对局后ELO
    agent2_elo_after: float                # Agent2对局后ELO
    result: GameResult                     # 对局结果(从agent1视角)
    played_at: datetime                    # 对局时间
    metadata: Optional[Dict[str, Any]] = None  # 额外元数据
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "match_id": self.match_id,
            "agent1_id": self.agent1_id,
            "agent2_id": self.agent2_id,
            "agent1_elo_before": self.agent1_elo_before,
            "agent2_elo_before": self.agent2_elo_before,
            "agent1_elo_after": self.agent1_elo_after,
            "agent2_elo_after": self.agent2_elo_after,
            "result": self.result.value,
            "played_at": self.played_at.isoformat(),
            "metadata": self.metadata
        }


@dataclass
class EloConfig:
    """ELO配置"""
    k_factor: float = 32.0                 # K因子(默认32)
    initial_elo: float = 1500.0            # 初始ELO分数
    min_elo: float = 0.0                   # 最小ELO分数
    max_elo: float = 3000.0                 # 最大ELO分数


# ============ 数据库模式 ============

AGENTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS agents (
    agent_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    elo REAL NOT NULL DEFAULT 1500.0,
    games_played INTEGER NOT NULL DEFAULT 0,
    wins INTEGER NOT NULL DEFAULT 0,
    losses INTEGER NOT NULL DEFAULT 0,
    draws INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT,
    UNIQUE(name, version)
);
"""

AGENTS_INDEXES_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_agent_name ON agents(name);",
    "CREATE INDEX IF NOT EXISTS idx_agent_version ON agents(version);",
    "CREATE INDEX IF NOT EXISTS idx_agent_elo ON agents(elo DESC);",
    "CREATE INDEX IF NOT EXISTS idx_agent_name_version ON agents(name, version);",
]

MATCHES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS matches (
    match_id TEXT PRIMARY KEY,
    agent1_id TEXT NOT NULL,
    agent2_id TEXT NOT NULL,
    agent1_elo_before REAL NOT NULL,
    agent2_elo_before REAL NOT NULL,
    agent1_elo_after REAL NOT NULL,
    agent2_elo_after REAL NOT NULL,
    result TEXT NOT NULL,
    played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT,
    FOREIGN KEY (agent1_id) REFERENCES agents(agent_id),
    FOREIGN KEY (agent2_id) REFERENCES agents(agent_id)
);
"""

MATCHES_INDEXES_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_match_agent1 ON matches(agent1_id);",
    "CREATE INDEX IF NOT EXISTS idx_match_agent2 ON matches(agent2_id);",
    "CREATE INDEX IF NOT EXISTS idx_match_played_at ON matches(played_at DESC);",
]


# ============ ELO计算器 ============

class EloCalculator:
    """ELO分数计算器"""
    
    def __init__(self, config: Optional[EloConfig] = None):
        """
        初始化计算器
        
        Args:
            config: ELO配置
        """
        self.config = config or EloConfig()
    
    def expected_score(self, elo1: float, elo2: float) -> float:
        """
        计算预期得分
        
        Args:
            elo1: Agent1的ELO分数
            elo2: Agent2的ELO分数
            
        Returns:
            Agent1的预期得分(0-1之间)
        """
        return 1.0 / (1.0 + 10.0 ** ((elo2 - elo1) / 400.0))
    
    def update_elo(
        self,
        elo1: float,
        elo2: float,
        result: GameResult
    ) -> Tuple[float, float]:
        """
        更新ELO分数
        
        Args:
            elo1: Agent1的当前ELO
            elo2: Agent2的当前ELO
            result: 对局结果(从Agent1视角)
            
        Returns:
            (Agent1新ELO, Agent2新ELO)
        """
        # 计算预期得分
        expected1 = self.expected_score(elo1, elo2)
        expected2 = 1.0 - expected1
        
        # 实际得分
        if result == GameResult.WIN:
            actual1 = 1.0
            actual2 = 0.0
        elif result == GameResult.LOSS:
            actual1 = 0.0
            actual2 = 1.0
        else:  # DRAW
            actual1 = 0.5
            actual2 = 0.5
        
        # 更新ELO
        new_elo1 = elo1 + self.config.k_factor * (actual1 - expected1)
        new_elo2 = elo2 + self.config.k_factor * (actual2 - expected2)
        
        # 限制范围
        new_elo1 = max(self.config.min_elo, min(self.config.max_elo, new_elo1))
        new_elo2 = max(self.config.min_elo, min(self.config.max_elo, new_elo2))
        
        return new_elo1, new_elo2
    
    def elo_difference(self, elo1: float, elo2: float) -> float:
        """
        计算ELO差异
        
        Args:
            elo1: Agent1的ELO
            elo2: Agent2的ELO
            
        Returns:
            ELO差异(正数表示Agent1更强)
        """
        return elo1 - elo2


# ============ ELO管理器 ============

class EloManager:
    """
    ELO评分管理器
    
    功能:
    - Agent注册和管理
    - ELO分数计算和更新
    - 对局记录
    - 多版本对比
    """
    
    def __init__(self, db_path: str = "data/elo.db", config: Optional[EloConfig] = None):
        """
        初始化管理器
        
        Args:
            db_path: 数据库路径
            config: ELO配置
        """
        self.db_path = db_path
        self.config = config or EloConfig()
        self.calculator = EloCalculator(self.config)
        self.conn: Optional[sqlite3.Connection] = None
        
        # 确保目录存在
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        logger.info(f"ELO管理器初始化: {db_path}")
    
    def connect(self):
        """连接数据库"""
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            logger.info(f"数据库连接成功: {self.db_path}")
    
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            self.conn = None
            logger.info("数据库连接已关闭")
    
    def initialize_schema(self):
        """初始化数据库模式"""
        self.connect()
        cursor = self.conn.cursor()
        
        try:
            # 创建表
            logger.info("创建agents表...")
            cursor.execute(AGENTS_TABLE_SQL)
            
            logger.info("创建matches表...")
            cursor.execute(MATCHES_TABLE_SQL)
            
            # 创建索引
            logger.info("创建索引...")
            for index_sql in AGENTS_INDEXES_SQL:
                cursor.execute(index_sql)
            
            for index_sql in MATCHES_INDEXES_SQL:
                cursor.execute(index_sql)
            
            self.conn.commit()
            logger.info("数据库模式初始化完成")
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"初始化数据库失败: {e}")
            raise
    
    # ============ Agent管理 ============
    
    def register_agent(
        self,
        name: str,
        version: str,
        initial_elo: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Agent:
        """
        注册新Agent
        
        Args:
            name: Agent名称
            version: 版本号
            initial_elo: 初始ELO分数(可选)
            metadata: 额外元数据(可选)
            
        Returns:
            Agent对象
            
        Raises:
            ValueError: Agent已存在
        """
        self.connect()
        cursor = self.conn.cursor()
        
        # 生成唯一ID
        agent_id = f"{name}_{version}"
        
        # 检查是否已存在
        cursor.execute("SELECT * FROM agents WHERE agent_id = ?", (agent_id,))
        if cursor.fetchone():
            raise ValueError(f"Agent已存在: {agent_id}")
        
        # 创建Agent
        elo = initial_elo if initial_elo is not None else self.config.initial_elo
        now = datetime.now()
        
        agent = Agent(
            agent_id=agent_id,
            name=name,
            version=version,
            elo=elo,
            created_at=now,
            updated_at=now,
            metadata=metadata
        )
        
        # 插入数据库
        cursor.execute("""
            INSERT INTO agents (
                agent_id, name, version, elo, games_played,
                wins, losses, draws, created_at, updated_at, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            agent.agent_id,
            agent.name,
            agent.version,
            agent.elo,
            agent.games_played,
            agent.wins,
            agent.losses,
            agent.draws,
            agent.created_at.isoformat(),
            agent.updated_at.isoformat(),
            json.dumps(metadata) if metadata else None
        ))
        
        self.conn.commit()
        
        logger.info(f"注册Agent: {agent.full_name} (ELO: {elo})")
        
        return agent
    
    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """
        获取Agent信息
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Agent对象,不存在返回None
        """
        self.connect()
        cursor = self.conn.cursor()
        
        cursor.execute("SELECT * FROM agents WHERE agent_id = ?", (agent_id,))
        row = cursor.fetchone()
        
        if row:
            return self._row_to_agent(row)
        
        return None
    
    def get_agent_by_name_version(self, name: str, version: str) -> Optional[Agent]:
        """
        根据名称和版本获取Agent
        
        Args:
            name: Agent名称
            version: 版本号
            
        Returns:
            Agent对象,不存在返回None
        """
        agent_id = f"{name}_{version}"
        return self.get_agent(agent_id)
    
    def list_agents(
        self,
        name: Optional[str] = None,
        min_elo: Optional[float] = None,
        limit: Optional[int] = None,
        order_by: str = "elo"
    ) -> List[Agent]:
        """
        列出Agent
        
        Args:
            name: 过滤名称(可选)
            min_elo: 最小ELO(可选)
            limit: 限制数量(可选)
            order_by: 排序字段(默认elo)
            
        Returns:
            Agent列表
        """
        self.connect()
        cursor = self.conn.cursor()
        
        conditions = []
        params = []
        
        if name:
            conditions.append("name = ?")
            params.append(name)
        
        if min_elo is not None:
            conditions.append("elo >= ?")
            params.append(min_elo)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        # 排序
        valid_order_by = ["elo", "games_played", "wins", "win_rate", "created_at"]
        if order_by not in valid_order_by:
            order_by = "elo"
        
        if order_by == "win_rate":
            # 胜率需要计算
            order_clause = "ORDER BY CAST(wins AS REAL) / NULLIF(games_played, 0) DESC"
        else:
            order_clause = f"ORDER BY {order_by} DESC"
        
        sql = f"SELECT * FROM agents WHERE {where_clause} {order_clause}"
        
        if limit:
            sql += f" LIMIT ?"
            params.append(limit)
        
        cursor.execute(sql, params)
        
        agents = [self._row_to_agent(row) for row in cursor.fetchall()]
        
        return agents
    
    def get_agent_versions(self, name: str) -> List[Agent]:
        """
        获取指定名称的所有版本
        
        Args:
            name: Agent名称
            
        Returns:
            Agent版本列表(按ELO排序)
        """
        return self.list_agents(name=name, order_by="elo")
    
    # ============ 对局记录 ============
    
    def record_match(
        self,
        agent1_id: str,
        agent2_id: str,
        result: GameResult,
        match_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> MatchRecord:
        """
        记录对局结果并更新ELO
        
        Args:
            agent1_id: Agent1 ID
            agent2_id: Agent2 ID
            result: 对局结果(从Agent1视角)
            match_id: 对局ID(可选,自动生成)
            metadata: 额外元数据(可选)
            
        Returns:
            对局记录
            
        Raises:
            ValueError: Agent不存在
        """
        self.connect()
        cursor = self.conn.cursor()
        
        # 获取Agent信息
        agent1 = self.get_agent(agent1_id)
        agent2 = self.get_agent(agent2_id)
        
        if not agent1:
            raise ValueError(f"Agent不存在: {agent1_id}")
        if not agent2:
            raise ValueError(f"Agent不存在: {agent2_id}")
        
        # 记录对局前ELO
        elo1_before = agent1.elo
        elo2_before = agent2.elo
        
        # 计算新ELO
        elo1_after, elo2_after = self.calculator.update_elo(
            elo1_before,
            elo2_before,
            result
        )
        
        # 更新Agent统计
        agent1.games_played += 1
        agent2.games_played += 1
        
        if result == GameResult.WIN:
            agent1.wins += 1
            agent2.losses += 1
        elif result == GameResult.LOSS:
            agent1.losses += 1
            agent2.wins += 1
        else:  # DRAW
            agent1.draws += 1
            agent2.draws += 1
        
        agent1.elo = elo1_after
        agent2.elo = elo2_after
        agent1.updated_at = datetime.now()
        agent2.updated_at = datetime.now()
        
        # 更新数据库
        cursor.execute("""
            UPDATE agents SET
                elo = ?,
                games_played = ?,
                wins = ?,
                losses = ?,
                draws = ?,
                updated_at = ?
            WHERE agent_id = ?
        """, (
            agent1.elo, agent1.games_played, agent1.wins,
            agent1.losses, agent1.draws, agent1.updated_at.isoformat(),
            agent1.agent_id
        ))
        
        cursor.execute("""
            UPDATE agents SET
                elo = ?,
                games_played = ?,
                wins = ?,
                losses = ?,
                draws = ?,
                updated_at = ?
            WHERE agent_id = ?
        """, (
            agent2.elo, agent2.games_played, agent2.wins,
            agent2.losses, agent2.draws, agent2.updated_at.isoformat(),
            agent2.agent_id
        ))
        
        # 生成对局ID
        if not match_id:
            match_id = f"{agent1_id}_vs_{agent2_id}_{datetime.now().timestamp()}"
        
        # 创建对局记录
        match_record = MatchRecord(
            match_id=match_id,
            agent1_id=agent1_id,
            agent2_id=agent2_id,
            agent1_elo_before=elo1_before,
            agent2_elo_before=elo2_before,
            agent1_elo_after=elo1_after,
            agent2_elo_after=elo2_after,
            result=result,
            played_at=datetime.now(),
            metadata=metadata
        )
        
        # 插入对局记录
        cursor.execute("""
            INSERT INTO matches (
                match_id, agent1_id, agent2_id,
                agent1_elo_before, agent2_elo_before,
                agent1_elo_after, agent2_elo_after,
                result, played_at, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            match_record.match_id,
            match_record.agent1_id,
            match_record.agent2_id,
            match_record.agent1_elo_before,
            match_record.agent2_elo_before,
            match_record.agent1_elo_after,
            match_record.agent2_elo_after,
            match_record.result.value,
            match_record.played_at.isoformat(),
            json.dumps(metadata) if metadata else None
        ))
        
        self.conn.commit()
        
        logger.info(
            f"对局记录: {agent1.name} vs {agent2.name}, "
            f"结果: {result.value}, "
            f"ELO变化: {agent1.name} {elo1_before:.1f} -> {elo1_after:.1f}, "
            f"{agent2.name} {elo2_before:.1f} -> {elo2_after:.1f}"
        )
        
        return match_record
    
    def get_match_history(
        self,
        agent_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[MatchRecord]:
        """
        获取对局历史
        
        Args:
            agent_id: 过滤Agent ID(可选)
            limit: 限制数量(可选)
            
        Returns:
            对局记录列表
        """
        self.connect()
        cursor = self.conn.cursor()
        
        if agent_id:
            sql = """
                SELECT * FROM matches
                WHERE agent1_id = ? OR agent2_id = ?
                ORDER BY played_at DESC
            """
            params = [agent_id, agent_id]
        else:
            sql = "SELECT * FROM matches ORDER BY played_at DESC"
            params = []
        
        if limit:
            sql += " LIMIT ?"
            params.append(limit)
        
        cursor.execute(sql, params)
        
        matches = [self._row_to_match(row) for row in cursor.fetchall()]
        
        return matches
    
    # ============ 对比分析 ============
    
    def compare_versions(
        self,
        name: str,
        version1: Optional[str] = None,
        version2: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        对比不同版本的Agent
        
        Args:
            name: Agent名称
            version1: 版本1(可选,默认最新版本)
            version2: 版本2(可选,默认第二新版本)
            
        Returns:
            对比结果字典
        """
        versions = self.get_agent_versions(name)
        
        if len(versions) < 1:
            raise ValueError(f"未找到Agent: {name}")
        
        if len(versions) < 2:
            return {
                "name": name,
                "versions": [v.to_dict() for v in versions],
                "comparison": "只有一个版本,无法对比"
            }
        
        # 选择要对比的版本
        if version1:
            v1 = next((v for v in versions if v.version == version1), None)
            if not v1:
                raise ValueError(f"未找到版本: {version1}")
        else:
            v1 = versions[0]  # 最新(ELO最高)
        
        if version2:
            v2 = next((v for v in versions if v.version == version2), None)
            if not v2:
                raise ValueError(f"未找到版本: {version2}")
        else:
            v2 = versions[1] if len(versions) > 1 else versions[0]
        
        # 计算ELO差异
        elo_diff = self.calculator.elo_difference(v1.elo, v2.elo)
        expected_score = self.calculator.expected_score(v1.elo, v2.elo)
        
        # 获取对局记录
        matches = self.get_match_history()
        head_to_head = [
            m for m in matches
            if (m.agent1_id == v1.agent_id and m.agent2_id == v2.agent_id) or
               (m.agent1_id == v2.agent_id and m.agent2_id == v1.agent_id)
        ]
        
        return {
            "name": name,
            "version1": v1.to_dict(),
            "version2": v2.to_dict(),
            "elo_difference": elo_diff,
            "expected_score_v1": expected_score,
            "expected_score_v2": 1.0 - expected_score,
            "head_to_head_matches": len(head_to_head),
            "head_to_head_records": [m.to_dict() for m in head_to_head[:10]]  # 最近10局
        }
    
    def get_leaderboard(
        self,
        limit: int = 10,
        name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取排行榜
        
        Args:
            limit: 返回数量
            name: 过滤名称(可选)
            
        Returns:
            排行榜列表
        """
        agents = self.list_agents(name=name, limit=limit, order_by="elo")
        
        return [
            {
                "rank": i + 1,
                **agent.to_dict()
            }
            for i, agent in enumerate(agents)
        ]
    
    # ============ 辅助方法 ============
    
    def _row_to_agent(self, row: sqlite3.Row) -> Agent:
        """将数据库行转换为Agent对象"""
        created_at = None
        if row["created_at"]:
            try:
                created_at = datetime.fromisoformat(row["created_at"])
            except:
                pass
        
        updated_at = None
        if row["updated_at"]:
            try:
                updated_at = datetime.fromisoformat(row["updated_at"])
            except:
                pass
        
        metadata = None
        if row["metadata"]:
            try:
                metadata = json.loads(row["metadata"])
            except:
                pass
        
        return Agent(
            agent_id=row["agent_id"],
            name=row["name"],
            version=row["version"],
            elo=row["elo"],
            games_played=row["games_played"],
            wins=row["wins"],
            losses=row["losses"],
            draws=row["draws"],
            created_at=created_at,
            updated_at=updated_at,
            metadata=metadata
        )
    
    def _row_to_match(self, row: sqlite3.Row) -> MatchRecord:
        """将数据库行转换为MatchRecord对象"""
        played_at = datetime.now()
        if row["played_at"]:
            try:
                played_at = datetime.fromisoformat(row["played_at"])
            except:
                pass
        
        metadata = None
        if row["metadata"]:
            try:
                metadata = json.loads(row["metadata"])
            except:
                pass
        
        return MatchRecord(
            match_id=row["match_id"],
            agent1_id=row["agent1_id"],
            agent2_id=row["agent2_id"],
            agent1_elo_before=row["agent1_elo_before"],
            agent2_elo_before=row["agent2_elo_before"],
            agent1_elo_after=row["agent1_elo_after"],
            agent2_elo_after=row["agent2_elo_after"],
            result=GameResult(row["result"]),
            played_at=played_at,
            metadata=metadata
        )
    
    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.close()


# ============ 工厂函数 ============

def create_elo_manager(
    db_path: str = "data/elo.db",
    config: Optional[EloConfig] = None
) -> EloManager:
    """
    创建并初始化ELO管理器
    
    Args:
        db_path: 数据库路径
        config: ELO配置
        
    Returns:
        EloManager实例
    """
    manager = EloManager(db_path, config)
    manager.initialize_schema()
    return manager

