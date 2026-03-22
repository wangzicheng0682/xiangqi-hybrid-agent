"""
棋盘状态编码器
将棋盘文本编码为向量,用于相似度检索
"""
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from abc import ABC, abstractmethod
import numpy as np
import hashlib
import logging
import pickle
import os

logger = logging.getLogger(__name__)


@dataclass
class EncoderConfig:
    """编码器配置"""
    encoder_type: str = "tfidf"         # 编码器类型: tfidf/hash/llm/fen
    vector_dim: int = 128               # 向量维度
    cache_embeddings: bool = True       # 是否缓存编码结果
    cache_dir: str = "data/embeddings"  # 缓存目录
    
    # TF-IDF参数
    max_features: int = 1000            # 最大特征数
    ngram_range: tuple = (1, 2)         # n-gram范围
    
    # 哈希编码参数
    hash_size: int = 128                # 哈希向量大小


class BaseEncoder(ABC):
    """编码器抽象基类"""
    
    def __init__(self, config: EncoderConfig):
        """
        初始化编码器
        
        Args:
            config: 编码器配置
        """
        self.config = config
        self.cache: Dict[str, np.ndarray] = {}
        
        if config.cache_embeddings:
            os.makedirs(config.cache_dir, exist_ok=True)
    
    @abstractmethod
    def encode(self, text: str) -> np.ndarray:
        """
        编码文本为向量
        
        Args:
            text: 输入文本
            
        Returns:
            向量表示
        """
        pass
    
    @abstractmethod
    def encode_batch(self, texts: List[str]) -> np.ndarray:
        """
        批量编码
        
        Args:
            texts: 文本列表
            
        Returns:
            向量矩阵(N x D)
        """
        pass
    
    def _get_cache_key(self, text: str) -> str:
        """生成缓存键"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    def _load_from_cache(self, cache_key: str) -> Optional[np.ndarray]:
        """从缓存加载"""
        if not self.config.cache_embeddings:
            return None
        
        # 内存缓存
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # 磁盘缓存
        cache_path = os.path.join(self.config.cache_dir, f"{cache_key}.npy")
        if os.path.exists(cache_path):
            try:
                vector = np.load(cache_path)
                self.cache[cache_key] = vector
                return vector
            except Exception as e:
                logger.warning(f"加载缓存失败: {e}")
        
        return None
    
    def _save_to_cache(self, cache_key: str, vector: np.ndarray):
        """保存到缓存"""
        if not self.config.cache_embeddings:
            return
        
        # 内存缓存
        self.cache[cache_key] = vector
        
        # 磁盘缓存
        cache_path = os.path.join(self.config.cache_dir, f"{cache_key}.npy")
        try:
            np.save(cache_path, vector)
        except Exception as e:
            logger.warning(f"保存缓存失败: {e}")


class TFIDFEncoder(BaseEncoder):
    """
    TF-IDF编码器
    使用scikit-learn的TfidfVectorizer
    """
    
    def __init__(self, config: EncoderConfig):
        super().__init__(config)
        
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.decomposition import TruncatedSVD
            
            self.vectorizer = TfidfVectorizer(
                max_features=config.max_features,
                ngram_range=config.ngram_range,
                strip_accents='unicode',
                lowercase=True
            )
            
            self.svd = TruncatedSVD(
                n_components=min(config.vector_dim, config.max_features)
            )
            
            self.fitted = False
            
        except ImportError:
            raise ImportError(
                "TF-IDF编码器需要scikit-learn库: pip install scikit-learn"
            )
        
        logger.info(f"TF-IDF编码器初始化: 维度={config.vector_dim}")
    
    def fit(self, texts: List[str]):
        """
        训练编码器
        
        Args:
            texts: 训练文本列表
        """
        logger.info(f"训练TF-IDF编码器: {len(texts)} 个样本")
        
        # TF-IDF转换
        tfidf_matrix = self.vectorizer.fit_transform(texts)
        
        # SVD降维
        self.svd.fit(tfidf_matrix)
        
        self.fitted = True
        logger.info("TF-IDF编码器训练完成")
    
    def encode(self, text: str) -> np.ndarray:
        """编码单个文本"""
        cache_key = self._get_cache_key(text)
        
        # 检查缓存
        cached = self._load_from_cache(cache_key)
        if cached is not None:
            return cached
        
        if not self.fitted:
            logger.warning("编码器未训练,返回零向量")
            return np.zeros(self.config.vector_dim)
        
        # TF-IDF + SVD
        tfidf = self.vectorizer.transform([text])
        vector = self.svd.transform(tfidf)[0]
        
        # 填充或截断到目标维度
        if len(vector) < self.config.vector_dim:
            vector = np.pad(vector, (0, self.config.vector_dim - len(vector)))
        else:
            vector = vector[:self.config.vector_dim]
        
        # 归一化
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        
        # 保存缓存
        self._save_to_cache(cache_key, vector)
        
        return vector
    
    def encode_batch(self, texts: List[str]) -> np.ndarray:
        """批量编码"""
        if not self.fitted:
            logger.warning("编码器未训练,返回零矩阵")
            return np.zeros((len(texts), self.config.vector_dim))
        
        # TF-IDF + SVD
        tfidf = self.vectorizer.transform(texts)
        vectors = self.svd.transform(tfidf)
        
        # 填充或截断
        result = np.zeros((len(texts), self.config.vector_dim))
        for i, vec in enumerate(vectors):
            if len(vec) < self.config.vector_dim:
                result[i, :len(vec)] = vec
            else:
                result[i] = vec[:self.config.vector_dim]
        
        # 归一化
        norms = np.linalg.norm(result, axis=1, keepdims=True)
        norms[norms == 0] = 1
        result = result / norms
        
        return result


class HashEncoder(BaseEncoder):
    """
    哈希编码器
    基于特征哈希的简单编码方案
    """
    
    def __init__(self, config: EncoderConfig):
        super().__init__(config)
        logger.info(f"哈希编码器初始化: 维度={config.vector_dim}")
    
    def encode(self, text: str) -> np.ndarray:
        """编码单个文本"""
        cache_key = self._get_cache_key(text)
        
        # 检查缓存
        cached = self._load_from_cache(cache_key)
        if cached is not None:
            return cached
        
        # 简单特征哈希
        vector = np.zeros(self.config.vector_dim)
        
        # 分词(简单按空格分)
        tokens = text.split()
        
        for token in tokens:
            # 哈希到向量位置
            hash_val = hash(token)
            idx = hash_val % self.config.vector_dim
            sign = 1 if hash_val % 2 == 0 else -1
            vector[idx] += sign
        
        # 归一化
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        
        # 保存缓存
        self._save_to_cache(cache_key, vector)
        
        return vector
    
    def encode_batch(self, texts: List[str]) -> np.ndarray:
        """批量编码"""
        return np.array([self.encode(text) for text in texts])


class FENEncoder(BaseEncoder):
    """
    FEN编码器
    基于FEN字符串的结构化编码
    """
    
    def __init__(self, config: EncoderConfig):
        super().__init__(config)
        
        # 棋子编码映射
        self.piece_encoding = {
            'r': 1, 'n': 2, 'b': 3, 'a': 4, 'k': 5, 'c': 6, 'p': 7,
            'R': -1, 'N': -2, 'B': -3, 'A': -4, 'K': -5, 'C': -6, 'P': -7,
            '1': 0, '2': 0, '3': 0, '4': 0, '5': 0, '6': 0, '7': 0, '8': 0, '9': 0
        }
        
        logger.info(f"FEN编码器初始化: 维度={config.vector_dim}")
    
    def encode(self, text: str) -> np.ndarray:
        """
        从文本中提取FEN并编码
        
        Args:
            text: 包含FEN的文本
            
        Returns:
            编码向量
        """
        cache_key = self._get_cache_key(text)
        
        # 检查缓存
        cached = self._load_from_cache(cache_key)
        if cached is not None:
            return cached
        
        # 提取FEN
        fen = self._extract_fen(text)
        if not fen:
            logger.warning("未找到FEN字符串")
            return np.zeros(self.config.vector_dim)
        
        # 编码FEN
        vector = self._encode_fen(fen)
        
        # 填充或截断到目标维度
        if len(vector) < self.config.vector_dim:
            vector = np.pad(vector, (0, self.config.vector_dim - len(vector)))
        else:
            vector = vector[:self.config.vector_dim]
        
        # 归一化
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        
        # 保存缓存
        self._save_to_cache(cache_key, vector)
        
        return vector
    
    def encode_batch(self, texts: List[str]) -> np.ndarray:
        """批量编码"""
        return np.array([self.encode(text) for text in texts])
    
    def _extract_fen(self, text: str) -> Optional[str]:
        """从文本中提取FEN字符串"""
        # 查找FEN:开头的行
        for line in text.split('\n'):
            if line.startswith("FEN:"):
                return line.replace("FEN:", "").strip()
        return None
    
    def _encode_fen(self, fen: str) -> np.ndarray:
        """
        编码FEN字符串
        
        将棋盘表示为90维向量(10x9=90个位置)
        """
        # 解析FEN位置部分
        position = fen.split()[0]
        rows = position.split('/')
        
        # 初始化棋盘向量
        board_vector = []
        
        for row in rows:
            for char in row:
                if char.isdigit():
                    # 空格
                    board_vector.extend([0] * int(char))
                else:
                    # 棋子
                    board_vector.append(self.piece_encoding.get(char, 0))
        
        return np.array(board_vector, dtype=np.float32)


class LLMEncoder(BaseEncoder):
    """
    LLM编码器
    使用大语言模型生成嵌入向量
    """
    
    def __init__(self, config: EncoderConfig):
        super().__init__(config)
        
        try:
            # 这里使用sentence-transformers作为示例
            # 实际可替换为其他嵌入模型
            from sentence_transformers import SentenceTransformer
            
            self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            
        except ImportError:
            raise ImportError(
                "LLM编码器需要sentence-transformers库: "
                "pip install sentence-transformers"
            )
        
        logger.info(f"LLM编码器初始化: 模型=paraphrase-multilingual-MiniLM-L12-v2")
    
    def encode(self, text: str) -> np.ndarray:
        """编码单个文本"""
        cache_key = self._get_cache_key(text)
        
        # 检查缓存
        cached = self._load_from_cache(cache_key)
        if cached is not None:
            return cached
        
        # 使用LLM编码
        vector = self.model.encode(text, convert_to_numpy=True)
        
        # 调整维度
        if len(vector) != self.config.vector_dim:
            # 简单截断或填充
            if len(vector) > self.config.vector_dim:
                vector = vector[:self.config.vector_dim]
            else:
                vector = np.pad(vector, (0, self.config.vector_dim - len(vector)))
        
        # 归一化
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        
        # 保存缓存
        self._save_to_cache(cache_key, vector)
        
        return vector
    
    def encode_batch(self, texts: List[str]) -> np.ndarray:
        """批量编码"""
        vectors = self.model.encode(texts, convert_to_numpy=True)
        
        # 调整维度
        result = np.zeros((len(texts), self.config.vector_dim))
        for i, vec in enumerate(vectors):
            if len(vec) > self.config.vector_dim:
                result[i] = vec[:self.config.vector_dim]
            else:
                result[i, :len(vec)] = vec
        
        # 归一化
        norms = np.linalg.norm(result, axis=1, keepdims=True)
        norms[norms == 0] = 1
        result = result / norms
        
        return result


# ============ 工厂函数 ============

def create_encoder(
    encoder_type: str = "fen",
    config: Optional[EncoderConfig] = None
) -> BaseEncoder:
    """
    工厂函数: 创建编码器
    
    Args:
        encoder_type: 编码器类型
        config: 配置
        
    Returns:
        编码器实例
        
    Raises:
        ValueError: 不支持的编码器类型
    """
    if config is None:
        config = EncoderConfig(encoder_type=encoder_type)
    
    encoders = {
        "tfidf": TFIDFEncoder,
        "hash": HashEncoder,
        "fen": FENEncoder,
        "llm": LLMEncoder
    }
    
    encoder_class = encoders.get(encoder_type.lower())
    if encoder_class is None:
        raise ValueError(
            f"不支持的编码器类型: {encoder_type}, "
            f"可选: {list(encoders.keys())}"
        )
    
    return encoder_class(config)


def compute_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """
    计算两个向量的余弦相似度
    
    Args:
        vec1: 向量1
        vec2: 向量2
        
    Returns:
        相似度(0-1)
    """
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    similarity = dot_product / (norm1 * norm2)
    
    # 归一化到[0, 1]
    return (similarity + 1) / 2