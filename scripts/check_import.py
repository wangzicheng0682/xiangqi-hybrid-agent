#!/usr/bin/env python3
"""Check which datasets were imported successfully"""
from neo4j import GraphDatabase

d = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'xiangqi123'))
s = d.session()

print('=== Games with moves by category ===')
result = s.run('''
    MATCH (g:Game)-[:HAS_POSITION]->()
    RETURN g.category as cat, count(g) as cnt
    ORDER BY cnt DESC
    LIMIT 20
''')
total_with_moves = 0
for r in result:
    print(f'  {r["cat"]}: {r["cnt"]:,}')
    total_with_moves += r["cnt"]
print(f'\nTotal with moves: {total_with_moves:,}')

print()
print('=== Games without moves by category ===')
result = s.run('''
    MATCH (g:Game)
    WHERE NOT (g)-[:HAS_POSITION]->()
    RETURN g.category as cat, count(g) as cnt
    ORDER BY cnt DESC
    LIMIT 20
''')
total_without_moves = 0
for r in result:
    print(f'  {r["cat"]}: {r["cnt"]:,}')
    total_without_moves += r["cnt"]
print(f'\nTotal without moves: {total_without_moves:,}')
