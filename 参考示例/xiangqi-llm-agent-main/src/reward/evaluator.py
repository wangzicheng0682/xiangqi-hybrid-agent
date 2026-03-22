"""
奖励评估模块
根据对弈结果和局面评估计算奖励
"""
from typing import Dict, Optional, List, Any
from dataclasses import dataclass
from enum import Enum
import logging

from src.game.board import Board
from src.game.engine_adapter import ChessEngineAdapter, GameResult
from src.self_play.game_runner import GameRecord, GameStep

logger = logging.getLogger(__name__)


class RewardType(Enum):
    """奖励类型"""
    WIN = "win"                    # 胜利奖励
    LOSS = "loss"                  # 失败惩罚
    DRAW = "draw"                  # 和棋奖励
    POSITION = "position"          # 局面奖励
    MIXED = "mixed"                # 混合奖励


@dataclass
class RewardConfig:
    """奖励配置"""
    # 终局奖励
    win_reward: float = 1.0        # 胜利奖励
    loss_reward: float = -1.0      # 失败惩罚
    draw_reward: float = 0.0       # 和棋奖励
    
    # 折扣因子
    gamma: float = 0.99            # 时间折扣因子
    use_discount: bool = True      # 是否使用折扣
    
    # 局面评估
    use_position_eval: bool = False  # 是否使用局面评估
    position_weight: float = 0.1   # 局面评估权重
    
    # 步数相关
    early_win_bonus: float = 0.1   # 快速获胜额外奖励
    long_game_penalty: float = 0.05  # 长对局惩罚
    step_threshold: int = 50       # 步数阈值
    
    # 奖励塑形
    use_reward_shaping: bool = True  # 是否使用奖励塑形
    intermediate_reward_weight: float = 0.05  # 中间奖励权重


@dataclass
class StepReward:
    """单步奖励"""
    step_number: int               # 步数
    player: str                    # 玩家
    move: str                      # 走法
    reward: float                  # 奖励值
    reward_type: RewardType        # 奖励类型
    details: Dict[str, float]      # 奖励详情


