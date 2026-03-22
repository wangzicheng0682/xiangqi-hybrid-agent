"""
Position Encoder for Xiangqi - 50M版本

基于NeurIPS 2024 "Amortized Planning with Large-Scale Transformers"
配置：8层Transformer, embedding=768, heads=8, ~50M参数
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, List, Tuple, Optional
import numpy as np
import math


class FENTokenizer:
    """FEN → tokens for Xiangqi (9x10 board)"""
    
    def __init__(self):
        self.vocab = {
            'K': 1, 'A': 2, 'B': 3, 'N': 4, 'R': 5, 'C': 6, 'P': 7,
            'k': 8, 'a': 9, 'b': 10, 'n': 11, 'r': 12, 'c': 13, 'p': 14,
            ' ': 15, '/': 16, 'w': 17, 'b': 18, '-': 19, '0': 20, '1': 21,
            '2': 22, '3': 23, '4': 24, '5': 25, '6': 26, '7': 27, '8': 28, '9': 29,
        }
        self.vocab_size = 100
        self.max_length = 100
    
    def tokenize(self, fen: str) -> List[int]:
        tokens = []
        for char in fen:
            if char in self.vocab:
                tokens.append(self.vocab[char])
            else:
                tokens.append(0)
        
        while len(tokens) < self.max_length:
            tokens.append(0)
        
        return tokens[:self.max_length]


class PositionalEncoding1D(nn.Module):
    """可学习的1D位置编码"""
    
    def __init__(self, max_length: int = 100, embed_dim: int = 768):
        super().__init__()
        self.embedding = nn.Embedding(max_length, embed_dim)
        nn.init.normal_(self.embedding.weight, std=0.02)
    
    def forward(self, seq_len: int) -> torch.Tensor:
        device = self.embedding.weight.device
        positions = torch.arange(seq_len, device=device)
        return self.embedding(positions)


class TransformerBlock(nn.Module):
    """Transformer块 with Pre-LN"""
    
    def __init__(self, embed_dim: int, num_heads: int, ff_dim: int, dropout: float = 0.1):
        super().__init__()
        self.attention = nn.MultiheadAttention(embed_dim, num_heads, dropout=dropout, batch_first=True)
        self.feed_forward = nn.Sequential(
            nn.Linear(embed_dim, ff_dim),
            nn.GELU(),
            nn.Linear(ff_dim, embed_dim),
        )
        self.norm1 = nn.LayerNorm(embed_dim)
        self.norm2 = nn.LayerNorm(embed_dim)
        self.dropout = nn.Dropout(dropout)
    
    def forward(self, x: torch.Tensor, mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        attn_out, _ = self.attention(self.norm1(x), self.norm1(x), self.norm1(x), attn_mask=mask)
        x = x + self.dropout(attn_out)
        
        ff_out = self.feed_forward(self.norm2(x))
        x = x + self.dropout(ff_out)
        
        return x


class PositionEncoder50M(nn.Module):
    """
    Position Encoder - 50M参数版本
    
    配置：
    - 8层Transformer
    - embedding=768
    - heads=8
    - ~50M参数
    
    输出：
    - embedding: 用于相似检索
    - action_values: 用于着法推荐 (128个胜率分箱)
    - state_value: 用于局面评估
    - policy: 用于着法概率
    """
    
    def __init__(
        self,
        vocab_size: int = 100,
        embed_dim: int = 768,
        num_heads: int = 8,
        num_layers: int = 8,
        ff_dim: int = 3072,
        max_moves: int = 100,
        num_action_bins: int = 128,
        dropout: float = 0.1
    ):
        super().__init__()
        
        self.embed_dim = embed_dim
        self.num_action_bins = num_action_bins
        
        self.token_embedding = nn.Embedding(vocab_size, embed_dim)
        self.position_embedding = PositionalEncoding1D(max_length=100, embed_dim=embed_dim)
        
        self.transformer_blocks = nn.ModuleList([
            TransformerBlock(embed_dim, num_heads, ff_dim, dropout)
            for _ in range(num_layers)
        ])
        
        self.final_norm = nn.LayerNorm(embed_dim)
        
        self.state_value_head = nn.Sequential(
            nn.Linear(embed_dim, embed_dim // 2),
            nn.GELU(),
            nn.Linear(embed_dim // 2, 1),
            nn.Tanh()
        )
        
        self.action_value_head = nn.Sequential(
            nn.Linear(embed_dim, embed_dim),
            nn.GELU(),
            nn.Linear(embed_dim, num_action_bins)
        )
        
        self.policy_head = nn.Sequential(
            nn.Linear(embed_dim, embed_dim),
            nn.GELU(),
            nn.Linear(embed_dim, max_moves)
        )
        
        self.embedding_head = nn.Sequential(
            nn.Linear(embed_dim, embed_dim),
            nn.GELU(),
            nn.Linear(embed_dim, 256)
        )
        
        self.semantic_head = nn.Sequential(
            nn.Linear(embed_dim, embed_dim // 2),
            nn.GELU(),
            nn.Linear(embed_dim // 2, 33)
        )
        
        self._init_weights()
    
    def _init_weights(self):
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                if module.bias is not None:
                    nn.init.zeros_(module.bias)
            elif isinstance(module, nn.Embedding):
                nn.init.normal_(module.weight, std=0.02)
    
    def forward(self, input_ids: torch.Tensor) -> Dict[str, torch.Tensor]:
        batch_size, seq_len = input_ids.shape
        
        x = self.token_embedding(input_ids)
        
        pos_emb = self.position_embedding(seq_len)
        x = x + pos_emb.unsqueeze(0)
        
        for block in self.transformer_blocks:
            x = block(x)
        
        x = self.final_norm(x)
        
        pooled_output = x.mean(dim=1)
        
        state_value = self.state_value_head(pooled_output)
        
        action_values = self.action_value_head(pooled_output)
        
        policy_logits = self.policy_head(pooled_output)
        
        embedding = self.embedding_head(pooled_output)
        embedding = F.normalize(embedding, p=2, dim=-1)
        
        semantic_tags = self.semantic_head(pooled_output)
        semantic_tags = torch.sigmoid(semantic_tags)
        
        return {
            'state_value': state_value.squeeze(-1),
            'action_values': action_values,
            'policy_logits': policy_logits,
            'embedding': embedding,
            'semantic_tags': semantic_tags,
            'hidden_states': x
        }


SEMANTIC_TAGS = [
    "opening", "middlegame", "endgame",
    "material_advantage", "material_disadvantage",
    "king_safety_red", "king_safety_black",
    "center_control", "side_control",
    "attack_red", "attack_black",
    "defense_red", "defense_black",
    "threat_red", "threat_black",
    "hanging_piece", "pinned_piece",
    "fork_opportunity", "skewer_opportunity",
    "passed_pawn", "isolated_pawn",
    "open_file", "semi_open_file",
    "active_rook", "passive_rook",
    "knight_outpost", "bishop_pair",
    "tempo_advantage", "initiative",
    "space_advantage", "mobility_advantage",
    "critical_position", "quiet_position"
]


def count_parameters(model):
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


if __name__ == "__main__":
    model = PositionEncoder50M()
    print(f"模型参数量: {count_parameters(model):,}")
    
    tokenizer = FENTokenizer()
    fen = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"
    tokens = tokenizer.tokenize(fen)
    tokens_tensor = torch.tensor([tokens], dtype=torch.long)
    
    with torch.no_grad():
        outputs = model(tokens_tensor)
    
    print(f"\n输出:")
    print(f"  state_value: {outputs['state_value'].shape}")
    print(f"  action_values: {outputs['action_values'].shape}")
    print(f"  policy_logits: {outputs['policy_logits'].shape}")
    print(f"  embedding: {outputs['embedding'].shape}")
    print(f"  semantic_tags: {outputs['semantic_tags'].shape}")
