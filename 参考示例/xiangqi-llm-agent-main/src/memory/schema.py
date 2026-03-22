"""
经验池数据库模式定义
使用SQLite存储经验数据
"""
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime
import sqlite3
import json
import logging

logger = logging.getLogger(__name__)


# ============ 数据类定义 ============

@dataclass
class Experience:
    """单条经验记录"""
    id: Optional[int] = None                    # 主键(自增)
    state_hash: str = ""                        # 状态哈希(索引)
    state_text: str = ""                        # 状态文本描述
    state_fen: str = ""                         # FEN格式状态
    move: str = ""                              # 走法
    reward: float = 0.0                         # 奖励值
    win_rate: float = 0.0                       # 胜率
    visit_count: int = 0                        # 访问次数
    total_reward: float = 0.0                   # 累计奖励
    player_color: str = ""                      # 玩家颜色(RED/BLACK)
    game_phase: str = ""                        # 对局阶段(开局/中局/残局)
    created_at: Optional[datetime] = None       # 创建时间
    updated_at: Optional[datetime] = None       # 更新时间
    metadata: Optional[Dict[str, Any]] = None   # 额外元数据
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "state_hash": self.state_hash,
            "state_text": self.state_text,
            "state_fen": self.state_fen,
            "move": self.move,
            "reward": self.reward,
            "win_rate": self.win_rate,
            "visit_count": self.visit_count,
            "total_reward": self.total_reward,
            "player_color": self.player_color,
            "game_phase": self.game_phase,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Experience":
        """从字典创建"""
        created_at = None
        if data.get("created_at"):
            try:
                created_at = datetime.fromisoformat(data["created_at"])
            except:
                pass
        
        updated_at = None
        if data.get("updated_at"):
            try:
                updated_at = datetime.fromisoformat(data["updated_at"])
            except:
                pass
        
        return cls(
            id=data.get("id"),
            state_hash=data.get("state_hash", ""),
            state_text=data.get("state_text", ""),
            state_fen=data.get("state_fen", ""),
            move=data.get("move", ""),
            reward=data.get("reward", 0.0),
            win_rate=data.get("win_rate", 0.0),
            visit_count=data.get("visit_count", 0),
            total_reward=data.get("total_reward", 0.0),
            player_color=data.get("player_color", ""),
            game_phase=data.get("game_phase", ""),
            created_at=created_at,
            updated_at=updated_at,
            metadata=data.get("metadata")
        )


@dataclass
class GameMetadata:
    """对局元数据记录"""
    id: Optional[int] = None
    game_id: str = ""                           # 对局ID
    red_player: str = ""                        # 红方玩家
    black_player: str = ""                      # 黑方玩家
    result: str = ""                            # 对局结果
    total_moves: int = 0                        # 总步数
    duration: float = 0.0                       # 持续时间(秒)
    start_time: Optional[datetime] = None       # 开始时间
    end_time: Optional[datetime] = None         # 结束时间
    metadata: Optional[Dict[str, Any]] = None   # 额外元数据


# ============ 数据库模式定义 ============

# 经验表SQL
EXPERIENCES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS experiences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    state_hash TEXT NOT NULL,
    state_text TEXT,
    state_fen TEXT NOT NULL,
    move TEXT NOT NULL,
    reward REAL NOT NULL DEFAULT 0.0,
    win_rate REAL NOT NULL DEFAULT 0.0,
    visit_count INTEGER NOT NULL DEFAULT 0,
    total_reward REAL NOT NULL DEFAULT 0.0,
    player_color TEXT NOT NULL,
    game_phase TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT
);
"""

# 索引
EXPERIENCES_INDEXES_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_state_hash ON experiences(state_hash);",
    "CREATE INDEX IF NOT EXISTS idx_move ON experiences(move);",
    "CREATE INDEX IF NOT EXISTS idx_state_move ON experiences(state_hash, move);",
    "CREATE INDEX IF NOT EXISTS idx_win_rate ON experiences(win_rate DESC);",
    "CREATE INDEX IF NOT EXISTS idx_visit_count ON experiences(visit_count DESC);",
    "CREATE INDEX IF NOT EXISTS idx_player_color ON experiences(player_color);",
    "CREATE INDEX IF NOT EXISTS idx_game_phase ON experiences(game_phase);",
]

# 对局元数据表SQL
GAMES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id TEXT UNIQUE NOT NULL,
    red_player TEXT NOT NULL,
    black_player TEXT NOT NULL,
    result TEXT NOT NULL,
    total_moves INTEGER NOT NULL,
    duration REAL NOT NULL,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    metadata TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# 对局表索引
GAMES_INDEXES_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_game_id ON games(game_id);",
    "CREATE INDEX IF NOT EXISTS idx_result ON games(result);",
    "CREATE INDEX IF NOT EXISTS idx_created_at ON games(created_at DESC);",
]

# 统计视图
STATISTICS_VIEW_SQL = """
CREATE VIEW IF NOT EXISTS experience_statistics AS
SELECT 
    state_hash,
    COUNT(*) as total_experiences,
    SUM(visit_count) as total_visits,
    AVG(win_rate) as avg_win_rate,
    AVG(reward) as avg_reward,
    MAX(updated_at) as last_updated
