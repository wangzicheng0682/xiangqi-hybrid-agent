"""
引擎连接池 - 避免每次请求创建新的Pikafish实例

PikafishEngine启动涉及进程创建和初始化，单例复用可节省约200ms/请求。
使用 analyze() 方法代替直接操作引擎，确保并发安全。
"""

import threading
from typing import Optional


class EnginePool:
    """Pikafish引擎单例池（线程安全）"""

    _instance: Optional["EnginePool"] = None
    _lock = threading.Lock()

    def __init__(self):
        self._engine = None
        self._engine_lock = threading.Lock()
        self._analyze_lock = threading.Lock()

    @classmethod
    def get_pool(cls) -> "EnginePool":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def get_engine(self):
        """获取引擎实例（线程安全，延迟初始化）"""
        if self._engine is None or not self._is_engine_alive(self._engine):
            with self._engine_lock:
                if self._engine is not None and not self._is_engine_alive(self._engine):
                    try:
                        self._engine.stop()
                    except Exception:
                        pass
                    self._engine = None
                if self._engine is None:
                    from core.engine.pikafish_engine import PikafishEngine
                    self._engine = PikafishEngine()
        return self._engine

    def _is_engine_alive(self, engine) -> bool:
        process = getattr(engine, "_process", None)
        if process is None:
            return False
        try:
            return process.poll() is None
        except Exception:
            return False

    def analyze(self, fen: str, depth: int = 20):
        """线程安全的分析接口，自动串行化并发请求"""
        with self._analyze_lock:
            for attempt in range(2):
                engine = self.get_engine()
                try:
                    return engine.analyze(fen, depth=depth)
                except RuntimeError as exc:
                    if "Engine process not running" not in str(exc) or attempt == 1:
                        raise
                    self.release()
            raise RuntimeError("Engine process not running")

    def analyze_multipv(self, fen: str, depth: int = 18, num_pv: int = 3):
        """线程安全的多候选走法分析"""
        with self._analyze_lock:
            for attempt in range(2):
                engine = self.get_engine()
                try:
                    return engine.analyze_multipv(fen, depth=depth, num_pv=num_pv)
                except RuntimeError as exc:
                    if "Engine process not running" not in str(exc) or attempt == 1:
                        raise
                    self.release()
            raise RuntimeError("Engine process not running")

    def release(self):
        """释放引擎实例（仅在服务关闭时调用）"""
        with self._engine_lock:
            if self._engine is not None:
                try:
                    self._engine.stop()
                except Exception:
                    pass
                self._engine = None


def get_engine():
    """便捷函数：获取引擎单例"""
    return EnginePool.get_pool().get_engine()


def engine_analyze(fen: str, depth: int = 20):
    """便捷函数：线程安全分析"""
    return EnginePool.get_pool().analyze(fen, depth=depth)
