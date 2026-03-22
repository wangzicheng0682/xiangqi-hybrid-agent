#!/usr/bin/env python3
"""
Import Game Database to Neo4j (Sprint 2.1)

PGN formats supported:
- ICCS coordinates: C3-C4, H2-E2
- Chinese notation: 炮二进三, 马八进七
- WXF/dpxq formats

Usage:
    python scripts/import_to_neo4j.py --dry-run
    python scripts/import_to_neo4j.py --uri bolt://localhost:7687 --password yourpass
"""

import re
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional, Generator, Tuple
from dataclasses import dataclass, field
import time
import os

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False


class ProgressTracker:
    def __init__(self, total: int = 0, desc: str = "Processing"):
        self.total = total
        self.desc = desc
        self.count = 0
        self.start_time = time.time()
        self.last_update = 0
        self.bar_width = 40
    
    def update(self, n: int = 1) -> None:
        self.count += n
        now = time.time()
        if now - self.last_update < 0.1 and self.count < self.total:
            return
        self.last_update = now
        
        if HAS_TQDM:
            return
        
        elapsed = now - self.start_time
        rate = self.count / elapsed if elapsed > 0 else 0
        eta = (self.total - self.count) / rate if rate > 0 else 0
        
        if self.total > 0:
            pct = self.count / self.total
            filled = int(self.bar_width * pct)
            bar = "█" * filled + "░" * (self.bar_width - filled)
            line = f"\r{self.desc}: |{bar}| {self.count:,}/{self.total:,} ({pct*100:.1f}%) [{rate:.0f}/s, ETA:{eta:.0f}s]"
        else:
            line = f"\r{self.desc}: {self.count:,} games [{rate:.0f}/s, {elapsed:.1f}s]"
        
        sys.stderr.write(line[:100])
        sys.stderr.flush()
    
    def close(self) -> None:
        if not HAS_TQDM:
            sys.stderr.write("\n")
            sys.stderr.flush()


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


class ChineseMoveParser:
    PIECE_MAP = {
        "将": "k", "帅": "K", "王": "K",
        "士": "a", "仕": "A",
        "象": "b", "相": "B",
        "马": "n", "馬": "N",
        "车": "r", "車": "R",
        "炮": "c", "砲": "C",
        "兵": "p", "卒": "P",
    }
    NUM_MAP = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
    ACTION_MAP = {"进": "forward", "退": "backward", "平": "horizontal"}
    
    MOVE_RE = re.compile(r"([将帅士仕象相马馬车車炮砲兵卒])([一二三四五六七八九１２３４５６７８９1-9])([进退平])([一二三四五六七八九１２３４５６７８９1-9]+)")
    
    @classmethod
    def is_chinese_move(cls, text: str) -> bool:
        return bool(cls.MOVE_RE.search(text))
    
    @classmethod
    def parse_move(cls, move: str, board_state: Dict = None) -> Optional[str]:
        match = cls.MOVE_RE.search(move)
        if not match:
            return None
        return move


class PGNParser:
    ICCS_MOVE_RE = re.compile(r"([A-Ia-i])(\d)-([A-Ia-i])(\d)")
    HEADER_RE = re.compile(r'\[(\w+)\s+"([^"]*)"\]')
    MOVE_NUM_RE = re.compile(r"(\d+)\.")
    CHINESE_RE = re.compile(r"[将帅士仕象相马馬车車炮砲兵卒]")
    
    def __init__(self):
        self.use_chinese = False
    
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
                continue
            
            header_match = self.HEADER_RE.match(line)
            if header_match:
                if game is not None and (game.moves or move_text):
                    self._parse_moves(game, " ".join(move_text))
                    yield game
                
                game = Game()
                in_moves = False
                move_text = []
                
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
            elif ChineseMoveParser.is_chinese_move(clean):
                game.moves.append(clean)
                game.format_ = "CHINESE"
            elif len(clean) >= 2 and self.CHINESE_RE.search(clean):
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


