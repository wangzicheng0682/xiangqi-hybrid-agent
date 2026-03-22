#!/usr/bin/env python3
"""Check why moves are not parsed"""
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
init_dir = PROJECT_ROOT / "data/init_data"

ICCS_MOVE_RE = re.compile(r"([A-Ia-i])(\d)-([A-Ia-i])(\d)")
CHINESE_RE = re.compile(r"[将帅士仕象相马馬车車炮砲兵卒]")

pgn_files = list(init_dir.rglob('*.pgn')) + list(init_dir.rglob('*.pgns'))

print(f'Total files: {len(pgn_files):,}')
print()

# 分析几个文件
for i, f in enumerate(pgn_files[:5]):
    print(f'=== File {i+1}: {f.name} ===')
    try:
        with open(f, 'r', encoding='utf-8', errors='ignore') as file:
            content = file.read()
        
        # 检查走法格式
        iccs_matches = ICCS_MOVE_RE.findall(content)
        chinese_matches = CHINESE_RE.findall(content)
        
        print(f'  ICCS moves found: {len(iccs_matches)}')
        print(f'  Chinese chars found: {len(chinese_matches)}')
        
        # 显示部分内容
        lines = content.split('\n')[:15]
        for line in lines:
            if line.strip():
                print(f'  {line[:80]}')
        print()
    except Exception as e:
        print(f'  Error: {e}')
        print()

# 检查大文件
print('=== Checking large files ===')
for f in pgn_files:
    if f.stat().st_size > 100000:  # > 100KB
        print(f'{f.name}: {f.stat().st_size / 1024:.1f} KB')
        with open(f, 'r', encoding='utf-8', errors='ignore') as file:
            content = file.read()
        iccs = len(ICCS_MOVE_RE.findall(content))
        chinese = len(CHINESE_RE.findall(content))
        print(f'  ICCS: {iccs}, Chinese: {chinese}')
        break
