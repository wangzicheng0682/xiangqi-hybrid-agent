"""
自我对弈游戏运行器
负责执行完整的象棋对局并记录过程
"""
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import logging
import uuid

from src.game.board import Board
from src.game.engine_adapter import ChessEngineAdapter, GameResult
from src.self_play.player import Player, PlayerColor

logger = logging.getLogger(__name__)


@dataclass
class GameStep:
    """单步记录"""
    step_number: int                    # 步数(从1开始)
    player: str                         # 行动玩家名称
    player_color: str                   # 行动玩家颜色
    board_before: Board                 # 走法前的棋盘状态
    move: str                           # 执行的走法
    board_after: Board                  # 走法后的棋盘状态
    state_hash: str                     # 状态哈希
    timestamp: float                    # 时间戳
    
    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "step_number": self.step_number,
            "player": self.player,
            "player_color": self.player_color,
            "board_before_fen": self.board_before.fen,
            "move": self.move,
            "board_after_fen": self.board_after.fen,
            "state_hash": self.state_hash,
            "timestamp": self.timestamp
        }


@dataclass
class GameRecord:
    """完整对局记录"""
    game_id: str                        # 对局ID
    red_player: str                     # 红方玩家名称
    black_player: str                   # 黑方玩家名称
    steps: List[GameStep]               # 步骤列表
    result: GameResult                  # 对局结果
    total_moves: int                    # 总步数
    start_time: datetime                # 开始时间
    end_time: datetime                  # 结束时间
    duration: float                     # 持续时间(秒)
    metadata: Dict[str, Any] = field(default_factory=dict)  # 额外元数据
    
    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "game_id": self.game_id,
            "red_player": self.red_player,
            "black_player": self.black_player,
            "steps": [step.to_dict() for step in self.steps],
            "result": self.result.value,
            "total_moves": self.total_moves,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "duration": self.duration,
            "metadata": self.metadata
        }
    
    def get_winner(self) -> Optional[str]:
        """
        获取胜者名称
        
        Returns:
            胜者名称,和棋返回None
        """
        if self.result == GameResult.RED_WIN:
            return self.red_player
        elif self.result == GameResult.BLACK_WIN:
            return self.black_player
        else:
            return None
    
    def get_moves_list(self) -> List[str]:
        """
        获取走法列表
        
        Returns:
            走法列表
        """
        return [step.move for step in self.steps]
    
    def get_trajectory(self) -> List[Tuple[str, str]]:
        """
        获取轨迹(状态-动作对)
        
        Returns:
            [(state_hash, move), ...]
        """
        return [(step.state_hash, step.move) for step in self.steps]


@dataclass
class GameRunnerConfig:
    """游戏运行器配置"""
    max_moves: int = 300                # 最大步数(超过判和)
    save_boards: bool = True            # 是否保存完整棋盘状态
    verbose: bool = True                # 是否打印详细信息
    log_interval: int = 10              # 日志输出间隔


