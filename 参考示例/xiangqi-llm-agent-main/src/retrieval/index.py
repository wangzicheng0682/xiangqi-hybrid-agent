"""
向量索引模块
使用FAISS或等价方案进行相似度检索
"""
from typing import List, Optional, Tuple, Dict, Any
from dataclasses import dataclass
import numpy as np
import logging
import pickle
import os

logger = logging.getLogger(__name__)


@dataclass
class IndexConfig:
    """索引配置"""
    index_type: str = "flat"            # 索引类型: flat/ivf/hnsw
    vector_dim: int = 128               # 向量维度
    
    # IVF参数
    nlist: int = 100                    # IVF聚类中心数
    nprobe: int = 10                    # IVF搜索聚类数
    
    # HNSW参数
    m: int = 32                         # HNSW边数
    ef_construction: int = 200          # HNSW构建参数
    ef_search: int = 50                 # HNSW搜索参数
    
    # 持久化
    save_index: bool = True             # 是否保存索引
    index_path: str = "data/index"      # 索引保存路径


@dataclass
class SearchResult:
    """搜索结果"""
    indices: List[int]                  # 相似向量的索引列表
    distances: List[float]              # 对应的距离列表
    similarities: List[float]           # 对应的相似度列表(0-1)


class VectorIndex:
    """
    向量索引基类
    提供统一的向量检索接口
    """
    
    def __init__(self, config: IndexConfig):
        """
        初始化索引
        
        Args:
            config: 索引配置
        """
        self.config = config
        self.vectors: List[np.ndarray] = []
        self.metadata: List[Dict[str, Any]] = []
        
        logger.info(
            f"向量索引初始化: 类型={config.index_type}, "
            f"维度={config.vector_dim}"
        )
    
    def add(self, vector: np.ndarray, metadata: Optional[Dict] = None):
        """
        添加单个向量
        
        Args:
            vector: 向量
            metadata: 元数据(可选)
        """
        if len(vector) != self.config.vector_dim:
            raise ValueError(
                f"向量维度不匹配: 期望{self.config.vector_dim}, "
                f"实际{len(vector)}"
            )
        
        self.vectors.append(vector.copy())
        self.metadata.append(metadata or {})
        
        logger.debug(f"添加向量: 索引={len(self.vectors)-1}")
    
    def add_batch(self, vectors: np.ndarray, metadata_list: Optional[List[Dict]] = None):
        """
        批量添加向量
        
        Args:
            vectors: 向量矩阵(N x D)
            metadata_list: 元数据列表(可选)
        """
        if vectors.shape[1] != self.config.vector_dim:
            raise ValueError(
                f"向量维度不匹配: 期望{self.config.vector_dim}, "
                f"实际{vectors.shape[1]}"
            )
        
        n = len(vectors)
        self.vectors.extend(vectors)
        
        if metadata_list:
            if len(metadata_list) != n:
                raise ValueError("向量数量与元数据数量不匹配")
            self.metadata.extend(metadata_list)
        else:
            self.metadata.extend([{}] * n)
        
        logger.info(f"批量添加向量: {n} 个")
    
    def search(
        self,
        query: np.ndarray,
        k: int = 10
    ) -> SearchResult:
        """
        搜索最相似的K个向量
        
        Args:
            query: 查询向量
            k: 返回数量
            
        Returns:
            搜索结果
        """
        raise NotImplementedError
    
    def search_batch(
        self,
        queries: np.ndarray,
        k: int = 10
    ) -> List[SearchResult]:
        """
        批量搜索
        
        Args:
            queries: 查询向量矩阵(N x D)
            k: 每个查询返回数量
            
        Returns:
            搜索结果列表
        """
        results = []
        for query in queries:
            results.append(self.search(query, k))
        return results
    
    def size(self) -> int:
        """获取索引中的向量数量"""
        return len(self.vectors)
    
    def get_vector(self, idx: int) -> Optional[np.ndarray]:
        """获取指定索引的向量"""
        if 0 <= idx < len(self.vectors):
            return self.vectors[idx]
        return None
    
    def get_metadata(self, idx: int) -> Optional[Dict]:
        """获取指定索引的元数据"""
        if 0 <= idx < len(self.metadata):
            return self.metadata[idx]
        return None
    
    def save(self, path: Optional[str] = None):
        """
        保存索引
        
        Args:
            path: 保存路径(可选)
        """
        if not self.config.save_index:
            return
        
        path = path or self.config.index_path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        data = {
            "config": self.config,
            "vectors": self.vectors,
            "metadata": self.metadata
        }
        
        with open(path, 'wb') as f:
            pickle.dump(data, f)
        
        logger.info(f"索引已保存: {path}")
    
    def load(self, path: Optional[str] = None):
        """
        加载索引
        
        Args:
            path: 加载路径(可选)
        """
        path = path or self.config.index_path
        
        if not os.path.exists(path):
            logger.warning(f"索引文件不存在: {path}")
            return
        
        with open(path, 'rb') as f:
            data = pickle.load(f)
        
        self.config = data["config"]
        self.vectors = data["vectors"]
        self.metadata = data["metadata"]
        
        logger.info(f"索引已加载: {path}, 向量数={len(self.vectors)}")


