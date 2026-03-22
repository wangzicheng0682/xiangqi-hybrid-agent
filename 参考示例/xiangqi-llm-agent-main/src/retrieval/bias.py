"""
走法偏置生成模块
根据相似局面检索结果,生成高胜率走法和应避免走法列表
"""
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import logging
import numpy as np

from src.retrieval.index import SearchResult, VectorIndex
from src.memory.schema import Experience
from src.memory.store import ExperienceStore

logger = logging.getLogger(__name__)


@dataclass
class MoveBias:
    """走法偏置信息"""
    move: str                              # 走法
    win_rate: float                        # 胜率
    visit_count: int                       # 访问次数
    similarity: float                      # 相似度
    reward: float = 0.0                    # 奖励值
    state_fen: Optional[str] = None        # 状态FEN
    game_phase: Optional[str] = None        # 对局阶段
    metadata: Optional[Dict[str, Any]] = None  # 额外元数据


@dataclass
class BiasResult:
    """偏置生成结果"""
    good_moves: List[MoveBias]             # 高胜率走法列表
    bad_moves: List[MoveBias]              # 应避免走法列表
    similar_positions: List[Dict[str, Any]] = field(default_factory=list)  # 相似局面信息
    avg_win_rate: Optional[float] = None   # 平均胜率
    total_experiences: int = 0             # 总经验数
    confidence: float = 0.0                # 置信度(基于相似度和访问次数)


@dataclass
class BiasConfig:
    """偏置生成配置"""
    min_win_rate: float = 0.6              # 高胜率阈值
    max_win_rate: float = 0.4              # 低胜率阈值
    min_visit_count: int = 1               # 最小访问次数
    min_similarity: float = 0.5           # 最小相似度阈值
    max_good_moves: int = 5                # 最多高胜率走法数
    max_bad_moves: int = 3                 # 最多应避免走法数
    weight_by_similarity: bool = True      # 是否按相似度加权
    weight_by_visits: bool = True          # 是否按访问次数加权
    aggregate_by_move: bool = True         # 是否按走法聚合


