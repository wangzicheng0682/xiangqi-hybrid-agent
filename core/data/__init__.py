"""
数据处理模块（阶段一：PGN数据预处理）

职责：
- PGN解析
- Pikafish批调用生成引擎真值
- 数据清洗与增强
- Parquet格式存储
"""

from .pgn_parser import PGNParser, GameRecord, PositionRecord
from .batch_engine import BatchEngineProcessor, EngineTruth
from .augmentation import augment_position, normalize_perspective, mirror_horizontal

__all__ = [
    # PGN解析
    'PGNParser',
    'GameRecord',
    'PositionRecord',
    # 批处理引擎
    'BatchEngineProcessor',
    'EngineTruth',
    # 数据增强
    'augment_position',
    'normalize_perspective',
    'mirror_horizontal',
]
