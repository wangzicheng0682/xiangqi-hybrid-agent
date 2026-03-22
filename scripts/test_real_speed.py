"""
用真实数据测试引擎速度
"""
import subprocess
import time
import threading
import json
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

class EngineWorker:
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
            start = time.time()
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
                
                elapsed = time.time() - start
                return {
                    'fen': fen,
                    'score': score,
                    'best_move': best_move,
                    'time': elapsed
                }
            except Exception as e:
                return None
    
    def stop(self):
        if self.proc:
            self.proc.kill()


def main():
    print("=" * 60)
    print("用真实数据测试引擎速度")
    print("=" * 60)
    
    ENGINE_PATH = "data/engine/pikafish-avx2.exe"
    DATA_PATH = "data/training/position_data_1m.jsonl"
    NUM_WORKERS = 22
    TEST_COUNT = 500
    DEPTH = 8
    
    print(f"\n加载数据...")
    with open(DATA_PATH, 'r') as f:
        all_lines = f.readlines()
    
    sample_lines = random.sample(all_lines, TEST_COUNT)
    test_fens = [json.loads(line)['fen'] for line in sample_lines]
    
    print(f"随机抽取 {TEST_COUNT} 个不同局面")
    
    engine_pool = {}
    pool_lock = threading.Lock()
    
    def get_worker():
        thread_id = threading.get_ident()
        with pool_lock:
            if thread_id not in engine_pool:
                worker = EngineWorker(ENGINE_PATH)
                worker.start()
                engine_pool[thread_id] = worker
            return engine_pool[thread_id]
    
    def annotate(fen):
        worker = get_worker()
        return worker.annotate(fen, DEPTH)
    
    print(f"\n开始测试 (深度={DEPTH}, 线程={NUM_WORKERS})...")
    start_time = time.time()
    
    results = []
    with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
        futures = {executor.submit(annotate, fen): fen for fen in test_fens}
        
        from tqdm import tqdm
        for future in tqdm(as_completed(futures), total=len(futures), desc="分析中"):
            result = future.result()
            if result:
                results.append(result)
    
    total_time = time.time() - start_time
    
    print(f"\n结果:")
    print(f"  完成数量: {len(results)}/{TEST_COUNT}")
    print(f"  总时间: {total_time:.1f}s")
    print(f"  速度: {len(results)/total_time:.1f} it/s")
    
    times = [r['time'] for r in results]
    avg_time = sum(times) / len(times) if times else 0
    max_time = max(times) if times else 0
    min_time = min(times) if times else 0
    
    print(f"  平均每局: {avg_time*1000:.1f}ms")
    print(f"  最快: {min_time*1000:.1f}ms")
    print(f"  最慢: {max_time*1000:.1f}ms")
    
    print(f"\n推算100万局面:")
    print(f"  预计时间: {1000000/len(results)*total_time/3600:.1f} 小时")
    
    for worker in engine_pool.values():
        worker.stop()


if __name__ == "__main__":
    main()
