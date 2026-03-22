"""
测试真实引擎分析速度
"""
import subprocess
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

class EngineWorker:
    def __init__(self, engine_path):
        self.engine_path = engine_path
        self.proc = None
        self.lock = threading.Lock()
        self.call_count = 0
        self.total_time = 0
    
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
                self.call_count += 1
                self.total_time += elapsed
                
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
    print("测试真实引擎分析速度")
    print("=" * 60)
    
    ENGINE_PATH = "data/engine/pikafish-avx2.exe"
    NUM_WORKERS = 22
    TEST_COUNT = 1000
    DEPTH = 8
    
    print(f"\n配置:")
    print(f"  测试数量: {TEST_COUNT}")
    print(f"  搜索深度: {DEPTH}")
    print(f"  并行线程: {NUM_WORKERS}")
    
    test_fens = [
        "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1",
        "2baka3/9/2R6/p8/4PP3/3p5/9/4r4/4A4/3AK4 b - - 40 40",
        "3akab2/4c4/bcn3n2/p1p1p3p/3r5/2P3R2/P3P3P/1C1CB1N2/4A4/3NKAB2 b - - 17 17",
    ] * (TEST_COUNT // 3 + 1)
    test_fens = test_fens[:TEST_COUNT]
    
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
    
    print(f"\n开始测试...")
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
    
    avg_time = sum(r['time'] for r in results) / len(results) if results else 0
    print(f"  平均每局: {avg_time*1000:.1f}ms")
    
    for worker in engine_pool.values():
        worker.stop()


if __name__ == "__main__":
    main()
