"""
LLM走法选择器
整合prompts和client,实现完整的走法选择流程
"""
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
import logging
import random

from src.llm.client import BaseLLMClient, LLMResponse
from src.llm.prompts import (
    MoveContext, ExperienceContext, PromptMode,
    create_move_prompt, parse_move_response,
    PromptBuilder, PromptParser
)

logger = logging.getLogger(__name__)


@dataclass
class MoveSelectorConfig:
    """走法选择器配置"""
    top_k: int = 3                    # 返回Top-K走法
    exploration_rate: float = 0.2     # 探索概率
    temperature: float = 0.7          # LLM温度
    max_retries: int = 3              # 最大重试次数
    fallback_random: bool = True      # 失败时随机降级
    use_experience: bool = True       # 是否使用经验
    min_good_moves: int = 1           # 最少好走法数量(用于提示)
    max_bad_moves: int = 3            # 最多坏走法数量(用于提示)


@dataclass
class RetrievedExperience:
    """检索到的经验"""
    good_moves: List[Dict[str, Any]]  # 好走法及其数据
    bad_moves: List[Dict[str, Any]]   # 坏走法及其数据
    similar_positions: List[Dict[str, Any]]  # 相似局面
    win_rate: Optional[float] = None  # 胜率


@dataclass
class MoveSelection:
    """走法选择结果"""
    selected_moves: List[str]         # 选中的走法列表(Top-K)
    scores: List[float]               # 对应的得分
    raw_response: str                 # LLM原始响应
    mode: PromptMode                  # 使用的模式
    retries: int                      # 重试次数
    fallback_used: bool = False       # 是否使用降级策略


