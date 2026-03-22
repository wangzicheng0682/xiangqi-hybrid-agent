#!/usr/bin/env python3
"""Test parser on dpxq file"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.import_optimized import PGNParser

parser = PGNParser()
pgn_file = PROJECT_ROOT / "data/init_data/dpxq-99813games.pgns"

count = 0
for game in parser.parse_file(pgn_file):
    count += 1
    if count <= 3:
        print(f"Game {count}:")
        print(f"  Red: {game.red}")
        print(f"  Black: {game.black}")
        print(f"  Event: {game.event}")
        print(f"  Moves: {len(game.moves)}")
        if game.moves:
            print(f"  First 5 moves: {game.moves[:5]}")
        print()
    elif count % 10000 == 0:
        print(f"Parsed {count} games...")
    
    if count >= 10:
        break

print(f"\nTotal parsed: {count}")
