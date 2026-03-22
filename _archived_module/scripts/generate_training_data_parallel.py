"""
并行生成训练数据 - 优化版v2

优化策略：
1. 减少进程数（避免内存溢出）
2. 子进程不加载PyTorch
3. 降低搜索深度
"""

import json
import sys
import subprocess
from pathlib import Path
from tqdm import tqdm
from concurrent.futures import ProcessPoolExecutor, as_completed

sys.path.insert(0, '.')

from neo4j import GraphDatabase


def annotate_with_engine(fen: str, engine_path: str, depth: int = 10):
    """用引擎标注单个局面（不加载PyTorch）"""
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
        pv = []
        
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
        
        semantic_tags = compute_semantic_tags_simple(fen)
        
        return {
            'fen': fen,
            'score': score,
            'best_move': best_move,
            'pv': pv,
            'semantic_tags': semantic_tags,
            'semantic_vector': [semantic_tags.get(tag, 0.0) for tag in get_semantic_tag_list()]
        }
    except Exception as e:
        return None


def get_semantic_tag_list():
    """返回语义标签列表（不依赖PyTorch）"""
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


def compute_semantic_tags_simple(fen: str):
    """简单的语义标签计算（不依赖PyTorch）"""
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
    
    open_files = 0
    for c in range(9):
        has_pawn = any(pieces[i] in 'Pp' for i in range(10))
        if not has_pawn:
            open_files += 1
    if open_files > 0:
        tags['open_file'] = min(1.0, open_files / 3)
    
    return tags


def main():
    print("=" * 60)
    print("Position Encoder 训练数据生成 (并行优化版v2)")
    print("=" * 60)
    
    NEO4J_URI = "bolt://localhost:7687"
    NEO4J_USER = "neo4j"
    NEO4J_PASSWORD = "xiangqi123"
    ENGINE_PATH = "data/engine/pikafish-avx2.exe"
    OUTPUT_PATH = Path("data/training/position_data_1m.jsonl")
    NUM_POSITIONS = 1000000
    ENGINE_DEPTH = 10
    NUM_WORKERS = 6
    
    print(f"\n配置:")
    print(f"  目标数量: {NUM_POSITIONS}")
    print(f"  搜索深度: {ENGINE_DEPTH}")
    print(f"  并行进程: {NUM_WORKERS}")
    
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"\n[Step 1] 连接Neo4j...")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    with driver.session() as session:
        result = session.run("MATCH (p:Position) RETURN count(p) as count")
        total_count = result.single()['count']
        print(f"Position节点总数: {total_count}")
    
    print(f"\n[Step 2] 提取 {NUM_POSITIONS} 个局面...")
    with driver.session() as session:
        query = """
        MATCH (p:Position)
        WHERE p.total_games >= 5
        RETURN p.fen as fen
        ORDER BY rand()
        LIMIT $limit
        """
        result = session.run(query, limit=NUM_POSITIONS)
        fens = [record['fen'] for record in result]
    
    print(f"提取了 {len(fens)} 个局面")
    driver.close()
    
    print(f"\n[Step 3] 并行标注 ({NUM_WORKERS} 进程)...")
    annotated = []
    
    with ProcessPoolExecutor(max_workers=NUM_WORKERS) as executor:
        futures = {executor.submit(annotate_with_engine, fen, ENGINE_PATH, ENGINE_DEPTH): fen for fen in fens}
        
        for future in tqdm(as_completed(futures), total=len(futures), desc="标注中"):
            result = future.result()
            if result:
                annotated.append(result)
    
    print(f"\n[Step 4] 保存到 {OUTPUT_PATH}...")
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        for item in annotated:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    
    print(f"\n{'=' * 60}")
    print(f"完成！生成 {len(annotated)} 条训练数据")
    print(f"保存到: {OUTPUT_PATH}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
