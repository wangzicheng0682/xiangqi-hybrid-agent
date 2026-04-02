"""
Pikafish 引擎封装 - UCI协议实现

Reference:
  - PRD: Sprint 2 / 引擎集成
  - TECH: Pikafish(UCI) / 工具优先原则
"""

import subprocess
import threading
import queue
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass

from .base import BaseEngine, EngineResult


@dataclass
class UCIInfo:
    score_cp: Optional[int] = None
    score_mate: Optional[int] = None
    depth: int = 0
    pv: List[str] = None
    
    def __post_init__(self):
        if self.pv is None:
            self.pv = []


class PikafishEngine(BaseEngine):
    PATHS = [
        Path(__file__).parent.parent.parent / "data" / "engine" / "pikafish-avx2.exe",
        Path(__file__).parent.parent.parent / "data" / "engine" / "pikafish.exe",
        Path(__file__).parent.parent.parent / "data" / "engine" / "pikafish-bmi2.exe",
    ]
    
    def __init__(self, engine_path: Optional[Path] = None, nnue_path: Optional[Path] = None):
        self.engine_path = self._find_engine(engine_path)
        self.nnue_path = nnue_path or (self.engine_path.parent / "pikafish.nnue")
        self._process: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()
        self._initialized = False
        self._output_queue = queue.Queue()
        self._reader_thread = None
    
    def _find_engine(self, engine_path: Optional[Path]) -> Path:
        if engine_path and engine_path.exists():
            return engine_path
        for p in self.PATHS:
            if p.exists():
                return p
        raise FileNotFoundError(
            f"Pikafish engine not found. Searched: {[str(p) for p in self.PATHS]}"
        )
    
    def _reader_loop(self):
        while self._process and self._process.poll() is None:
            try:
                line = self._process.stdout.readline()
                if line:
                    self._output_queue.put(line.strip())
            except Exception:
                break
    
    def _send_command(self, cmd: str) -> None:
        if not self._process or self._process.poll() is not None:
            raise RuntimeError("Engine process not running")
        self._process.stdin.write(cmd + "\n")
        self._process.stdin.flush()
    
    def _read_until(self, target: str, timeout: float = 30.0) -> List[str]:
        import time
        lines = []
        start = time.time()
        while time.time() - start < timeout:
            try:
                line = self._output_queue.get(timeout=0.1)
                lines.append(line)
                if target in line:
                    break
            except queue.Empty:
                if self._process and self._process.poll() is not None:
                    break
                continue
        return lines
    
    def start(self) -> None:
        with self._lock:
            if self._process and self._process.poll() is None:
                return
            self._process = subprocess.Popen(
                [str(self.engine_path)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                cwd=str(self.engine_path.parent),
            )
            self._output_queue = queue.Queue()
            self._reader_thread = threading.Thread(target=self._reader_loop, daemon=True)
            self._reader_thread.start()
            self._init_uci()
            self._initialized = True
    
    def _init_uci(self) -> None:
        self._send_command("uci")
        self._read_until("uciok")
        if self.nnue_path.exists():
            self._send_command(f"setoption name EvalFile value {self.nnue_path.name}")
        self._send_command("isready")
        self._read_until("readyok")
    
    def stop(self) -> None:
        with self._lock:
            if self._process:
                try:
                    self._send_command("quit")
                    self._process.wait(timeout=5)
                except Exception:
                    self._process.kill()
                finally:
                    self._process = None
                    self._initialized = False
                    self._reader_thread = None
    
    def _parse_info(self, lines: List[str]) -> UCIInfo:
        info = UCIInfo()
        for line in lines:
            if line.startswith("info depth"):
                parts = line.split()
                for i, p in enumerate(parts):
                    if p == "depth" and i + 1 < len(parts):
                        info.depth = int(parts[i + 1])
                    elif p == "score" and i + 2 < len(parts):
                        score_type = parts[i + 1]
                        score_val = int(parts[i + 2])
                        if score_type == "cp":
                            info.score_cp = score_val
                        elif score_type == "mate":
                            info.score_mate = score_val
                    elif p == "pv" and i + 1 < len(parts):
                        info.pv = parts[i + 1:]
        return info
    
    def analyze(self, fen: str, depth: int = 20) -> EngineResult:
        if not self._initialized:
            self.start()
        with self._lock:
            self._send_command(f"position fen {fen}")
            self._send_command("isready")
            self._read_until("readyok")
            self._send_command(f"go depth {depth}")
            lines = self._read_until("bestmove", timeout=120.0)
            info = self._parse_info(lines)
            bestmove = ""
            for line in lines:
                if line.startswith("bestmove"):
                    parts = line.split()
                    if len(parts) >= 2:
                        bestmove = parts[1]
                    break
            score = 0.0
            if info.score_cp is not None:
                score = info.score_cp / 100.0
            elif info.score_mate is not None:
                score = 100.0 if info.score_mate > 0 else -100.0
            return EngineResult(
                bestmove=bestmove,
                score=score,
                depth=info.depth,
                pv=info.pv,
            )

    def analyze_multipv(self, fen: str, depth: int = 18, num_pv: int = 3) -> List[EngineResult]:
        """
        多候选走法分析（MultiPV）

        Args:
            fen: FEN串
            depth: 搜索深度
            num_pv: 候选数量

        Returns:
            按评分排序的 EngineResult 列表
        """
        if not self._initialized:
            self.start()
        with self._lock:
            self._send_command(f"setoption name MultiPV value {num_pv}")
            self._send_command("isready")
            self._read_until("readyok")
            self._send_command(f"position fen {fen}")
            self._send_command("isready")
            self._read_until("readyok")
            self._send_command(f"go depth {depth}")
            lines = self._read_until("bestmove", timeout=120.0)

            # 恢复 MultiPV=1
            self._send_command(f"setoption name MultiPV value 1")
            self._send_command("isready")
            self._read_until("readyok")

            # 解析每条 PV 线——只取最终深度的结果
            pv_results: dict = {}  # multipv_index -> info
            for line in lines:
                if not line.startswith("info depth"):
                    continue
                parts = line.split()
                mpv_idx = 1
                cur_depth = 0
                score_cp = None
                score_mate = None
                pv_moves: List[str] = []

                for i, p in enumerate(parts):
                    if p == "depth" and i + 1 < len(parts):
                        cur_depth = int(parts[i + 1])
                    elif p == "multipv" and i + 1 < len(parts):
                        mpv_idx = int(parts[i + 1])
                    elif p == "score" and i + 2 < len(parts):
                        if parts[i + 1] == "cp":
                            score_cp = int(parts[i + 2])
                        elif parts[i + 1] == "mate":
                            score_mate = int(parts[i + 2])
                    elif p == "pv" and i + 1 < len(parts):
                        pv_moves = parts[i + 1:]

                # 更新：保留同一 PV 索引最高深度的结果
                if mpv_idx not in pv_results or cur_depth >= pv_results[mpv_idx]["depth"]:
                    pv_results[mpv_idx] = {
                        "depth": cur_depth,
                        "score_cp": score_cp,
                        "score_mate": score_mate,
                        "pv": pv_moves,
                    }

            results: List[EngineResult] = []
            for idx in sorted(pv_results.keys()):
                info = pv_results[idx]
                score = 0.0
                if info["score_cp"] is not None:
                    score = info["score_cp"] / 100.0
                elif info["score_mate"] is not None:
                    score = 100.0 if info["score_mate"] > 0 else -100.0
                bestmove = info["pv"][0] if info["pv"] else ""
                results.append(EngineResult(
                    bestmove=bestmove,
                    score=score,
                    depth=info["depth"],
                    pv=info["pv"],
                ))

            return results
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, *args):
        self.stop()
    
    def is_ready(self) -> bool:
        return self._initialized and self._process and self._process.poll() is None
