#!/usr/bin/env python3
"""Debug import_batch method"""
import sys
import traceback
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.import_optimized import PGNParser, BatchImporter, Game, XiangqiBoard
import threading

parser = PGNParser()
importer = BatchImporter("bolt://localhost:7687", "neo4j", "xiangqi123", "neo4j")
importer.lock = threading.Lock()

if not importer.connect():
    print("Failed to connect")
    sys.exit(1)

pgn_file = PROJECT_ROOT / "data/init_data/dpxq-99813games.pgns"

batch = []
game_id = 0
for game in parser.parse_file(pgn_file):
    game_id += 1
    batch.append((game_id, game))
    if len(batch) >= 5:
        break

print(f"Batch size: {len(batch)}")

# 调用 import_batch 并捕获错误
try:
    result = importer.import_batch(batch)
    print(f"Result: {result}")
except Exception as e:
    print(f"Error: {e}")
    traceback.print_exc()

importer.close()