FROM experiences
GROUP BY state_hash;
"""


# ============ 数据库管理类 ============

class ExperienceDatabase:
    """经验池数据库管理"""
    
    def __init__(self, db_path: str = "data/experiences.db"):
        """
        初始化数据库
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        
        logger.info(f"初始化经验池数据库: {db_path}")
    
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
            logger.info("创建经验表...")
            cursor.execute(EXPERIENCES_TABLE_SQL)
            
            logger.info("创建对局表...")
            cursor.execute(GAMES_TABLE_SQL)
            
            # 创建索引
            logger.info("创建索引...")
            for index_sql in EXPERIENCES_INDEXES_SQL:
                cursor.execute(index_sql)
            
            for index_sql in GAMES_INDEXES_SQL:
                cursor.execute(index_sql)
            
            # 创建视图
            logger.info("创建统计视图...")
            cursor.execute(STATISTICS_VIEW_SQL)
            
            self.conn.commit()
            logger.info("数据库模式初始化完成")
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"初始化数据库失败: {e}")
            raise
    
    def drop_all_tables(self):
        """删除所有表(危险操作,仅用于测试)"""
        self.connect()
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("DROP TABLE IF EXISTS experiences;")
            cursor.execute("DROP TABLE IF EXISTS games;")
            cursor.execute("DROP VIEW IF EXISTS experience_statistics;")
            self.conn.commit()
            logger.warning("所有表已删除")
        except Exception as e:
            self.conn.rollback()
            logger.error(f"删除表失败: {e}")
            raise
    
    def get_table_info(self) -> Dict[str, Any]:
        """
        获取表信息
        
        Returns:
            包含表统计的字典
        """
        self.connect()
        cursor = self.conn.cursor()
        
        info = {}
        
        # 经验表统计
        cursor.execute("SELECT COUNT(*) FROM experiences;")
        info["total_experiences"] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT state_hash) FROM experiences;")
        info["unique_states"] = cursor.fetchone()[0]
        
        cursor.execute("SELECT SUM(visit_count) FROM experiences;")
        result = cursor.fetchone()[0]
        info["total_visits"] = result if result else 0
        
        # 对局表统计
        cursor.execute("SELECT COUNT(*) FROM games;")
        info["total_games"] = cursor.fetchone()[0]
        
        # 数据库大小
        cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size();")
        size_bytes = cursor.fetchone()[0]
        info["db_size_mb"] = size_bytes / (1024 * 1024)
        
        return info
    
    def vacuum(self):
        """优化数据库(回收空间)"""
        self.connect()
        logger.info("开始优化数据库...")
        self.conn.execute("VACUUM;")
        logger.info("数据库优化完成")
    
    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.close()


# ============ 辅助函数 ============

def create_database(db_path: str = "data/experiences.db") -> ExperienceDatabase:
    """
    创建并初始化数据库
    
    Args:
        db_path: 数据库路径
        
    Returns:
        ExperienceDatabase实例
    """
    import os
    
    # 确保目录存在
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    db = ExperienceDatabase(db_path)
    db.initialize_schema()
    
    return db


def serialize_metadata(metadata: Optional[Dict[str, Any]]) -> Optional[str]:
    """
    序列化元数据为JSON字符串
    
    Args:
        metadata: 元数据字典
        
    Returns:
        JSON字符串
    """
    if metadata is None:
        return None
    return json.dumps(metadata, ensure_ascii=False)


def deserialize_metadata(metadata_str: Optional[str]) -> Optional[Dict[str, Any]]:
    """
    反序列化元数据
    
    Args:
        metadata_str: JSON字符串
        
    Returns:
        元数据字典
    """
    if not metadata_str:
        return None
    try:
        return json.loads(metadata_str)
    except:
        return None


def row_to_experience(row: sqlite3.Row) -> Experience:
    """
    将数据库行转换为Experience对象
    
    Args:
        row: SQLite行对象
        
    Returns:
        Experience对象
    """
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
    
    return Experience(
        id=row["id"],
        state_hash=row["state_hash"],
        state_text=row["state_text"],
        state_fen=row["state_fen"],
        move=row["move"],
        reward=row["reward"],
        win_rate=row["win_rate"],
        visit_count=row["visit_count"],
        total_reward=row["total_reward"],
        player_color=row["player_color"],
        game_phase=row["game_phase"],
        created_at=created_at,
        updated_at=updated_at,
        metadata=deserialize_metadata(row["metadata"])
    )