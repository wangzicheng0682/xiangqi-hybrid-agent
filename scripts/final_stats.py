#!/usr/bin/env python3
"""Count games with moves"""
from neo4j import GraphDatabase

d = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'xiangqi123'))
s = d.session()

# 统计有走法的对局
result = s.run('''
    MATCH (g:Game)-[:HAS_POSITION]->()
    RETURN count(DISTINCT g) as games_with_moves
''').single()
print(f'Games with moves: {result["games_with_moves"]:,}')

# 总对局数
total = s.run('MATCH (g:Game) RETURN count(g)').single()[0]
print(f'Total games: {total:,}')

# 有效率
print(f'Valid rate: {result["games_with_moves"]/total*100:.1f}%')

# Position 统计
positions = s.run('MATCH (p:Position) RETURN count(p)').single()[0]
print(f'Positions: {positions:,}')

# 平均每盘走法数
moves = s.run('MATCH ()-[r:HAS_POSITION]->() RETURN count(r)').single()[0]
print(f'Total moves: {moves:,}')
print(f'Avg moves/game: {moves/result["games_with_moves"]:.1f}')
