import sys
sys.path.insert(0, '.')
from core.kg.neo4j_kg import Neo4jKG

kg = Neo4jKG()
if kg.connect():
    stats = kg.get_statistics()
    print(f"对局数: {stats['games']:,}")
    print(f"局面数: {stats['positions']:,}")
    print(f"棋手数: {stats['players']:,}")
    print(f"走法数: {stats['moves']:,}")
    kg.close()
else:
    print('连接失败')