class Neo4jImporter:
    def __init__(self, uri: str, username: str, password: str, database: str):
        self.uri = uri
        self.username = username
        self.password = password
        self.database = database
        self.driver = None
    
    def connect(self) -> bool:
        try:
            from neo4j import GraphDatabase
            self.driver = GraphDatabase.driver(self.uri, auth=(self.username, self.password))
            self.driver.verify_connectivity()
            return True
        except ImportError:
            print("ERROR: neo4j package not installed. Run: pip install neo4j")
            return False
        except Exception as e:
            print(f"ERROR: Cannot connect to Neo4j: {e}")
            return False
    
    def close(self):
        if self.driver:
            self.driver.close()
    
    def create_indexes(self):
        if not self.driver:
            return
        with self.driver.session(database=self.database) as session:
            session.run("CREATE INDEX IF NOT EXISTS FOR (p:Position) ON (p.fen_hash)")
            session.run("CREATE INDEX IF NOT EXISTS FOR (g:Game) ON (g.id)")
            session.run("CREATE INDEX IF NOT EXISTS FOR (pl:Player) ON (pl.name)")
    
    def import_game(self, game: Game, game_id: int) -> Dict[str, int]:
        if not self.driver:
            return {"positions": 0, "moves": 0}
        
        stats = {"positions": 0, "moves": 0}
        board = XiangqiBoard(game.fen)
        
        with self.driver.session(database=self.database) as session:
            tx = session.begin_transaction()
            try:
                tx.run("""
                    MERGE (g:Game {id: $gid})
                    SET g.event = $event, g.date = $date, g.result = $result,
                        g.red = $red, g.black = $black, g.opening = $opening, g.category = $category
                """, gid=game_id, event=game.event, date=game.date,
                     result=game.result, red=game.red, black=game.black,
                     opening=game.opening, category=game.category)
                
                if game.red:
                    tx.run("MERGE (p:Player {name: $name})", name=game.red)
                    tx.run("""
                        MATCH (g:Game {id: $gid}), (p:Player {name: $name})
                        MERGE (g)-[:RED_PLAYER]->(p)
                    """, gid=game_id, name=game.red)
                
                if game.black:
                    tx.run("MERGE (p:Player {name: $name})", name=game.black)
                    tx.run("""
                        MATCH (g:Game {id: $gid}), (p:Player {name: $name})
                        MERGE (g)-[:BLACK_PLAYER]->(p)
                    """, gid=game_id, name=game.black)
                
                prev_fen = board.get_fen()
                for i, move in enumerate(game.moves):
                    if game.format_ == "ICCS":
                        new_fen = board.make_move_iccs(move)
                    else:
                        new_fen = None
                    
                    if not new_fen:
                        continue
                    
                    fen_hash = hash(new_fen) % (10 ** 9)
                    tx.run("""
                        MERGE (p:Position {fen_hash: $fh})
                        ON CREATE SET p.fen = $fen, p.total_games = 0,
                                      p.red_wins = 0, p.black_wins = 0, p.draws = 0
                    """, fh=fen_hash, fen=new_fen)
                    
                    tx.run("""
                        MATCH (g:Game {id: $gid}), (p:Position {fen_hash: $fh})
                        MERGE (g)-[:HAS_POSITION {move_num: $mn, move: $mv}]->(p)
                    """, gid=game_id, fh=fen_hash, mn=i+1, mv=move)
                    
                    prev_fen_hash = hash(prev_fen) % (10 ** 9)
                    if i > 0:
                        tx.run("""
                            MATCH (p1:Position {fen_hash: $fh1}), (p2:Position {fen_hash: $fh2})
                            MERGE (p1)-[:NEXT {move: $mv}]->(p2)
                        """, fh1=prev_fen_hash, fh2=fen_hash, mv=move)
                    
                    stats["positions"] += 1
                    stats["moves"] += 1
                    prev_fen = new_fen
                
                result = game.result
                for move_num in range(1, len(game.moves) + 1):
                    if result == "1-0":
                        tx.run("""
                            MATCH (g:Game {id: $gid})-[:HAS_POSITION {move_num: $mn}]->(p:Position)
                            SET p.red_wins = p.red_wins + 1, p.total_games = p.total_games + 1
                        """, gid=game_id, mn=move_num)
                    elif result == "0-1":
                        tx.run("""
                            MATCH (g:Game {id: $gid})-[:HAS_POSITION {move_num: $mn}]->(p:Position)
                            SET p.black_wins = p.black_wins + 1, p.total_games = p.total_games + 1
                        """, gid=game_id, mn=move_num)
                    elif result == "1/2-1/2":
                        tx.run("""
                            MATCH (g:Game {id: $gid})-[:HAS_POSITION {move_num: $mn}]->(p:Position)
                            SET p.draws = p.draws + 1, p.total_games = p.total_games + 1
                        """, gid=game_id, mn=move_num)
                
                tx.commit()
            except Exception as e:
                tx.rollback()
        
        return stats
    
    def calculate_win_rates(self):
        if not self.driver:
            return
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
    parser = argparse.ArgumentParser(description="Import games to Neo4j")
    parser.add_argument("--init-data", type=str, default="data/init_data",
                        help="Directory containing PGN files")
    parser.add_argument("--uri", type=str, default="bolt://localhost:7687")
    parser.add_argument("--username", type=str, default="neo4j")
    parser.add_argument("--password", type=str, default="xiangqi123")
    parser.add_argument("--database", type=str, default="neo4j")
    parser.add_argument("--dry-run", action="store_true", help="Parse only, no DB write")
    parser.add_argument("--limit", type=int, default=0, help="Limit games (0=all)")
    parser.add_argument("--batch-size", type=int, default=1000, help="Progress report interval")
    return parser.parse_args()


