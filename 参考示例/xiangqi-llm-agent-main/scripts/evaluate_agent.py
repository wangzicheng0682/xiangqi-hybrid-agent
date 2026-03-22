"""
Agent评估脚本
评估指定Agent的ELO分数
"""
import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.evaluation.elo import EloManager, GameResult as EloGameResult, create_elo_manager
from src.game.engine_adapter import ChessEngineAdapter
from src.llm.client import create_llm_client, LLMConfig
from src.self_play.player import Player, PlayerConfig, PlayerColor
from src.self_play.game_runner import GameRunner, GameRunnerConfig
import yaml

logger = logging.getLogger(__name__)


def load_config():
    """加载配置"""
    config_path = Path(__file__).parent.parent / "configs" / "self_play.yaml"
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    return {}


def main(args):
    """主函数"""
    logger.info("=" * 60)
    logger.info("Agent评估")
    logger.info("=" * 60)
    
    # 加载配置
    config = load_config()
    
    # 初始化组件
    engine = ChessEngineAdapter()
    llm_client = create_llm_client()
    
    # ELO管理器
    elo_manager = create_elo_manager()
    
    # 注册或获取Agent
    agent1 = elo_manager.get_agent_by_name_version(args.agent_name, args.agent_version)
    if not agent1:
        agent1 = elo_manager.register_agent(args.agent_name, args.agent_version)
        logger.info(f"注册Agent: {agent1.full_name}")
    else:
        logger.info(f"找到Agent: {agent1.full_name}, 当前ELO: {agent1.elo:.1f}")
    
    # 对手
    if args.opponent_name and args.opponent_version:
        agent2 = elo_manager.get_agent_by_name_version(args.opponent_name, args.opponent_version)
        if not agent2:
            agent2 = elo_manager.register_agent(args.opponent_name, args.opponent_version)
    else:
        # 使用基准Agent
        agent2 = elo_manager.get_agent_by_name_version("Baseline", "v1.0")
        if not agent2:
            agent2 = elo_manager.register_agent("Baseline", "v1.0", initial_elo=1500.0)
    
    logger.info(f"对手: {agent2.full_name}, 当前ELO: {agent2.elo:.1f}")
    
    # 创建玩家
    player_config1 = PlayerConfig(color=PlayerColor.RED)
    player_config2 = PlayerConfig(color=PlayerColor.BLACK)
    player1 = Player(agent1.name, llm_client, engine, player_config1)
    player2 = Player(agent2.name, llm_client, engine, player_config2)
    
    # 游戏运行器
    runner = GameRunner(engine, GameRunnerConfig())
    
    # 运行对局
    logger.info(f"\n开始评估: {args.num_games} 局对弈")
    
    results = {"wins": 0, "losses": 0, "draws": 0}
    
    for i in range(args.num_games):
        logger.info(f"\n对局 {i + 1}/{args.num_games}")
        
        try:
            game_record = runner.run_game(player1, player2)
            
            # 更新ELO
            if game_record.result.value == "RED_WIN":
                elo_manager.record_match(agent1.agent_id, agent2.agent_id, EloGameResult.WIN)
                results["wins"] += 1
            elif game_record.result.value == "BLACK_WIN":
                elo_manager.record_match(agent1.agent_id, agent2.agent_id, EloGameResult.LOSS)
                results["losses"] += 1
            else:
                elo_manager.record_match(agent1.agent_id, agent2.agent_id, EloGameResult.DRAW)
                results["draws"] += 1
            
            logger.info(f"结果: {game_record.result.value}")
        
        except Exception as e:
            logger.error(f"对局失败: {e}", exc_info=True)
            continue
    
    # 输出结果
    agent1_updated = elo_manager.get_agent(agent1.agent_id)
    logger.info("\n" + "=" * 60)
    logger.info("评估结果")
    logger.info("=" * 60)
    logger.info(f"Agent: {agent1_updated.full_name}")
    logger.info(f"初始ELO: {agent1.elo:.1f}")
    logger.info(f"最终ELO: {agent1_updated.elo:.1f}")
    logger.info(f"ELO变化: {agent1_updated.elo - agent1.elo:+.1f}")
    logger.info(f"胜: {results['wins']}, 负: {results['losses']}, 和: {results['draws']}")
    logger.info(f"胜率: {results['wins'] / args.num_games * 100:.1f}%")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="评估Agent")
    parser.add_argument('--agent-name', type=str, required=True, help='Agent名称')
    parser.add_argument('--agent-version', type=str, required=True, help='Agent版本')
    parser.add_argument('--opponent-name', type=str, help='对手名称')
    parser.add_argument('--opponent-version', type=str, help='对手版本')
    parser.add_argument('--num-games', type=int, default=10, help='对局数量')
    
    args = parser.parse_args()
    main(args)

