"""
候选语义骨干模型 - 快速验证报告

48小时内必须交付的验证结果：
1. 训练损失 vs 验证损失
2. 1000 局面分数校准 MAE
3. 相似局面检索人工抽检结论
4. 语义头探测实验结果
"""

import torch
import torch.nn as nn
import json
import random
import subprocess
import numpy as np
from pathlib import Path
from tqdm import tqdm
from datetime import datetime

import sys
sys.path.insert(0, '.')

from core.encoder.position_encoder_50m import PositionEncoder50M, FENTokenizer


def run_validation():
    print("=" * 70)
    print("候选语义骨干模型 - 验证报告")
    print(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    MODEL_PATH = "data/models/position_encoder_50m_final.pt"
    DATA_PATH = "data/training/position_data_1m.jsonl"
    ENGINE_PATH = "data/engine/pikafish-avx2.exe"
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"\n设备: {device}")
    
    print(f"\n[1/5] 加载模型...")
    model = PositionEncoder50M().to(device)
    checkpoint = torch.load(MODEL_PATH, map_location=device)
    model.load_state_dict(checkpoint['model_state_dict'])
    model.eval()
    
    train_loss = checkpoint.get('loss', 0)
    epoch = checkpoint.get('epoch', 0)
    print(f"  模型 epoch: {epoch + 1}")
    print(f"  训练损失: {train_loss:.4f}")
    
    print(f"\n[2/5] 加载数据并分割验证集...")
    with open(DATA_PATH, 'r') as f:
        all_data = [json.loads(line) for line in tqdm(f, desc="读取数据")]
    
    random.seed(42)
    random.shuffle(all_data)
    
    split_idx = int(len(all_data) * 0.9)
    train_data = all_data[:split_idx]
    val_data = all_data[split_idx:]
    
    print(f"  训练集: {len(train_data):,}")
    print(f"  验证集: {len(val_data):,}")
    
    tokenizer = FENTokenizer()
    
    print(f"\n{'='*70}")
    print("实验1：训练集 vs 验证集损失对比")
    print("="*70)
    
    def compute_loss(data, name, sample_size=10000):
        losses = []
        sample = random.sample(data, min(sample_size, len(data)))
        
        with torch.no_grad():
            for item in tqdm(sample, desc=f"计算{name}损失"):
                tokens = tokenizer.tokenize(item['fen'])
                input_ids = torch.tensor([tokens], dtype=torch.long).to(device)
                
                outputs = model(input_ids)
                pred_state = outputs['state_value'].item()
                true_state = item.get('state_value', 0.0) or 0.0
                
                loss = (pred_state - true_state) ** 2
                losses.append(loss)
        
        return np.mean(losses), np.std(losses)
    
    train_loss_new, train_std = compute_loss(train_data, "训练集")
    val_loss, val_std = compute_loss(val_data, "验证集")
    
    ratio = val_loss / train_loss_new if train_loss_new > 0 else 999
    
    print(f"\n结果:")
    print(f"  训练集损失: {train_loss_new:.4f} ± {train_std:.4f}")
    print(f"  验证集损失: {val_loss:.4f} ± {val_std:.4f}")
    print(f"  比值 (val/train): {ratio:.2f}")
    
    if ratio < 1.2:
        exp1_verdict = "✅ 正常，模型学到了通用模式"
    elif ratio < 1.5:
        exp1_verdict = "⚠️ 轻微过拟合"
    else:
        exp1_verdict = "❌ 严重过拟合"
    
    print(f"\n判断: {exp1_verdict}")
    
    print(f"\n{'='*70}")
    print("实验2：分数校准测试（需要引擎）")
    print("="*70)
    
    sample_size = 100
    sample = random.sample(val_data, min(sample_size, len(val_data)))
    
    proc = subprocess.Popen(
        [ENGINE_PATH],
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
    
    errors = []
    results = []
    
    for item in tqdm(sample, desc="校准测试"):
        fen = item['fen']
        
        tokens = tokenizer.tokenize(fen)
        input_ids = torch.tensor([tokens], dtype=torch.long).to(device)
        
        with torch.no_grad():
            outputs = model(input_ids)
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
        results.append({'fen': fen, 'pred': pred_score, 'engine': engine_score, 'error': error})
    
    proc.kill()
    
    mae = np.mean(errors)
    max_error = max(errors)
    pct_under_30 = sum(1 for e in errors if e < 30) / len(errors) * 100
    pct_under_50 = sum(1 for e in errors if e < 50) / len(errors) * 100
    
    print(f"\n结果:")
    print(f"  样本数: {len(errors)}")
    print(f"  MAE: {mae:.2f} 分")
    print(f"  最大误差: {max_error:.2f} 分")
    print(f"  误差 < 30分: {pct_under_30:.1f}%")
    print(f"  误差 < 50分: {pct_under_50:.1f}%")
    
    if mae < 30:
        exp2_verdict = "✅ 可用"
    elif mae < 50:
        exp2_verdict = "⚠️ 勉强可用"
    else:
        exp2_verdict = "❌ 不可靠"
    
    print(f"\n判断: {exp2_verdict}")
    
    print(f"\n{'='*70}")
    print("实验3：相似局面检索测试")
    print("="*70)
    
    print("生成 embedding 数据库...")
    all_embeddings = []
    all_fens = []
    
    with torch.no_grad():
        for item in tqdm(val_data[:50000], desc="生成embedding"):
            tokens = tokenizer.tokenize(item['fen'])
            input_ids = torch.tensor([tokens], dtype=torch.long).to(device)
            
            outputs = model(input_ids)
            all_embeddings.append(outputs['embedding'].cpu().numpy().flatten())
            all_fens.append(item['fen'])
    
    all_embeddings = np.vstack(all_embeddings)
    
    def get_phase(fen: str) -> str:
        board = fen.split()[0]
        count = sum(1 for c in board if c.isalpha())
        if count >= 26:
            return 'opening'
        elif count >= 14:
            return 'middlegame'
        else:
            return 'endgame'
    
    test_positions = random.sample(val_data, 50)
    correct = 0
    total = 0
    
    for item in tqdm(test_positions, desc="检索测试"):
        tokens = tokenizer.tokenize(item['fen'])
        input_ids = torch.tensor([tokens], dtype=torch.long).to(device)
        
        with torch.no_grad():
            query_emb = model(input_ids)['embedding'].cpu().numpy().flatten()
        
        similarities = np.dot(all_embeddings, query_emb)
        top5_idx = np.argsort(similarities)[-6:-1][::-1]
        
        query_phase = get_phase(item['fen'])
        match_count = sum(1 for idx in top5_idx if get_phase(all_fens[idx]) == query_phase)
        
        if match_count >= 3:
            correct += 1
        total += 1
    
    accuracy = correct / total * 100
    
    print(f"\n结果:")
    print(f"  阶段匹配准确率: {accuracy:.1f}%")
    
    if accuracy > 80:
        exp3_verdict = "✅ Embedding 学到了局面结构"
    elif accuracy > 50:
        exp3_verdict = "⚠️ Embedding 有一定效果"
    else:
        exp3_verdict = "❌ Embedding 没学到东西"
    
    print(f"\n判断: {exp3_verdict}")
    
    print(f"\n{'='*70}")
    print("实验4：语义头探测实验")
    print("="*70)
    
    print("生成语义标签...")
    labeled_data = []
    
    for item in tqdm(train_data[:50000], desc="生成标签"):
        fen = item['fen']
        score = item.get('state_value', 0) or 0
        
        phase = 0 if sum(1 for c in fen.split()[0] if c.isalpha()) >= 26 else (1 if sum(1 for c in fen.split()[0] if c.isalpha()) >= 14 else 2)
        
        labeled_data.append({
            'fen': fen,
            'phase': phase
        })
    
    for param in model.parameters():
        param.requires_grad = False
    
    probe_head = nn.Linear(768, 3).to(device)
    optimizer = torch.optim.Adam(probe_head.parameters(), lr=1e-3)
    loss_fn = nn.CrossEntropyLoss()
    
    print("训练探测头...")
    
    for epoch in range(5):
        random.shuffle(labeled_data)
        total_loss = 0
        correct = 0
        total = 0
        
        for i in range(0, len(labeled_data) - 32, 32):
            batch = labeled_data[i:i+32]
            
            input_ids = torch.tensor(
                [tokenizer.tokenize(item['fen']) for item in batch],
                dtype=torch.long
            ).to(device)
            
            labels = torch.tensor([item['phase'] for item in batch], dtype=torch.long).to(device)
            
            with torch.no_grad():
                hidden = model(input_ids)['hidden_states'].mean(dim=1)
            
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
    
    val_labeled = [{'fen': item['fen'], 'phase': 0 if sum(1 for c in item['fen'].split()[0] if c.isalpha()) >= 26 else (1 if sum(1 for c in item['fen'].split()[0] if c.isalpha()) >= 14 else 2)} for item in val_data[:5000]]
    
    val_correct = 0
    val_total = 0
    
    with torch.no_grad():
        for i in range(0, len(val_labeled) - 32, 32):
            batch = val_labeled[i:i+32]
            
            input_ids = torch.tensor(
                [tokenizer.tokenize(item['fen']) for item in batch],
                dtype=torch.long
            ).to(device)
            
            labels = torch.tensor([item['phase'] for item in batch], dtype=torch.long).to(device)
            
            hidden = model(input_ids)['hidden_states'].mean(dim=1)
            logits = probe_head(hidden)
            pred = logits.argmax(dim=1)
            
            val_correct += (pred == labels).sum().item()
            val_total += len(labels)
    
    val_acc = val_correct / val_total * 100
    
    print(f"\n结果:")
    print(f"  验证集阶段分类准确率: {val_acc:.1f}%")
    
    if val_acc > 70:
        exp4_verdict = "✅ 模型内部有棋理知识"
    elif val_acc > 50:
        exp4_verdict = "⚠️ 模型内部有部分棋理知识"
    else:
        exp4_verdict = "❌ 模型没学到棋理"
    
    print(f"\n判断: {exp4_verdict}")
    
    for param in model.parameters():
        param.requires_grad = True
    
    print(f"\n{'='*70}")
    print("验证总结")
    print("="*70)
    
    print(f"\n实验1 损失对比: {exp1_verdict}")
    print(f"  训练损失: {train_loss_new:.4f}, 验证损失: {val_loss:.4f}, 比值: {ratio:.2f}")
    
    print(f"\n实验2 分数校准: {exp2_verdict}")
    print(f"  MAE: {mae:.2f}分, <30分: {pct_under_30:.1f}%, <50分: {pct_under_50:.1f}%")
    
    print(f"\n实验3 相似检索: {exp3_verdict}")
    print(f"  阶段匹配准确率: {accuracy:.1f}%")
    
    print(f"\n实验4 语义探测: {exp4_verdict}")
    print(f"  验证集准确率: {val_acc:.1f}%")
    
    print(f"\n{'='*70}")
    print("结论")
    print("="*70)
    
    passed = sum(1 for v in [exp1_verdict, exp2_verdict, exp3_verdict, exp4_verdict] if '✅' in v)
    partial = sum(1 for v in [exp1_verdict, exp2_verdict, exp3_verdict, exp4_verdict] if '⚠️' in v)
    failed = sum(1 for v in [exp1_verdict, exp2_verdict, exp3_verdict, exp4_verdict] if '❌' in v)
    
    print(f"\n通过: {passed}/4, 部分通过: {partial}/4, 未通过: {failed}/4")
    
    if passed >= 3:
        overall = "✅ 候选语义骨干模型基本可用，可作为中间层组件"
    elif passed + partial >= 3:
        overall = "⚠️ 模型有潜力，但需要进一步优化"
    else:
        overall = "❌ 模型当前状态不适合作为骨干，需要重新训练或调整"
    
    print(f"\n总评: {overall}")
    
    report = {
        'timestamp': datetime.now().isoformat(),
        'model_epoch': epoch + 1,
        'train_loss': train_loss_new,
        'val_loss': val_loss,
        'loss_ratio': ratio,
        'mae': mae,
        'retrieval_accuracy': accuracy,
        'probe_accuracy': val_acc,
        'verdicts': {
            'loss_comparison': exp1_verdict,
            'score_calibration': exp2_verdict,
            'similarity_retrieval': exp3_verdict,
            'semantic_probe': exp4_verdict
        },
        'overall': overall
    }
    
    with open('docs/validation_report.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n报告已保存到: docs/validation_report.json")
    
    return report


if __name__ == "__main__":
    run_validation()