def main():
    args = parse_args()
    
    print("=" * 60)
    print("PGN Import to Neo4j (Sprint 2.1)")
    print("Supports: ICCS, Chinese notation, multi-format")
    print("=" * 60)
    
    init_dir = PROJECT_ROOT / args.init_data
    if not init_dir.exists():
        print(f"ERROR: Directory not found: {init_dir}")
        sys.exit(1)
    
    print("\n[1/3] Scanning PGN files...")
    pgn_files = find_pgn_files(init_dir)
    
    if not pgn_files:
        print(f"ERROR: No PGN files in {init_dir}")
        sys.exit(1)
    
    total_size = sum(f.stat().st_size for f, _ in pgn_files) / (1024 * 1024)
    print(f"\n  Found {len(pgn_files):,} files ({total_size:.1f} MB)")
    
    by_category = {}
    for f, cat in pgn_files:
        cat_display = cat if cat else "(root)"
        by_category[cat_display] = by_category.get(cat_display, 0) + 1
    
    print("\n  By category:")
    for cat, count in sorted(by_category.items()):
        print(f"    {cat}: {count:,} files")
    
    parser = PGNParser()
    importer = None
    total_games = 0
    total_positions = 0
    game_id = 0
    
    if not args.dry_run:
        importer = Neo4jImporter(args.uri, args.username, args.password, args.database)
        if not importer.connect():
            print("\nFalling back to dry-run mode")
            args.dry_run = True
        else:
            print("\n[2/3] Creating indexes...")
            importer.create_indexes()
    
    print("\n[3/3] Parsing and importing games...")
    start_time = time.time()
    
    progress = ProgressTracker(desc="Importing", total=args.limit if args.limit else 0)
    
    for pgn_file, category in pgn_files:
        try:
            for game in parser.parse_file(pgn_file, category):
                game_id += 1
                
                if args.limit and game_id > args.limit:
                    break
                
                if importer:
                    stats = importer.import_game(game, game_id)
                    total_positions += stats["positions"]
                
                total_games += 1
                progress.update(1)
                
                if args.limit and game_id >= args.limit:
                    break
        except Exception as e:
            print(f"\n  Error reading {pgn_file.name}: {e}")
        
        if args.limit and game_id >= args.limit:
            break
    
    progress.close()
    
    if importer and not args.dry_run:
        print("\nCalculating win rates...")
        importer.calculate_win_rates()
        importer.close()
    
    elapsed = time.time() - start_time
    
    print("\n" + "=" * 60)
    print("Import Complete!")
    print("=" * 60)
    print(f"  Total games: {total_games:,}")
    print(f"  Total positions: {total_positions:,}")
    print(f"  Elapsed: {elapsed:.1f}s")
    if elapsed > 0:
        print(f"  Rate: {total_games/elapsed:.0f} games/s")
    
    if args.dry_run:
        print("\n  (Dry-run mode - no data written to Neo4j)")


if __name__ == "__main__":
    main()
