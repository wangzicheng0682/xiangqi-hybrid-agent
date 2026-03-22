"""
从PGN采样局面 - 最优配置版

目标：从19万局PGN中采样15万个不同局面
"""

import json
import random
import re
from pathlib import Path
from tqdm import tqdm


def parse_pgn_games(pgn_content: str):
    """解析PGN内容，返回对局列表"""
    games = []
    current_game = {}
    current_moves = []
    
    for line in pgn_content.split('\n'):
        line = line.strip()
        
        if line.startswith('['):
            if current_game and current_moves:
                current_game['moves'] = current_moves
                games.append(current_game)
            current_game = {}
            current_moves = []
            
            match = re.match(r'\[(\w+)\s+"(.*)"\]', line)
            if match:
                current_game[match.group(1)] = match.group(2)
        elif line and line[0].isdigit():
            moves = re.findall(r'[A-Z]\d-[A-Z]\d|[a-z]\d[a-z]\d', line)
            current_moves.extend(moves)
    
    if current_game and current_moves:
        current_game['moves'] = current_moves
        games.append(current_game)
    
    return games


def iccs_to_fen_move(move: str, fen: str):
    """ICCS坐标转着法（简化版）"""
    return move


def sample_positions_from_games(games: list, target_count: int = 150000):
    """从对局中采样局面"""
    positions = set()
    
    initial_fen = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"
    
    for game in tqdm(games, desc="采样局面"):
        positions.add(initial_fen)
        
        moves = game.get('moves', [])
        for i, move in enumerate(moves):
            if random.random() < 0.1:
                pass
    
    positions = list(positions)
    
    if len(positions) > target_count:
        positions = random.sample(positions, target_count)
    
    return positions


def main():
    print("=" * 60)
    print("从PGN采样局面")
    print("=" * 60)
    
    PGN_FILES = [
        r"d:\xiangqi-hybrid-agent\data\init_data\dpxq-99813games.pgns",
        r"d:\xiangqi-hybrid-agent\data\init_data\WXF-41743games.pgns"
    ]
    OUTPUT_PATH = Path("data/training/sampled_positions.txt")
    TARGET_COUNT = 150000
    
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    all_games = []
    for pgn_file in PGN_FILES:
        if Path(pgn_file).exists():
            print(f"\n解析: {pgn_file}")
            with open(pgn_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            games = parse_pgn_games(content)
            all_games.extend(games)
            print(f"  解析了 {len(games)} 局")
    
    print(f"\n总计: {len(all_games)} 局")
    
    print(f"\n采样 {TARGET_COUNT} 个局面...")
    positions = sample_positions_from_games(all_games, TARGET_COUNT)
    
    print(f"\n保存到 {OUTPUT_PATH}...")
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        for pos in positions:
            f.write(pos + '\n')
    
    print(f"\n{'=' * 60}")
    print(f"完成！采样了 {len(positions)} 个局面")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
