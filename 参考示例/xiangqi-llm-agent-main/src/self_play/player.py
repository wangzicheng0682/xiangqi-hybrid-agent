"""
中国象棋AI玩家
封装走法选择逻辑,支持红方/黑方,探索/利用模式切换
"""
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
import logging

from src.game.board import Board
from src.game.engine_adapter import ChessEngineAdapter
from src.game.notation import NotationConverter
from src.llm.client import BaseLLMClient
from src.llm.move_selector import (
    MoveSelector, MoveSelectorConfig, 
    RetrievedExperience, MoveSelection
)
from src.llm.prompts import PromptMode

logger = logging.getLogger(__name__)


class PlayerColor(Enum):
    """玩家颜色"""
    RED = "RED"
    BLACK = "BLACK"


class PlayerMode(Enum):
    """玩家模式"""
    EXPLOITATION = "exploitation"  # 利用模式: 选择最优走法
    EXPLORATION = "exploration"    # 探索模式: 尝试新走法
    MIXED = "mixed"               # 混合模式: 动态切换


@dataclass
class PlayerConfig:
    """玩家配置"""
    color: PlayerColor                          # 玩家颜色
    mode: PlayerMode = PlayerMode.MIXED         # 玩家模式
    exploration_rate: float = 0.2               # 探索概率(混合模式下)
    temperature: float = 0.7                    # LLM温度
    top_k: int = 3                              # Top-K走法数量
    use_retrieval: bool = True                  # 是否使用检索
    max_retries: int = 3                        # 最大重试次数
    fallback_random: bool = True                # 降级策略
    
    # 阶段相关配置
    opening_exploration_rate: float = 0.3       # 开局探索率
    midgame_exploration_rate: float = 0.2       # 中局探索率
    endgame_exploration_rate: float = 0.1       # 残局探索率


@dataclass
class PlayerStats:
    """玩家统计"""
    moves_made: int = 0                         # 已下步数
    explorations: int = 0                       # 探索次数
    exploitations: int = 0                      # 利用次数
    retries: int = 0                            # 重试次数
    fallbacks: int = 0                          # 降级次数


