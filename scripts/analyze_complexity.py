"""
分析局面复杂度
"""
import subprocess
import time
import json
import random

ENGINE_PATH = "data/engine/pikafish-avx2.exe"
DATA_PATH = "data/training/position_data_1m.jsonl"

proc = subprocess.Popen(
    [ENGINE_PATH],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.DEVNULL,
    text=True,
    bufsize=1
)

proc.stdin.write("uci\n")
proc.stdin.flush()
while "uciok" not in proc.stdout.readline():
    pass

with open(DATA_PATH, 'r') as f:
    all_lines = f.readlines()

sample = random.sample(all_lines, 20)

print("分析20个随机局面的搜索时间:\n")

times = []
for i, line in enumerate(sample):
    fen = json.loads(line)['fen']
    
    start = time.time()
    proc.stdin.write(f"position fen {fen}\ngo depth 8\n")
    proc.stdin.flush()
    
    nodes = 0
    while True:
        line_out = proc.stdout.readline()
        if 'nodes' in line_out and 'nps' in line_out:
            try:
                nodes = int(line_out.split('nodes')[1].split()[0])
            except:
                pass
        if 'bestmove' in line_out:
            break
    
    elapsed = (time.time() - start) * 1000
    times.append(elapsed)
    print(f"{i+1:2d}. {elapsed:6.1f}ms, nodes={nodes:,}")

proc.kill()

print(f"\n统计:")
print(f"  平均: {sum(times)/len(times):.1f}ms")
print(f"  最快: {min(times):.1f}ms")
print(f"  最慢: {max(times):.1f}ms")
print(f"  中位数: {sorted(times)[len(times)//2]:.1f}ms")

speed_single = 1000 / (sum(times)/len(times))
speed_parallel = speed_single * 22
print(f"\n推算速度:")
print(f"  单线程: {speed_single:.1f} it/s")
print(f"  22线程: {speed_parallel:.1f} it/s")
print(f"  100万需要: {1000000/speed_parallel/60:.1f} 分钟")
