"""
主入口文件
提供统一的命令行接口，调度各个模块
"""
import argparse
import logging
import sys
import yaml
from pathlib import Path
from typing import Optional, Dict, Any

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_config(config_name: str) -> Dict[str, Any]:
    """
    加载配置文件
    
    Args:
        config_name: 配置文件名（不含.yaml）
        
    Returns:
        配置字典
    """
    config_path = Path(__file__).parent.parent / "configs" / f"{config_name}.yaml"
    
    if not config_path.exists():
        logger.warning(f"配置文件不存在: {config_path}, 使用默认配置")
        return {}
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    logger.info(f"加载配置文件: {config_path}")
    return config or {}


def run_self_play(args):
    """运行自我对弈"""
    from scripts.run_self_play import main as self_play_main
    self_play_main(args)


def evaluate_agent(args):
    """评估Agent"""
    from scripts.evaluate_agent import main as evaluate_main
    evaluate_main(args)


def import_games(args):
    """导入人类对局"""
    from scripts.import_human_games import main as import_main
    import_main(args)


def cleanup_experience(args):
    """清理经验池"""
    from scripts.cleanup_experience import main as cleanup_main
    cleanup_main(args)


def run_api_server(args):
    """运行API服务器"""
    import uvicorn
    from src.api.server import app
    
    host = args.host or "0.0.0.0"
    port = args.port or 8000
    reload = args.reload
    
    logger.info(f"启动API服务器: http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, reload=reload)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="中国象棋AI - 主入口",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 运行自我对弈
  python -m src.main self-play --num-games 10
  
  # 评估Agent
  python -m src.main evaluate --agent-name MyAgent --agent-version v1.0
  
  # 运行API服务器
  python -m src.main api --host 0.0.0.0 --port 8000
  
  # 导入人类对局
  python -m src.main import-games --file games.pgn
  
  # 清理经验池
  python -m src.main cleanup --min-visits 5
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 自我对弈
    self_play_parser = subparsers.add_parser('self-play', help='运行自我对弈')
    self_play_parser.add_argument('--num-games', type=int, default=10, help='对局数量')
    self_play_parser.add_argument('--config', type=str, help='配置文件路径（可选）')
    self_play_parser.add_argument('--output-dir', type=str, default='data/games', help='输出目录')
    
    # 评估Agent
    evaluate_parser = subparsers.add_parser('evaluate', help='评估Agent')
    evaluate_parser.add_argument('--agent-name', type=str, required=True, help='Agent名称')
    evaluate_parser.add_argument('--agent-version', type=str, required=True, help='Agent版本')
    evaluate_parser.add_argument('--opponent-name', type=str, help='对手名称')
    evaluate_parser.add_argument('--opponent-version', type=str, help='对手版本')
    evaluate_parser.add_argument('--num-games', type=int, default=10, help='对局数量')
    
    # API服务器
    api_parser = subparsers.add_parser('api', help='运行API服务器')
    api_parser.add_argument('--host', type=str, help='主机地址')
    api_parser.add_argument('--port', type=int, help='端口号')
    api_parser.add_argument('--reload', action='store_true', help='自动重载')
    
    # 导入对局
    import_parser = subparsers.add_parser('import-games', help='导入人类对局')
    import_parser.add_argument('--file', type=str, required=True, help='对局文件路径')
    import_parser.add_argument('--format', type=str, default='pgn', help='文件格式 (pgn, json)')
    
    # 清理经验池
    cleanup_parser = subparsers.add_parser('cleanup', help='清理经验池')
    cleanup_parser.add_argument('--min-visits', type=int, default=5, help='最小访问次数')
    cleanup_parser.add_argument('--min-win-rate', type=float, help='最小胜率')
    cleanup_parser.add_argument('--dry-run', action='store_true', help='仅显示，不删除')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    try:
        if args.command == 'self-play':
            run_self_play(args)
        elif args.command == 'evaluate':
            evaluate_agent(args)
        elif args.command == 'import-games':
            import_games(args)
        elif args.command == 'cleanup':
            cleanup_experience(args)
        elif args.command == 'api':
            run_api_server(args)
        else:
            parser.print_help()
            sys.exit(1)
    
    except KeyboardInterrupt:
        logger.info("用户中断")
        sys.exit(0)
    except Exception as e:
        logger.error(f"执行失败: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

