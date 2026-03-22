#!/usr/bin/env python3
"""Check for duplicate game IDs"""
from neo4j import GraphDatabase

d = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'xiangqi123'))
s = d.session()

print('=== Game ID duplicates ===')
result = s.run('''
    MATCH (g:Game)
    WITH g.id AS id, count(g) AS cnt
    WHERE cnt > 1
    RETURN count(*) AS dup_ids, sum(cnt) AS total_in_dups
    LIMIT 1
''').single()
print(f'Duplicate IDs: {result["dup_ids"]}')
print(f'Total in duplicates: {result["total_in_dups"]}')

print()
print('=== Game ID distribution ===')
result = s.run('''
    MATCH (g:Game)
    RETURN min(g.id) as min_id, max(g.id) as max_id, count(g) as total
''').single()
print(f'Min ID: {result["min_id"]}')
print(f'Max ID: {result["max_id"]}')
print(f'Total games: {result["total"]}')

print()
print('=== Check if IDs 10001-100000 exist ===')
result = s.run('MATCH (g:Game) WHERE g.id >= 10001 AND g.id <= 100100 RETURN count(g)').single()[0]
print(f'Games with ID 10001-100100: {result}')