class GameRunner:
    """
    自我对弈游戏运行器
    
    职责:
    - 执行完整的象棋对局
    - 记录每一步的状态和走法
    - 判断终局并返回结果
    """
    
    def __init__(
        self,
        engine: ChessEngineAdapter,
        config: Optional[GameRunnerConfig] = None
    ):
        """
        初始化运行器
        
        Args:
            engine: 象棋引擎
            config: 运行器配置
        """
        self.engine = engine
        self.config = config or GameRunnerConfig()
        
        logger.info("游戏运行器初始化完成")
    
    def run_game(
        self,
        red_player: Player,
        black_player: Player,
        initial_board: Optional[Board] = None,
        game_id: Optional[str] = None
    ) -> GameRecord:
        """
        运行一局完整对弈
        
        Args:
            red_player: 红方玩家
            black_player: 黑方玩家
            initial_board: 初始棋盘(可选,默认标准开局)
            game_id: 对局ID(可选,默认自动生成)
            
        Returns:
            完整对局记录
            
        Raises:
            ValueError: 玩家配置错误
        """
        # 验证玩家颜色
        if red_player.config.color != PlayerColor.RED:
            raise ValueError(f"红方玩家 {red_player.name} 颜色配置错误")
        if black_player.config.color != PlayerColor.BLACK:
            raise ValueError(f"黑方玩家 {black_player.name} 颜色配置错误")
        
        # 初始化
        game_id = game_id or self._generate_game_id()
        board = initial_board or Board.create_initial()
        steps: List[GameStep] = []
        start_time = datetime.now()
        
        logger.info(
            f"开始对局 {game_id}: "
            f"{red_player.name} vs {black_player.name}"
        )
        
        # 玩家映射
        players = {
            "RED": red_player,
            "BLACK": black_player
        }
        
        # 主循环
        step_number = 0
        while True:
            step_number += 1
            
            # 检查最大步数
            if step_number > self.config.max_moves:
                logger.warning(f"对局 {game_id} 超过最大步数 {self.config.max_moves}")
                result = GameResult.DRAW
                break
            
            # 检查终局
            if self.engine.is_terminal(board):
                print(dir(self.engine))
                result = self.engine.get_winner(board)
                logger.info(f"对局 {game_id} 终局: {result.value}")
                break
            
            # 获取当前玩家
            current_color = self.engine.get_current_player(board)
            current_player = players[current_color]
            
            # 记录走法前状态
            board_before = board.copy() if self.config.save_boards else board
            
            # 选择走法
            try:
                move = current_player.select_move(board)
            except Exception as e:
                logger.error(
                    f"对局 {game_id} 步数 {step_number}: "
                    f"玩家 {current_player.name} 走法选择失败: {e}"
                )
                # 判负
                result = GameResult.BLACK_WIN if current_color == "RED" else GameResult.RED_WIN
                break
            
            # 应用走法
            try:
                board_after = self.engine.apply_move(board, move)
            except Exception as e:
                logger.error(
                    f"对局 {game_id} 步数 {step_number}: "
                    f"走法 {move} 应用失败: {e}"
                )
                # 判负
                result = GameResult.BLACK_WIN if current_color == "RED" else GameResult.RED_WIN
                break
            
            # 记录步骤
            step = GameStep(
                step_number=step_number,
                player=current_player.name,
                player_color=current_color,
                board_before=board_before,
                move=move,
                board_after=board_after.copy() if self.config.save_boards else board_after,
                state_hash=board_before.get_state_hash(),
                timestamp=datetime.now().timestamp()
            )
            steps.append(step)
            
            # 更新棋盘
            board = board_after
            
            # 输出日志
            if self.config.verbose and step_number % self.config.log_interval == 0:
                logger.info(
                    f"对局 {game_id} 进行中: "
                    f"步数 {step_number}, "
                    f"当前玩家 {current_player.name}, "
                    f"走法 {move}"
                )
        
        # 结束时间
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # 构建记录
        record = GameRecord(
            game_id=game_id,
            red_player=red_player.name,
            black_player=black_player.name,
            steps=steps,
            result=result,
            total_moves=len(steps),
            start_time=start_time,
            end_time=end_time,
            duration=duration,
            metadata={
                "red_player_stats": red_player.get_stats().__dict__,
                "black_player_stats": black_player.get_stats().__dict__
            }
        )
        
        logger.info(
            f"对局 {game_id} 结束: "
            f"结果 {result.value}, "
            f"步数 {len(steps)}, "
            f"耗时 {duration:.2f}秒"
        )
        
        return record
    
    def run_games_batch(
        self,
        red_player: Player,
        black_player: Player,
        num_games: int,
        reset_stats: bool = True
    ) -> List[GameRecord]:
        """
        批量运行多局对弈
        
        Args:
            red_player: 红方玩家
            black_player: 黑方玩家
            num_games: 对局数量
            reset_stats: 是否在开始前重置统计
            
        Returns:
            对局记录列表
        """
        if reset_stats:
            red_player.reset_stats()
            black_player.reset_stats()
        
        logger.info(f"开始批量对弈: {num_games} 局")
        
        records = []
        for i in range(num_games):
            logger.info(f"对局 {i+1}/{num_games}")
            
            record = self.run_game(
                red_player=red_player,
                black_player=black_player
            )
            records.append(record)
        
        logger.info(f"批量对弈完成: {num_games} 局")
        self._print_batch_summary(records)
        
        return records
    
    # ============ 内部方法 ============
    
    def _generate_game_id(self) -> str:
        """生成对局ID"""
        return f"game_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    
    def _print_batch_summary(self, records: List[GameRecord]):
        """
        打印批量对弈汇总
        
        Args:
            records: 对局记录列表
        """
        total = len(records)
        red_wins = sum(1 for r in records if r.result == GameResult.RED_WIN)
        black_wins = sum(1 for r in records if r.result == GameResult.BLACK_WIN)
        draws = sum(1 for r in records if r.result == GameResult.DRAW)
        
        avg_moves = sum(r.total_moves for r in records) / total
        avg_duration = sum(r.duration for r in records) / total
        
        logger.info("=" * 50)
        logger.info(f"批量对弈汇总 (共{total}局):")
        logger.info(f"  红方胜: {red_wins} ({red_wins/total*100:.1f}%)")
        logger.info(f"  黑方胜: {black_wins} ({black_wins/total*100:.1f}%)")
        logger.info(f"  和棋: {draws} ({draws/total*100:.1f}%)")
        logger.info(f"  平均步数: {avg_moves:.1f}")
        logger.info(f"  平均耗时: {avg_duration:.2f}秒")
        logger.info("=" * 50)


# ============ 便捷函数 ============

def create_game_runner(
    engine: ChessEngineAdapter,
    max_moves: int = 300,
    verbose: bool = True
) -> GameRunner:
    """
    工厂函数: 创建游戏运行器
    
    Args:
        engine: 象棋引擎
        max_moves: 最大步数
        verbose: 是否详细输出
        
    Returns:
        GameRunner实例
    """
    config = GameRunnerConfig(
        max_moves=max_moves,
        verbose=verbose
    )
    
    return GameRunner(engine, config)


def run_single_game(
    red_player: Player,
    black_player: Player,
    engine: ChessEngineAdapter
) -> GameRecord:
    """
    快捷函数: 运行单局对弈
    
    Args:
        red_player: 红方玩家
        black_player: 黑方玩家
        engine: 象棋引擎
        
    Returns:
        对局记录
    """
    runner = GameRunner(engine)
    return runner.run_game(red_player, black_player)


def run_multiple_games(
    red_player: Player,
    black_player: Player,
    engine: ChessEngineAdapter,
    num_games: int
) -> List[GameRecord]:
    """
    快捷函数: 运行多局对弈
    
    Args:
        red_player: 红方玩家
        black_player: 黑方玩家
        engine: 象棋引擎
        num_games: 对局数量
        
    Returns:
        对局记录列表
    """
    runner = GameRunner(engine)
    return runner.run_games_batch(red_player, black_player, num_games)