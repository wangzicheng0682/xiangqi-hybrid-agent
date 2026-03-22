"""
经验池存储管理
提供经验数据的CRUD操作
"""
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
import logging
import sqlite3

from src.memory.schema import (
    Experience, GameMetadata, ExperienceDatabase,
    serialize_metadata, deserialize_metadata, row_to_experience
)

logger = logging.getLogger(__name__)


class ExperienceStore:
    """
    经验池存储管理器
    
    职责:
    - 经验数据的增删改查
    - 统计信息更新
    - 批量操作
    """
    
    def __init__(self, db_path: str = "data/experiences.db"):
        """
        初始化存储管理器
        
        Args:
            db_path: 数据库路径
        """
        self.db = ExperienceDatabase(db_path)
        self.db.connect()
        
        logger.info(f"经验池存储初始化: {db_path}")
    
    def close(self):
        """关闭数据库连接"""
        self.db.close()
    
    # ============ CREATE 操作 ============
    
    def add_experience(self, experience: Experience) -> int:
        """
        添加单条经验
        
        Args:
            experience: 经验对象
            
        Returns:
            新记录的ID
        """
        cursor = self.db.conn.cursor()
        
        sql = """
        INSERT INTO experiences (
            state_hash, state_text, state_fen, move,
            reward, win_rate, visit_count, total_reward,
            player_color, game_phase, metadata
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        
        cursor.execute(sql, (
            experience.state_hash,
            experience.state_text,
            experience.state_fen,
            experience.move,
            experience.reward,
            experience.win_rate,
            experience.visit_count,
            experience.total_reward,
            experience.player_color,
            experience.game_phase,
            serialize_metadata(experience.metadata)
        ))
        
        self.db.conn.commit()
        exp_id = cursor.lastrowid
        
        logger.debug(f"添加经验: ID={exp_id}, state={experience.state_hash[:8]}, move={experience.move}")
        
        return exp_id
    
    def add_experiences_batch(self, experiences: List[Experience]) -> int:
        """
        批量添加经验
        
        Args:
            experiences: 经验列表
            
        Returns:
            添加的记录数
        """
        if not experiences:
            return 0
        
        cursor = self.db.conn.cursor()
        
        sql = """
        INSERT INTO experiences (
            state_hash, state_text, state_fen, move,
            reward, win_rate, visit_count, total_reward,
            player_color, game_phase, metadata
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        
        data = [
            (
                exp.state_hash,
                exp.state_text,
                exp.state_fen,
                exp.move,
                exp.reward,
                exp.win_rate,
                exp.visit_count,
                exp.total_reward,
                exp.player_color,
                exp.game_phase,
                serialize_metadata(exp.metadata)
            )
            for exp in experiences
        ]
        
        cursor.executemany(sql, data)
        self.db.conn.commit()
        
        count = cursor.rowcount
        logger.info(f"批量添加经验: {count} 条")
        
        return count
    
    # ============ READ 操作 ============
    
    def get_experience_by_id(self, exp_id: int) -> Optional[Experience]:
        """
        根据ID获取经验
        
        Args:
            exp_id: 经验ID
            
        Returns:
            Experience对象,不存在返回None
        """
        cursor = self.db.conn.cursor()
        
        sql = "SELECT * FROM experiences WHERE id = ?;"
        cursor.execute(sql, (exp_id,))
        
        row = cursor.fetchone()
        if row:
            return row_to_experience(row)
        
        return None
    
    def get_experiences_by_state(
        self,
        state_hash: str,
        limit: Optional[int] = None
    ) -> List[Experience]:
        """
        根据状态哈希获取经验
        
        Args:
            state_hash: 状态哈希
            limit: 限制返回数量
            
        Returns:
            经验列表
        """
        cursor = self.db.conn.cursor()
        
        sql = "SELECT * FROM experiences WHERE state_hash = ?"
        params = [state_hash]
        
        if limit:
            sql += " LIMIT ?;"
            params.append(limit)
        else:
            sql += ";"
        
        cursor.execute(sql, params)
        
        experiences = [row_to_experience(row) for row in cursor.fetchall()]
        
        logger.debug(f"查询状态 {state_hash[:8]}: 找到 {len(experiences)} 条经验")
        
        return experiences
    
    def get_experience_by_state_move(
        self,
        state_hash: str,
        move: str
    ) -> Optional[Experience]:
        """
        根据状态和走法获取经验
        
        Args:
            state_hash: 状态哈希
            move: 走法
            
        Returns:
            Experience对象,不存在返回None
        """
        cursor = self.db.conn.cursor()
        
        sql = "SELECT * FROM experiences WHERE state_hash = ? AND move = ? LIMIT 1;"
        cursor.execute(sql, (state_hash, move))
        
        row = cursor.fetchone()
        if row:
            return row_to_experience(row)
        
        return None
    
    def get_top_experiences_by_state(
        self,
        state_hash: str,
        limit: int = 10,
        order_by: str = "win_rate"
    ) -> List[Experience]:
        """
        获取某状态下的Top-K经验
        
        Args:
            state_hash: 状态哈希
            limit: 返回数量
            order_by: 排序字段("win_rate"/"reward"/"visit_count")
            
        Returns:
            经验列表(按指定字段降序)
        """
        cursor = self.db.conn.cursor()
        
        valid_orders = ["win_rate", "reward", "visit_count"]
        if order_by not in valid_orders:
            order_by = "win_rate"
        
        sql = f"""
        SELECT * FROM experiences 
        WHERE state_hash = ? 
        ORDER BY {order_by} DESC 
        LIMIT ?;
        """
        
        cursor.execute(sql, (state_hash, limit))
        
        experiences = [row_to_experience(row) for row in cursor.fetchall()]
        
        logger.debug(
            f"查询Top-{limit}经验 (state={state_hash[:8]}, order={order_by}): "
            f"返回 {len(experiences)} 条"
        )
        
        return experiences
    
    def search_experiences(
        self,
        player_color: Optional[str] = None,
        game_phase: Optional[str] = None,
        min_visit_count: Optional[int] = None,
        min_win_rate: Optional[float] = None,
        limit: int = 100
    ) -> List[Experience]:
        """
        搜索经验(支持多条件)
        
        Args:
            player_color: 玩家颜色
            game_phase: 对局阶段
            min_visit_count: 最小访问次数
            min_win_rate: 最小胜率
            limit: 返回数量限制
            
        Returns:
            经验列表
        """
        cursor = self.db.conn.cursor()
        
        conditions = []
        params = []
        
        if player_color:
            conditions.append("player_color = ?")
            params.append(player_color)
        
        if game_phase:
            conditions.append("game_phase = ?")
            params.append(game_phase)
        
        if min_visit_count is not None:
            conditions.append("visit_count >= ?")
            params.append(min_visit_count)
        
        if min_win_rate is not None:
            conditions.append("win_rate >= ?")
            params.append(min_win_rate)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        sql = f"""
        SELECT * FROM experiences 
        WHERE {where_clause}
        ORDER BY win_rate DESC
        LIMIT ?;
        """
        params.append(limit)
        
        cursor.execute(sql, params)
        
        experiences = [row_to_experience(row) for row in cursor.fetchall()]
        
        logger.debug(f"搜索经验: 找到 {len(experiences)} 条")
        
        return experiences
    
    # ============ UPDATE 操作 ============
    
    def update_experience(self, experience: Experience) -> bool:
        """
        更新经验记录
        
        Args:
            experience: 经验对象(必须有id)
            
        Returns:
            是否更新成功
        """
        if experience.id is None:
            logger.warning("更新失败: 经验ID为空")
            return False
        
        cursor = self.db.conn.cursor()
        
        sql = """
        UPDATE experiences SET
            state_hash = ?,
            state_text = ?,
            state_fen = ?,
            move = ?,
            reward = ?,
            win_rate = ?,
            visit_count = ?,
            total_reward = ?,
            player_color = ?,
            game_phase = ?,
            metadata = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?;
        """
        
        cursor.execute(sql, (
            experience.state_hash,
            experience.state_text,
            experience.state_fen,
            experience.move,
            experience.reward,
            experience.win_rate,
            experience.visit_count,
            experience.total_reward,
            experience.player_color,
            experience.game_phase,
            serialize_metadata(experience.metadata),
            experience.id
        ))
        
        self.db.conn.commit()
        
        success = cursor.rowcount > 0
        if success:
            logger.debug(f"更新经验: ID={experience.id}")
        
        return success
    
    def update_statistics(
        self,
        state_hash: str,
        move: str,
        reward: float,
        is_win: bool
    ) -> bool:
        """
        更新统计信息(增量更新)
        
        Args:
            state_hash: 状态哈希
            move: 走法
            reward: 新奖励
            is_win: 是否胜利
            
        Returns:
            是否更新成功
        """
        cursor = self.db.conn.cursor()
        
        # 检查记录是否存在
        exp = self.get_experience_by_state_move(state_hash, move)
        
        if exp:
            # 更新现有记录
            new_visit_count = exp.visit_count + 1
            new_total_reward = exp.total_reward + reward
            new_avg_reward = new_total_reward / new_visit_count
            
            # 更新胜率
            old_wins = exp.win_rate * exp.visit_count
            new_wins = old_wins + (1.0 if is_win else 0.0)
            new_win_rate = new_wins / new_visit_count
            
            sql = """
            UPDATE experiences SET
                reward = ?,
                win_rate = ?,
                visit_count = ?,
                total_reward = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?;
            """
            
            cursor.execute(sql, (
                new_avg_reward,
                new_win_rate,
                new_visit_count,
                new_total_reward,
                exp.id
            ))
            
            logger.debug(
                f"更新统计: state={state_hash[:8]}, move={move}, "
                f"visits={new_visit_count}, win_rate={new_win_rate:.3f}"
            )
        else:
            # 创建新记录
            logger.debug(f"统计更新: 记录不存在,跳过 (state={state_hash[:8]}, move={move})")
            return False
        
        self.db.conn.commit()
        return cursor.rowcount > 0
    
    def increment_visit_count(
        self,
        state_hash: str,
        move: str,
        count: int = 1
    ) -> bool:
        """
        增加访问次数
        
        Args:
            state_hash: 状态哈希
            move: 走法
            count: 增加的次数
            
        Returns:
            是否更新成功
        """
        cursor = self.db.conn.cursor()
        
        sql = """
        UPDATE experiences SET
            visit_count = visit_count + ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE state_hash = ? AND move = ?;
        """
        
        cursor.execute(sql, (count, state_hash, move))
        self.db.conn.commit()
        
        return cursor.rowcount > 0
    
    # ============ DELETE 操作 ============
    
    def delete_experience(self, exp_id: int) -> bool:
        """
        删除经验
        
        Args:
            exp_id: 经验ID
            
        Returns:
            是否删除成功
        """
        cursor = self.db.conn.cursor()
        
        sql = "DELETE FROM experiences WHERE id = ?;"
        cursor.execute(sql, (exp_id,))
        
        self.db.conn.commit()
        
        success = cursor.rowcount > 0
        if success:
            logger.debug(f"删除经验: ID={exp_id}")
        
        return success
    
    def delete_experiences_by_state(self, state_hash: str) -> int:
        """
        删除某状态的所有经验
        
        Args:
            state_hash: 状态哈希
            
        Returns:
            删除的记录数
        """
        cursor = self.db.conn.cursor()
        
        sql = "DELETE FROM experiences WHERE state_hash = ?;"
        cursor.execute(sql, (state_hash,))
        
        self.db.conn.commit()
        
        count = cursor.rowcount
        logger.info(f"删除状态 {state_hash[:8]} 的经验: {count} 条")
        
        return count
    
    def clear_all_experiences(self) -> int:
        """
        清空所有经验(危险操作)
        
        Returns:
            删除的记录数
        """
        cursor = self.db.conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM experiences;")
        count = cursor.fetchone()[0]
        
        cursor.execute("DELETE FROM experiences;")
        self.db.conn.commit()
        
        logger.warning(f"清空所有经验: {count} 条")
        
        return count
    
    # ============ 统计与聚合 ============
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取全局统计信息
        
        Returns:
            统计字典
        """
        cursor = self.db.conn.cursor()
        
        stats = {}
        
        # 总经验数
        cursor.execute("SELECT COUNT(*) FROM experiences;")
        stats["total_experiences"] = cursor.fetchone()[0]
        
        # 唯一状态数
        cursor.execute("SELECT COUNT(DISTINCT state_hash) FROM experiences;")
        stats["unique_states"] = cursor.fetchone()[0]
        
        # 总访问次数
        cursor.execute("SELECT SUM(visit_count) FROM experiences;")
        result = cursor.fetchone()[0]
        stats["total_visits"] = result if result else 0
        
        # 平均胜率
        cursor.execute("SELECT AVG(win_rate) FROM experiences WHERE visit_count > 0;")
        result = cursor.fetchone()[0]
        stats["avg_win_rate"] = result if result else 0.0
        
        # 平均奖励
        cursor.execute("SELECT AVG(reward) FROM experiences WHERE visit_count > 0;")
        result = cursor.fetchone()[0]
        stats["avg_reward"] = result if result else 0.0
        
        # 玩家颜色分布
        cursor.execute("SELECT player_color, COUNT(*) FROM experiences GROUP BY player_color;")
        stats["color_distribution"] = {row[0]: row[1] for row in cursor.fetchall()}
        
        # 阶段分布
        cursor.execute("SELECT game_phase, COUNT(*) FROM experiences GROUP BY game_phase;")
        stats["phase_distribution"] = {row[0]: row[1] for row in cursor.fetchall()}
        
        return stats
    
    def get_state_statistics(self, state_hash: str) -> Dict[str, Any]:
        """
        获取特定状态的统计信息
        
        Args:
            state_hash: 状态哈希
            
        Returns:
            统计字典
        """
        cursor = self.db.conn.cursor()
        
        stats = {"state_hash": state_hash}
        
        # 总经验数
        cursor.execute("SELECT COUNT(*) FROM experiences WHERE state_hash = ?;", (state_hash,))
        stats["total_moves"] = cursor.fetchone()[0]
        
        # 总访问次数
        cursor.execute("SELECT SUM(visit_count) FROM experiences WHERE state_hash = ?;", (state_hash,))
        result = cursor.fetchone()[0]
        stats["total_visits"] = result if result else 0
        
        # 平均胜率
        cursor.execute("SELECT AVG(win_rate) FROM experiences WHERE state_hash = ?;", (state_hash,))
        result = cursor.fetchone()[0]
        stats["avg_win_rate"] = result if result else 0.0
        
        # 最佳走法
        cursor.execute("""
            SELECT move, win_rate, visit_count 
            FROM experiences 
            WHERE state_hash = ? 
            ORDER BY win_rate DESC 
            LIMIT 1;
        """, (state_hash,))
        row = cursor.fetchone()
        if row:
            stats["best_move"] = {
                "move": row[0],
                "win_rate": row[1],
                "visit_count": row[2]
            }
        else:
            stats["best_move"] = None
        
        return stats
    
    # ============ 上下文管理 ============
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.close()


# ============ 便捷函数 ============

def create_experience_store(db_path: str = "data/experiences.db") -> ExperienceStore:
    """
    工厂函数: 创建经验池存储
    
    Args:
        db_path: 数据库路径
        
    Returns:
        ExperienceStore实例
    """
    return ExperienceStore(db_path)