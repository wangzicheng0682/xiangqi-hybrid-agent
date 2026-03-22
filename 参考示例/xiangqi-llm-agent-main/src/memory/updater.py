"""
经验池更新器
负责根据对弈结果更新经验池,并维护数据质量
"""
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import logging
from datetime import datetime, timedelta

from src.memory.store import ExperienceStore
from src.memory.schema import Experience
from src.self_play.game_runner import GameRecord, GameStep
from src.reward.evaluator import StepReward

logger = logging.getLogger(__name__)


@dataclass
class UpdaterConfig:
    """更新器配置"""
    # 更新策略
    update_mode: str = "incremental"    # 更新模式: incremental/overwrite
    
    # 淘汰策略
    enable_pruning: bool = True         # 是否启用淘汰
    prune_interval: int = 100           # 淘汰间隔(对局数)
    min_visit_threshold: int = 2        # 最小访问次数阈值
    min_win_rate_threshold: float = 0.2 # 最小胜率阈值
    max_experiences_per_state: int = 50 # 每个状态最多保留经验数
    
    # 数据老化
    enable_aging: bool = False          # 是否启用老化
    aging_days: int = 30                # 超过N天的数据视为老化
    
    # 批量更新
    batch_size: int = 100               # 批量更新大小
    
    # 统计记录
    enable_stats_logging: bool = True   # 是否记录统计信息


@dataclass
class UpdateStats:
    """更新统计"""
    games_processed: int = 0            # 处理的对局数
    experiences_added: int = 0          # 新增经验数
    experiences_updated: int = 0        # 更新经验数
    experiences_pruned: int = 0         # 淘汰经验数
    last_update_time: Optional[datetime] = None
    last_prune_time: Optional[datetime] = None