class RewardEvaluator:
    """
    奖励评估器
    
    职责:
    - 计算终局奖励
    - (可选)计算局面评估奖励
    - 支持时间折扣
    - 支持奖励塑形
    """
    
    def __init__(
        self,
        config: Optional[RewardConfig] = None,
        engine: Optional[ChessEngineAdapter] = None
    ):
        """
        初始化评估器
        
        Args:
            config: 奖励配置
            engine: 象棋引擎(用于局面评估)
        """
        self.config = config or RewardConfig()
        self.engine = engine
        
        if self.config.use_position_eval and engine is None:
            logger.warning("启用局面评估但未提供引擎,将禁用局面评估")
            self.config.use_position_eval = False
        
        logger.info(
            f"奖励评估器初始化: "
            f"胜={self.config.win_reward}, "
            f"负={self.config.loss_reward}, "
            f"和={self.config.draw_reward}, "
            f"γ={self.config.gamma}"
        )
    
    def evaluate_game(
        self,
        game_record: GameRecord
    ) -> List[StepReward]:
        """
        评估完整对局的奖励
        
        Args:
            game_record: 对局记录
            
        Returns:
            每一步的奖励列表
        """
        logger.info(
            f"评估对局 {game_record.game_id}: "
            f"结果={game_record.result.value}, "
            f"步数={game_record.total_moves}"
        )
        
        # 计算终局奖励
        terminal_rewards = self._compute_terminal_rewards(game_record)
        
        # 应用时间折扣
        if self.config.use_discount:
            terminal_rewards = self._apply_discount(terminal_rewards)
        
        # 添加中间奖励(可选)
        if self.config.use_reward_shaping:
            terminal_rewards = self._add_intermediate_rewards(
                terminal_rewards, game_record
            )
        
        logger.info(f"对局 {game_record.game_id} 奖励计算完成")
        
        return terminal_rewards
    
    def evaluate_position(
        self,
        board: Board,
        player_color: str
    ) -> float:
        """
        评估局面价值
        
        Args:
            board: 棋盘状态
            player_color: 玩家颜色("RED"/"BLACK")
            
        Returns:
            局面评估值(-1到1之间)
        """
        if not self.config.use_position_eval or not self.engine:
            return 0.0
        
        # 简化版局面评估(可扩展为调用引擎评估)
        # 这里返回0,实际使用时应调用引擎或ML模型
        logger.debug(f"评估局面: {player_color}")
        return 0.0
    
    # ============ 内部方法 ============
    
    def _compute_terminal_rewards(
        self,
        game_record: GameRecord
    ) -> List[StepReward]:
        """
        计算终局奖励
        
        Args:
            game_record: 对局记录
            
        Returns:
            奖励列表
        """
        result = game_record.result
        red_player = game_record.red_player
        black_player = game_record.black_player
        total_moves = game_record.total_moves
        
        # 确定基础奖励
        if result == GameResult.RED_WIN:
            red_reward = self.config.win_reward
            black_reward = self.config.loss_reward
        elif result == GameResult.BLACK_WIN:
            red_reward = self.config.loss_reward
            black_reward = self.config.win_reward
        elif result == GameResult.DRAW:
            red_reward = self.config.draw_reward
            black_reward = self.config.draw_reward
        else:
            # ONGOING(不应该出现)
            red_reward = 0.0
            black_reward = 0.0
        
        # 应用步数调整
        red_reward = self._adjust_for_steps(red_reward, total_moves, result == GameResult.RED_WIN)
        black_reward = self._adjust_for_steps(black_reward, total_moves, result == GameResult.BLACK_WIN)
        
        # 构建奖励列表
        rewards = []
        for step in game_record.steps:
            if step.player == red_player:
                reward_value = red_reward
            else:
                reward_value = black_reward
            
            rewards.append(StepReward(
                step_number=step.step_number,
                player=step.player,
                move=step.move,
                reward=reward_value,
                reward_type=self._get_reward_type(result, step.player, red_player, black_player),
                details={
                    "base_reward": reward_value,
                    "terminal_reward": reward_value
                }
            ))
        
        return rewards
    
    def _apply_discount(
        self,
        rewards: List[StepReward]
    ) -> List[StepReward]:
        """
        应用时间折扣(从终局往前传播)
        
        Args:
            rewards: 原始奖励列表
            
        Returns:
            折扣后的奖励列表
        """
        if not rewards:
            return rewards
        
        total_steps = len(rewards)
        discounted_rewards = []
        
        for i, reward in enumerate(rewards):
            # 计算距离终局的步数
            steps_to_end = total_steps - i - 1
            
            # 应用折扣: R_t = gamma^(T-t) * R_T
            discount_factor = self.config.gamma ** steps_to_end
            discounted_value = reward.reward * discount_factor
            
            # 创建新的奖励对象
            new_reward = StepReward(
                step_number=reward.step_number,
                player=reward.player,
                move=reward.move,
                reward=discounted_value,
                reward_type=reward.reward_type,
                details={
                    **reward.details,
                    "discount_factor": discount_factor,
                    "original_reward": reward.reward
                }
            )
            discounted_rewards.append(new_reward)
        
        return discounted_rewards
    
    def _add_intermediate_rewards(
        self,
        rewards: List[StepReward],
        game_record: GameRecord
    ) -> List[StepReward]:
        """
        添加中间奖励(奖励塑形)
        
        Args:
            rewards: 当前奖励列表
            game_record: 对局记录
            
        Returns:
            添加中间奖励后的列表
        """
        if not self.config.use_position_eval or not self.engine:
            return rewards
        
        # 简化版:可根据局面评估添加中间奖励
        # 这里暂不实现,返回原奖励
        return rewards
    
    def _adjust_for_steps(
        self,
        base_reward: float,
        total_steps: int,
        is_winner: bool
    ) -> float:
        """
        根据步数调整奖励
        
        Args:
            base_reward: 基础奖励
            total_steps: 总步数
            is_winner: 是否是胜者
            
        Returns:
            调整后的奖励
        """
        adjusted_reward = base_reward
        
        if is_winner and total_steps < self.config.step_threshold:
            # 快速获胜奖励
            bonus = self.config.early_win_bonus * (
                1.0 - total_steps / self.config.step_threshold
            )
            adjusted_reward += bonus
            logger.debug(f"快速获胜奖励: +{bonus:.3f}")
        
        elif total_steps > self.config.step_threshold * 2:
            # 长对局惩罚
            penalty = self.config.long_game_penalty * (
                total_steps / self.config.step_threshold - 2.0
            )
            adjusted_reward -= penalty
            logger.debug(f"长对局惩罚: -{penalty:.3f}")
        
        return adjusted_reward
    
    def _get_reward_type(
        self,
        result: GameResult,
        player: str,
        red_player: str,
        black_player: str
    ) -> RewardType:
        """
        确定奖励类型
        
        Args:
            result: 对局结果
            player: 当前玩家
            red_player: 红方玩家名称
            black_player: 黑方玩家名称
            
        Returns:
            奖励类型
        """
        if result == GameResult.DRAW:
            return RewardType.DRAW
        
        is_red = (player == red_player)
        
        if (result == GameResult.RED_WIN and is_red) or \
           (result == GameResult.BLACK_WIN and not is_red):
            return RewardType.WIN
        else:
            return RewardType.LOSS


