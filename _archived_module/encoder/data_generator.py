"""
数据生成器：从Neo4j提取数据并用Pikafish标注
用于训练Position Encoder

包含语义标签生成：
1. 规则弱监督（零成本）
2. 引擎诱导伪标签
3. LLM辅助标注（可选）
"""

import json
import random
from typing import List, Dict, Optional
from pathlib import Path
from neo4j import GraphDatabase
from tqdm import tqdm
import sys
sys.path.insert(0, '.')

from core.engine.pikafish_engine import PikafishEngine
from core.encoder.semantic_labeler import (
    RuleBasedLabeler, 
    EngineInducedLabeler,
    SemanticLabelerPipeline
)


class DataGenerator:
    """从Neo4j生成训练数据，包含语义标签"""
    
    def __init__(
        self,
        neo4j_uri: str = "bolt://localhost:7687",
        neo4j_user: str = "neo4j",
        neo4j_password: str = "xiangqi123",
        engine_path: str = "data/engine/pikafish-avx2.exe",
        enable_semantic_labels: bool = True
    ):
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        self.engine = PikafishEngine(Path(engine_path))
        self.enable_semantic_labels = enable_semantic_labels
        
        if enable_semantic_labels:
            self.semantic_labeler = SemanticLabelerPipeline(engine=self.engine)
        
    def close(self):
        self.driver.close()
        try:
            self.engine.stop()
        except:
            pass
    
    def extract_positions(
        self, 
        limit: int = 10000,
        min_games: int = 10,
        sample_strategy: str = "diverse"
    ) -> List[Dict]:
        """
        从Neo4j提取局面数据
        
        Args:
            limit: 提取数量
            min_games: 最少历史对局数
            sample_strategy: 采样策略 ('diverse' 或 'popular')
        """
        with self.driver.session() as session:
            if sample_strategy == "diverse":
                # 多样化采样：从不同阶段采样
                query = """
                MATCH (p:Position)
                WHERE p.total_games >= $min_games
                RETURN p.fen as fen, 
                       p.total_games as total_games,
                       p.red_win_rate as red_win_rate,
                       p.black_win_rate as black_win_rate,
                       p.draw_rate as draw_rate
                ORDER BY rand()
                LIMIT $limit
                """
            else:
                # 热门采样：按对局数排序
                query = """
                MATCH (p:Position)
                WHERE p.total_games >= $min_games
                RETURN p.fen as fen, 
                       p.total_games as total_games,
                       p.red_win_rate as red_win_rate,
                       p.black_win_rate as black_win_rate,
                       p.draw_rate as draw_rate
                ORDER BY p.total_games DESC
                LIMIT $limit
                """
            
            result = session.run(query, min_games=min_games, limit=limit)
            positions = [dict(record) for record in result]
        
        print(f"从Neo4j提取了 {len(positions)} 个局面")
        return positions
    
    def annotate_with_engine(
        self, 
        positions: List[Dict],
        depth: int = 15,
        num_variants: int = 3
    ) -> List[Dict]:
        """
        用Pikafish引擎标注局面 + 生成语义标签
        
        Args:
            positions: 局面列表
            depth: 搜索深度
            num_variants: 返回的候选着法数
        """
        annotated = []
        prev_score = None
        
        for i, pos in enumerate(tqdm(positions, desc="标注中")):
            fen = pos['fen']
            
            try:
                result = self.engine.analyze(fen, depth=depth)
                
                if result:
                    item = {
                        'fen': fen,
                        'total_games': pos.get('total_games', 0),
                        'red_win_rate': pos.get('red_win_rate', 0.5),
                        'black_win_rate': pos.get('black_win_rate', 0.5),
                        'draw_rate': pos.get('draw_rate', 0),
                        'score': result.score,
                        'best_move': result.bestmove,
                        'pv': result.pv[:num_variants] if result.pv else [],
                        'depth': depth
                    }
                    
                    if self.enable_semantic_labels:
                        semantic_labels = self.semantic_labeler.label(
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
                print(f"Error analyzing {fen}: {e}")
                continue
        
        print(f"成功标注 {len(annotated)}/{len(positions)} 局面")
        return annotated
    
    def save_to_jsonl(self, data: List[Dict], output_path: str):
        """保存为JSONL格式"""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for item in data:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
        
        print(f"保存 {len(data)} 条数据到 {output_path}")
    
    def generate_training_data(
        self,
        output_path: str = "data/training/position_data.jsonl",
        num_positions: int = 10000,
        engine_depth: int = 15,
        sample_strategy: str = "diverse"
    ):
        """
        完整的数据生成流程
        """
        print(f"开始生成训练数据 (目标: {num_positions} 局面)")
        
        # 1. 提取局面
        positions = self.extract_positions(
            limit=num_positions,
            sample_strategy=sample_strategy
        )
        
        # 2. 用引擎标注
        annotated = self.annotate_with_engine(positions, depth=engine_depth)
        
        # 3. 保存
        self.save_to_jsonl(annotated, output_path)
        
        return annotated
    
    def quick_sample(self, num: int = 1000) -> List[Dict]:
        """快速采样（不做引擎标注，用于测试）"""
        return self.extract_positions(limit=num, sample_strategy="diverse")


def main():
    """测试数据生成"""
    generator = DataGenerator()
    
    # 快速测试：采样100个局面
    positions = generator.quick_sample(100)
    print(f"\n采样结果示例:")
    print(f"  FEN: {positions[0]['fen']}")
    print(f"  对局数: {positions[0]['total_games']}")
    print(f"  红方胜率: {positions[0]['red_win_rate']:.1%}")
    
    generator.close()


if __name__ == "__main__":
    main()
