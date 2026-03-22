"""
训练50M参数模型 - 优化版

配置：
- 参数量: 50M (8层, embedding=768, heads=8)
- 数据: 100万局面
- Batch size: 32 (梯度累积2步)
- 损失函数: action-value + state-value + policy
- 优化: 流式加载，避免内存爆炸
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader, IterableDataset
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR
from pathlib import Path
import json
import random
from tqdm import tqdm
import sys

sys.path.insert(0, '.')

from core.encoder.position_encoder_50m import PositionEncoder50M, FENTokenizer


class StreamingXiangqiDataset(IterableDataset):
    """流式加载数据集"""
    
    def __init__(self, data_path: str, tokenizer: FENTokenizer = None, shuffle_buffer: int = 10000):
        self.data_path = data_path
        self.tokenizer = tokenizer or FENTokenizer()
        self.shuffle_buffer = shuffle_buffer
        
        with open(data_path, 'r') as f:
            self.total_lines = sum(1 for _ in f)
    
    def __iter__(self):
        with open(self.data_path, 'r', encoding='utf-8') as f:
            buffer = []
            for line in f:
                item = json.loads(line.strip())
                
                tokens = self.tokenizer.tokenize(item['fen'])
                state_value = item.get('state_value', 0.0) or 0.0
                action_value = item.get('action_value', 0.0) or 0.0
                
                sample = {
                    'input_ids': torch.tensor(tokens, dtype=torch.long),
                    'state_value': torch.tensor(state_value, dtype=torch.float),
                    'action_value': torch.tensor(action_value, dtype=torch.float),
                }
                
                buffer.append(sample)
                
                if len(buffer) >= self.shuffle_buffer:
                    random.shuffle(buffer)
                    for s in buffer:
                        yield s
                    buffer = []
            
            if buffer:
                random.shuffle(buffer)
                for s in buffer:
                    yield s
    
    def __len__(self):
        return self.total_lines


def collate_fn(batch):
    return {
        'input_ids': torch.stack([item['input_ids'] for item in batch]),
        'state_value': torch.stack([item['state_value'] for item in batch]),
        'action_value': torch.stack([item['action_value'] for item in batch]),
    }


def train():
    print("=" * 60)
    print("训练50M参数模型 - 优化版")
    print("=" * 60)
    
    DATA_PATH = "data/training/position_data_1m.jsonl"
    MODEL_SAVE_PATH = "data/models/position_encoder_50m_final.pt"
    EPOCHS = 10
    BATCH_SIZE = 32
    ACCUMULATION_STEPS = 2
    LR = 3e-5
    DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
    
    print(f"\n配置:")
    print(f"  数据: {DATA_PATH}")
    print(f"  Epochs: {EPOCHS}")
    print(f"  Batch size: {BATCH_SIZE}")
    print(f"  梯度累积: {ACCUMULATION_STEPS}")
    print(f"  有效Batch: {BATCH_SIZE * ACCUMULATION_STEPS}")
    print(f"  学习率: {LR}")
    print(f"  设备: {DEVICE}")
    
    if not Path(DATA_PATH).exists():
        print(f"\n错误: 数据文件不存在: {DATA_PATH}")
        return
    
    Path(MODEL_SAVE_PATH).parent.mkdir(parents=True, exist_ok=True)
    
    print(f"\n[Step 1] 初始化数据集...")
    tokenizer = FENTokenizer()
    dataset = StreamingXiangqiDataset(DATA_PATH, tokenizer)
    
    train_loader = DataLoader(
        dataset,
        batch_size=BATCH_SIZE,
        collate_fn=collate_fn,
        num_workers=0
    )
    print(f"  总样本数: {len(dataset):,}")
    
    print(f"\n[Step 2] 初始化模型...")
    model = PositionEncoder50M().to(DEVICE)
    
    total_params = sum(p.numel() for p in model.parameters())
    print(f"  总参数: {total_params:,}")
    
    optimizer = AdamW(model.parameters(), lr=LR, weight_decay=0.01)
    scheduler = CosineAnnealingLR(optimizer, T_max=EPOCHS * (len(dataset) // BATCH_SIZE))
    
    state_value_loss_fn = nn.MSELoss()
    action_value_loss_fn = nn.MSELoss()
    
    print(f"\n[Step 3] 开始训练...")
    
    for epoch in range(EPOCHS):
        model.train()
        total_loss = 0
        num_batches = 0
        
        optimizer.zero_grad()
        
        progress_bar = tqdm(train_loader, desc=f"Epoch {epoch+1}/{EPOCHS}", total=len(dataset)//BATCH_SIZE)
        
        for batch_idx, batch in enumerate(progress_bar):
            input_ids = batch['input_ids'].to(DEVICE)
            state_value = batch['state_value'].to(DEVICE)
            action_value = batch['action_value'].to(DEVICE)
            
            outputs = model(input_ids)
            
            pred_state_value = outputs['state_value']
            pred_action_value = outputs['action_values'][:, 0]
            
            loss_state = state_value_loss_fn(pred_state_value, state_value)
            loss_action = action_value_loss_fn(pred_action_value, action_value)
            
            loss = loss_state + loss_action
            
            loss = loss / ACCUMULATION_STEPS
            loss.backward()
            
            if (batch_idx + 1) % ACCUMULATION_STEPS == 0:
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                scheduler.step()
                optimizer.zero_grad()
            
            total_loss += loss.item() * ACCUMULATION_STEPS
            num_batches += 1
            
            progress_bar.set_postfix({
                'loss': f'{total_loss/num_batches:.4f}',
                'lr': f'{scheduler.get_last_lr()[0]:.6f}'
            })
        
        avg_loss = total_loss / num_batches
        print(f"\nEpoch {epoch+1} 完成 - 平均损失: {avg_loss:.4f}")
        
        checkpoint = {
            'epoch': epoch,
            'model_state_dict': model.state_dict(),
            'optimizer_state_dict': optimizer.state_dict(),
            'loss': avg_loss
        }
        torch.save(checkpoint, MODEL_SAVE_PATH)
        print(f"模型保存到: {MODEL_SAVE_PATH}")
    
    print(f"\n{'=' * 60}")
    print(f"训练完成!")
    print(f"模型保存到: {MODEL_SAVE_PATH}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    train()
