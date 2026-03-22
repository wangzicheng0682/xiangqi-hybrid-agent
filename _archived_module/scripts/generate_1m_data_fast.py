"""
生成100万训练数据 - 极速版

优化点:
1. 线程数 = 22 (避免过订阅)
2. 批量写文件 (每1000条写一次)
3. 搜索深度 = 8
4. 每个线程复用引擎进程 (避免重复启动开销)
"""

import json
import subprocess
import random
import os
import time
import threading
from pathlib import Path
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from neo4j import GraphDatabase


class EngineWorker:
    """持久化引擎工作器"""
    def __init__(self, engine_path):
        self.engine_path = engine_path
        self.proc = None
        self.lock = threading.Lock()
    
    def start(self):
        self.proc = subprocess.Popen(
            [self.engine_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1
        )
        self.proc.stdin.write("uci\n")
        self.proc.stdin.flush()
        while True:
            line = self.proc.stdout.readline()
            if "uciok" in line:
                break
    
    def annotate(self, fen: str, depth: int = 8):
        with self.lock:
            try:
                self.proc.stdin.write(f"position fen {fen}\ngo depth {depth}\n")
                self.proc.stdin.flush()
                
                score = 0.0
                best_move = ""
                
                while True:
                    line = self.proc.stdout.readline()
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
                        break
                    elif line == '':
                        return None
                
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
    
    def stop(self):
        if self.proc:
            self.proc.kill()


engine_pool = {}
engine_pool_lock = threading.Lock()


def get_worker(engine_path):
    """获取当前线程的引擎工作器"""
    thread_id = threading.get_ident()
    with engine_pool_lock:
        if thread_id not in engine_pool:
            worker = EngineWorker(engine_path)
            worker.start()
            engine_pool[thread_id] = worker
        return engine_pool[thread_id]


def annotate_position(fen: str, engine_path: str, depth: int = 8):
    """使用持久化引擎标注"""
    worker = get_worker(engine_path)
    return worker.annotate(fen, depth)


def main():
    print("=" * 60)
    print("生成100万训练数据 - 极速版")
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
    print(f"  搜索深度: {ENGINE_DEPTH}")
    print(f"  并行线程: {NUM_WORKERS}")
    print(f"  批量写入: 每{BATCH_SIZE}条")
    print(f"  引擎复用: 是")
    
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
    
    print(f"\n[Step 3] 启动 {NUM_WORKERS} 个引擎进程...")
    time.sleep(1)
    
    print(f"\n[Step 4] 并行标注...")
    
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
    
    for worker in engine_pool.values():
        worker.stop()
    
    print(f"\n{'=' * 60}")
    print(f"完成! 生成 {total_written:,} 条训练数据")
    print(f"保存到: {OUTPUT_PATH}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
