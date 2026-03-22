"""
生成训练数据脚本

从Neo4j提取局面 -> Pikafish标注 -> 语义标签生成 -> 保存
"""

import json
import sys
from pathlib import Path
from tqdm import tqdm

sys.path.insert(0, '.')

from neo4j import GraphDatabase
from core.engine.pikafish_engine import PikafishEngine
from core.encoder.semantic_labeler import SemanticLabelerPipeline


def main():
    print("=" * 60)
    print("Position Encoder 训练数据生成")
    print("=" * 60)
    
    NEO4J_URI = "bolt://localhost:7687"
    NEO4J_USER = "neo4j"
    NEO4J_PASSWORD = "xiangqi123"
    ENGINE_PATH = Path("data/engine/pikafish-avx2.exe")
    OUTPUT_PATH = Path("data/training/position_data.jsonl")
    NUM_POSITIONS = 10000
    ENGINE_DEPTH = 12
    
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"\n[Step 1] 连接Neo4j...")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    with driver.session() as session:
        result = session.run("MATCH (p:Position) RETURN count(p) as count")
        total_count = result.single()['count']
        print(f"Position节点总数: {total_count}")
    
    print(f"\n[Step 2] 提取 {NUM_POSITIONS} 个局面...")
    with driver.session() as session:
        query = """
        MATCH (p:Position)
        WHERE p.total_games >= 5
        RETURN p.fen as fen, 
               p.total_games as total_games,
               p.red_win_rate as red_win_rate
        ORDER BY rand()
        LIMIT $limit
        """
        result = session.run(query, limit=NUM_POSITIONS)
        positions = [dict(record) for record in result]
    
    print(f"提取了 {len(positions)} 个局面")
    driver.close()
    
    print(f"\n[Step 3] 初始化引擎和标签生成器...")
    engine = PikafishEngine(ENGINE_PATH)
    engine.start()
    labeler = SemanticLabelerPipeline(engine=engine)
    
    print(f"\n[Step 4] 标注局面 (depth={ENGINE_DEPTH})...")
    annotated = []
    prev_score = None
    
    for pos in tqdm(positions, desc="标注中"):
        fen = pos['fen']
        
        try:
            result = engine.analyze(fen, depth=ENGINE_DEPTH)
            
            item = {
                'fen': fen,
                'total_games': pos.get('total_games', 0),
                'red_win_rate': pos.get('red_win_rate', 0.5),
                'score': result.score,
                'best_move': result.bestmove,
                'pv': result.pv[:3] if result.pv else [],
                'depth': ENGINE_DEPTH
            }
            
            semantic_labels = labeler.label(
                fen, 
                prev_score=prev_score,
                engine_info={'score': result.score, 'best_move': result.bestmove, 'pv': result.pv}
            )
            item['semantic_tags'] = semantic_labels.tags
            item['semantic_sources'] = semantic_labels.sources
            item['semantic_vector'] = semantic_labels.to_vector()
            
            annotated.append(item)
            prev_score = result.score
            
        except Exception as e:
            print(f"\n错误: {fen[:30]}... - {e}")
            continue
    
    engine.stop()
    
    print(f"\n[Step 5] 保存到 {OUTPUT_PATH}...")
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        for item in annotated:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    
    print(f"\n{'=' * 60}")
    print(f"完成！生成 {len(annotated)} 条训练数据")
    print(f"保存到: {OUTPUT_PATH}")
    print(f"{'=' * 60}")
    
    if annotated:
        print(f"\n示例数据:")
        sample = annotated[0]
        print(f"  FEN: {sample['fen'][:50]}...")
        print(f"  Score: {sample['score']}")
        print(f"  Best Move: {sample['best_move']}")
        print(f"  Semantic Tags: {list(sample['semantic_tags'].keys())[:5]}...")


if __name__ == "__main__":
    main()
