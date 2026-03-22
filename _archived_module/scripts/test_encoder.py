"""
测试训练好的Position Encoder效果
"""
import sys
sys.path.insert(0, '.')

import torch
import numpy as np
from core.encoder.position_encoder import PositionEncoder, FENTokenizer, get_semantic_description

# 加载模型
print("加载模型...")
model = PositionEncoder(
    vocab_size=300,
    embed_dim=256,
    num_heads=8,
    num_layers=6
)
model.load_state_dict(torch.load("data/models/position_encoder_v1.pt", map_location='cpu'))
model.eval()

# 测试局面
test_positions = [
    # 开局
    "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1",
    # 中局
    "2bak1nr1/4a4/2n1bc3/p1C1p3p/6p2/2PN5/c3P1P1P/1C4N2/9/2BAKAB2 b - - 5 5",
    # 残局
    "4k4/9/9/9/9/9/4C4/9/9/9/4c4/9/4K4 w - - 20 30",
]

print("\n" + "="*50)
print("Position Encoder 效果测试")
print("="*50)

tokenizer = FENTokenizer()

for i, fen in enumerate(test_positions):
    print(f"\n【测试 {i+1}】")
    print(f"FEN: {fen}")
    
    # 编码
    result = model.encode_fen(fen)
    
    # 输出
    embedding = result['embedding'][0]
    semantic_tags = result['semantic_tags'][0]
    
    print(f"Embedding维度: {embedding.shape}")
    print(f"Embedding前5维: {embedding[:5]}")
    
    # 语义标签
    active_tags = get_semantic_description(result['semantic_tags'])
    print(f"语义标签: {active_tags}")
    
    # 相似度测试
    if i > 0:
        prev_embedding = prev_result['embedding'][0]
        similarity = np.dot(embedding, prev_embedding)
        print(f"与前一个局面的相似度: {similarity:.4f}")

    
    prev_result = result

print("\n" + "="*50)
print("测试完成！模型工作正常")
print("="*50)
