"""
Position Encoder 训练脚本

基于NeurIPS 2024方法
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
from typing import Dict, List, Optional
import json
import random
from pathlib import Path
from tqdm import tqdm
import numpy as np

from core.encoder.position_encoder import PositionEncoder, FENTokenizer, SEMANTIC_TAGS


class XiangqiDataset(Dataset):
    """象棋局面数据集"""
    
    def __init__(self, data_path: str, tokenizer: FENTokenizer = None):
        self.data_path = data_path
        self.tokenizer = tokenizer or FENTokenizer()
        
        self.data = []
        self._load_data()
        
    def _load_data(self):
        """加载JSONL数据"""
        with open(self.data_path, 'r', encoding='utf-8') as f:
            for line in f:
                item = json.loads(line.strip())
                self.data.append(item)
        
        print(f"加载了 {len(self.data)} 条训练数据")
    
    def __len__(self):
        return len(self.data)
    
    def __getitem__(self, idx) -> Dict[str, torch.Tensor]:
        item = self.data[idx]
        
        fen_tokens = self.tokenizer.tokenize(item['fen'])
        
        score = item.get('score', 0)
        if score is None:
            score = 0
        score = score / 100.0
        
        red_win_rate = item.get('red_win_rate', 0.5)
        if red_win_rate is None:
            red_win_rate = 0.5
        
        semantic_vector = item.get('semantic_vector', [0.0] * len(SEMANTIC_TAGS))
        if semantic_vector is None:
            semantic_vector = [0.0] * len(SEMANTIC_TAGS)
        
        return {
            'fen_tokens': torch.tensor(fen_tokens, dtype=torch.long),
            'score': torch.tensor(score, dtype=torch.float),
            'red_win_rate': torch.tensor(red_win_rate, dtype=torch.float),
            'semantic_tags': torch.tensor(semantic_vector, dtype=torch.float),
            'fen': item['fen']
        }


class XiangqiDataCollator:
    """数据整理器"""
    
    def __init__(self, tokenizer: FENTokenizer):
        self.tokenizer = tokenizer
    
    def __call__(self, batch: List[Dict]) -> Dict[str, torch.Tensor]:
        return {
            'fen_tokens': torch.stack([item['fen_tokens'] for item in batch]),
            'score': torch.stack([item['score'] for item in batch]).unsqueeze(1),
            'red_win_rate': torch.stack([item['red_win_rate'] for item in batch]).unsqueeze(1),
            'semantic_tags': torch.stack([item['semantic_tags'] for item in batch]),
        }


class PositionEncoderTrainer:
    """Position Encoder训练器"""
    
    def __init__(
        self,
        model: PositionEncoder,
        lr: float = 1e-4,
        weight_decay: float = 0.01,
        device: str = "cuda" if torch.cuda.is_available() else "cpu"
    ):
        self.model = model.to(device)
        self.device = device
        
        # 优化器
        self.optimizer = torch.optim.AdamW(
            model.parameters(),
            lr=lr,
            weight_decay=weight_decay
        )
        
        # 学习率调度
        self.scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            self.optimizer,
            T_max=10,
            eta_min=1e-6
        )
        
        # 损失函数
        self.mse_loss = nn.MSELoss()
        self.ce_loss = nn.CrossEntropyLoss()
        self.bce_loss = nn.BCELoss()
        
    def compute_loss(self, outputs: Dict[str, torch.Tensor], targets: Dict[str, torch.Tensor]) -> Dict[str, torch.Tensor]:
        """计算多任务损失（包含语义标签）"""
        losses = {}
        
        if 'score' in targets:
            value_loss = self.mse_loss(
                outputs['value'].squeeze(-1),
                targets['score']
            )
            losses['value'] = value_loss
        
        if 'red_win_rate' in targets:
            win_rate_loss = self.mse_loss(
                outputs['red_win_rate'].squeeze(-1),
                targets['red_win_rate']
            )
            losses['red_win_rate'] = win_rate_loss
        
        if 'semantic_tags' in targets and 'semantic_tags' in outputs:
            semantic_loss = self.bce_loss(
                outputs['semantic_tags'],
                targets['semantic_tags']
            )
            losses['semantic'] = semantic_loss
        
        total_loss = (
            losses.get('value', 0) * 1.0 +
            losses.get('red_win_rate', 0) * 0.5 +
            losses.get('semantic', 0) * 0.3
        )
        losses['total'] = total_loss
        
        return losses
    
    def train_epoch(self, dataloader: DataLoader) -> Dict[str, float]:
        """训练一个epoch"""
        self.model.train()
        total_loss = 0
        total_value_loss = 0
        total_semantic_loss = 0
        num_batches = 0
        
        for batch in tqdm(dataloader, desc="Training"):
            fen_tokens = batch['fen_tokens'].to(self.device)
            score = batch['score'].to(self.device)
            red_win_rate = batch['red_win_rate'].to(self.device)
            semantic_tags = batch['semantic_tags'].to(self.device)
            
            outputs = self.model(fen_tokens)
            
            hidden = outputs['hidden_states'].mean(dim=1)
            value_pred = nn.functional.linear(hidden, self.model.action_head[0].weight[:1, :])
            win_rate_pred = nn.functional.linear(hidden, self.model.action_head[0].weight[1:2, :])
            
            value_loss = self.mse_loss(value_pred.squeeze(), score)
            win_rate_loss = self.mse_loss(win_rate_pred.squeeze(), red_win_rate)
            
            semantic_pred = outputs['semantic_tags']
            semantic_loss = self.bce_loss(semantic_pred, semantic_tags)
            
            loss = value_loss + win_rate_loss * 0.5 + semantic_loss * 0.3
            
            self.optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
            self.optimizer.step()
            
            total_loss += loss.item()
            total_value_loss += value_loss.item()
            total_semantic_loss += semantic_loss.item()
            num_batches += 1
        
        self.scheduler.step()
        
        return {
            'loss': total_loss / num_batches,
            'value_loss': total_value_loss / num_batches,
            'semantic_loss': total_semantic_loss / num_batches,
            'lr': self.scheduler.get_last_lr()[0]
        }
    
    @torch.no_grad()
    def evaluate(self, dataloader: DataLoader) -> Dict[str, float]:
        """评估"""
        self.model.eval()
        total_loss = 0
        num_batches = 0
        
        for batch in tqdm(dataloader, desc="Evaluating"):
            fen_tokens = batch['fen_tokens'].to(self.device)
            score = batch['score'].to(self.device)
            red_win_rate = batch['red_win_rate'].to(self.device)
            
            outputs = self.model(fen_tokens)
            hidden = outputs['hidden_states'].mean(dim=1)
            value_pred = nn.functional.linear(hidden, self.model.action_head[0].weight[:1, :])
            win_rate_pred = nn.functional.linear(hidden, self.model.action_head[0].weight[1:2, :])
            
            value_loss = self.mse_loss(value_pred.squeeze(), score)
            win_rate_loss = self.mse_loss(win_rate_pred.squeeze(), red_win_rate)
            loss = value_loss + win_rate_loss * 0.5
            
            total_loss += loss.item()
            num_batches += 1
        
        return {'val_loss': total_loss / num_batches}
    
    def save_checkpoint(self, path: str, epoch: int, metrics: Dict):
        """保存检查点"""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        
        torch.save({
            'epoch': epoch,
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'scheduler_state_dict': self.scheduler.state_dict(),
            'metrics': metrics
        }, path)
        
        print(f"保存检查点到 {path}")


def train(
    train_data_path: str,
    val_data_path: Optional[str] = None,
    model_save_path: str = "data/models/position_encoder.pt",
    epochs: int = 10,
    batch_size: int = 32,
    lr: float = 1e-4,
    embed_dim: int = 256,
    num_heads: int = 8,
    num_layers: int = 6,
    device: str = "cuda" if torch.cuda.is_available() else "cpu"
):
    """训练函数"""
    
    print(f"训练配置:")
    print(f"  数据: {train_data_path}")
    print(f"  Epochs: {epochs}")
    print(f"  Batch size: {batch_size}")
    print(f"  学习率: {lr}")
    print(f"  设备: {device}")
    print()
    
    # 数据集
    tokenizer = FENTokenizer()
    train_dataset = XiangqiDataset(train_data_path, tokenizer)
    collator = XiangqiDataCollator(tokenizer)
    
    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        collate_fn=collator,
        num_workers=0
    )
    
    # 模型
    model = PositionEncoder(
        vocab_size=tokenizer.vocab_size,
        embed_dim=embed_dim,
        num_heads=num_heads,
        num_layers=num_layers
    )
    
    # 训练器
    trainer = PositionEncoderTrainer(model, lr=lr, device=device)
    
    best_val_loss = float('inf')
    
    for epoch in range(epochs):
        print(f"\n=== Epoch {epoch + 1}/{epochs} ===")
        
        train_metrics = trainer.train_epoch(train_loader)
        print(f"训练损失: {train_metrics['loss']:.4f}")
        print(f"  - Value损失: {train_metrics['value_loss']:.4f}")
        print(f"  - Semantic损失: {train_metrics['semantic_loss']:.4f}")
        print(f"  - 学习率: {train_metrics['lr']:.6f}")
        
        if val_data_path:
            val_dataset = XiangqiDataset(val_data_path, tokenizer)
            val_loader = DataLoader(val_dataset, batch_size=batch_size, collate_fn=collator)
            val_metrics = trainer.evaluate(val_loader)
            print(f"验证损失: {val_metrics['val_loss']:.4f}")
            
            if val_metrics['val_loss'] < best_val_loss:
                best_val_loss = val_metrics['val_loss']
                trainer.save_checkpoint(model_save_path, epoch, val_metrics)
        else:
            trainer.save_checkpoint(model_save_path, epoch, train_metrics)
    
    print(f"\n训练完成! 最终模型保存到 {model_save_path}")


def main():
    """测试训练脚本"""
    # 检查PyTorch
    print(f"PyTorch版本: {torch.__version__}")
    print(f"CUDA可用: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"CUDA设备: {torch.cuda.get_device_name(0)}")
    
    # 测试数据加载
    data_path = "data/training/position_data.jsonl"
    if Path(data_path).exists():
        dataset = XiangqiDataset(data_path)
        print(f"\n数据集大小: {len(dataset)}")
        sample = dataset[0]
        print(f"样本tokens: {sample['fen_tokens'][:10]}...")
        print(f"样本score: {sample['score']}")
    else:
        print(f"\n数据文件不存在: {data_path}")
        print("请先运行 data_generator.py 生成训练数据")


if __name__ == "__main__":
    main()