class Player:
    """
    中国象棋AI玩家
    
    职责:
    - 在给定棋盘状态下选择走法
    - 支持红方/黑方
    - 支持探索/利用模式切换
    - 调用move_selector和经验检索
    """
    
    def __init__(
        self,
        name: str,
        llm_client: BaseLLMClient,
        engine: ChessEngineAdapter,
        config: Optional[PlayerConfig] = None,
        retrieval_callback: Optional[callable] = None
    ):
        """
        初始化玩家
        
        Args:
            name: 玩家名称
            llm_client: LLM客户端
            engine: 象棋引擎
            config: 玩家配置
            retrieval_callback: 经验检索回调函数 (board) -> RetrievedExperience
        """
        self.name = name
        self.client = llm_client
        self.engine = engine
        self.config = config or PlayerConfig(color=PlayerColor.RED)
        self.retrieval_callback = retrieval_callback
        
        # 初始化组件
        self.notation = NotationConverter()
        self.move_selector = self._create_move_selector()
        
        # 统计数据
        self.stats = PlayerStats()
        
        logger.info(
            f"创建玩家: {name} ({self.config.color.value}), "
            # f"模式: {self.config.mode.value}"
            f"模式: {self.config.mode}"
        )
    
    def select_move(
        self,
        board: Board,
        retrieved_experience: Optional[RetrievedExperience] = None
    ) -> str:
        """
        选择走法
        
        Args:
            board: 当前棋盘状态
            retrieved_experience: 检索到的经验(可选,优先使用此参数)
            
        Returns:
            选中的走法(坐标格式)
            
        Raises:
            ValueError: 无合法走法或玩家颜色不匹配
        """
        # 验证轮次
        current_player = self.engine.get_current_player(board)
        if current_player != self.config.color.value:
            raise ValueError(
                f"玩家 {self.name} ({self.config.color.value}) "
                f"无法在 {current_player} 的回合行动"
            )
        
        # 获取合法走法
        legal_moves = self.engine.legal_moves(board)
        if not legal_moves:
            raise ValueError(f"玩家 {self.name}: 无合法走法")
        
        logger.info(
            f"玩家 {self.name} 选择走法, "
            f"回合: {board.get_move_count()}, "
            f"合法走法数: {len(legal_moves)}"
        )
        
        # 生成走法描述
        move_descriptions = [
            self.notation.coord_to_chinese(move, board.fen)
            for move in legal_moves
        ]
        
        # 检索经验(如果未提供)
        if retrieved_experience is None and self.retrieval_callback:
            try:
                retrieved_experience = self.retrieval_callback(board)
            except Exception as e:
                logger.warning(f"经验检索失败: {e}")
                retrieved_experience = None
        
        # 判断对局阶段
        game_phase = self._determine_game_phase(board)
        
        # 调用move_selector
        try:
            result = self.move_selector.select_moves(
                board_text=board.to_text(include_history=True),
                legal_moves=legal_moves,
                move_descriptions=move_descriptions,
                current_player=current_player,
                move_count=board.get_move_count(),
                game_phase=game_phase,
                retrieved_experience=retrieved_experience
            )
            
            # 更新统计
            self._update_stats(result)
            
            selected_move = result.selected_moves[0]
            logger.info(
                f"玩家 {self.name} 选择: {selected_move} "
                f"({self.notation.coord_to_chinese(selected_move, board.fen)}), "
                f"模式: {result.mode.value}"
            )
            
            return selected_move
            
        except Exception as e:
            logger.error(f"玩家 {self.name} 走法选择失败: {e}")
            raise
    
    def select_move_batch(
        self,
        board: Board,
        top_k: Optional[int] = None
    ) -> List[str]:
        """
        批量选择Top-K走法
        
        Args:
            board: 当前棋盘
            top_k: 返回走法数量(默认使用配置中的top_k)
            
        Returns:
            Top-K走法列表
        """
        if top_k is None:
            top_k = self.config.top_k
        
        # 临时修改配置
        original_top_k = self.move_selector.config.top_k
        self.move_selector.config.top_k = top_k
        
        try:
            # 获取合法走法
            legal_moves = self.engine.legal_moves(board)
            move_descriptions = [
                self.notation.coord_to_chinese(move, board.fen)
                for move in legal_moves
            ]
            
            # 检索经验
            retrieved_experience = None
            if self.retrieval_callback:
                try:
                    retrieved_experience = self.retrieval_callback(board)
                except Exception as e:
                    logger.warning(f"经验检索失败: {e}")
            
            game_phase = self._determine_game_phase(board)
            
            result = self.move_selector.select_moves(
                board_text=board.to_text(include_history=True),
                legal_moves=legal_moves,
                move_descriptions=move_descriptions,
                current_player=self.engine.get_current_player(board),
                move_count=board.get_move_count(),
                game_phase=game_phase,
                retrieved_experience=retrieved_experience
            )
            
            return result.selected_moves
            
        finally:
            # 恢复配置
            self.move_selector.config.top_k = original_top_k
    
    def get_stats(self) -> PlayerStats:
        """获取玩家统计数据"""
        return self.stats
    
    def reset_stats(self):
        """重置统计数据"""
        self.stats = PlayerStats()
        logger.info(f"玩家 {self.name} 统计数据已重置")
    
    def set_mode(self, mode: PlayerMode):
        """
        设置玩家模式
        
        Args:
            mode: 新模式
        """
        old_mode = self.config.mode
        self.config.mode = mode
        logger.info(f"玩家 {self.name} 模式切换: {old_mode.value} -> {mode.value}")
    
    def set_exploration_rate(self, rate: float):
        """
        设置探索率
        
        Args:
            rate: 探索率(0-1)
        """
        if not 0 <= rate <= 1:
            raise ValueError(f"探索率必须在[0, 1]范围内: {rate}")
        
        self.config.exploration_rate = rate
        self.move_selector.config.exploration_rate = rate
        logger.info(f"玩家 {self.name} 探索率设置为: {rate}")
    
    # ============ 内部方法 ============
    
    def _create_move_selector(self) -> MoveSelector:
        """创建走法选择器"""
        selector_config = MoveSelectorConfig(
            top_k=self.config.top_k,
            exploration_rate=self.config.exploration_rate,
            temperature=self.config.temperature,
            max_retries=self.config.max_retries,
            fallback_random=self.config.fallback_random,
            use_experience=self.config.use_retrieval
        )
        
        return MoveSelector(self.client, selector_config)
    
    def _determine_game_phase(self, board: Board) -> str:
        """
        判断对局阶段
        
        Args:
            board: 棋盘状态
            
        Returns:
            阶段名称("开局"/"中局"/"残局")
        """
        move_count = board.get_move_count()
        
        if move_count < 20:
            return "开局"
        elif move_count < 60:
            return "中局"
        else:
            return "残局"
    
    def _get_phase_exploration_rate(self, game_phase: str) -> float:
        """
        根据阶段获取探索率
        
        Args:
            game_phase: 对局阶段
            
        Returns:
            探索率
        """
        phase_rates = {
            "开局": self.config.opening_exploration_rate,
            "中局": self.config.midgame_exploration_rate,
            "残局": self.config.endgame_exploration_rate
        }
        
        return phase_rates.get(game_phase, self.config.exploration_rate)
    
    def _update_stats(self, result: MoveSelection):
        """
        更新统计数据
        
        Args:
            result: 走法选择结果
        """
        self.stats.moves_made += 1
        self.stats.retries += result.retries
        
        if result.fallback_used:
            self.stats.fallbacks += 1
        
        if result.mode == PromptMode.EXPLORATION:
            self.stats.explorations += 1
        elif result.mode == PromptMode.EXPLOITATION:
            self.stats.exploitations += 1
    
    def __repr__(self) -> str:
        """字符串表示"""
        return (
            f"Player(name={self.name}, "
            f"color={self.config.color.value}, "
            f"mode={self.config.mode.value}, "
            f"moves={self.stats.moves_made})"
        )


