#!/usr/bin/env python3
"""Test import_batch directly"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.import_optimized import PGNParser, BatchImporter, Game

parser = PGNParser()
importer = BatchImporter("bolt://localhost:7687", "neo4j", "xiangqi123", "neo4j")

if not importer.connect():
    print("Failed to connect")
    sys.exit(1)

print("Testing import_batch...")

pgn_file = PROJECT_ROOT / "data/init_data/dpxq-99813games.pgns"

batch = []
game_id = 0
for game in parser.parse_file(pgn_file):
    game_id += 1
    batch.append((game_id, game))
    if len(batch) >= 5:
        break

print(f"Batch size: {len(batch)}")
for gid, g in batch:
    print(f"  ID={gid}: {g.red} vs {g.black}, moves={len(g.moves)}")

print("\nImporting batch...")
result = importer.import_batch(batch)
print(f"Result: {result}")

importer.close()
