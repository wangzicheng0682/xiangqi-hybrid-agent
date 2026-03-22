"""
从PGN文件生成训练数据

解析PGN → 提取每个局面 → 引擎标注 → 语义标签
"""

import json
import sys
import subprocess
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from tqdm import tqdm
import re

sys.path.insert(0, '.')


def parse_pgn_file(pgn_path: str):
    """解析PGN文件，提取所有FEN"""
    fens = set()
    
    with open(pgn_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    games = content.split('\n\n[')
    
    for game in games:
        moves_start = game.find('1.')
        if moves_start == -1:
            continue
        
        moves_section = game[moves_start:]
        moves_section = re.sub(r'\{[^}]*\}', '', moves_section)
        moves_section = re.sub(r'\([^)]*\)', '', moves_section)
        moves_section = re.sub(r'\d+\.\.\.', '', moves_section)
        moves_section = re.sub(r'1-0|0-1|1/2-1/2|\*', '', moves_section)
        
        moves = moves_section.split()
        moves = [m for m in moves if re.match(r'^[a-zA-Z]\d[a-zA-Z]\d$', m) or '+' in m or '#' in m]
        
        if moves:
            initial_fen = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"
            fens.add(initial_fen)
    
    return list(fens)


def annotate_position(fen: str, engine_path: str, depth: int = 10):
    """标注单个局面"""
    try:
        proc = subprocess.Popen(
            [engine_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        commands = f"position fen {fen}\ngo depth {depth}\n"
        stdout, _ = proc.communicate(input=commands, timeout=30)
        proc.kill()
        
        score = 0
        best_move = ""
        
        for line in stdout.split('\n'):
            if 'score cp' in line:
                parts = line.split('score cp')[1].split()[0]
                try:
                    score = int(parts) / 100.0
                except:
                    pass
            elif 'score mate' in line:
                parts = line.split('score mate')[1].split()[0]
                try:
                    mate_in = int(parts)
                    score = 100 if mate_in > 0 else -100
                except:
                    pass
            elif 'bestmove' in line:
                parts = line.split()
                if len(parts) >= 2:
                    best_move = parts[1]
        
        semantic_tags = compute_semantic_tags(fen)
        
        return {
            'fen': fen,
            'score': score,
            'best_move': best_move,
            'semantic_tags': semantic_tags,
            'semantic_vector': [semantic_tags.get(tag, 0.0) for tag in get_semantic_tag_list()]
        }
    except Exception as e:
        return None


def get_semantic_tag_list():
    return [
        "opening", "middlegame", "endgame",
        "material_advantage", "material_disadvantage",
        "king_safety_red", "king_safety_black",
        "center_control", "side_control",
        "attack_red", "attack_black",
        "defense_red", "defense_black",
        "threat_red", "threat_black",
        "hanging_piece", "pinned_piece",
        "fork_opportunity", "skewer_opportunity",
        "passed_pawn", "isolated_pawn",
        "open_file", "semi_open_file",
        "active_rook", "passive_rook",
        "knight_outpost", "bishop_pair",
        "tempo_advantage", "initiative",
        "space_advantage", "mobility_advantage",
        "critical_position", "quiet_position"
    ]


def compute_semantic_tags(fen: str):
    tags = {}
    board_str = fen.split()[0]
    pieces = board_str.replace('/', '')
    piece_count = sum(1 for c in pieces if c.isalpha())
    
    if piece_count >= 28:
        tags['opening'] = 0.9
    elif piece_count >= 16:
        tags['middlegame'] = 0.9
    else:
        tags['endgame'] = 0.9
    
    red_value = sum({'K':0,'A':20,'B':20,'N':40,'R':90,'C':45,'P':10}.get(c, 0) for c in pieces if c.isupper())
    black_value = sum({'k':0,'a':20,'b':20,'n':40,'r':90,'c':45,'p':10}.get(c, 0) for c in pieces if c.islower())
    
    diff = red_value - black_value
    if diff > 100:
        tags['material_advantage'] = min(1.0, diff / 500)
    elif diff < -100:
        tags['material_disadvantage'] = min(1.0, abs(diff) / 500)
    
    return tags


def main():
    print("=" * 60)
    print("从PGN生成训练数据")
    print("=" * 60)
    
    PGN_FILES = [
        r"d:\xiangqi-hybrid-agent\data\init_data\dpxq-99813games.pgns",
        r"d:\xiangqi-hybrid-agent\data\init_data\WXF-41743games.pgns"
    ]
    ENGINE_PATH = "data/engine/pikafish-avx2.exe"
    OUTPUT_PATH = Path("data/training/position_data_pgn.jsonl")
    NUM_POSITIONS = 1000000
    ENGINE_DEPTH = 10
    NUM_WORKERS = 6
    
    print(f"\n[Step 1] 解析PGN文件...")
    all_fens = []
    for pgn_file in PGN_FILES:
        if Path(pgn_file).exists():
            print(f"  解析: {pgn_file}")
            fens = parse_pgn_file(pgn_file)
            all_fens.extend(fens)
            print(f"  提取: {len(fens)} 个初始局面")
    
    all_fens = list(set(all_fens))
    print(f"\n总计唯一局面: {len(all_fens)}")
    
    if len(all_fens) > NUM_POSITIONS:
        import random
        all_fens = random.sample(all_fens, NUM_POSITIONS)
        print(f"采样到: {NUM_POSITIONS} 个局面")
    
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"\n[Step 2] 并行标注 ({NUM_WORKERS} 进程)...")
    annotated = []
    
    with ProcessPoolExecutor(max_workers=NUM_WORKERS) as executor:
        futures = {executor.submit(annotate_position, fen, ENGINE_PATH, ENGINE_DEPTH): fen for fen in all_fens}
        
        for future in tqdm(as_completed(futures), total=len(futures), desc="标注中"):
            result = future.result()
            if result:
                annotated.append(result)
    
    print(f"\n[Step 3] 保存到 {OUTPUT_PATH}...")
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        for item in annotated:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    
    print(f"\n{'=' * 60}")
    print(f"完成！生成 {len(annotated)} 条训练数据")
    print(f"保存到: {OUTPUT_PATH}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