class MoveSelector:
    """LLM走法选择器"""
    
    def __init__(
        self,
        llm_client: BaseLLMClient,
        config: Optional[MoveSelectorConfig] = None
    ):
        """
        初始化选择器
        
        Args:
            llm_client: LLM客户端
            config: 配置(可选)
        """
        self.client = llm_client
        self.config = config or MoveSelectorConfig()
        self.builder = PromptBuilder()
        self.parser = PromptParser()
    
    def select_moves(
        self,
        board_text: str,
        legal_moves: List[str],
        move_descriptions: List[str],
        current_player: str,
        move_count: int,
        game_phase: str = "中局",
        retrieved_experience: Optional[RetrievedExperience] = None
    ) -> MoveSelection:
        """
        选择走法
        
        Args:
            board_text: 棋盘文本表示
            legal_moves: 合法走法列表
            move_descriptions: 走法描述列表
            current_player: 当前行动方
            move_count: 回合数
            game_phase: 对局阶段
            retrieved_experience: 检索到的经验(可选)
            
        Returns:
            走法选择结果
            
        Raises:
            ValueError: 输入参数无效
        """
        # 参数验证
        if not legal_moves:
            raise ValueError("合法走法列表为空")
        
        if len(legal_moves) != len(move_descriptions):
            logger.warning(f"走法数量({len(legal_moves)})与描述数量({len(move_descriptions)})不匹配")
            # 补齐描述
            move_descriptions = move_descriptions + [""] * (len(legal_moves) - len(move_descriptions))
        
        # 决定模式(探索 vs 利用)
        mode = self._decide_mode()
        
        # 构建上下文
        context = MoveContext(
            board_text=board_text,
            legal_moves=legal_moves,
            move_descriptions=move_descriptions,
            current_player=current_player,
            move_count=move_count,
            game_phase=game_phase
        )
        
        # 转换经验格式
        experience_ctx = self._convert_experience(retrieved_experience)
        
        # 尝试选择走法(带重试)
        for attempt in range(self.config.max_retries):
            try:
                logger.info(f"走法选择尝试 {attempt + 1}/{self.config.max_retries}, 模式: {mode.value}")
                
                result = self._select_with_llm(
                    context=context,
                    mode=mode,
                    experience=experience_ctx
                )
                
                if result:
                    logger.info(f"走法选择成功: {result.selected_moves[:self.config.top_k]}")
                    return result
                
            except Exception as e:
                logger.warning(f"走法选择失败 (尝试 {attempt + 1}): {e}")
        
        # 所有尝试失败,使用降级策略
        logger.warning("所有LLM尝试失败,使用降级策略")
        return self._fallback_selection(legal_moves, mode)
    
    def select_top_move(
        self,
        board_text: str,
        legal_moves: List[str],
        move_descriptions: List[str],
        current_player: str,
        move_count: int,
        game_phase: str = "中局",
        retrieved_experience: Optional[RetrievedExperience] = None
    ) -> str:
        """
        选择单个最佳走法(便捷方法)
        
        Args:
            参数同select_moves
            
        Returns:
            选中的走法
        """
        result = self.select_moves(
            board_text=board_text,
            legal_moves=legal_moves,
            move_descriptions=move_descriptions,
            current_player=current_player,
            move_count=move_count,
            game_phase=game_phase,
            retrieved_experience=retrieved_experience
        )
        
        return result.selected_moves[0]
    
    # ============ 内部方法 ============
    
    def _select_with_llm(
        self,
        context: MoveContext,
        mode: PromptMode,
        experience: Optional[ExperienceContext]
    ) -> Optional[MoveSelection]:
        """
        使用LLM进行走法选择
        
        Args:
            context: 走法上下文
            mode: 选择模式
            experience: 经验上下文
            
        Returns:
            选择结果,失败返回None
        """
        # 构建Prompt
        prompts = self.builder.build_move_selection_prompt(
            context=context,
            mode=mode,
            experience=experience
        )
        
        # 调用LLM
        response = self.client.generate(
            prompt=prompts["user"],
            system_prompt=prompts["system"],
            temperature=self.config.temperature
        )
        
        logger.debug(f"LLM原始响应: {response.content[:200]}...")
        
        # 解析响应
        move_idx = self.parser.parse_move_selection(
            response.content,
            len(context.legal_moves)
        )
        
        if move_idx is None:
            logger.warning(f"无法解析LLM响应: {response.content[:100]}")
            return None
        
        # 验证走法合法性(冗余检查)
        if not (0 <= move_idx < len(context.legal_moves)):
            logger.warning(f"解析的走法索引越界: {move_idx}")
            return None
        
        selected_move = context.legal_moves[move_idx]
        
        # 生成Top-K列表
        top_k_moves = self._generate_top_k(
            selected_move=selected_move,
            all_moves=context.legal_moves,
            experience=experience
        )
        
        return MoveSelection(
            selected_moves=top_k_moves,
            scores=[1.0] * len(top_k_moves),  # 简化版得分
            raw_response=response.content,
            mode=mode,
            retries=0,
            fallback_used=False
        )
    
    def _generate_top_k(
        self,
        selected_move: str,
        all_moves: List[str],
        experience: Optional[ExperienceContext]
    ) -> List[str]:
        """
        生成Top-K走法列表
        
        策略:
        1. 首选LLM选择的走法
        2. 从经验中选择高奖励走法
        3. 随机补充剩余位置
        
        Args:
            selected_move: LLM选择的走法
            all_moves: 所有合法走法
            experience: 经验上下文
            
        Returns:
            Top-K走法列表
        """
        top_k = [selected_move]
        
        # 从经验中补充
        if experience and experience.historical_moves:
            for move_data in experience.historical_moves:
                move = move_data.get("move", "")
                if move in all_moves and move not in top_k:
                    top_k.append(move)
                    if len(top_k) >= self.config.top_k:
                        break
        
        # 随机补充到top_k数量
        remaining_moves = [m for m in all_moves if m not in top_k]
        random.shuffle(remaining_moves)
        
        while len(top_k) < self.config.top_k and remaining_moves:
            top_k.append(remaining_moves.pop(0))
        
        return top_k[:self.config.top_k]
    
    def _decide_mode(self) -> PromptMode:
        """
        决定选择模式(探索 vs 利用)
        
        Returns:
            选择模式
        """
        if random.random() < self.config.exploration_rate:
            return PromptMode.EXPLORATION
        else:
            return PromptMode.EXPLOITATION
    
    def _convert_experience(
        self,
        retrieved: Optional[RetrievedExperience]
    ) -> Optional[ExperienceContext]:
        """
        转换经验格式
        
        Args:
            retrieved: 检索到的经验
            
        Returns:
            经验上下文
        """
        if not retrieved or not self.config.use_experience:
            return None
        
        # 过滤和排序
        good_moves = retrieved.good_moves[:self.config.min_good_moves + 5]
        bad_moves = retrieved.bad_moves[:self.config.max_bad_moves]
        
        # 合并为历史走法(好走法优先)
        historical_moves = []
        
        for move_data in good_moves:
            historical_moves.append({
                "move": move_data.get("move", ""),
                "reward": move_data.get("reward", 0.5),
                "count": move_data.get("count", 1)
            })
        
        return ExperienceContext(
            similar_positions=retrieved.similar_positions,
            historical_moves=historical_moves,
            win_rate=retrieved.win_rate
        )
    
    def _fallback_selection(
        self,
        legal_moves: List[str],
        mode: PromptMode
    ) -> MoveSelection:
        """
        降级策略: LLM失败时的备选方案
        
        Args:
            legal_moves: 合法走法列表
            mode: 原始模式
            
        Returns:
            降级选择结果
        """
        if not self.config.fallback_random:
            raise RuntimeError("LLM走法选择失败且未启用降级策略")
        
        logger.warning("使用随机降级策略")
        
        # 随机选择
        selected = random.sample(
            legal_moves,
            min(self.config.top_k, len(legal_moves))
        )
        
        return MoveSelection(
            selected_moves=selected,
            scores=[0.5] * len(selected),  # 中性得分
            raw_response="[FALLBACK] 随机选择",
            mode=mode,
            retries=self.config.max_retries,
            fallback_used=True
        )
    
    def _validate_moves(
        self,
        moves: List[str],
        legal_moves: List[str]
    ) -> List[str]:
        """
        验证走法合法性
        
        Args:
            moves: 待验证的走法
            legal_moves: 合法走法列表
            
        Returns:
            过滤后的合法走法
        """
        valid_moves = []
        legal_set = set(legal_moves)
        
        for move in moves:
            if move in legal_set:
                valid_moves.append(move)
            else:
                logger.warning(f"过滤非法走法: {move}")
        
        return valid_moves


# ============ 便捷函数 ============

def create_move_selector(
    llm_client: BaseLLMClient,
    config: Optional[MoveSelectorConfig] = None
) -> MoveSelector:
    """
    工厂函数: 创建走法选择器
    
    Args:
        llm_client: LLM客户端
        config: 配置
        
    Returns:
        MoveSelector实例
    """
    return MoveSelector(llm_client, config)


def select_move_simple(
    llm_client: BaseLLMClient,
    board_text: str,
    legal_moves: List[str]
) -> str:
    """
    简化版走法选择(用于快速测试)
    
    Args:
        llm_client: LLM客户端
        board_text: 棋盘文本
        legal_moves: 合法走法
        
    Returns:
        选中的走法
    """
    selector = MoveSelector(llm_client)
    
    # 使用简化描述
    move_descriptions = [f"走法{i+1}" for i in range(len(legal_moves))]
    
    result = selector.select_moves(
        board_text=board_text,
        legal_moves=legal_moves,
        move_descriptions=move_descriptions,
        current_player="红方",
        move_count=1
    )
    
    return result.selected_moves[0]