class BiasGenerator:
    """
    走法偏置生成器
    
    功能:
    - 从检索结果中提取经验数据
    - 根据胜率分类走法
    - 生成结构化偏置信息供Prompt使用
    """
    
    def __init__(
        self,
        index: VectorIndex,
        experience_store: ExperienceStore,
        config: Optional[BiasConfig] = None
    ):
        """
        初始化偏置生成器
        
        Args:
            index: 向量索引
            experience_store: 经验存储
            config: 配置(可选)
        """
        self.index = index
        self.store = experience_store
        self.config = config or BiasConfig()
        
        logger.info(
            f"偏置生成器初始化: "
            f"高胜率阈值={self.config.min_win_rate}, "
            f"低胜率阈值={self.config.max_win_rate}"
        )
    
    def generate_bias(
        self,
        search_result: SearchResult,
        current_player: Optional[str] = None,
        game_phase: Optional[str] = None
    ) -> BiasResult:
        """
        根据检索结果生成走法偏置
        
        Args:
            search_result: 向量检索结果
            current_player: 当前玩家颜色(可选,用于过滤)
            game_phase: 当前对局阶段(可选,用于过滤)
            
        Returns:
            偏置生成结果
        """
        if not search_result.indices:
            logger.debug("检索结果为空,返回空偏置")
            return BiasResult(
                good_moves=[],
                bad_moves=[],
                total_experiences=0
            )
        
        # 从索引中提取经验数据
        experiences = self._extract_experiences(
            search_result,
            current_player,
            game_phase
        )
        
        if not experiences:
            logger.debug("未找到有效经验数据")
            return BiasResult(
                good_moves=[],
                bad_moves=[],
                total_experiences=0
            )
        
        # 按走法聚合经验
        if self.config.aggregate_by_move:
            move_bias_map = self._aggregate_by_move(experiences, search_result)
        else:
            move_bias_map = self._create_move_bias_list(experiences, search_result)
        
        # 分类走法
        good_moves, bad_moves = self._classify_moves(move_bias_map)
        
        # 计算统计信息
        avg_win_rate = self._calculate_avg_win_rate(experiences)
        confidence = self._calculate_confidence(experiences, search_result)
        
        # 构建相似局面信息
        similar_positions = self._build_similar_positions(experiences, search_result)
        
        result = BiasResult(
            good_moves=good_moves,
            bad_moves=bad_moves,
            similar_positions=similar_positions,
            avg_win_rate=avg_win_rate,
            total_experiences=len(experiences),
            confidence=confidence
        )
        
        logger.info(
            f"偏置生成完成: "
            f"高胜率走法={len(good_moves)}, "
            f"应避免走法={len(bad_moves)}, "
            f"置信度={confidence:.2f}"
        )
        
        return result
    
    def _extract_experiences(
        self,
        search_result: SearchResult,
        current_player: Optional[str],
        game_phase: Optional[str]
    ) -> List[Tuple[Experience, float]]:
        """
        从检索结果中提取经验数据
        
        Args:
            search_result: 检索结果
            current_player: 当前玩家
            game_phase: 对局阶段
            
        Returns:
            (经验, 相似度) 元组列表
        """
        experiences = []
        
        for idx, similarity in zip(search_result.indices, search_result.similarities):
            # 过滤低相似度结果
            if similarity < self.config.min_similarity:
                continue
            
            # 从索引元数据中获取经验ID或状态哈希
            metadata = self.index.get_metadata(idx)
            if not metadata:
                continue
            
            # 尝试从metadata中获取经验ID
            exp_id = metadata.get("experience_id")
            state_hash = metadata.get("state_hash")
            
            experience = None
            
            if exp_id:
                # 通过ID获取经验
                experience = self.store.get_experience_by_id(exp_id)
            elif state_hash:
                # 通过状态哈希获取经验(取第一个)
                exps = self.store.get_experiences_by_state(state_hash, limit=1)
                if exps:
                    experience = exps[0]
            
            if not experience:
                continue
            
            # 过滤玩家颜色
            if current_player and experience.player_color != current_player:
                continue
            
            # 过滤对局阶段
            if game_phase and experience.game_phase and experience.game_phase != game_phase:
                continue
            
            # 过滤访问次数
            if experience.visit_count < self.config.min_visit_count:
                continue
            
            experiences.append((experience, similarity))
        
        return experiences
    
    def _aggregate_by_move(
        self,
        experiences: List[Tuple[Experience, float]],
        search_result: SearchResult
    ) -> Dict[str, MoveBias]:
        """
        按走法聚合经验数据
        
        Args:
            experiences: 经验列表
            search_result: 检索结果
            
        Returns:
            走法到偏置信息的映射
        """
        move_data = defaultdict(lambda: {
            "win_rates": [],
            "visit_counts": [],
            "similarities": [],
            "rewards": [],
            "weights": [],
            "state_fens": [],
            "game_phases": [],
            "metadata_list": []
        })
        
        for experience, similarity in experiences:
            move = experience.move
            if not move:
                continue
            
            # 计算权重
            weight = 1.0
            if self.config.weight_by_similarity:
                weight *= similarity
            if self.config.weight_by_visits:
                weight *= (1.0 + np.log1p(experience.visit_count))
            
            move_data[move]["win_rates"].append(experience.win_rate)
            move_data[move]["visit_counts"].append(experience.visit_count)
            move_data[move]["similarities"].append(similarity)
            move_data[move]["rewards"].append(experience.reward)
            move_data[move]["weights"].append(weight)
            move_data[move]["state_fens"].append(experience.state_fen)
            move_data[move]["game_phases"].append(experience.game_phase)
            move_data[move]["metadata_list"].append(experience.metadata)
        
        # 计算加权平均
        move_bias_map = {}
        for move, data in move_data.items():
            weights = np.array(data["weights"])
            total_weight = weights.sum()
            
            if total_weight == 0:
                continue
            
            # 加权平均胜率
            win_rates = np.array(data["win_rates"])
            avg_win_rate = np.average(win_rates, weights=weights)
            
            # 总访问次数
            total_visits = sum(data["visit_counts"])
            
            # 平均相似度
            avg_similarity = np.average(data["similarities"], weights=weights)
            
            # 平均奖励
            rewards = np.array(data["rewards"])
            avg_reward = np.average(rewards, weights=weights) if len(rewards) > 0 else 0.0
            
            # 选择最有代表性的状态FEN
            best_idx = np.argmax(weights)
            representative_fen = data["state_fens"][best_idx] if data["state_fens"] else None
            representative_phase = data["game_phases"][best_idx] if data["game_phases"] else None
            representative_metadata = data["metadata_list"][best_idx] if data["metadata_list"] else None
            
            move_bias_map[move] = MoveBias(
                move=move,
                win_rate=float(avg_win_rate),
                visit_count=int(total_visits),
                similarity=float(avg_similarity),
                reward=float(avg_reward),
                state_fen=representative_fen,
                game_phase=representative_phase,
                metadata=representative_metadata
            )
        
        return move_bias_map
    
    def _create_move_bias_list(
        self,
        experiences: List[Tuple[Experience, float]],
        search_result: SearchResult
    ) -> Dict[str, MoveBias]:
        """
        不聚合,直接创建走法偏置列表
        
        Args:
            experiences: 经验列表
            search_result: 检索结果
            
        Returns:
            走法到偏置信息的映射
        """
        move_bias_map = {}
        
        for experience, similarity in experiences:
            move = experience.move
            if not move:
                continue
            
            # 如果已存在,选择更好的(更高的访问次数或相似度)
            if move in move_bias_map:
                existing = move_bias_map[move]
                if (experience.visit_count > existing.visit_count or
                    similarity > existing.similarity):
                    move_bias_map[move] = MoveBias(
                        move=move,
                        win_rate=experience.win_rate,
                        visit_count=experience.visit_count,
                        similarity=similarity,
                        reward=experience.reward,
                        state_fen=experience.state_fen,
                        game_phase=experience.game_phase,
                        metadata=experience.metadata
                    )
            else:
                move_bias_map[move] = MoveBias(
                    move=move,
                    win_rate=experience.win_rate,
                    visit_count=experience.visit_count,
                    similarity=similarity,
                    reward=experience.reward,
                    state_fen=experience.state_fen,
                    game_phase=experience.game_phase,
                    metadata=experience.metadata
                )
        
        return move_bias_map
    
    def _classify_moves(
        self,
        move_bias_map: Dict[str, MoveBias]
    ) -> Tuple[List[MoveBias], List[MoveBias]]:
        """
        分类走法为高胜率和低胜率
        
        Args:
            move_bias_map: 走法偏置映射
            
        Returns:
            (高胜率走法列表, 低胜率走法列表)
        """
        good_moves = []
        bad_moves = []
        
        for move_bias in move_bias_map.values():
            if move_bias.win_rate >= self.config.min_win_rate:
                good_moves.append(move_bias)
            elif move_bias.win_rate <= self.config.max_win_rate:
                bad_moves.append(move_bias)
        
        # 排序并限制数量
        good_moves.sort(
            key=lambda x: (x.win_rate, x.visit_count, x.similarity),
            reverse=True
        )
        good_moves = good_moves[:self.config.max_good_moves]
        
        bad_moves.sort(
            key=lambda x: (x.win_rate, -x.visit_count, -x.similarity)
        )
        bad_moves = bad_moves[:self.config.max_bad_moves]
        
        return good_moves, bad_moves
    
    def _calculate_avg_win_rate(
        self,
        experiences: List[Tuple[Experience, float]]
    ) -> Optional[float]:
        """计算平均胜率"""
        if not experiences:
            return None
        
        total_weight = 0.0
        weighted_sum = 0.0
        
        for experience, similarity in experiences:
            weight = similarity * (1.0 + np.log1p(experience.visit_count))
            weighted_sum += experience.win_rate * weight
            total_weight += weight
        
        if total_weight == 0:
            return None
        
        return weighted_sum / total_weight
    
    def _calculate_confidence(
        self,
        experiences: List[Tuple[Experience, float]],
        search_result: SearchResult
    ) -> float:
        """
        计算置信度
        
        基于:
        - 相似度
        - 访问次数
        - 经验数量
        """
        if not experiences:
            return 0.0
        
        # 平均相似度
        avg_similarity = np.mean([sim for _, sim in experiences])
        
        # 总访问次数(归一化)
        total_visits = sum(exp.visit_count for exp, _ in experiences)
        normalized_visits = min(total_visits / 100.0, 1.0)  # 100次访问为满分
        
        # 经验数量(归一化)
        normalized_count = min(len(experiences) / 10.0, 1.0)  # 10条经验为满分
        
        # 综合置信度
        confidence = (
            0.5 * avg_similarity +
            0.3 * normalized_visits +
            0.2 * normalized_count
        )
        
        return float(np.clip(confidence, 0.0, 1.0))
    
    def _build_similar_positions(
        self,
        experiences: List[Tuple[Experience, float]],
        search_result: SearchResult
    ) -> List[Dict[str, Any]]:
        """
        构建相似局面信息
        
        Args:
            experiences: 经验列表
            search_result: 检索结果
            
        Returns:
            相似局面信息列表
        """
        positions = []
        
        # 去重(按状态哈希)
        seen_hashes = set()
        
        for experience, similarity in experiences[:5]:  # 最多5个
            if experience.state_hash in seen_hashes:
                continue
            
            seen_hashes.add(experience.state_hash)
            
            positions.append({
                "state_fen": experience.state_fen,
                "state_hash": experience.state_hash,
                "similarity": similarity,
                "win_rate": experience.win_rate,
                "visit_count": experience.visit_count,
                "game_phase": experience.game_phase
            })
        
        return positions
    
    def to_prompt_format(self, bias_result: BiasResult) -> Dict[str, Any]:
        """
        转换为Prompt可用的格式
        
        Args:
            bias_result: 偏置结果
            
        Returns:
            Prompt格式的字典
        """
        # 格式化高胜率走法
        good_moves_text = []
        for i, move_bias in enumerate(bias_result.good_moves, 1):
            good_moves_text.append(
                f"{i}. {move_bias.move} "
                f"(胜率: {move_bias.win_rate:.1%}, "
                f"访问: {move_bias.visit_count}, "
                f"相似度: {move_bias.similarity:.2f})"
            )
        
        # 格式化应避免走法
        bad_moves_text = []
        for i, move_bias in enumerate(bias_result.bad_moves, 1):
            bad_moves_text.append(
                f"{i}. {move_bias.move} "
                f"(胜率: {move_bias.win_rate:.1%}, "
                f"访问: {move_bias.visit_count}, "
                f"相似度: {move_bias.similarity:.2f})"
            )
        
        # 格式化相似局面
        similar_positions_text = []
        for pos in bias_result.similar_positions:
            similar_positions_text.append(
                f"FEN: {pos['state_fen']}, "
                f"相似度: {pos['similarity']:.2f}, "
                f"胜率: {pos['win_rate']:.1%}"
            )
        
        return {
            "good_moves": {
                "list": [mb.move for mb in bias_result.good_moves],
                "details": [
                    {
                        "move": mb.move,
                        "win_rate": mb.win_rate,
                        "visit_count": mb.visit_count,
                        "similarity": mb.similarity,
                        "reward": mb.reward
                    }
                    for mb in bias_result.good_moves
                ],
                "formatted_text": "\n".join(good_moves_text) if good_moves_text else "无"
            },
            "bad_moves": {
                "list": [mb.move for mb in bias_result.bad_moves],
                "details": [
                    {
                        "move": mb.move,
                        "win_rate": mb.win_rate,
                        "visit_count": mb.visit_count,
                        "similarity": mb.similarity,
                        "reward": mb.reward
                    }
                    for mb in bias_result.bad_moves
                ],
                "formatted_text": "\n".join(bad_moves_text) if bad_moves_text else "无"
            },
            "similar_positions": {
                "list": bias_result.similar_positions,
                "formatted_text": "\n".join(similar_positions_text) if similar_positions_text else "无"
            },
            "statistics": {
                "avg_win_rate": bias_result.avg_win_rate,
                "total_experiences": bias_result.total_experiences,
                "confidence": bias_result.confidence
            },
            "summary": self._generate_summary(bias_result)
        }
    
    def _generate_summary(self, bias_result: BiasResult) -> str:
        """生成摘要文本"""
        parts = []
        
        if bias_result.good_moves:
            parts.append(
                f"找到 {len(bias_result.good_moves)} 个高胜率走法 "
                f"(平均胜率: {bias_result.avg_win_rate:.1%})"
            )
        
        if bias_result.bad_moves:
            parts.append(
                f"发现 {len(bias_result.bad_moves)} 个应避免走法"
            )
        
        if bias_result.confidence > 0:
            parts.append(f"置信度: {bias_result.confidence:.1%}")
        
        return " | ".join(parts) if parts else "无相似经验"
    
    def to_retrieved_experience(self, bias_result: BiasResult) -> Dict[str, Any]:
        """
        转换为RetrievedExperience格式
        
        Args:
            bias_result: 偏置结果
            
        Returns:
            符合RetrievedExperience格式的字典
        """
        # 转换高胜率走法
        good_moves = [
            {
                "move": mb.move,
                "win_rate": mb.win_rate,
                "visit_count": mb.visit_count,
                "similarity": mb.similarity,
                "reward": mb.reward,
                "state_fen": mb.state_fen,
                "game_phase": mb.game_phase,
                "metadata": mb.metadata
            }
            for mb in bias_result.good_moves
        ]
        
        # 转换应避免走法
        bad_moves = [
            {
                "move": mb.move,
                "win_rate": mb.win_rate,
                "visit_count": mb.visit_count,
                "similarity": mb.similarity,
                "reward": mb.reward,
                "state_fen": mb.state_fen,
                "game_phase": mb.game_phase,
                "metadata": mb.metadata
            }
            for mb in bias_result.bad_moves
        ]
        
        return {
            "good_moves": good_moves,
            "bad_moves": bad_moves,
            "similar_positions": bias_result.similar_positions,
            "win_rate": bias_result.avg_win_rate
        }


# ============ 工厂函数 ============

def create_bias_generator(
    index: VectorIndex,
    experience_store: ExperienceStore,
    config: Optional[BiasConfig] = None
) -> BiasGenerator:
    """
    创建偏置生成器
    
    Args:
        index: 向量索引
        experience_store: 经验存储
        config: 配置(可选)
        
    Returns:
        BiasGenerator实例
    """
    return BiasGenerator(index, experience_store, config)

