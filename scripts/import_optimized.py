#!/usr/bin/env python3
"""
Optimized Import Script for Neo4j (Sprint 2.1)

Optimizations:
- Batch commits (100 games per transaction)
- Multi-threaded parallel import
- Progress visualization

Usage:
    python scripts/import_optimized.py --password xiangqi123
"""

import re
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Optional, Generator, Tuple
from dataclasses import dataclass, field
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False


@dataclass
class Game:
    event: str = ""
    site: str = ""
    date: str = ""
    round_: str = ""
    red_team: str = ""
    red: str = ""
    black_team: str = ""
    black: str = ""
    result: str = ""
    opening: str = ""
    fen: str = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"
    format_: str = "ICCS"
    category: str = ""
    moves: List[str] = field(default_factory=list)


class PGNParser:
    ICCS_MOVE_RE = re.compile(r"([A-Ia-i])(\d)-([A-Ia-i])(\d)")
    HEADER_RE = re.compile(r'\[(\w+)\s+"([^"]*)"\]')
    MOVE_NUM_RE = re.compile(r"(\d+)\.")
    CHINESE_RE = re.compile(r"[将帅士仕象相马馬车車炮砲兵卒]")
    
    def parse_file(self, pgn_path: Path, category: str = "") -> Generator[Game, None, None]:
        encodings = ["utf-8", "gbk", "gb2312", "gb18030", "big5"]
        content = None
        
        for enc in encodings:
            try:
                with open(pgn_path, "r", encoding=enc) as f:
                    content = f.read()
                break
            except (UnicodeDecodeError, UnicodeError):
                continue
        
        if content is None:
            with open(pgn_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        
        for game in self._parse_games(content):
            game.category = category
            yield game
    
    def _parse_games(self, content: str) -> Generator[Game, None, None]:
        game = None
        in_moves = False
        move_text = []
        
        for line in content.split("\n"):
            line = line.strip()
            if not line:
                if in_moves and game is not None:
                    self._parse_moves(game, " ".join(move_text))
                    yield game
                    game = None
                    in_moves = False
                    move_text = []
                continue
            
            header_match = self.HEADER_RE.match(line)
            if header_match:
                if in_moves and game is not None:
                    self._parse_moves(game, " ".join(move_text))
                    yield game
                    game = None
                    in_moves = False
                    move_text = []
                
                if game is None:
                    game = Game()
                
                key, value = header_match.groups()
                self._set_header(game, key, value)
            elif game is not None and (line.startswith("1.") or in_moves or self.CHINESE_RE.search(line)):
                in_moves = True
                move_text.append(line)
        
        if game is not None and (game.moves or move_text):
            self._parse_moves(game, " ".join(move_text))
            yield game
    
    def _set_header(self, game: Game, key: str, value: str):
        mapping = {
            "Event": "event", "Site": "site", "Date": "date", "Round": "round_",
            "RedTeam": "red_team", "Red": "red", "BlackTeam": "black_team",
            "Black": "black", "Result": "result", "Opening": "opening",
            "FEN": "fen", "Format": "format_",
            "WhiteTeam": "red_team", "White": "red",
        }
        if key in mapping:
            setattr(game, mapping[key], value)
    
    def _parse_moves(self, game: Game, text: str):
        tokens = text.split()
        for tok in tokens:
            if tok in ("1-0", "0-1", "1/2-1/2", "*"):
                if not game.result:
                    game.result = tok
                break
            
            if self.MOVE_NUM_RE.match(tok):
                continue
            
            clean = tok.strip("?!+·")
            
            if self.ICCS_MOVE_RE.match(clean):
                game.moves.append(clean)
            elif self.CHINESE_RE.search(clean):
                game.moves.append(clean)
                game.format_ = "CHINESE"


class XiangqiBoard:
    INITIAL_FEN = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"
    
    def __init__(self, fen: str = None):
        self.board = self._fen_to_board(fen or self.INITIAL_FEN)
        self.red_to_move = "w" in (fen or self.INITIAL_FEN)
        self.move_count = 0
    
    def _fen_to_board(self, fen: str) -> List[List[str]]:
        board = [[""] * 9 for _ in range(10)]
        rows = fen.split()[0].split("/")
        for r, row in enumerate(rows):
            c = 0
            for ch in row:
                if ch.isdigit():
                    c += int(ch)
                else:
                    board[r][c] = ch
                    c += 1
        return board
    
    def _board_to_fen(self) -> str:
        rows = []
        for row in self.board:
            fen_row = ""
            empty = 0
            for cell in row:
                if cell:
                    if empty:
                        fen_row += str(empty)
                        empty = 0
                    fen_row += cell
                else:
                    empty += 1
            if empty:
                fen_row += str(empty)
            rows.append(fen_row)
        turn = "w" if self.red_to_move else "b"
        return f"{'/'.join(rows)} {turn} - - {self.move_count // 2 + 1} {self.move_count // 2 + 1}"
    
    def make_move_iccs(self, iccs: str) -> Optional[str]:
        match = PGNParser.ICCS_MOVE_RE.match(iccs)
        if not match:
            return None
        
        fc, fr, tc, tr = match.groups()
        from_col, from_row = ord(fc.upper()) - ord('A'), int(fr)
        to_col, to_row = ord(tc.upper()) - ord('A'), int(tr)
        
        if not (0 <= from_col < 9 and 0 <= from_row < 10 and 0 <= to_col < 9 and 0 <= to_row < 10):
            return None
        
        piece = self.board[9 - from_row][from_col]
        if not piece:
            return None
        
        self.board[9 - from_row][from_col] = ""
        self.board[9 - to_row][to_col] = piece
        self.red_to_move = not self.red_to_move
        self.move_count += 1
        
        return self._board_to_fen()
    
    def get_fen(self) -> str:
        return self._board_to_fen()


def process_game_to_records(game: Game, game_id: int) -> List[Dict]:
    records = []
    board = XiangqiBoard(game.fen)
    
    records.append({
        "type": "game",
        "game_id": game_id,
        "event": game.event,
        "date": game.date,
        "result": game.result,
        "red": game.red,
        "black": game.black,
        "opening": game.opening,
        "category": game.category,
    })
    
    if game.red:
        records.append({"type": "player", "name": game.red, "game_id": game_id, "role": "RED"})
    if game.black:
        records.append({"type": "player", "name": game.black, "game_id": game_id, "role": "BLACK"})
    
    prev_fen = board.get_fen()
    for i, move in enumerate(game.moves):
        if game.format_ == "ICCS":
            new_fen = board.make_move_iccs(move)
        else:
            new_fen = None
        
        if not new_fen:
            continue
        
        fen_hash = hash(new_fen) % (10 ** 9)
        prev_fen_hash = hash(prev_fen) % (10 ** 9)
        
        records.append({
            "type": "position",
            "game_id": game_id,
            "move_num": i + 1,
            "move": move,
            "fen": new_fen,
            "fen_hash": fen_hash,
            "prev_fen_hash": prev_fen_hash if i > 0 else None,
        })
        
        prev_fen = new_fen
    
    return records


class BatchImporter:
    def __init__(self, uri: str, username: str, password: str, database: str, batch_size: int = 100):
        self.uri = uri
        self.username = username
        self.password = password
        self.database = database
        self.batch_size = batch_size
        self.driver = None
        self.lock = threading.Lock()
    
    def connect(self) -> bool:
        try:
            from neo4j import GraphDatabase
            self.driver = GraphDatabase.driver(self.uri, auth=(self.username, self.password))
            self.driver.verify_connectivity()
            return True
        except Exception as e:
            print(f"ERROR: Cannot connect to Neo4j: {e}")
            return False
    
    def close(self):
        if self.driver:
            self.driver.close()
    
    def create_indexes(self):
        with self.driver.session(database=self.database) as session:
            session.run("CREATE INDEX IF NOT EXISTS FOR (p:Position) ON (p.fen_hash)")
            session.run("CREATE INDEX IF NOT EXISTS FOR (g:Game) ON (g.id)")
            session.run("CREATE INDEX IF NOT EXISTS FOR (pl:Player) ON (pl.name)")
    
    def import_batch(self, batch: List[Tuple[int, Game]]) -> int:
        if not self.driver:
            return 0
        
        game_records = []
        player_records = []
        position_records = []
        
        for game_id, game in batch:
            game_records.append({
                "gid": game_id,
                "event": game.event,
                "date": game.date,
                "result": game.result,
                "red": game.red,
                "black": game.black,
                "opening": game.opening,
                "category": game.category,
            })
            
            if game.red:
                player_records.append({"name": game.red, "gid": game_id, "role": "RED"})
            if game.black:
                player_records.append({"name": game.black, "gid": game_id, "role": "BLACK"})
            
            board = XiangqiBoard(game.fen)
            prev_fen = board.get_fen()
            
            for i, move in enumerate(game.moves):
                if game.format_ == "ICCS":
                    new_fen = board.make_move_iccs(move)
                else:
                    new_fen = None
                
                if not new_fen:
                    continue
                
                fen_hash = hash(new_fen) % (10 ** 9)
                prev_fen_hash = hash(prev_fen) % (10 ** 9)
                
                position_records.append({
                    "gid": game_id,
                    "move_num": i + 1,
                    "move": move,
                    "fen": new_fen,
                    "fen_hash": fen_hash,
                    "prev_fen_hash": prev_fen_hash if i > 0 else None,
                    "result": game.result,
                })
                
                prev_fen = new_fen
        
        with self.lock:
            with self.driver.session(database=self.database) as session:
                tx = session.begin_transaction()
                try:
                    if game_records:
                        tx.run("""
                            UNWIND $games AS g
                            MERGE (game:Game {id: g.gid})
                            SET game.event = g.event, game.date = g.date, game.result = g.result,
                                game.red = g.red, game.black = g.black, game.opening = g.opening, game.category = g.category
                        """, games=game_records)
                    
                    if player_records:
                        tx.run("""
                            UNWIND $players AS p
                            MERGE (pl:Player {name: p.name})
                        """, players=player_records)
                        
                        tx.run("""
                            UNWIND $players AS p
                            MATCH (g:Game {id: p.gid}), (pl:Player {name: p.name})
                            FOREACH (_ IN CASE WHEN p.role = 'RED' THEN [1] ELSE [] END |
                                MERGE (g)-[:RED_PLAYER]->(pl))
                            FOREACH (_ IN CASE WHEN p.role = 'BLACK' THEN [1] ELSE [] END |
                                MERGE (g)-[:BLACK_PLAYER]->(pl))
                        """, players=player_records)
                    
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
                        
                        tx.run("""
                            UNWIND $positions AS p
                            WITH p WHERE p.prev_fen_hash IS NOT NULL
                            MATCH (p1:Position {fen_hash: p.prev_fen_hash}), (p2:Position {fen_hash: p.fen_hash})
                            MERGE (p1)-[:NEXT {move: p.move}]->(p2)
                        """, positions=position_records)
                        
                        for result_type in [("1-0", "red_wins"), ("0-1", "black_wins"), ("1/2-1/2", "draws")]:
                            tx.run(f"""
                                UNWIND $positions AS p
                                WITH p WHERE p.result = $res
                                MATCH (pos:Position {{fen_hash: p.fen_hash}})
                                SET pos.total_games = pos.total_games + 1, pos.{result_type[1]} = pos.{result_type[1]} + 1
                            """, positions=position_records, res=result_type[0])
                    
                    tx.commit()
                    return len(batch)
                except Exception as e:
                    print(f"ERROR in import_batch: {e}")
                    import traceback
                    traceback.print_exc()
                    tx.rollback()
                    return 0
    
    def calculate_win_rates(self):
        with self.driver.session(database=self.database) as session:
            session.run("""
                MATCH (p:Position)
                WHERE p.total_games > 0
                SET p.red_win_rate = toFloat(p.red_wins) / p.total_games,
                    p.black_win_rate = toFloat(p.black_wins) / p.total_games,
                    p.draw_rate = toFloat(p.draws) / p.total_games
            """)


def find_pgn_files(base_dir: Path) -> List[Tuple[Path, str]]:
    files = []
    for f in base_dir.rglob("*"):
        if f.suffix.lower() in (".pgn", ".pgns"):
            rel_path = f.relative_to(base_dir)
            category = str(rel_path.parent) if rel_path.parent != Path(".") else ""
            files.append((f, category))
    return files


def parse_args():
    parser = argparse.ArgumentParser(description="Optimized import to Neo4j")
    parser.add_argument("--init-data", type=str, default="data/init_data")
    parser.add_argument("--uri", type=str, default="bolt://localhost:7687")
    parser.add_argument("--username", type=str, default="neo4j")
    parser.add_argument("--password", type=str, default="xiangqi123")
    parser.add_argument("--database", type=str, default="neo4j")
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--limit", type=int, default=0)
    return parser.parse_args()


def main():
    args = parse_args()
    
    print("=" * 60)
    print("Optimized PGN Import to Neo4j")
    print(f"Batch size: {args.batch_size}, Workers: {args.workers}")
    print("=" * 60)
    
    init_dir = PROJECT_ROOT / args.init_data
    pgn_files = find_pgn_files(init_dir)
    
    if not pgn_files:
        print(f"ERROR: No PGN files in {init_dir}")
        sys.exit(1)
    
    total_size = sum(f.stat().st_size for f, _ in pgn_files) / (1024 * 1024)
    print(f"\nFound {len(pgn_files):,} files ({total_size:.1f} MB)")
    
    importer = BatchImporter(args.uri, args.username, args.password, args.database, args.batch_size)
    if not importer.connect():
        sys.exit(1)
    
    print("\nCreating indexes...")
    importer.create_indexes()
    
    print("\nParsing and importing games...")
    start_time = time.time()
    
    parser = PGNParser()
    batch = []
    total_games = 0
    game_id = 0
    start_id = 0
    
    if HAS_TQDM:
        pbar = tqdm(desc="Importing", unit="games")
    else:
        print("Importing games...")
    
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = []
        
        for pgn_file, category in pgn_files:
            try:
                for game in parser.parse_file(pgn_file, category):
                    game_id += 1
                    batch.append((game_id, game))
                    
                    if len(batch) >= args.batch_size:
                        future = executor.submit(importer.import_batch, batch.copy())
                        futures.append(future)
                        total_games += len(batch)
                        batch = []
                        
                        if HAS_TQDM:
                            pbar.update(args.batch_size)
                        elif total_games % 1000 == 0:
                            elapsed = time.time() - start_time
                            rate = total_games / elapsed if elapsed > 0 else 0
                            print(f"\r  {total_games:,} games ({rate:.0f}/s)", end="", flush=True)
                    
                    if args.limit and game_id >= args.limit:
                        break
            except Exception as e:
                pass
            
            if args.limit and game_id >= args.limit:
                break
        
        if batch:
            future = executor.submit(importer.import_batch, batch.copy())
            futures.append(future)
            total_games += len(batch)
            if HAS_TQDM:
                pbar.update(len(batch))
        
        for future in as_completed(futures):
            future.result()
    
    if HAS_TQDM:
        pbar.close()
    
    print("\n\nCalculating win rates...")
    importer.calculate_win_rates()
    importer.close()
    
    elapsed = time.time() - start_time
    
    print("\n" + "=" * 60)
    print("Import Complete!")
    print("=" * 60)
    print(f"  Total games: {total_games:,}")
    print(f"  Elapsed: {elapsed:.1f}s")
    if elapsed > 0:
        print(f"  Rate: {total_games/elapsed:.0f} games/s")


if __name__ == "__main__":
    main()
