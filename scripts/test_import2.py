#!/usr/bin/env python3
"""Test import_batch with error handling"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.import_optimized import PGNParser, BatchImporter, Game, XiangqiBoard

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

# 手动测试导入
game_records = []
player_records = []
position_records = []

for gid, game in batch:
    game_records.append({
        "gid": gid,
        "event": game.event,
        "date": game.date,
        "result": game.result,
        "red": game.red,
        "black": game.black,
        "opening": game.opening,
        "category": game.category,
    })
    
    if game.red:
        player_records.append({"name": game.red, "gid": gid, "role": "RED"})
    if game.black:
        player_records.append({"name": game.black, "gid": gid, "role": "BLACK"})
    
    board = XiangqiBoard(game.fen)
    prev_fen = board.get_fen()
    
    for i, move in enumerate(game.moves):
        new_fen = board.make_move_iccs(move)
        if not new_fen:
            print(f"  Invalid move: {move}")
            continue
        
        fen_hash = hash(new_fen) % (10 ** 9)
        prev_fen_hash = hash(prev_fen) % (10 ** 9)
        
        position_records.append({
            "gid": gid,
            "move_num": i + 1,
            "move": move,
            "fen": new_fen,
            "fen_hash": fen_hash,
            "prev_fen_hash": prev_fen_hash if i > 0 else None,
            "result": game.result,
        })
        
        prev_fen = new_fen

print(f"Game records: {len(game_records)}")
print(f"Player records: {len(player_records)}")
print(f"Position records: {len(position_records)}")

# 直接测试 Cypher
from neo4j import GraphDatabase
driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "xiangqi123"))
session = driver.session()

try:
    session.run("""
        UNWIND $games AS g
        MERGE (game:Game {id: g.gid})
        SET game.event = g.event, game.date = g.date, game.result = g.result,
            game.red = g.red, game.black = g.black, game.opening = g.opening, game.category = g.category
    """, games=game_records)
    print("Games inserted successfully")
except Exception as e:
    print(f"Error inserting games: {e}")

session.close()
driver.close()
importer.close()
