"""
生成100万训练数据 - 优化版

优化点:
1. 线程数 = CPU核心数 - 2 (避免过订阅)
2. 批量写文件 (每1000条写一次)
3. 降低搜索深度 12 -> 8 (速度翻倍)
"""

import json
import subprocess
import random
import os
from pathlib import Path
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from neo4j import GraphDatabase


def annotate_position(fen: str, engine_path: str, depth: int = 8):
    """单个局面标注"""
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
        
        score = 0.0
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
                    score = 100.0 if mate_in > 0 else -100.0
                except:
                    pass
            elif 'bestmove' in line:
                parts = line.split()
                if len(parts) >= 2:
                    best_move = parts[1]
        
        action_value = max(-1.0, min(1.0, score / 100.0))
        
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
            'semantic_tags': semantic_tags
        }
    except Exception as e:
        return None


def main():
    print("=" * 60)
    print("生成100万训练数据 - 优化版")
    print("=" * 60)
    
    NEO4J_URI = "bolt://localhost:7687"
    NEO4J_USER = "neo4j"
    NEO4J_PASSWORD = "xiangqi123"
    ENGINE_PATH = "data/engine/pikafish-avx2.exe"
    OUTPUT_PATH = Path("data/training/position_data_1m.jsonl")
    NUM_POSITIONS = 1000000
    ENGINE_DEPTH = 8
    NUM_WORKERS = 22
    BATCH_SIZE = 1000
    
    print(f"\n配置:")
    print(f"  目标数量: {NUM_POSITIONS:,}")
    print(f"  搜索深度: {ENGINE_DEPTH} (降低以提速)")
    print(f"  并行线程: {NUM_WORKERS} (24核 - 2系统保留)")
    print(f"  批量写入: 每{BATCH_SIZE}条")
    
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
    
    print(f"\n[Step 3] 并行标注 ({NUM_WORKERS} 线程)...")
    
    batch = []
    total_written = 0
    
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
            futures = {executor.submit(annotate_position, fen, ENGINE_PATH, ENGINE_DEPTH): fen for fen in fens}
            
            for future in tqdm(as_completed(futures), total=len(futures), desc="标注中"):
                result = future.result()
                if result:
                    batch.append(result)
                    
                    if len(batch) >= BATCH_SIZE:
                        for item in batch:
                            f.write(json.dumps(item, ensure_ascii=False) + '\n')
                        total_written += len(batch)
                        batch = []
        
        if batch:
            for item in batch:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
            total_written += len(batch)
    
    print(f"\n{'=' * 60}")
    print(f"完成! 生成 {total_written:,} 条训练数据")
    print(f"保存到: {OUTPUT_PATH}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