class MonteCarloRewardEvaluator(RewardEvaluator):
    """
    蒙特卡洛奖励评估器
    使用MC方法计算回报
    """
    
    def evaluate_game(
        self,
        game_record: GameRecord
    ) -> List[StepReward]:
        """
        使用MC方法评估
        G_t = R_{t+1} + γR_{t+2} + γ²R_{t+3} + ...
        """
        logger.info(f"使用MC方法评估对局 {game_record.game_id}")
        
        # 先获取终局奖励
        terminal_rewards = self._compute_terminal_rewards(game_record)
        
        if not self.config.use_discount:
            return terminal_rewards
        
        # 计算累积回报(从后往前)
        mc_rewards = []
        cumulative_return = 0.0
        
        for reward in reversed(terminal_rewards):
            # G_t = R_t + γ * G_{t+1}
            cumulative_return = reward.reward + self.config.gamma * cumulative_return
            
            mc_reward = StepReward(
                step_number=reward.step_number,
                player=reward.player,
                move=reward.move,
                reward=cumulative_return,
                reward_type=reward.reward_type,
                details={
                    "terminal_reward": reward.reward,
                    "cumulative_return": cumulative_return
                }
            )
            mc_rewards.insert(0, mc_reward)
        
        return mc_rewards


# ============ 便捷函数 ============

def create_reward_evaluator(
    config: Optional[RewardConfig] = None,
    engine: Optional[ChessEngineAdapter] = None,
    use_monte_carlo: bool = False
) -> RewardEvaluator:
    """
    工厂函数: 创建奖励评估器
    
    Args:
        config: 奖励配置
        engine: 象棋引擎
        use_monte_carlo: 是否使用MC方法
        
    Returns:
        RewardEvaluator实例
    """
    if use_monte_carlo:
        return MonteCarloRewardEvaluator(config, engine)
    else:
        return RewardEvaluator(config, engine)


def evaluate_game_simple(
    game_record: GameRecord,
    win_reward: float = 1.0,
    loss_reward: float = -1.0
) -> List[StepReward]:
    """
    简化版对局评估(无折扣)
    
    Args:
        game_record: 对局记录
        win_reward: 胜利奖励
        loss_reward: 失败奖励
        
    Returns:
        奖励列表
    """
    config = RewardConfig(
        win_reward=win_reward,
        loss_reward=loss_reward,
        use_discount=False
    )
    evaluator = RewardEvaluator(config)
    return evaluator.evaluate_game(game_record)


def compute_average_reward(rewards: List[StepReward], player: str) -> float:
    """
    计算某个玩家的平均奖励
    
    Args:
        rewards: 奖励列表
        player: 玩家名称
        
    Returns:
        平均奖励
    """
    player_rewards = [r.reward for r in rewards if r.player == player]
    
    if not player_rewards:
        return 0.0
    
    return sum(player_rewards) / len(player_rewards)