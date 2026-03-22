"""
导入人类对局脚本
从PGN或其他格式文件导入人类对局到经验池
"""
import argparse
import logging
import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.memory.store import ExperienceStore
from src.game.board import Board
from src.game.engine_adapter import ChessEngineAdapter

logger = logging.getLogger(__name__)


def parse_pgn_file(file_path: Path):
    """解析PGN文件（简化实现）"""
    # 这里应该实现完整的PGN解析
    # 简化版本，实际需要处理PGN格式
    logger.warning("PGN解析功能待实现，当前仅支持JSON格式")
    return []


def parse_json_file(file_path: Path):
    """解析JSON格式的对局文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    games = []
    if isinstance(data, list):
        games = data
    elif isinstance(data, dict):
        if 'games' in data:
            games = data['games']
        else:
            games = [data]
    
    return games


def import_game(game_data: dict, store: ExperienceStore, engine: ChessEngineAdapter):
    """导入单局对局"""
    try:
        fen = game_data.get('initial_fen', Board.create_initial().fen)
        moves = game_data.get('moves', [])
        result = game_data.get('result', 'DRAW')
        
        board = Board(fen=fen, move_history=[])
        
        for i, move in enumerate(moves):
            # 应用走法
            from src.game.engine_adapter import Board as EngineBoard
            engine_board = EngineBoard(fen=board.fen, move_history=board.move_history)
            new_board = engine.apply_move(engine_board, move)
            
            # 创建经验记录
            state_hash = board.get_state_hash()
            player_color = "RED" if i % 2 == 0 else "BLACK"
            
            # 判断胜率（简化）
            if result == "RED_WIN":
                win_rate = 1.0 if player_color == "RED" else 0.0
            elif result == "BLACK_WIN":
                win_rate = 1.0 if player_color == "BLACK" else 0.0
            else:
                win_rate = 0.5
            
            # 添加到经验池
            from src.memory.schema import Experience
            experience = Experience(
                state_hash=state_hash,
                state_fen=board.fen,
                move=move,
                reward=1.0 if win_rate > 0.5 else -1.0,
                win_rate=win_rate,
                visit_count=1,
                total_reward=1.0 if win_rate > 0.5 else -1.0,
                player_color=player_color,
                game_phase="中局"  # 简化
            )
            
            store.add_experience(experience)
            
            # 更新棋盘
            board = Board(fen=new_board.fen, move_history=board.move_history + [move])
        
        return True
    
    except Exception as e:
        logger.error(f"导入对局失败: {e}", exc_info=True)
        return False


def main(args):
    """主函数"""
    logger.info("=" * 60)
    logger.info("导入人类对局")
    logger.info("=" * 60)
    
    file_path = Path(args.file)
    if not file_path.exists():
        logger.error(f"文件不存在: {file_path}")
        return
    
    # 初始化组件
    store = ExperienceStore()
    engine = ChessEngineAdapter()
    
    # 解析文件
    logger.info(f"解析文件: {file_path}")
    
    if args.format == 'json':
        games = parse_json_file(file_path)
    elif args.format == 'pgn':
        games = parse_pgn_file(file_path)
    else:
        logger.error(f"不支持的格式: {args.format}")
        return
    
    logger.info(f"找到 {len(games)} 局对局")
    
    # 导入对局
    imported = 0
    failed = 0
    
    for i, game_data in enumerate(games):
        logger.info(f"导入对局 {i + 1}/{len(games)}")
        if import_game(game_data, store, engine):
            imported += 1
        else:
            failed += 1
    
    logger.info("\n" + "=" * 60)
    logger.info("导入完成")
    logger.info("=" * 60)
    logger.info(f"成功: {imported}")
    logger.info(f"失败: {failed}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="导入人类对局")
    parser.add_argument('--file', type=str, required=True, help='对局文件路径')
    parser.add_argument('--format', type=str, default='json', choices=['json', 'pgn'], help='文件格式')
    
    args = parser.parse_args()
    main(args)

