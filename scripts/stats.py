#!/usr/bin/env python3
"""Quick stats check"""
from neo4j import GraphDatabase

d = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'xiangqi123'))
s = d.session()

print('=== Data Statistics ===')
print(f'Games: {s.run("MATCH (g:Game) RETURN count(g)").single()[0]:,}')
print(f'Positions: {s.run("MATCH (p:Position) RETURN count(p)").single()[0]:,}')
print(f'Players: {s.run("MATCH (p:Player) RETURN count(p)").single()[0]:,}')
print(f'Moves: {s.run("MATCH ()-[r:HAS_POSITION]->() RETURN count(r)").single()[0]:,}')
print(f'Next: {s.run("MATCH ()-[r:NEXT]->() RETURN count(r)").single()[0]:,}')
print()
print('=== By Category ===')
for r in s.run('MATCH (g:Game) WHERE g.category IS NOT NULL RETURN g.category as cat, count(g) as cnt ORDER BY cnt DESC LIMIT 15'):
    print(f'  {r["cat"]}: {r["cnt"]:,}')
