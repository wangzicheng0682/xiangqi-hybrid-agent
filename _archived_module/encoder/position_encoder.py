"""
Position Encoder for Xiangqi

基于NeurIPS 2024 "Amortized Planning with Large-Scale Transformers"
将FEN编码为embedding和action_values
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, List, Tuple, Optional
import numpy as np


class FENTokenizer:
    """FEN → 77 tokens (基于NeurIPS论文)"""
    
    def __init__(self):
        # 词汇表
        self.vocab = {
            # 棋子
            'K': 1, 'A': 2, 'B': 3, 'N': 4, 'R': 5, 'C': 6, 'P': 7,  # 红方
            'k': 8, 'a': 9, 'b': 10, 'n': 11, 'r': 12, 'c': 13, 'p': 14,  # 黑方
            '1': 15, '2': 16, '3': 17, '4': 18, '5': 19, '6': 20, '7': 21, '8': 22, '9': 23,
            '/': 24, ' ': 25, '-': 26, 'w': 27, 'b': 28,  # FEN特殊字符
            '0': 29, '1': 30, '2': 31, '3': 32, '4': 33, '5': 34, '6': 35, '7': 36, '8': 37, '9': 38,
            ' ': 39, ' ': 40, ' ': 41, ' ': 42, ' ': 43, ' ': 44, ' ': 45, ' ': 46, ' ': 47,
        }
        self.vocab_size = 300  # 预留空间
        
    def tokenize(self, fen: str) -> List[int]:
        """FEN → 77 tokens"""
        tokens = []
        
        # 简化版：直接字符映射
        for char in fen:
            if char in self.vocab:
                tokens.append(self.vocab[char])
            else:
                tokens.append(0)  # 未知字符
        
        # 填充到77长度
        while len(tokens) < 77:
            tokens.append(0)
        
        return tokens[:77]
    
    def detokenize(self, tokens: List[int]) -> str:
        """tokens → FEN (简化版)"""
        reverse_vocab = {v: k for k, v in self.vocab.items()}
        fen_chars = []
        
        for token in tokens:
            if token in reverse_vocab:
                fen_chars.append(reverse_vocab[token])
            elif token == 0:
                break
        
        return ''.join(fen_chars)


class PositionEncoder(nn.Module):
    """
    Position Encoder: FEN → [embedding, action_values]
    
    基于NeurIPS 2024论文架构
    """
    
    def __init__(
        self,
        vocab_size: int = 300,
        embed_dim: int = 256,
        num_heads: int = 8,
        num_layers: int = 6,
        max_moves: int = 100,  # 最大合法着法数
        dropout: float = 0.1
    ):
        super().__init__()
        
        self.tokenizer = FENTokenizer()
        self.embed_dim = embed_dim
        self.max_moves = max_moves
        
        # Token嵌入
        self.token_embedding = nn.Embedding(vocab_size, embed_dim)
        self.position_embedding = nn.Embedding(77, embed_dim)
        
        # Transformer Encoder
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=embed_dim,
            nhead=num_heads,
            dim_feedforward=embed_dim * 4,
            dropout=dropout,
            activation='gelu',
            batch_first=True
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        
        # Layer Norm
        self.layer_norm = nn.LayerNorm(embed_dim)
        
        # 输出头
        # 1. Embedding (用于相似检索)
        self.embedding_head = nn.Sequential(
            nn.Linear(embed_dim, embed_dim),
            nn.LayerNorm(embed_dim),
            nn.GELU(),
            nn.Linear(embed_dim, embed_dim)
        )
        
        # 2. Action Values (用于着法推荐)
        self.action_head = nn.Sequential(
            nn.Linear(embed_dim, embed_dim // 2),
            nn.LayerNorm(embed_dim // 2),
            nn.GELU(),
            nn.Linear(embed_dim // 2, max_moves)
        )
        
        # 3. Semantic Tags (用于LLM解释)
        self.semantic_head = nn.Sequential(
            nn.Linear(embed_dim, embed_dim // 2),
            nn.LayerNorm(embed_dim // 2),
            nn.GELU(),
            nn.Linear(embed_dim // 2, len(SEMANTIC_TAGS))
        )
        
        # 初始化
        self._init_weights()
    
    def _init_weights(self):
        """权重初始化"""
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                if module.bias is not None:
                    nn.init.zeros_(module.bias)
            elif isinstance(module, nn.Embedding):
                nn.init.normal_(module.weight, std=0.02)
    
    def forward(self, fen_tokens: torch.Tensor, attention_mask: Optional[torch.Tensor] = None) -> Dict[str, torch.Tensor]:
        """
        前向传播
        
        Args:
            fen_tokens: [batch_size, 77] token IDs
            attention_mask: [batch_size, 77] attention mask
            
        Returns:
            {
                'embedding': [batch_size, embed_dim],  # 归一化embedding
                'action_values': [batch_size, max_moves],  # 着法价值
                'semantic_tags': [batch_size, 32],  # 语义标签
                'hidden_states': [batch_size, 77, embed_dim]  # 中间表示
            }
        """
        batch_size, seq_len = fen_tokens.shape
        
        # Token嵌入 + 位置嵌入
        token_embeds = self.token_embedding(fen_tokens)
        positions = torch.arange(seq_len, device=fen_tokens.device).unsqueeze(0).expand(batch_size, -1)
        pos_embeds = self.position_embedding(positions)
        
        hidden_states = token_embeds + pos_embeds
        
        # Transformer编码
        if attention_mask is not None:
            # 将attention mask转换为Transformer格式
            attention_mask = attention_mask.float()
            attention_mask = attention_mask.masked_fill(attention_mask == 0, float('-inf'))
            attention_mask = attention_mask.masked_fill(attention_mask == 1, 0.0)
        
        hidden_states = self.transformer(hidden_states, src_key_padding_mask=attention_mask)
        
        # 全局池化 (取CLS token，这里用第一个token)
        pooled_output = hidden_states[:, 0, :]  # [batch_size, embed_dim]
        pooled_output = self.layer_norm(pooled_output)
        
        # 生成输出
        outputs = {}
        
        # 1. Embedding (用于相似检索)
        embedding = self.embedding_head(pooled_output)
        embedding = F.normalize(embedding, p=2, dim=-1)  # L2归一化
        outputs['embedding'] = embedding
        
        # 2. Action Values (用于着法推荐)
        action_values = self.action_head(pooled_output)
        outputs['action_values'] = action_values
        
        # 3. Semantic Tags (用于LLM解释)
        semantic_tags = self.semantic_head(pooled_output)
        semantic_tags = torch.sigmoid(semantic_tags)  # 多标签分类
        outputs['semantic_tags'] = semantic_tags
        
        # 4. 中间表示 (用于分析)
        outputs['hidden_states'] = hidden_states
        
        return outputs
    
    def encode_fen(self, fen: str) -> Dict[str, np.ndarray]:
        """单局面编码 (推理用)"""
        self.eval()
        
        # Token化
        tokens = self.tokenizer.tokenize(fen)
        tokens_tensor = torch.tensor([tokens], dtype=torch.long)
        
        # 前向传播
        with torch.no_grad():
            outputs = self.forward(tokens_tensor)
        
        # 转换为numpy
        results = {}
        for key, tensor in outputs.items():
            results[key] = tensor.cpu().numpy()
        
        return results


# 语义标签定义 (32种)
SEMANTIC_TAGS = [
    "opening", "middlegame", "endgame",           # 阶段
    "material_advantage", "material_disadvantage", # 子力
    "king_safety_red", "king_safety_black",        # 王安全
    "center_control", "side_control",              # 控制
    "attack_red", "attack_black",                  # 攻击
    "defense_red", "defense_black",              # 防守
    "threat_red", "threat_black",                # 威胁
    "hanging_piece", "pinned_piece",             # 战术
    "fork_opportunity", "skewer_opportunity",     # 战术机会
    "passed_pawn", "isolated_pawn",              # 兵形
    "open_file", "semi_open_file",                # 线路
    "active_rook", "passive_rook",                # 车活跃度
    "knight_outpost", "bishop_pair",              # 子力优势
    "tempo_advantage", "initiative",               # 节奏
    "space_advantage", "mobility_advantage",      # 空间/机动性
    "critical_position", "quiet_position"           # 局面性质
]


def get_semantic_description(tags: np.ndarray) -> List[str]:
    """将语义标签转换为描述"""
    active_tags = []
    for i, prob in enumerate(tags[0]):  # batch_size=1
        if prob > 0.5:  # 阈值
            active_tags.append(SEMANTIC_TAGS[i])
    return active_tags
