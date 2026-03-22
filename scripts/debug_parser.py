#!/usr/bin/env python3
"""Debug parser for dpxq"""
import re
from pathlib import Path

HEADER_RE = re.compile(r'\[(\w+)\s+"([^"]*)"\]')

pgn_file = Path("data/init_data/dpxq-99813games.pgns")

with open(pgn_file, 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read(100000)

games = content.split('\n\n')
print(f'Games in sample: {len(games)}')

for i, game_text in enumerate(games[:5]):
    print(f'\n=== Game {i+1} ===')
    headers = HEADER_RE.findall(game_text)
    for k, v in headers:
        print(f'  {k}: "{v}"')
    
    # 检查 Red 字段
    red_headers = [v for k, v in headers if k == 'Red']
    black_headers = [v for k, v in headers if k == 'Black']
    print(f'\n  Red field: {red_headers}')
    print(f'  Black field: {black_headers}')
