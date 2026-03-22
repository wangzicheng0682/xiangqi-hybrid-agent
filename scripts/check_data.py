"""检查训练数据"""
import json
from pathlib import Path

data_path = Path('data/training/position_data.jsonl')
if data_path.exists():
    with open(data_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    print(f'训练数据文件: {data_path}')
    print(f'数据条数: {len(lines)}')
    
    sample = json.loads(lines[0])
    print(f'\n数据字段: {list(sample.keys())}')
    print(f'semantic_vector维度: {len(sample.get("semantic_vector", []))}')
    print(f'\n示例数据:')
    print(f'  FEN: {sample["fen"][:50]}...')
    print(f'  Score: {sample["score"]}')
    print(f'  Best Move: {sample["best_move"]}')
else:
    print(f'文件不存在: {data_path}')