class FlatIndex(VectorIndex):
    """
    简单暴力搜索索引
    适合小规模数据(<10000)
    """
    
    def __init__(self, config: IndexConfig):
        super().__init__(config)
        logger.info("使用Flat索引(暴力搜索)")
    
    def search(self, query: np.ndarray, k: int = 10) -> SearchResult:
        """搜索最相似的K个向量"""
        if not self.vectors:
            return SearchResult(indices=[], distances=[], similarities=[])
        
        # 转换为numpy数组
        vectors_array = np.array(self.vectors)
        
        # 计算余弦相似度
        # 归一化查询向量
        query_norm = query / (np.linalg.norm(query) + 1e-10)
        
        # 归一化数据库向量
        vectors_norm = vectors_array / (np.linalg.norm(vectors_array, axis=1, keepdims=True) + 1e-10)
        
        # 计算点积(余弦相似度)
        similarities = np.dot(vectors_norm, query_norm)
        
        # Top-K
        k = min(k, len(similarities))
        top_k_indices = np.argsort(similarities)[::-1][:k]
        top_k_similarities = similarities[top_k_indices]
        
        # 转换为距离(1 - similarity)
        distances = 1.0 - top_k_similarities
        
        return SearchResult(
            indices=top_k_indices.tolist(),
            distances=distances.tolist(),
            similarities=top_k_similarities.tolist()
        )


