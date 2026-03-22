"""
验证数据文件的时间戳
"""
import os
import json
from datetime import datetime

DATA_PATH = "data/training/position_data_1m.jsonl"

stat = os.stat(DATA_PATH)
print(f"文件信息:")
print(f"  大小: {stat.st_size / 1024 / 1024:.1f} MB")
print(f"  创建时间: {datetime.fromtimestamp(stat.st_ctime)}")
print(f"  修改时间: {datetime.fromtimestamp(stat.st_mtime)}")

with open(DATA_PATH, 'r') as f:
    lines = f.readlines()
    
print(f"  行数: {len(lines):,}")

first_10 = [json.loads(line) for line in lines[:10]]
print(f"\n前10条数据:")
for i, item in enumerate(first_10[:5]):
    print(f"  {i+1}. best_move={item.get('best_move')}, state_value={item.get('state_value'):.4f}")

import random
sample = random.sample(lines, 10)
print(f"\n随机10条:")
for i, line in enumerate(sample):
    item = json.loads(line)
    print(f"  {i+1}. best_move={item.get('best_move')}, state_value={item.get('state_value'):.4f}")
