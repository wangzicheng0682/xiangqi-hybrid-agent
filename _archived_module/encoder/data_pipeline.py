"""
优化的数据生成流程：
1. 预处理局面
2. 批量标注
3. 生成训练数据
"""

import json
import random
from typing import List, Dict, Optional
from pathlib import Path
from neo4j import GraphDatabase
from concurrent.futures import ProcessPoolExecutor, as_completed
from tqdm import tqdm
import multiprocessing


class PositionPreprocessor:
    """局面预处理器"""
    
    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    
    def close(self):
        self.driver.close()
    
    def extract_positions(self, limit: int = 10000, min_games: int = 5) -> List[Dict]:
        """从Neo4j提取局面"""
        with self.driver.session() as session:
            query = """
            MATCH (p:Position)
            WHERE p.total_games >= $min_games
            RETURN p.fen as fen, 
                   p.total_games as total_games,
                   p.red_win_rate as red_win_rate
            ORDER BY rand()
            LIMIT $limit
            """
            result = session.run(query, min_games=min_games, limit=limit)
            positions = [dict(record) for record in result]
        return positions
    
    def classify_phase(self, fen: str) -> str:
        """判断局面阶段"""
        board = fen.split()[0]
        pieces = sum(1 for c in board if c.isalpha())
        
        if pieces >= 28:
            return "opening"
        elif pieces >= 16:
            return "middlegame"
        else:
            return "endgame"
    
    def preprocess(self, positions: List[Dict]) -> List[Dict]:
        """预处理：分类和过滤"""
        processed = []
        
        for pos in positions:
            fen = pos['fen']
            phase = self.classify_phase(fen)
            
            processed.append({
                'fen': fen,
                'total_games': pos.get('total_games', 0),
                'red_win_rate': pos.get('red_win_rate', 0.5),
                'phase': phase
            })
        
        return processed
    
    def save_intermediate(self, positions: List[Dict], output_path: str):
        """保存中间文件"""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            for pos in positions:
                f.write(json.dumps(pos, ensure_ascii=False) + '\n')
        print(f"保存 {len(positions)} 个局面到 {output_path}")


class EngineAnnotator:
    """引擎标注器"""
    
    def __init__(self, engine_path: str):
        self.engine_path = engine_path
    
    def annotate_single(self, fen: str, depth: int = 12) -> Dict:
        """标注单个局面"""
        import subprocess
        
        try:
            # 启动引擎
            process = subprocess.Popen(
                [self.engine_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # 发送命令
            commands = f"position fen {fen}\ngo depth {depth}\n"
            stdout, _ = process.communicate(commands, timeout=30)
            
            # 解析结果
            score = 0
            best_move = ""
            
            for line in stdout.split('\n'):
                if 'score cp' in line:
                    try:
                        score = int(line.split('score cp')[1].split()[0])
                    except:
                        pass
                if 'bestmove' in line:
                    best_move = line.split('bestmove')[1].strip().split()[0]
            
            process.terminate()
            
            return {
                'fen': fen,
                'score': score,
                'best_move': best_move,
                'depth': depth
            }
        except Exception as e:
            return {'fen': fen, 'score': 0, 'best_move': '', 'error': str(e)}
    
    def annotate_batch(self, positions: List[Dict], depth: int = 12, num_workers: int = 4) -> List[Dict]:
        """批量标注（多进程）"""
        annotated = []
        
        with ProcessPoolExecutor(max_workers=num_workers) as executor:
            futures = {
                executor.submit(self.annotate_single, pos['fen'], depth): pos
                for pos in positions
            }
            
            for future in tqdm(as_completed(futures), total=len(futures), desc="标注中"):
                result = future.result()
                original = futures[future]
                
                if 'error' not in result:
                    annotated.append({
                        **original,
                        'score': result['score'],
                        'best_move': result['best_move']
                    })
        
        return annotated


def main():
    """主流程"""
    print("=" * 50)
    print("优化数据生成流程")
    print("=" * 50)
    
    # Step 1: 预处理
    print("\n[Step 1] 预处理局面...")
    preprocessor = PositionPreprocessor(
        "bolt://localhost:7687",
        "neo4j",
        "xiangqi123"
    )
    
    positions = preprocessor.extract_positions(limit=10000)
    processed = preprocessor.preprocess(positions)
    preprocessor.save_intermediate(processed, "data/training/positions_preprocessed.jsonl")
    preprocessor.close()
    
    # Step 2: 批量标注
    print("\n[Step 2] 批量引擎标注...")
    annotator = EngineAnnotator("data/engine/pikafish-avx2.exe")
    annotated = annotator.annotate_batch(processed, depth=12, num_workers=4)
    
    # Step 3: 保存训练数据
    print("\n[Step 3] 保存训练数据...")
    output_path = "data/training/position_data_10k.jsonl"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        for item in annotated:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    
    print(f"\n完成！生成 {len(annotated)} 条训练数据")
    print(f"保存到: {output_path}")


if __name__ == "__main__":
    main()
