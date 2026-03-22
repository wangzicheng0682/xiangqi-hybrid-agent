#!/usr/bin/env python3
"""Analyze why games count is lower than expected"""
from neo4j import GraphDatabase
from pathlib import Path

d = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'xiangqi123'))
s = d.session()

print('=== Game ID Distribution ===')
result = s.run('MATCH (g:Game) RETURN min(g.id) as min_id, max(g.id) as max_id, count(g) as cnt').single()
print(f'Min ID: {result["min_id"]}')
print(f'Max ID: {result["max_id"]}')
print(f'Total Games in DB: {result["cnt"]:,}')

print()
print('=== PGN Files ===')
init_dir = Path('data/init_data')
pgn_files = list(init_dir.rglob('*.pgn')) + list(init_dir.rglob('*.pgns'))
print(f'Total PGN files: {len(pgn_files):,}')

print()
print('=== Check for duplicate games ===')
dup_check = s.run('''
    MATCH (g:Game)
    WITH g.red + "-" + g.black + "-" + g.date AS key, count(g) AS cnt
    WHERE cnt > 1
    RETURN count(*) AS duplicate_groups, sum(cnt) AS total_in_dups
''').single()
print(f'Duplicate groups: {dup_check["duplicate_groups"]}')
print(f'Total in duplicates: {dup_check["total_in_dups"]}')

print()
print('=== Games without moves ===')
no_moves = s.run('MATCH (g:Game) WHERE NOT (g)-[:HAS_POSITION]->() RETURN count(g)').single()[0]
print(f'Games without moves: {no_moves:,}')

print()
print('=== Sample file analysis ===')
sample_file = pgn_files[0] if pgn_files else None
if sample_file:
    print(f'Sample file: {sample_file}')
    with open(sample_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    games_in_file = content.count('[Event')
    print(f'Games in this file: {games_in_file}')