# ============ 便捷函数 ============

def create_player(
    name: str,
    color: PlayerColor,
    llm_client: BaseLLMClient,
    engine: ChessEngineAdapter,
    mode: PlayerMode = PlayerMode.MIXED,
    exploration_rate: float = 0.2,
    retrieval_callback: Optional[callable] = None
) -> Player:
    """
    工厂函数: 创建玩家
    
    Args:
        name: 玩家名称
        color: 玩家颜色
        llm_client: LLM客户端
        engine: 象棋引擎
        mode: 玩家模式
        exploration_rate: 探索率
        retrieval_callback: 经验检索回调
        
    Returns:
        Player实例
    """
    config = PlayerConfig(
        color=color,
        mode=mode,
        exploration_rate=exploration_rate
    )
    
    return Player(
        name=name,
        llm_client=llm_client,
        engine=engine,
        config=config,
        retrieval_callback=retrieval_callback
    )


def create_player_pair(
    llm_client: BaseLLMClient,
    engine: ChessEngineAdapter,
    red_name: str = "红方AI",
    black_name: str = "黑方AI",
    mode: PlayerMode = PlayerMode.MIXED,
    retrieval_callback: Optional[callable] = None
) -> tuple[Player, Player]:
    """
    创建对弈双方玩家
    
    Args:
        llm_client: LLM客户端
        engine: 象棋引擎
        red_name: 红方名称
        black_name: 黑方名称
        mode: 玩家模式
        retrieval_callback: 经验检索回调
        
    Returns:
        (红方玩家, 黑方玩家)
    """
    red_player = create_player(
        name=red_name,
        color=PlayerColor.RED,
        llm_client=llm_client,
        engine=engine,
        mode=mode,
        retrieval_callback=retrieval_callback
    )
    
    black_player = create_player(
        name=black_name,
        color=PlayerColor.BLACK,
        llm_client=llm_client,
        engine=engine,
        mode=mode,
        retrieval_callback=retrieval_callback
    )
    
    return red_player, black_player