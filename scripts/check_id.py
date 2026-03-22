#!/usr/bin/env python3
"""Check games by ID range"""
from neo4j import GraphDatabase

d = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'xiangqi123'))
s = d.session()

print('=== Games by ID range ===')
for start, end in [(1, 10000), (10001, 50000), (50001, 100000), (100001, 200000)]:
    total = s.run(f'MATCH (g:Game) WHERE g.id >= {start} AND g.id <= {end} RETURN count(g)').single()[0]
    with_moves = s.run(f'MATCH (g:Game)-[:HAS_POSITION]->() WHERE g.id >= {start} AND g.id <= {end} RETURN count(g)').single()[0]
    print(f'ID {start}-{end}: {total:,} games, {with_moves:,} with moves')

print()
print('=== Sample game with ID > 10000 ===')
result = s.run('''
    MATCH (g:Game)
    WHERE g.id > 10000
    RETURN g.id, g.red, g.black, g.event
    LIMIT 5
''')
for r in result:
    print(f'  ID={r["g.id"]}: {r["g.red"]} vs {r["g.black"]} ({r["g.event"]})')
