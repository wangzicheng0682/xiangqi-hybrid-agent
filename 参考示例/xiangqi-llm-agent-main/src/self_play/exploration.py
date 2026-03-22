"""
探索策略模块
根据经验池统计决定探索行为
"""
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import random
import logging
import math

logger = logging.getLogger(__name__)


class ExplorationStrategy(Enum):
    """探索策略类型"""
    GREEDY = "greedy"              # 贪心: 选择最优走法
    EPSILON_GREEDY = "epsilon_greedy"  # ε-贪心: 以ε概率随机探索
    UCB = "ucb"                    # UCB: 上置信界算法
    SOFTMAX = "softmax"            # Softmax: 根据得分概率采样
    MIXED = "mixed"                # 混合: 动态切换策略


class ActionType(Enum):
    """动作类型"""
    GREEDY = "greedy"              # 贪心: 选择已知最优
    SUB_OPTIMAL = "sub_optimal"    # 次优: 选择次优走法
    RANDOM = "random"              # 随机: 完全随机探索


@dataclass
class MoveStatistics:
    """走法统计信息"""
    move: str                      # 走法
    visit_count: int               # 访问次数
    total_reward: float            # 累计奖励
    avg_reward: float              # 平均奖励
    last_visit: Optional[float] = None  # 最后访问时间


@dataclass
class ExplorationConfig:
    """探索配置"""
    strategy: ExplorationStrategy = ExplorationStrategy.EPSILON_GREEDY
    
    # Epsilon-Greedy参数
    epsilon: float = 0.2           # 探索概率
    epsilon_decay: float = 0.995   # ε衰减率
    epsilon_min: float = 0.05      # 最小ε值
    
    # 子选项概率
    greedy_prob: float = 0.7       # 贪心概率
    sub_optimal_prob: float = 0.2  # 次优概率
    random_prob: float = 0.1       # 随机探索概率
    
    # UCB参数
    ucb_c: float = 1.414           # UCB探索常数(√2)
    
    # Softmax参数
    temperature: float = 1.0       # 温度参数
    
    # 动态调整
    phase_adaptive: bool = True    # 是否根据对局阶段调整
    opening_epsilon: float = 0.3   # 开局探索率
    midgame_epsilon: float = 0.2   # 中局探索率
    endgame_epsilon: float = 0.1   # 残局探索率


@dataclass
class ExplorationDecision:
    """探索决策结果"""
    selected_move: str             # 选中的走法
    action_type: ActionType        # 动作类型
    confidence: float              # 置信度(0-1)
    all_scores: Dict[str, float]   # 所有走法的得分
    statistics: Optional[Dict[str, MoveStatistics]] = None  # 统计信息


