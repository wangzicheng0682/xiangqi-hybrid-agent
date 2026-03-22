import sys
sys.path.insert(0, '.')

print('=== 知识图谱查询测试 ===')
from core.kg.neo4j_kg import Neo4jKG

kg = Neo4jKG()
if kg.connect():
    print('Neo4j KG: 已连接')
    
    # 测试初始局面查询
    initial_fen = 'rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1'
    print(f'\n查询初始局面: {initial_fen[:30]}...')
    
    result = kg.query_position(initial_fen)
    if result:
        print(f'  总对局: {result.total_games}')
        print(f'  红方胜率: {result.red_win_rate*100:.1f}%')
        print(f'  黑方胜率: {result.black_win_rate*100:.1f}%')
    else:
        print('  无数据')
    
    # 测试推荐着法
    print('\n推荐着法:')
    next_moves = kg.get_next_moves(initial_fen)
    for i, m in enumerate(next_moves[:5], 1):
        print(f'  {i}. {m["move"]} ({m["games"]}局)')
    
    # 测试棋手搜索
    print('\n搜索棋手:')
    games = kg.search_games(player='许银川', limit=3)
    for g in games:
        print(f'  {g.red} vs {g.black} ({g.event})')
    
    kg.close()
else:
    print('Neo4j KG: 连接失败')
