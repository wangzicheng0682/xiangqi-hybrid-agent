"""
59M 模型验证实验

实验内容：
1. 训练集 vs 验证集损失对比
2. 1000 局面分数校准测试
3. 相似局面检索测试
4. 冻结骨干 + 语义头探测
"""

import torch
import torch.nn as nn
import json
import random
import subprocess
import time
import numpy as np
from pathlib import Path
from tqdm import tqdm
from collections import defaultdict

import sys
sys.path.insert(0, '.')

from core.encoder.position_encoder_50m import PositionEncoder50M, FENTokenizer, SEMANTIC_TAGS


class ModelValidator:
    """模型验证器"""
    
    def __init__(self, model_path: str, data_path: str, engine_path: str = "data/engine/pikafish-avx2.exe"):
        self.model_path = model_path
        self.data_path = data_path
        self.engine_path = engine_path
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.tokenizer = FENTokenizer()
        
        print(f"设备: {self.device}")
        
        self._load_model()
        self._load_data()
    
    def _load_model(self):
        print(f"\n加载模型: {self.model_path}")
        self.model = PositionEncoder50M().to(self.device)
        
        checkpoint = torch.load(self.model_path, map_location=self.device)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.model.eval()
        
        print(f"模型 epoch: {checkpoint.get('epoch', 'N/A')}")
        print(f"训练损失: {checkpoint.get('loss', 'N/A'):.4f}")
    
    def _load_data(self):
        print(f"\n加载数据: {self.data_path}")
        
        with open(self.data_path, 'r') as f:
            self.all_data = [json.loads(line) for line in tqdm(f, desc="读取数据")]
        
        print(f"总数据量: {len(self.all_data):,}")
        
        random.shuffle(self.all_data)
        
        split_idx = int(len(self.all_data) * 0.9)
        self.train_data = self.all_data[:split_idx]
        self.val_data = self.all_data[split_idx:]
        
        print(f"训练集: {len(self.train_data):,}")
        print(f"验证集: {len(self.val_data):,}")
    
    def experiment_1_loss_comparison(self, sample_size: int = 10000):
        """实验1：训练集 vs 验证集损失对比"""
        print("\n" + "=" * 60)
        print("实验1：训练集 vs 验证集损失对比")
        print("=" * 60)
        
        loss_fn = nn.MSELoss()
        
        def compute_loss(data, name):
            losses = []
            sample = random.sample(data, min(sample_size, len(data)))
            
            self.model.eval()
            with torch.no_grad():
                for item in tqdm(sample, desc=f"计算{name}损失"):
                    tokens = self.tokenizer.tokenize(item['fen'])
                    input_ids = torch.tensor([tokens], dtype=torch.long).to(self.device)
                    
                    outputs = self.model(input_ids)
                    
                    pred_state = outputs['state_value'].item()
                    true_state = item.get('state_value', 0.0) or 0.0
                    
                    loss = (pred_state - true_state) ** 2
                    losses.append(loss)
            
            return np.mean(losses), np.std(losses)
        
        train_loss, train_std = compute_loss(self.train_data, "训练集")
        val_loss, val_std = compute_loss(self.val_data, "验证集")
        
        print(f"\n结果:")
        print(f"  训练集损失: {train_loss:.4f} ± {train_std:.4f}")
        print(f"  验证集损失: {val_loss:.4f} ± {val_std:.4f}")
        print(f"  比值 (val/train): {val_loss/train_loss:.2f}")
        
        if val_loss / train_loss < 1.2:
            verdict = "✅ 正常，模型学到了通用模式"
        elif val_loss / train_loss < 1.5:
            verdict = "⚠️ 轻微过拟合"
        else:
            verdict = "❌ 严重过拟合"
        
        print(f"\n判断: {verdict}")
        
        return {
            'train_loss': train_loss,
            'val_loss': val_loss,
            'ratio': val_loss / train_loss,
            'verdict': verdict
        }
    
    def experiment_2_score_calibration(self, sample_size: int = 100):
        """实验2：分数校准测试"""
        print("\n" + "=" * 60)
        print("实验2：分数校准测试（需要引擎）")
        print("=" * 60)
        
        sample = random.sample(self.val_data, min(sample_size, len(self.val_data)))
        
        errors = []
        results = []
        
        proc = subprocess.Popen(
            [self.engine_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1
        )
        
        proc.stdin.write("uci\n")
        proc.stdin.flush()
        while "uciok" not in proc.stdout.readline():
            pass
        
        for item in tqdm(sample, desc="校准测试"):
            fen = item['fen']
            
            tokens = self.tokenizer.tokenize(fen)
            input_ids = torch.tensor([tokens], dtype=torch.long).to(self.device)
            
            with torch.no_grad():
                outputs = self.model(input_ids)
                pred_score = outputs['state_value'].item() * 100
            
            proc.stdin.write(f"position fen {fen}\ngo depth 12\n")
            proc.stdin.flush()
            
            engine_score = 0
            while True:
                line = proc.stdout.readline()
                if 'score cp' in line and 'bound' not in line:
                    try:
                        engine_score = int(line.split('score cp')[1].split()[0]) / 100
                    except:
                        pass
                if 'bestmove' in line:
                    break
            
            error = abs(pred_score - engine_score)
            errors.append(error)
            
            results.append({
                'fen': fen,
                'pred': pred_score,
                'engine': engine_score,
                'error': error
            })
        
        proc.kill()
        
        mae = np.mean(errors)
        print(f"\n结果:")
        print(f"  样本数: {len(errors)}")
        print(f"  MAE: {mae:.2f} 分")
        print(f"  最大误差: {max(errors):.2f} 分")
        print(f"  误差 < 30分: {sum(1 for e in errors if e < 30) / len(errors) * 100:.1f}%")
        print(f"  误差 < 50分: {sum(1 for e in errors if e < 50) / len(errors) * 100:.1f}%")
        
        if mae < 30:
            verdict = "✅ 可用"
        elif mae < 50:
            verdict = "⚠️ 勉强可用"
        else:
            verdict = "❌ 不可靠"
        
        print(f"\n判断: {verdict}")
        
        return {
            'mae': mae,
            'max_error': max(errors),
            'verdict': verdict,
            'samples': results[:10]
        }
    
    def experiment_3_similarity_retrieval(self, sample_size: int = 50):
        """实验3：相似局面检索测试"""
        print("\n" + "=" * 60)
        print("实验3：相似局面检索测试")
        print("=" * 60)
        
        test_positions = random.sample(self.val_data, sample_size)
        
        print(f"生成所有局面的 embedding...")
        all_embeddings = []
        all_fens = []
        
        self.model.eval()
        with torch.no_grad():
            for item in tqdm(self.val_data[:50000], desc="生成embedding"):
                tokens = self.tokenizer.tokenize(item['fen'])
                input_ids = torch.tensor([tokens], dtype=torch.long).to(self.device)
                
                outputs = self.model(input_ids)
                all_embeddings.append(outputs['embedding'].cpu().numpy())
                all_fens.append(item['fen'])
        
        all_embeddings = np.vstack(all_embeddings)
        
        correct = 0
        total = 0
        
        print(f"\n检索测试...")
        for item in tqdm(test_positions, desc="检索"):
            tokens = self.tokenizer.tokenize(item['fen'])
            input_ids = torch.tensor([tokens], dtype=torch.long).to(self.device)
            
            with torch.no_grad():
                query_emb = self.model(input_ids)['embedding'].cpu().numpy()
            
            similarities = np.dot(all_embeddings, query_emb.T).flatten()
            top5_idx = np.argsort(similarities)[-6:-1][::-1]
            
            query_phase = self._get_phase(item['fen'])
            match_count = 0
            for idx in top5_idx:
                if self._get_phase(all_fens[idx]) == query_phase:
                    match_count += 1
            
            if match_count >= 3:
                correct += 1
            total += 1
        
        accuracy = correct / total * 100
        print(f"\n结果:")
        print(f"  阶段匹配准确率: {accuracy:.1f}%")
        
        if accuracy > 80:
            verdict = "✅ Embedding 学到了局面结构"
        elif accuracy > 50:
            verdict = "⚠️ Embedding 有一定效果"
        else:
            verdict = "❌ Embedding 没学到东西"
        
        print(f"\n判断: {verdict}")
        
        return {
            'accuracy': accuracy,
            'verdict': verdict
        }
    
    def experiment_4_semantic_probe(self):
        """实验4：冻结骨干 + 语义头探测"""
        print("\n" + "=" * 60)
        print("实验4：语义头探测实验")
        print("=" * 60)
        
        print("生成语义标签...")
        labeled_data = []
        
        for item in tqdm(self.train_data[:50000], desc="生成标签"):
            fen = item['fen']
            score = item.get('state_value', 0) or 0
            
            phase = self._get_phase(fen)
            
            if score > 0.3:
                initiative = 0
            elif score < -0.3:
                initiative = 2
            else:
                initiative = 1
            
            abs_score = abs(score)
            if abs_score > 0.8:
                risk = 2
            elif abs_score > 0.3:
                risk = 1
            else:
                risk = 0
            
            labeled_data.append({
                'fen': fen,
                'phase': phase,
                'initiative': initiative,
                'risk': risk
            })
        
        for param in self.model.parameters():
            param.requires_grad = False
        
        self.model.semantic_head[-1].weight.requires_grad = True
        self.model.semantic_head[-1].bias.requires_grad = True
        
        probe_head = nn.Linear(768, 5).to(self.device)
        optimizer = torch.optim.Adam(probe_head.parameters(), lr=1e-3)
        loss_fn = nn.CrossEntropyLoss()
        
        print(f"\n训练探测头...")
        
        for epoch in range(5):
            random.shuffle(labeled_data)
            total_loss = 0
            correct = 0
            total = 0
            
            for i in range(0, len(labeled_data) - 32, 32):
                batch = labeled_data[i:i+32]
                
                input_ids = torch.tensor(
                    [self.tokenizer.tokenize(item['fen']) for item in batch],
                    dtype=torch.long
                ).to(self.device)
                
                labels = torch.tensor([item['phase'] for item in batch], dtype=torch.long).to(self.device)
                
                with torch.no_grad():
                    hidden = self.model(input_ids)['hidden_states'].mean(dim=1)
                
                logits = probe_head(hidden)
                loss = loss_fn(logits, labels)
                
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                
                total_loss += loss.item()
                pred = logits.argmax(dim=1)
                correct += (pred == labels).sum().item()
                total += len(labels)
            
            acc = correct / total * 100
            print(f"  Epoch {epoch+1}: Loss={total_loss:.4f}, Acc={acc:.1f}%")
        
        val_correct = 0
        val_total = 0
        
        val_labeled = []
        for item in self.val_data[:5000]:
            fen = item['fen']
            phase = self._get_phase(fen)
            val_labeled.append({'fen': fen, 'phase': phase})
        
        with torch.no_grad():
            for i in range(0, len(val_labeled) - 32, 32):
                batch = val_labeled[i:i+32]
                
                input_ids = torch.tensor(
                    [self.tokenizer.tokenize(item['fen']) for item in batch],
                    dtype=torch.long
                ).to(self.device)
                
                labels = torch.tensor([item['phase'] for item in batch], dtype=torch.long).to(self.device)
                
                hidden = self.model(input_ids)['hidden_states'].mean(dim=1)
                logits = probe_head(hidden)
                pred = logits.argmax(dim=1)
                
                val_correct += (pred == labels).sum().item()
                val_total += len(labels)
        
        val_acc = val_correct / val_total * 100
        
        print(f"\n结果:")
        print(f"  验证集阶段分类准确率: {val_acc:.1f}%")
        
        if val_acc > 70:
            verdict = "✅ 模型内部有棋理知识"
        elif val_acc > 50:
            verdict = "⚠️ 模型内部有部分棋理知识"
        else:
            verdict = "❌ 模型没学到棋理"
        
        print(f"\n判断: {verdict}")
        
        for param in self.model.parameters():
            param.requires_grad = True
        
        return {
            'val_accuracy': val_acc,
            'verdict': verdict
        }
    
    def _get_phase(self, fen: str) -> int:
        board = fen.split()[0]
        count = sum(1 for c in board if c.isalpha())
        if count >= 26:
            return 0
        elif count >= 14:
            return 1
        else:
            return 2
    
    def run_all_experiments(self):
        """运行所有实验"""
        print("=" * 60)
        print("59M 模型验证实验")
        print("=" * 60)
        
        results = {}
        
        results['exp1_loss'] = self.experiment_1_loss_comparison()
        results['exp2_calibration'] = self.experiment_2_score_calibration()
        results['exp3_similarity'] = self.experiment_3_similarity_retrieval()
        results['exp4_probe'] = self.experiment_4_semantic_probe()
        
        print("\n" + "=" * 60)
        print("验证总结")
        print("=" * 60)
        
        print(f"\n实验1 损失对比: {results['exp1_loss']['verdict']}")
        print(f"实验2 分数校准: {results['exp2_calibration']['verdict']}")
        print(f"实验3 相似检索: {results['exp3_similarity']['verdict']}")
        print(f"实验4 语义探测: {results['exp4_probe']['verdict']}")
        
        return results


if __name__ == "__main__":
    validator = ModelValidator(
        model_path="data/models/position_encoder_50m_final.pt",
        data_path="data/training/position_data_1m.jsonl"
    )
    
    results = validator.run_all_experiments()
