#!/usr/bin/env python3
"""Test import_batch with detailed error"""
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

pgn_file = PROJECT_ROOT / "data/init_data/dpxq-99813games.pgns"

batch = []
game_id = 0
for game in parser.parse_file(pgn_file):
    game_id += 1
    batch.append((game_id, game))
    if len(batch) >= 5:
        break

print(f"Batch size: {len(batch)}")

# 手动测试
game_records = []
player_records = []
position_records = []

for gid, game in batch:
    print(f"\nGame {gid}: {game.red} vs {game.black}")
    print(f"  format: {game.format_}")
    print(f"  moves: {len(game.moves)}")
    
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
    
    board = XiangqiBoard(game.fen)
    prev_fen = board.get_fen()
    
    for i, move in enumerate(game.moves):
        if game.format_ == "ICCS":
            new_fen = board.make_move_iccs(move)
        else:
            new_fen = None
        
        if not new_fen:
            print(f"  Invalid move at {i+1}: {move}")
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

print(f"\nTotal position_records: {len(position_records)}")

# 直接测试事务
from neo4j import GraphDatabase
driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "xiangqi123"))
session = driver.session()
tx = session.begin_transaction()

try:
    tx.run("""
        UNWIND $games AS g
        MERGE (game:Game {id: g.gid})
        SET game.event = g.event, game.date = g.date, game.result = g.result,
            game.red = g.red, game.black = g.black, game.opening = g.opening, game.category = g.category
    """, games=game_records)
    
    if position_records:
        tx.run("""
            UNWIND $positions AS p
            MERGE (pos:Position {fen_hash: p.fen_hash})
            ON CREATE SET pos.fen = p.fen, pos.total_games = 0,
                          pos.red_wins = 0, pos.black_wins = 0, pos.draws = 0
        """, positions=position_records)
        
        tx.run("""
            UNWIND $positions AS p
            MATCH (g:Game {id: p.gid}), (pos:Position {fen_hash: p.fen_hash})
            MERGE (g)-[:HAS_POSITION {move_num: p.move_num, move: p.move}]->(pos)
        """, positions=position_records)
    
    tx.commit()
    print("\nTransaction committed successfully")
except Exception as e:
    tx.rollback()
    print(f"\nTransaction failed: {e}")

session.close()
driver.close()
importer.close()
