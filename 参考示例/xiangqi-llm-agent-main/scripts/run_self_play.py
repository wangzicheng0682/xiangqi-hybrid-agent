"""
自我对弈脚本
运行指定数量的自我对弈对局
"""
import argparse
import logging
import sys
from pathlib import Path
from datetime import datetime
import json

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.game.engine_adapter import ChessEngineAdapter
from src.llm.client import create_llm_client, LLMConfig
from src.self_play.player import Player, PlayerConfig, PlayerColor
from src.self_play.game_runner import GameRunner, GameRunnerConfig
from src.memory.store import ExperienceStore
from src.memory.updater import ExperienceUpdater
from src.reward.evaluator import RewardEvaluator, RewardConfig
from src.evaluation.elo import EloManager, GameResult as EloGameResult, create_elo_manager
import yaml

logger = logging.getLogger(__name__)


def load_config(config_path: Path = None) -> dict:
    """加载配置"""
    if config_path and config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    # 加载默认配置
    default_config_path = Path(__file__).parent.parent / "configs" / "self_play.yaml"
    if default_config_path.exists():
        with open(default_config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    return {}


def main(args):
    """主函数"""
    logger.info("=" * 60)
    logger.info("启动自我对弈")
    logger.info("=" * 60)
    
    # 加载配置
    config = load_config(args.config and Path(args.config))
    
    # 初始化组件
    logger.info("初始化组件...")
    
    # 引擎
    engine = ChessEngineAdapter()
    
    # LLM客户端
    llm_config = LLMConfig()
    llm_client = create_llm_client(config.get('llm', {}).get('provider', 'anthropic'), llm_config)
    
    # 玩家配置
    player_cfg = config.get('player', {})
    red_config = PlayerConfig(
        color=PlayerColor.RED,
        mode=player_cfg.get('mode', 'mixed'),
        exploration_rate=player_cfg.get('exploration_rate', 0.2),
        temperature=player_cfg.get('temperature', 0.7),
        top_k=player_cfg.get('top_k', 3),
        use_retrieval=player_cfg.get('use_retrieval', True)
    )
    
    black_config = PlayerConfig(
        color=PlayerColor.BLACK,
        mode=player_cfg.get('mode', 'mixed'),
        exploration_rate=player_cfg.get('exploration_rate', 0.2),
        temperature=player_cfg.get('temperature', 0.7),
        top_k=player_cfg.get('top_k', 3),
        use_retrieval=player_cfg.get('use_retrieval', True)
    )
    
    # 创建玩家
    red_player = Player("Red_Player", llm_client, engine, red_config)
    black_player = Player("Black_Player", llm_client, engine, black_config)
    
    # 游戏运行器
    runner_cfg = config.get('game_runner', {})
    runner_config = GameRunnerConfig(
        max_moves=runner_cfg.get('max_moves', 300),
        save_boards=runner_cfg.get('save_boards', True),
        verbose=runner_cfg.get('verbose', True),
        log_interval=runner_cfg.get('log_interval', 10)
    )
    runner = GameRunner(engine, runner_config)
    
    # 经验存储和更新器
    experience_store = ExperienceStore()
    reward_config = RewardConfig()
    evaluator = RewardEvaluator(reward_config)
    updater = ExperienceUpdater(experience_store)
    
    # ELO管理器
    elo_manager = create_elo_manager()
    
    # 注册Agent（如果不存在）
    red_agent_id = f"Red_Player_v1.0"
    black_agent_id = f"Black_Player_v1.0"
    
    if not elo_manager.get_agent(red_agent_id):
        elo_manager.register_agent("Red_Player", "v1.0")
    if not elo_manager.get_agent(black_agent_id):
        elo_manager.register_agent("Black_Player", "v1.0")
    
    # 运行对局
    logger.info(f"开始运行 {args.num_games} 局对弈...")
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    results = {
        "red_wins": 0,
        "black_wins": 0,
        "draws": 0,
        "games": []
    }
    
    for i in range(args.num_games):
        logger.info(f"\n{'=' * 60}")
        logger.info(f"对局 {i + 1}/{args.num_games}")
        logger.info(f"{'=' * 60}")
        
        try:
            # 运行对局
            # game_record = runner.run_game(red_player, black_player)
            game_record = runner.run_game(red_player, black_player, initial_board=engine.get_initial_board)
            
            # 计算奖励
            step_rewards = evaluator.evaluate_game(game_record)
            
            # 更新经验池
            updater.update_from_game(game_record, step_rewards)
            
            # 更新ELO
            result_map = {
                "RED_WIN": EloGameResult.WIN,
                "BLACK_WIN": EloGameResult.LOSS,
                "DRAW": EloGameResult.DRAW
            }
            elo_result = result_map.get(game_record.result.value, EloGameResult.DRAW)
            
            if elo_result == EloGameResult.WIN:
                elo_manager.record_match(red_agent_id, black_agent_id, EloGameResult.WIN)
            elif elo_result == EloGameResult.LOSS:
                elo_manager.record_match(red_agent_id, black_agent_id, EloGameResult.LOSS)
            else:
                elo_manager.record_match(red_agent_id, black_agent_id, EloGameResult.DRAW)
            
            # 保存对局记录
            game_file = output_dir / f"game_{game_record.game_id}.json"
            with open(game_file, 'w', encoding='utf-8') as f:
                json.dump(game_record.to_dict(), f, ensure_ascii=False, indent=2)
            
            # 统计
            if game_record.result.value == "RED_WIN":
                results["red_wins"] += 1
            elif game_record.result.value == "BLACK_WIN":
                results["black_wins"] += 1
            else:
                results["draws"] += 1
            
            results["games"].append({
                "game_id": game_record.game_id,
                "result": game_record.result.value,
                "moves": game_record.total_moves,
                "duration": game_record.duration
            })
            
            logger.info(f"对局完成: {game_record.result.value}, 步数: {game_record.total_moves}")
        
        except Exception as e:
            logger.error(f"对局失败: {e}", exc_info=True)
            continue
    
    # 输出统计
    logger.info("\n" + "=" * 60)
    logger.info("对弈统计")
    logger.info("=" * 60)
    logger.info(f"总对局数: {args.num_games}")
    logger.info(f"红方胜: {results['red_wins']}")
    logger.info(f"黑方胜: {results['black_wins']}")
    logger.info(f"和局: {results['draws']}")
    
    # 保存统计
    stats_file = output_dir / f"stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    logger.info(f"\n统计已保存: {stats_file}")
    logger.info("自我对弈完成")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="运行自我对弈")
    parser.add_argument('--num-games', type=int, default=10, help='对局数量')
    parser.add_argument('--config', type=str, help='配置文件路径')
    parser.add_argument('--output-dir', type=str, default='data/games', help='输出目录')
    
    args = parser.parse_args()
    main(args)

