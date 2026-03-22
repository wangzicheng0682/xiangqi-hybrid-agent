"""
Pikafish批处理引擎
批量生成引擎真值（bestmove/score/PV）
"""

import subprocess
import json
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any
from pathlib import Path
import logging
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing as mp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class EngineTruth:
    """引擎真值"""
    fen: str                            # 局面FEN
    bestmove: Optional[str] = None      # 最佳走法（UCI格式）
    score_cp: Optional[int] = None      # 子力分差（厘兵）
    score_mate: Optional[int] = None    # 杀棋步数
    pv: List[str] = None                # 主变走子序列
    depth: int = 0                      # 搜索深度
    nodes: int = 0                      # 搜索节点数
    time_ms: int = 0                    # 推理时间（毫秒）
    
    def __post_init__(self):
        if self.pv is None:
            self.pv = []
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @property
    def is_mate(self) -> bool:
        """是否发现杀棋"""
        return self.score_mate is not None


class BatchEngineProcessor:
    """
    Pikafish批处理引擎
    
    多进程批量调用Pikafish引擎，生成引擎真值
    """
    
    def __init__(self, engine_path: Path, depth: int = 16, num_workers: int = None):
        """
        初始化批处理引擎
        
        Args:
            engine_path: Pikafish引擎路径
            depth: 搜索深度（默认16，平衡速度和精度）
            num_workers: 并行进程数（默认CPU核心数）
        """
        self.engine_path = Path(engine_path)
        self.depth = depth
        self.num_workers = num_workers or max(1, mp.cpu_count() - 1)
        
        if not self.engine_path.exists():
            raise FileNotFoundError(f"引擎文件不存在: {engine_path}")
    
    def analyze_single(self, fen: str) -> EngineTruth:
        """
        分析单个局面
        
        Args:
            fen: 局面FEN
            
        Returns:
            EngineTruth: 引擎分析结果
        """
        try:
            # 启动引擎进程
            process = subprocess.Popen(
                [str(self.engine_path)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
            
            # UCI协议通信
            process.stdin.write("uci\n")
            process.stdin.flush()
            
            # 等待uciok
            while True:
                line = process.stdout.readline().strip()
                if line == "uciok":
                    break
            
            # 设置局面
            process.stdin.write(f"position fen {fen}\n")
            process.stdin.flush()
            
            # 开始分析
            process.stdin.write(f"go depth {self.depth}\n")
            process.stdin.flush()
            
            # 解析输出
            result = EngineTruth(fen=fen)
            
            while True:
                line = process.stdout.readline().strip()
                
                if line.startswith("info"):
                    # 解析info信息
                    self._parse_info_line(line, result)
                
                elif line.startswith("bestmove"):
                    # 解析bestmove
                    parts = line.split()
                    if len(parts) >= 2:
                        result.bestmove = parts[1]
                    break
            
            # 退出引擎
            process.stdin.write("quit\n")
            process.stdin.flush()
            process.wait(timeout=5)
            
            return result
            
        except Exception as e:
            logger.error(f"分析局面失败 {fen}: {e}")
            return EngineTruth(fen=fen)
    
    def _parse_info_line(self, line: str, result: EngineTruth):
        """解析info输出行"""
        parts = line.split()
        
        i = 0
        while i < len(parts):
            part = parts[i]
            
            if part == "depth" and i + 1 < len(parts):
                result.depth = int(parts[i + 1])
                i += 2
            elif part == "score":
                if i + 2 < len(parts):
                    score_type = parts[i + 1]
                    score_value = int(parts[i + 2])
                    if score_type == "cp":
                        result.score_cp = score_value
                    elif score_type == "mate":
                        result.score_mate = score_value
                    i += 3
                else:
                    i += 1
            elif part == "pv":
                # 解析主变
                pv_moves = []
                j = i + 1
                while j < len(parts) and not parts[j].startswith("info"):
                    pv_moves.append(parts[j])
                    j += 1
                result.pv = pv_moves
                i = j
            elif part == "nodes" and i + 1 < len(parts):
                result.nodes = int(parts[i + 1])
                i += 2
            elif part == "time" and i + 1 < len(parts):
                result.time_ms = int(parts[i + 1])
                i += 2
            else:
                i += 1
    
    def analyze_batch(self, fens: List[str], show_progress: bool = True) -> List[EngineTruth]:
        """
        批量分析局面
        
        Args:
            fens: FEN列表
            show_progress: 是否显示进度
            
        Returns:
            List[EngineTruth]: 分析结果列表
        """
        logger.info(f"开始批量分析 {len(fens)} 个局面，深度={self.depth}，进程数={self.num_workers}")
        
        results = []
        completed = 0
        
        with ProcessPoolExecutor(max_workers=self.num_workers) as executor:
            # 提交所有任务
            future_to_fen = {
                executor.submit(self.analyze_single, fen): fen 
                for fen in fens
            }
            
            # 收集结果
            for future in as_completed(future_to_fen):
                fen = future_to_fen[future]
                try:
                    result = future.result(timeout=60)
                    results.append(result)
                except Exception as e:
                    logger.error(f"分析失败 {fen}: {e}")
                    results.append(EngineTruth(fen=fen))
                
                completed += 1
                if show_progress and completed % 100 == 0:
                    logger.info(f"进度: {completed}/{len(fens)} ({completed/len(fens)*100:.1f}%)")
        
        logger.info(f"批量分析完成: {len(results)} 个局面")
        return results
    
    def save_results(self, results: List[EngineTruth], output_path: Path):
        """
        保存分析结果到JSONL文件
        
        Args:
            results: 分析结果列表
            output_path: 输出文件路径
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for result in results:
                f.write(json.dumps(result.to_dict(), ensure_ascii=False) + '\n')
        
        logger.info(f"结果已保存: {output_path}")


def generate_engine_truth_dataset(
    fens: List[str],
    engine_path: Path,
    output_path: Path,
    depth: int = 16,
    num_workers: int = None
):
    """
    生成引擎真值数据集
    
    Args:
        fens: FEN列表
        engine_path: Pikafish引擎路径
        output_path: 输出文件路径
        depth: 搜索深度
        num_workers: 并行进程数
    """
    processor = BatchEngineProcessor(engine_path, depth, num_workers)
    results = processor.analyze_batch(fens)
    processor.save_results(results, output_path)


if __name__ == "__main__":
    # 测试
    engine_path = Path("data/engine/pikafish-avx2.exe")
    
    test_fens = [
        "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1",
        "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR b - - 0 1",
    ]
    
    processor = BatchEngineProcessor(engine_path, depth=10)
    
    for fen in test_fens:
        result = processor.analyze_single(fen)
        print(f"\nFEN: {fen}")
        print(f"  Bestmove: {result.bestmove}")
        print(f"  Score: {result.score_cp}")
        print(f"  PV: {result.pv[:5]}")
