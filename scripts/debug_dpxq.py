#!/usr/bin/env python3
"""Debug dpxq parsing"""
import re
from pathlib import Path

ICCS_MOVE_RE = re.compile(r"([A-Ia-i])(\d)-([A-Ia-i])(\d)")
HEADER_RE = re.compile(r'\[(\w+)\s+"([^"]*)"\]')
MOVE_NUM_RE = re.compile(r"(\d+)\.")

pgn_file = Path("data/init_data/dpxq-99813games.pgns")

print(f'Reading: {pgn_file}')
print(f'Size: {pgn_file.stat().st_size / 1024 / 1024:.1f} MB')

# 读取前几盘
with open(pgn_file, 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read(50000)  # 前 50KB

print()
print('=== Sample content ===')
print(content[:2000])

print()
print('=== Parsing test ===')
games = content.split('\n\n')
print(f'Potential games in sample: {len(games)}')

for i, game_text in enumerate(games[:3]):
    print(f'\n--- Game {i+1} ---')
    headers = HEADER_RE.findall(game_text)
    for k, v in headers:
        print(f'  {k}: {v}')
    
    # 提取走法
    lines = game_text.split('\n')
    move_lines = [l for l in lines if l.strip() and not l.startswith('[')]
    move_text = ' '.join(move_lines)
    
    # 查找 ICCS 走法
    iccs_moves = ICCS_MOVE_RE.findall(move_text)
    print(f'  ICCS moves found: {len(iccs_moves)}')
    if iccs_moves:
        print(f'  First 5: {iccs_moves[:5]}')
