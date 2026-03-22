"""
Phase 1: 训练Position Encoder
"""
import sys
sys.path.insert(0, '.')

import torch
from torch.utils.data import DataLoader
from pathlib import Path
from core.encoder.position_encoder import PositionEncoder, FENTokenizer
from core.encoder.trainer import XiangqiDataset, XiangqiDataCollator, PositionEncoderTrainer

print("=" * 50)
print("Phase 1: 训练Position Encoder")
print("=" * 50)

# 检查GPU
print(f"\n设备: {'cuda' if torch.cuda.is_available() else 'cpu'}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")

# 加载数据
print("\n加载数据...")
tokenizer = FENTokenizer()
dataset = XiangqiDataset("data/training/position_data_10k.jsonl", tokenizer)
collator = XiangqiDataCollator(tokenizer)

dataloader = DataLoader(
    dataset,
    batch_size=32,
    shuffle=True,
    collate_fn=collator,
    num_workers=0
)

# 创建模型
print("\n创建模型...")
model = PositionEncoder(
    vocab_size=300,
    embed_dim=256,
    num_heads=8,
    num_layers=6
)

# 计算参数量
total_params = sum(p.numel() for p in model.parameters())
print(f"模型参数量: {total_params:,}")

# 训练
print("\n开始训练...")
trainer = PositionEncoderTrainer(model, lr=1e-4)

for epoch in range(5):
    metrics = trainer.train_epoch(dataloader)
    print(f"Epoch {epoch+1}: loss={metrics['loss']:.4f}, lr={metrics['lr']:.6f}")

# 保存模型
print("\n保存模型...")
Path("data/models").mkdir(parents=True, exist_ok=True)
torch.save(model.state_dict(), "data/models/position_encoder_v1.pt")
print("模型已保存到: data/models/position_encoder_v1.pt")

print("\n训练完成！")