class ExperienceUpdater:
    """
    经验池更新器
    
    职责:
    - 根据对弈结果更新经验池
    - 增量更新统计信息
    - 定期淘汰低质量数据
    - 维护数据质量
    """
    
    def __init__(
        self,
        store: ExperienceStore,
        config: Optional[UpdaterConfig] = None
    ):
        """
        初始化更新器
        
        Args:
            store: 经验池存储
            config: 更新器配置
        """
        self.store = store
        self.config = config or UpdaterConfig()
        self.stats = UpdateStats()
        
        logger.info(
            f"经验池更新器初始化: 模式={self.config.update_mode}, "
            f"淘汰={'启用' if self.config.enable_pruning else '禁用'}"
        )
    
    def update_from_game(
        self,
        game_record: GameRecord,
        step_rewards: List[StepReward]
    ):
        """
        根据对局结果更新经验池
        
        Args:
            game_record: 对局记录
            step_rewards: 每一步的奖励列表
        """
        if len(game_record.steps) != len(step_rewards):
            logger.warning(
                f"对局步数({len(game_record.steps)})与奖励数({len(step_rewards)})不匹配"
            )
            return
        
        logger.info(f"更新经验池: 对局={game_record.game_id}, 步数={len(game_record.steps)}")
        
        # 判断胜负
        winner = game_record.get_winner()
        
        # 处理每一步
        added = 0
        updated = 0
        
        for step, reward in zip(game_record.steps, step_rewards):
            is_win = (winner == step.player) if winner else False
            
            result = self._update_step_experience(
                step=step,
                reward=reward.reward,
                is_win=is_win
            )
            
            if result == "added":
                added += 1
            elif result == "updated":
                updated += 1
        
        # 更新统计
        self.stats.games_processed += 1
        self.stats.experiences_added += added
        self.stats.experiences_updated += updated
        self.stats.last_update_time = datetime.now()
        
        logger.info(
            f"对局 {game_record.game_id} 更新完成: "
            f"新增={added}, 更新={updated}"
        )
        
        # 定期淘汰
        if self.config.enable_pruning and \
           self.stats.games_processed % self.config.prune_interval == 0:
            self.prune_low_quality_experiences()
    
    def update_from_games_batch(
        self,
        game_records: List[GameRecord],
        rewards_list: List[List[StepReward]]
    ):
        """
        批量更新多局对弈
        
        Args:
            game_records: 对局记录列表
            rewards_list: 对应的奖励列表
        """
        if len(game_records) != len(rewards_list):
            logger.warning("对局数与奖励列表数不匹配")
            return
        
        logger.info(f"批量更新经验池: {len(game_records)} 局对弈")
        
        for game_record, step_rewards in zip(game_records, rewards_list):
            self.update_from_game(game_record, step_rewards)
        
        if self.config.enable_stats_logging:
            self._log_stats()
    
    def prune_low_quality_experiences(self):
        """淘汰低质量经验"""
        logger.info("开始淘汰低质量经验...")
        
        pruned_total = 0
        
        # 1. 淘汰低访问次数的经验
        pruned = self._prune_by_visit_count()
        pruned_total += pruned
        logger.info(f"淘汰低访问经验: {pruned} 条")
        
        # 2. 淘汰低胜率的经验
        pruned = self._prune_by_win_rate()
        pruned_total += pruned
        logger.info(f"淘汰低胜率经验: {pruned} 条")
        
        # 3. 限制每个状态的经验数量
        pruned = self._prune_by_state_limit()
        pruned_total += pruned
        logger.info(f"淘汰超限经验: {pruned} 条")
        
        # 4. 淘汰老化数据(如果启用)
        if self.config.enable_aging:
            pruned = self._prune_by_age()
            pruned_total += pruned
            logger.info(f"淘汰老化经验: {pruned} 条")
        
        # 更新统计
        self.stats.experiences_pruned += pruned_total
        self.stats.last_prune_time = datetime.now()
        
        logger.info(f"淘汰完成: 共 {pruned_total} 条经验")
    
    def get_stats(self) -> UpdateStats:
        """获取更新统计"""
        return self.stats
    
    def reset_stats(self):
        """重置统计"""
        self.stats = UpdateStats()
        logger.info("更新统计已重置")
    
    # ============ 内部方法 ============
    
    def _update_step_experience(
        self,
        step: GameStep,
        reward: float,
        is_win: bool
    ) -> str:
        """
        更新单步经验
        
        Args:
            step: 对局步骤
            reward: 奖励值
            is_win: 是否胜利
            
        Returns:
            "added" / "updated" / "skipped"
        """
        state_hash = step.state_hash
        move = step.move
        
        # 查询现有经验
        existing = self.store.get_experience_by_state_move(state_hash, move)
        
        if existing:
            # 更新模式
            if self.config.update_mode == "incremental":
                # 增量更新
                success = self.store.update_statistics(
                    state_hash=state_hash,
                    move=move,
                    reward=reward,
                    is_win=is_win
                )
                return "updated" if success else "skipped"
            
            elif self.config.update_mode == "overwrite":
                # 覆盖模式(简单实现,实际可能需要更复杂逻辑)
                existing.reward = reward
                existing.visit_count += 1
                existing.total_reward += reward
                
                # 更新胜率
                old_wins = existing.win_rate * (existing.visit_count - 1)
                new_wins = old_wins + (1.0 if is_win else 0.0)
                existing.win_rate = new_wins / existing.visit_count
                
                self.store.update_experience(existing)
                return "updated"
        
        else:
            # 新增经验
            new_exp = Experience(
                state_hash=state_hash,
                state_text=step.board_before.to_text(include_history=False),
                state_fen=step.board_before.fen,
                move=move,
                reward=reward,
                win_rate=1.0 if is_win else 0.0,
                visit_count=1,
                total_reward=reward,
                player_color=step.player_color,
                game_phase=self._infer_game_phase(step.step_number),
                metadata={
                    "step_number": step.step_number,
                    "player": step.player
                }
            )
            
            self.store.add_experience(new_exp)
            return "added"
    
    def _prune_by_visit_count(self) -> int:
        """
        淘汰低访问次数的经验
        
        Returns:
            淘汰的数量
        """
        cursor = self.store.db.conn.cursor()
        
        sql = """
        DELETE FROM experiences 
        WHERE visit_count < ?;
        """
        
        cursor.execute(sql, (self.config.min_visit_threshold,))
        self.store.db.conn.commit()
        
        return cursor.rowcount
    
    def _prune_by_win_rate(self) -> int:
        """
        淘汰低胜率的经验(且访问次数充足)
        
        Returns:
            淘汰的数量
        """
        cursor = self.store.db.conn.cursor()
        
        # 只淘汰访问次数>=5且胜率低的经验
        sql = """
        DELETE FROM experiences 
        WHERE win_rate < ? AND visit_count >= 5;
        """
        
        cursor.execute(sql, (self.config.min_win_rate_threshold,))
        self.store.db.conn.commit()
        
        return cursor.rowcount
    
    def _prune_by_state_limit(self) -> int:
        """
        限制每个状态的经验数量(保留胜率最高的)
        
        Returns:
            淘汰的数量
        """
        cursor = self.store.db.conn.cursor()
        
        # 查找超限的状态
        sql = """
        SELECT state_hash, COUNT(*) as count
        FROM experiences
        GROUP BY state_hash
        HAVING count > ?;
        """
        
        cursor.execute(sql, (self.config.max_experiences_per_state,))
        overflowing_states = cursor.fetchall()
        
        pruned = 0
        
        for state_hash, count in overflowing_states:
            # 保留Top-K,删除其余
            delete_sql = """
            DELETE FROM experiences
            WHERE id IN (
                SELECT id FROM experiences
                WHERE state_hash = ?
                ORDER BY win_rate ASC, visit_count ASC
                LIMIT ?
            );
            """
            
            to_delete = count - self.config.max_experiences_per_state
            cursor.execute(delete_sql, (state_hash, to_delete))
            pruned += cursor.rowcount
        
        self.store.db.conn.commit()
        
        return pruned
    
    def _prune_by_age(self) -> int:
        """
        淘汰老化数据
        
        Returns:
            淘汰的数量
        """
        cutoff_date = datetime.now() - timedelta(days=self.config.aging_days)
        
        cursor = self.store.db.conn.cursor()
        
        sql = """
        DELETE FROM experiences 
        WHERE updated_at < ?;
        """
        
        cursor.execute(sql, (cutoff_date.isoformat(),))
        self.store.db.conn.commit()
        
        return cursor.rowcount
    
    def _infer_game_phase(self, step_number: int) -> str:
        """
        推断对局阶段
        
        Args:
            step_number: 步数
            
        Returns:
            阶段名称
        """
        if step_number <= 20:
            return "开局"
        elif step_number <= 60:
            return "中局"
        else:
            return "残局"
    
    def _log_stats(self):
        """记录统计信息"""
        logger.info("=" * 50)
        logger.info("经验池更新统计:")
        logger.info(f"  处理对局: {self.stats.games_processed}")
        logger.info(f"  新增经验: {self.stats.experiences_added}")
        logger.info(f"  更新经验: {self.stats.experiences_updated}")
        logger.info(f"  淘汰经验: {self.stats.experiences_pruned}")
        
        if self.stats.last_update_time:
            logger.info(f"  最后更新: {self.stats.last_update_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        if self.stats.last_prune_time:
            logger.info(f"  最后淘汰: {self.stats.last_prune_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 全局统计
        global_stats = self.store.get_statistics()
        logger.info(f"  当前总经验: {global_stats['total_experiences']}")
        logger.info(f"  唯一状态数: {global_stats['unique_states']}")
        logger.info(f"  平均胜率: {global_stats['avg_win_rate']:.3f}")
        logger.info("=" * 50)


# ============ 便捷函数 ============

def create_experience_updater(
    store: ExperienceStore,
    config: Optional[UpdaterConfig] = None
) -> ExperienceUpdater:
    """
    工厂函数: 创建经验池更新器
    
    Args:
        store: 经验池存储
        config: 配置
        
    Returns:
        ExperienceUpdater实例
    """
    return ExperienceUpdater(store, config)


def update_experiences_from_games(
    store: ExperienceStore,
    game_records: List[GameRecord],
    rewards_list: List[List[StepReward]],
    config: Optional[UpdaterConfig] = None
):
    """
    快捷函数: 从多局对弈更新经验池
    
    Args:
        store: 经验池存储
        game_records: 对局记录列表
        rewards_list: 奖励列表
        config: 配置
    """
    updater = ExperienceUpdater(store, config)
    updater.update_from_games_batch(game_records, rewards_list)