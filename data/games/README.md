# Game Databases Directory

Place your game databases here in PGN format.

## Format

PGN (Portable Game Notation) files with Chinese chess notation.

Example:
```
[Event "National Championship"]
[Date "2020.05.15"]
[White "Player A"]
[Black "Player B"]
[Result "1-0"]

1. 炮二平五 马８进７ 2. 马二进三 车９平８ 3. 车一平二 卒７进１
...
1-0
```

## Sources

### Professional Games
- National championships
- International tournaments
- Grandmaster games

### Historical Games
- Classical annotated games
- Famous endgame studies

### Personal Collection
- Your own games
- Club tournament games

## Import to Neo4j

After adding PGN files, run:
```bash
python scripts/import_to_neo4j.py
```

This will:
- Parse game records
- Extract positions
- Build knowledge graph
- Calculate win rates
- Identify openings

## File Organization

```
games/
├── professional/
│   ├── 2020_championship.pgn
│   └── 2021_national_league.pgn
├── classical/
│   └── annotated_classics.pgn
└── personal/
    └── my_games.pgn
```

## Configuration

Update `config/settings.yaml`:
```yaml
knowledge_graph:
  uri: "bolt://localhost:7687"
  username: "neo4j"
  password: "your_password"
```
