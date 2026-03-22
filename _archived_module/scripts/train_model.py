"""
训练 Position Encoder 模型

验证训练管线是否正常工作
"""

import torch
import sys
from pathlib import Path

sys.path.insert(0, '.')

from core.encoder.position_encoder import PositionEncoder, FENTokenizer
from core.encoder.trainer import XiangqiDataset, XiangqiDataCollator, PositionEncoderTrainer

def main():
    print("=" * 60)
    print("Position Encoder 训练")
    print("=" * 60)
    
    print(f"\nPyTorch版本: {torch.__version__}")
    print(f"CUDA可用: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"CUDA设备: {torch.cuda.get_device_name(0)}")
    
    DATA_PATH = "data/training/position_data_10k.jsonl"
    MODEL_SAVE_PATH = "data/models/position_encoder_10k.pt"
    EPOCHS = 10
    BATCH_SIZE = 64
    LR = 5e-5
    EMBED_DIM = 256
    NUM_HEADS = 8
    NUM_LAYERS = 6
    DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
    
    print(f"\n训练配置:")
    print(f"  数据: {DATA_PATH}")
    print(f"  Epochs: {EPOCHS}")
    print(f"  Batch size: {BATCH_SIZE}")
    print(f"  学习率: {LR}")
    print(f"  嵌入维度: {EMBED_DIM}")
    print(f"  层数: {NUM_LAYERS}")
    print(f"  设备: {DEVICE}")
    
    Path(MODEL_SAVE_PATH).parent.mkdir(parents=True, exist_ok=True)
    
    print(f"\n[Step 1] 加载数据...")
    tokenizer = FENTokenizer()
    dataset = XiangqiDataset(DATA_PATH, tokenizer)
    collator = XiangqiDataCollator(tokenizer)
    
    from torch.utils.data import DataLoader
    train_loader = DataLoader(
        dataset,
        batch_size=BATCH_SIZE,
        shuffle=True,
        collate_fn=collator,
        num_workers=0
    )
    print(f"  批次数: {len(train_loader)}")
    
    print(f"\n[Step 2] 初始化模型...")
    model = PositionEncoder(
        vocab_size=tokenizer.vocab_size,
        embed_dim=EMBED_DIM,
        num_heads=NUM_HEADS,
        num_layers=NUM_LAYERS
    )
    
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"  总参数: {total_params:,}")
    print(f"  可训练参数: {trainable_params:,}")
    
    print(f"\n[Step 3] 开始训练...")
    trainer = PositionEncoderTrainer(model, lr=LR, device=DEVICE)
    
    for epoch in range(EPOCHS):
        print(f"\n=== Epoch {epoch + 1}/{EPOCHS} ===")
        
        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()
        
        train_metrics = trainer.train_epoch(train_loader)
        print(f"训练损失: {train_metrics['loss']:.4f}")
        print(f"  - Value损失: {train_metrics['value_loss']:.4f}")
        print(f"  - Semantic损失: {train_metrics['semantic_loss']:.4f}")
        print(f"  - 学习率: {train_metrics['lr']:.6f}")
        
        if torch.cuda.is_available():
            print(f"  - GPU显存峰值: {torch.cuda.max_memory_allocated(0) / 1024**2:.1f} MB")
    
    print(f"\n[Step 4] 保存模型...")
    trainer.save_checkpoint(MODEL_SAVE_PATH, EPOCHS - 1, train_metrics)
    
    print(f"\n{'=' * 60}")
    print(f"训练完成！模型保存到: {MODEL_SAVE_PATH}")
    print(f"{'=' * 60}")

if __name__ == "__main__":
    main()