class FAISSIndex(VectorIndex):
    """
    FAISS索引
    适合大规模数据
    """
    
    def __init__(self, config: IndexConfig):
        super().__init__(config)
        
        try:
            import faiss
            self.faiss = faiss
            
            # 创建FAISS索引
            if config.index_type == "flat":
                # 暴力搜索
                self.index = faiss.IndexFlatIP(config.vector_dim)  # Inner Product
                
            elif config.index_type == "ivf":
                # IVF索引
                quantizer = faiss.IndexFlatIP(config.vector_dim)
                self.index = faiss.IndexIVFFlat(
                    quantizer,
                    config.vector_dim,
                    config.nlist,
                    faiss.METRIC_INNER_PRODUCT
                )
                self.trained = False
                
            elif config.index_type == "hnsw":
                # HNSW索引
                self.index = faiss.IndexHNSWFlat(
                    config.vector_dim,
                    config.m,
                    faiss.METRIC_INNER_PRODUCT
                )
                self.index.hnsw.efConstruction = config.ef_construction
                self.index.hnsw.efSearch = config.ef_search
                
            else:
                raise ValueError(f"不支持的FAISS索引类型: {config.index_type}")
            
            logger.info(f"使用FAISS索引: {config.index_type}")
            
        except ImportError:
            raise ImportError("FAISS索引需要faiss库: pip install faiss-cpu")
    
    def add(self, vector: np.ndarray, metadata: Optional[Dict] = None):
        """添加单个向量"""
        super().add(vector, metadata)
        
        # 归一化
        vector_norm = vector / (np.linalg.norm(vector) + 1e-10)
        vector_norm = vector_norm.reshape(1, -1).astype('float32')
        
        # 对于IVF索引,需要先训练
        if self.config.index_type == "ivf" and not self.trained:
            # 当向量数量达到nlist时,训练索引
            if len(self.vectors) >= self.config.nlist:
                self._train_ivf()
            else:
                # 训练前不添加到索引,只保存在self.vectors中
                return
        
        # 添加到FAISS索引(非IVF或已训练的IVF)
        self.index.add(vector_norm)
    
    def add_batch(self, vectors: np.ndarray, metadata_list: Optional[List[Dict]] = None):
        """批量添加向量"""
        super().add_batch(vectors, metadata_list)
        
        # 归一化
        vectors_norm = vectors / (np.linalg.norm(vectors, axis=1, keepdims=True) + 1e-10)
        vectors_norm = vectors_norm.astype('float32')
        
        # 对于IVF索引,需要先训练
        if self.config.index_type == "ivf" and not self.trained:
            # 当向量数量达到nlist时,训练索引
            if len(self.vectors) >= self.config.nlist:
                self._train_ivf()
            else:
                # 训练前不添加到索引,只保存在self.vectors中
                return
        
        # 添加到FAISS索引(非IVF或已训练的IVF)
        self.index.add(vectors_norm)
    
    def search(self, query: np.ndarray, k: int = 10) -> SearchResult:
        """搜索最相似的K个向量"""
        if self.index.ntotal == 0:
            return SearchResult(indices=[], distances=[], similarities=[])
        
        # 归一化查询向量
        query_norm = query / (np.linalg.norm(query) + 1e-10)
        query_norm = query_norm.reshape(1, -1).astype('float32')
        
        # FAISS搜索
        k = min(k, self.index.ntotal)
        distances, indices = self.index.search(query_norm, k)
        
        # 转换为相似度(inner product已经是相似度)
        similarities = distances[0].tolist()
        distances = (1.0 - distances[0]).tolist()
        indices = indices[0].tolist()
        
        return SearchResult(
            indices=indices,
            distances=distances,
            similarities=similarities
        )
    
    def _train_ivf(self):
        """训练IVF索引"""
        logger.info("训练IVF索引...")
        
        vectors_array = np.array(self.vectors).astype('float32')
        vectors_norm = vectors_array / (np.linalg.norm(vectors_array, axis=1, keepdims=True) + 1e-10)
        
        # 训练索引
        self.index.train(vectors_norm)
        self.trained = True
        
        # 添加所有已收集的向量
        self.index.add(vectors_norm)
        
        # 设置搜索参数
        self.index.nprobe = self.config.nprobe
        
        logger.info(f"IVF索引训练完成,已添加 {len(vectors_norm)} 个向量")
    
    def save(self, path: Optional[str] = None):
        """保存索引"""
        if not self.config.save_index:
            return
        
        path = path or self.config.index_path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        # 保存FAISS索引
        faiss_path = path + ".faiss"
        self.faiss.write_index(self.index, faiss_path)
        
        # 保存元数据
        meta_path = path + ".meta"
        data = {
            "config": self.config,
            "metadata": self.metadata
        }
        with open(meta_path, 'wb') as f:
            pickle.dump(data, f)
        
        logger.info(f"FAISS索引已保存: {path}")
    
    def load(self, path: Optional[str] = None):
        """加载索引"""
        path = path or self.config.index_path
        
        faiss_path = path + ".faiss"
        meta_path = path + ".meta"
        
        if not os.path.exists(faiss_path):
            logger.warning(f"FAISS索引文件不存在: {faiss_path}")
            return
        
        # 加载FAISS索引
        self.index = self.faiss.read_index(faiss_path)
        
        # 加载元数据
        if os.path.exists(meta_path):
            with open(meta_path, 'rb') as f:
                data = pickle.load(f)
            self.config = data["config"]
            self.metadata = data["metadata"]
        
        logger.info(f"FAISS索引已加载: {path}, 向量数={self.index.ntotal}")


# ============ 工厂函数 ============

def create_index(
    index_type: str = "flat",
    config: Optional[IndexConfig] = None,
    use_faiss: bool = True
) -> VectorIndex:
    """
    工厂函数: 创建向量索引
    
    Args:
        index_type: 索引类型
        config: 配置
        use_faiss: 是否使用FAISS(如果可用)
        
    Returns:
        VectorIndex实例
    """
    if config is None:
        config = IndexConfig(index_type=index_type)
    
    # 尝试使用FAISS
    if use_faiss:
        try:
            return FAISSIndex(config)
        except ImportError:
            logger.warning("FAISS不可用,回退到Flat索引")
    
    # 回退到简单索引
    return FlatIndex(config)


def load_index(path: str, use_faiss: bool = True) -> VectorIndex:
    """
    加载已保存的索引
    
    Args:
        path: 索引路径
        use_faiss: 是否尝试加载FAISS索引
        
    Returns:
        加载的索引实例
    """
    # 检查FAISS索引
    faiss_path = path + ".faiss"
    if use_faiss and os.path.exists(faiss_path):
        try:
            config = IndexConfig()
            index = FAISSIndex(config)
            index.load(path)
            return index
        except Exception as e:
            logger.warning(f"加载FAISS索引失败: {e}")
    
    # 加载简单索引
    if os.path.exists(path):
        config = IndexConfig()
        index = FlatIndex(config)
        index.load(path)
        return index
    
    raise FileNotFoundError(f"索引文件不存在: {path}")