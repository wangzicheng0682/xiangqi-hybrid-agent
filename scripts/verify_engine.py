"""验证引擎输出与数据是否匹配"""
import subprocess

proc = subprocess.Popen(
    ['data/engine/pikafish-avx2.exe'],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.DEVNULL,
    text=True,
    bufsize=1
)

test_cases = [
    ('2baka3/9/2R6/p8/4PP3/3p5/9/4r4/4A4/3AK4 b - - 40 40', 'a6a5'),
    ('3akab2/4c4/bcn3n2/p1p1p3p/3r5/2P3R2/P3P3P/1C1CB1N2/4A4/3NKAB2 b - - 17 17', 'c6c5'),
    ('2bakab2/7r1/1cn3c1n/p1p1p1p2/8p/2PN2P2/P3P3P/1C2B3C/5N3/R1BAKA3 b - - 10 10', 'h8h1'),
]

proc.stdin.write('uci\n')
proc.stdin.flush()
while 'uciok' not in proc.stdout.readline():
    pass

print("验证数据中的best_move是否与引擎一致:\n")

for fen, expected_move in test_cases:
    proc.stdin.write(f'position fen {fen}\ngo depth 8\n')
    proc.stdin.flush()
    
    best_move = ''
    score = ''
    while True:
        line = proc.stdout.readline()
        if 'score' in line:
            score = line.strip()
        if 'bestmove' in line:
            best_move = line.split()[1]
            break
    
    match = "✓" if best_move == expected_move else "✗"
    print(f"{match} FEN: {fen[:40]}...")
    print(f"    数据: {expected_move}  引擎: {best_move}")
    print(f"    Score: {score}")
    print()

proc.kill()