class ExplorationManager:
    """
    探索管理器
    
    职责:
    - 根据经验池统计决定探索策略
    - 在贪心/次优/随机之间平衡
    - 支持多种探索算法
    """
    
    def __init__(self, config: Optional[ExplorationConfig] = None):
        """
        初始化探索管理器
        
        Args:
            config: 探索配置
        """
        self.config = config or ExplorationConfig()
        self.current_epsilon = self.config.epsilon
        self.exploration_count = 0
        self.exploitation_count = 0
        
        logger.info(
            f"探索管理器初始化: 策略={self.config.strategy.value}, "
            f"ε={self.config.epsilon}"
        )
    
    def decide_action(
        self,
        legal_moves: List[str],
        move_statistics: Optional[Dict[str, MoveStatistics]] = None,
        game_phase: str = "中局",
        total_visits: int = 0
    ) -> ExplorationDecision:
        """
        决定探索动作
        
        Args:
            legal_moves: 合法走法列表
            move_statistics: 走法统计信息(可选)
            game_phase: 对局阶段
            total_visits: 总访问次数
            
        Returns:
            探索决策结果
        """
        if not legal_moves:
            raise ValueError("合法走法列表为空")
        
        # 调整探索参数(根据阶段)
        if self.config.phase_adaptive:
            epsilon = self._get_phase_epsilon(game_phase)
        else:
            epsilon = self.current_epsilon
        
        # 根据策略选择
        if self.config.strategy == ExplorationStrategy.GREEDY:
            decision = self._greedy_selection(legal_moves, move_statistics)
        
        elif self.config.strategy == ExplorationStrategy.EPSILON_GREEDY:
            decision = self._epsilon_greedy_selection(
                legal_moves, move_statistics, epsilon
            )
        
        elif self.config.strategy == ExplorationStrategy.UCB:
            decision = self._ucb_selection(
                legal_moves, move_statistics, total_visits
            )
        
        elif self.config.strategy == ExplorationStrategy.SOFTMAX:
            decision = self._softmax_selection(legal_moves, move_statistics)
        
        elif self.config.strategy == ExplorationStrategy.MIXED:
            decision = self._mixed_selection(
                legal_moves, move_statistics, epsilon, total_visits
            )
        
        else:
            raise ValueError(f"不支持的策略: {self.config.strategy}")
        
        # 更新统计
        self._update_stats(decision.action_type)
        
        logger.debug(
            f"探索决策: {decision.selected_move}, "
            f"类型={decision.action_type.value}, "
            f"置信度={decision.confidence:.3f}"
        )
        
        return decision
    
    def update_epsilon(self):
        """更新epsilon值(衰减)"""
        self.current_epsilon = max(
            self.config.epsilon_min,
            self.current_epsilon * self.config.epsilon_decay
        )
        logger.debug(f"Epsilon衰减至: {self.current_epsilon:.4f}")
    
    def reset_epsilon(self):
        """重置epsilon为初始值"""
        self.current_epsilon = self.config.epsilon
        logger.info(f"Epsilon重置为: {self.current_epsilon}")
    
    def get_exploration_rate(self) -> float:
        """
        获取当前探索率
        
        Returns:
            探索率(0-1)
        """
        total = self.exploration_count + self.exploitation_count
        if total == 0:
            return 0.0
        return self.exploration_count / total
    
    # ============ 内部策略实现 ============
    
    def _greedy_selection(
        self,
        legal_moves: List[str],
        move_statistics: Optional[Dict[str, MoveStatistics]]
    ) -> ExplorationDecision:
        """纯贪心选择"""
        if not move_statistics:
            # 无统计信息,随机选择
            return self._random_selection(legal_moves, ActionType.RANDOM)
        
        # 按平均奖励排序
        sorted_moves = self._sort_moves_by_reward(legal_moves, move_statistics)
        
        if not sorted_moves:
            return self._random_selection(legal_moves, ActionType.RANDOM)
        
        selected_move = sorted_moves[0]
        scores = {move: stat.avg_reward for move, stat in move_statistics.items()}
        
        return ExplorationDecision(
            selected_move=selected_move,
            action_type=ActionType.GREEDY,
            confidence=1.0,
            all_scores=scores,
            statistics=move_statistics
        )
    
    def _epsilon_greedy_selection(
        self,
        legal_moves: List[str],
        move_statistics: Optional[Dict[str, MoveStatistics]],
        epsilon: float
    ) -> ExplorationDecision:
        """ε-贪心选择"""
        # 决定是探索还是利用
        if random.random() < epsilon:
            # 探索: 根据概率分配
            rand = random.random()
            
            if rand < self.config.random_prob / epsilon:
                # 完全随机
                return self._random_selection(legal_moves, ActionType.RANDOM)
            else:
                # 次优选择
                return self._sub_optimal_selection(legal_moves, move_statistics)
        else:
            # 利用: 贪心选择
            return self._greedy_selection(legal_moves, move_statistics)
    
    def _ucb_selection(
        self,
        legal_moves: List[str],
        move_statistics: Optional[Dict[str, MoveStatistics]],
        total_visits: int
    ) -> ExplorationDecision:
        """UCB上置信界选择"""
        if not move_statistics or total_visits == 0:
            return self._random_selection(legal_moves, ActionType.RANDOM)
        
        # 计算UCB得分
        ucb_scores = {}
        for move in legal_moves:
            stat = move_statistics.get(move)
            
            if stat is None or stat.visit_count == 0:
                # 未访问的走法赋予高优先级
                ucb_scores[move] = float('inf')
            else:
                # UCB公式: avg_reward + c * sqrt(ln(total) / visit_count)
                exploration_bonus = self.config.ucb_c * math.sqrt(
                    math.log(total_visits + 1) / stat.visit_count
                )
                ucb_scores[move] = stat.avg_reward + exploration_bonus
        
        # 选择UCB最高的走法
        selected_move = max(ucb_scores.keys(), key=lambda m: ucb_scores[m])
        
        # 判断动作类型
        action_type = ActionType.GREEDY
        if ucb_scores[selected_move] == float('inf'):
            action_type = ActionType.RANDOM
        
        return ExplorationDecision(
            selected_move=selected_move,
            action_type=action_type,
            confidence=0.8,
            all_scores=ucb_scores,
            statistics=move_statistics
        )
    
    def _softmax_selection(
        self,
        legal_moves: List[str],
        move_statistics: Optional[Dict[str, MoveStatistics]]
    ) -> ExplorationDecision:
        """Softmax概率采样"""
        if not move_statistics:
            return self._random_selection(legal_moves, ActionType.RANDOM)
        
        # 计算softmax概率
        rewards = []
        valid_moves = []
        
        for move in legal_moves:
            stat = move_statistics.get(move)
            if stat and stat.visit_count > 0:
                rewards.append(stat.avg_reward / self.config.temperature)
                valid_moves.append(move)
        
        if not valid_moves:
            return self._random_selection(legal_moves, ActionType.RANDOM)
        
        # Softmax归一化
        max_reward = max(rewards)
        exp_rewards = [math.exp(r - max_reward) for r in rewards]
        sum_exp = sum(exp_rewards)
        probabilities = [e / sum_exp for e in exp_rewards]
        
        # 按概率采样
        selected_move = random.choices(valid_moves, weights=probabilities)[0]
        
        # 构建得分字典
        scores = {m: p for m, p in zip(valid_moves, probabilities)}
        
        return ExplorationDecision(
            selected_move=selected_move,
            action_type=ActionType.GREEDY,
            confidence=scores[selected_move],
            all_scores=scores,
            statistics=move_statistics
        )
    
    def _mixed_selection(
        self,
        legal_moves: List[str],
        move_statistics: Optional[Dict[str, MoveStatistics]],
        epsilon: float,
        total_visits: int
    ) -> ExplorationDecision:
        """混合策略: 动态选择"""
        # 根据访问次数选择策略
        if total_visits < 10:
            # 早期: 随机探索
            return self._random_selection(legal_moves, ActionType.RANDOM)
        elif total_visits < 100:
            # 中期: UCB
            return self._ucb_selection(legal_moves, move_statistics, total_visits)
        else:
            # 后期: ε-贪心
            return self._epsilon_greedy_selection(
                legal_moves, move_statistics, epsilon
            )
    
    def _sub_optimal_selection(
        self,
        legal_moves: List[str],
        move_statistics: Optional[Dict[str, MoveStatistics]]
    ) -> ExplorationDecision:
        """次优选择"""
        if not move_statistics:
            return self._random_selection(legal_moves, ActionType.SUB_OPTIMAL)
        
        # 按奖励排序
        sorted_moves = self._sort_moves_by_reward(legal_moves, move_statistics)
        
        if len(sorted_moves) < 2:
            return self._random_selection(legal_moves, ActionType.SUB_OPTIMAL)
        
        # 选择次优(第2-5名随机)
        sub_optimal_range = sorted_moves[1:min(5, len(sorted_moves))]
        selected_move = random.choice(sub_optimal_range)
        
        scores = {move: stat.avg_reward for move, stat in move_statistics.items()}
        
        return ExplorationDecision(
            selected_move=selected_move,
            action_type=ActionType.SUB_OPTIMAL,
            confidence=0.6,
            all_scores=scores,
            statistics=move_statistics
        )
    
    def _random_selection(
        self,
        legal_moves: List[str],
        action_type: ActionType
    ) -> ExplorationDecision:
        """随机选择"""
        selected_move = random.choice(legal_moves)
        
        return ExplorationDecision(
            selected_move=selected_move,
            action_type=action_type,
            confidence=0.0,
            all_scores={move: 0.0 for move in legal_moves}
        )
    
    def _sort_moves_by_reward(
        self,
        legal_moves: List[str],
        move_statistics: Dict[str, MoveStatistics]
    ) -> List[str]:
        """
        按平均奖励排序走法
        
        Args:
            legal_moves: 合法走法列表
            move_statistics: 统计信息
            
        Returns:
            排序后的走法列表
        """
        moves_with_stats = [
            (move, move_statistics.get(move))
            for move in legal_moves
            if move in move_statistics and move_statistics[move].visit_count > 0
        ]
        
        # 按平均奖励降序排序
        sorted_moves = sorted(
            moves_with_stats,
            key=lambda x: x[1].avg_reward if x[1] else -float('inf'),
            reverse=True
        )
        
        return [move for move, _ in sorted_moves]
    
    def _get_phase_epsilon(self, game_phase: str) -> float:
        """
        根据对局阶段获取epsilon
        
        Args:
            game_phase: 对局阶段
            
        Returns:
            epsilon值
        """
        phase_epsilons = {
            "开局": self.config.opening_epsilon,
            "中局": self.config.midgame_epsilon,
            "残局": self.config.endgame_epsilon
        }
        
        return phase_epsilons.get(game_phase, self.current_epsilon)
    
    def _update_stats(self, action_type: ActionType):
        """更新统计计数"""
        if action_type == ActionType.GREEDY:
            self.exploitation_count += 1
        else:
            self.exploration_count += 1


# ============ 便捷函数 ============

def create_exploration_manager(
    strategy: ExplorationStrategy = ExplorationStrategy.EPSILON_GREEDY,
    epsilon: float = 0.2,
    config: Optional[ExplorationConfig] = None
) -> ExplorationManager:
    """
    工厂函数: 创建探索管理器
    
    Args:
        strategy: 探索策略
        epsilon: 探索概率
        config: 完整配置(可选)
        
    Returns:
        ExplorationManager实例
    """
    if config is None:
        config = ExplorationConfig(
            strategy=strategy,
            epsilon=epsilon
        )
    
    return ExplorationManager(config)


def select_exploration_move(
    legal_moves: List[str],
    move_statistics: Optional[Dict[str, MoveStatistics]],
    strategy: ExplorationStrategy = ExplorationStrategy.EPSILON_GREEDY,
    epsilon: float = 0.2
) -> str:
    """
    快捷函数: 选择探索走法
    
    Args:
        legal_moves: 合法走法列表
        move_statistics: 统计信息
        strategy: 策略
        epsilon: 探索率
        
    Returns:
        选中的走法
    """
    manager = create_exploration_manager(strategy, epsilon)
    decision = manager.decide_action(legal_moves, move_statistics)
    return decision.selected_move