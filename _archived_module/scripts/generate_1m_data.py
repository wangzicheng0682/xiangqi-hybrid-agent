"""
生成100万训练数据

从Neo4j提取局面，用Pikafish标注action-values (128个胜率分箱)
"""

import json
import subprocess
import random
from pathlib import Path
from tqdm import tqdm
from concurrent.futures import ProcessPoolExecutor, as_completed
from neo4j import GraphDatabase


def annotate_position_full(fen: str, engine_path: str, depth: int = 12):
    """标注单个局面 - 完整版"""
    try:
        proc = subprocess.Popen(
            [engine_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        commands = f"position fen {fen}\ngo depth {depth}\n"
        stdout, _ = proc.communicate(input=commands, timeout=60)
        proc.kill()
        
        score = 0.0
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
                    score = 100.0 if mate_in > 0 else -100.0
                except:
                    pass
            elif 'bestmove' in line:
                parts = line.split()
                if len(parts) >= 2:
                    best_move = parts[1]
            elif ' pv ' in line:
                pv_part = line.split(' pv ')[1].split()
                pv = pv_part[:5]
        
        action_value = score / 100.0
        action_value = max(-1.0, min(1.0, action_value))
        
        piece_count = sum(1 for c in fen.split()[0] if c.isalpha())
        
        semantic_tags = {}
        if piece_count >= 28:
            semantic_tags['opening'] = 0.9
        elif piece_count >= 16:
            semantic_tags['middlegame'] = 0.9
        else:
            semantic_tags['endgame'] = 0.9
        
        return {
            'fen': fen,
            'state_value': action_value,
            'action_value': action_value,
            'best_move': best_move,
            'pv': pv,
            'semantic_tags': semantic_tags
        }
    except Exception as e:
        return None


def main():
    print("=" * 60)
    print("生成100万训练数据")
    print("=" * 60)
    
    NEO4J_URI = "bolt://localhost:7687"
    NEO4J_USER = "neo4j"
    NEO4J_PASSWORD = "xiangqi123"
    ENGINE_PATH = "data/engine/pikafish-avx2.exe"
    OUTPUT_PATH = Path("data/training/position_data_1m.jsonl")
    NUM_POSITIONS = 1000000
    ENGINE_DEPTH = 12
    NUM_WORKERS = 20
    
    print(f"\n配置:")
    print(f"  目标数量: {NUM_POSITIONS:,}")
    print(f"  搜索深度: {ENGINE_DEPTH}")
    print(f"  并行进程: {NUM_WORKERS}")
    
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"\n[Step 1] 连接Neo4j...")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    with driver.session() as session:
        result = session.run("MATCH (p:Position) RETURN count(p) as count")
        total_count = result.single()['count']
        print(f"Position节点总数: {total_count:,}")
    
    print(f"\n[Step 2] 提取 {NUM_POSITIONS:,} 个局面...")
    with driver.session() as session:
        query = """
        MATCH (p:Position)
        RETURN p.fen as fen
        ORDER BY rand()
        LIMIT $limit
        """
        result = session.run(query, limit=NUM_POSITIONS)
        fens = [record['fen'] for record in result]
    
    print(f"提取了 {len(fens):,} 个局面")
    driver.close()
    
    print(f"\n[Step 3] 并行标注 ({NUM_WORKERS} 进程)...")
    annotated = []
    
    with ProcessPoolExecutor(max_workers=NUM_WORKERS) as executor:
        futures = {executor.submit(annotate_position_full, fen, ENGINE_PATH, ENGINE_DEPTH): fen for fen in fens}
        
        for future in tqdm(as_completed(futures), total=len(futures), desc="标注中"):
            result = future.result()
            if result:
                annotated.append(result)
                
                if len(annotated) % 10000 == 0:
                    print(f"\n已标注: {len(annotated):,}")
    
    print(f"\n[Step 4] 保存到 {OUTPUT_PATH}...")
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        for item in annotated:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    
    print(f"\n{'=' * 60}")
    print(f"完成!生成 {len(annotated):,} 条训练数据")
    print(f"保存到: {OUTPUT_PATH}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
