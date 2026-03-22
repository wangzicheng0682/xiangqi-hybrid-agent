"""
LLM Prompt模板管理
所有与LLM交互的Prompt生成逻辑集中在此
"""
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum


class PromptMode(Enum):
    """Prompt模式"""
    EXPLOITATION = "exploitation"  # 利用模式: 选择最优走法
    EXPLORATION = "exploration"    # 探索模式: 尝试新走法
    EVALUATION = "evaluation"      # 评估模式: 评价局面


@dataclass
class MoveContext:
    """走法上下文信息"""
    board_text: str           # 棋盘文本表示
    legal_moves: List[str]    # 合法走法列表(坐标格式)
    move_descriptions: List[str]  # 走法描述(中文格式)
    current_player: str       # 当前行动方
    move_count: int          # 当前回合数
    game_phase: str          # 对局阶段(开局/中局/残局)


@dataclass
class ExperienceContext:
    """经验上下文信息"""
    similar_positions: List[Dict[str, Any]]  # 相似局面
    historical_moves: List[Dict[str, Any]]   # 历史走法
    win_rate: Optional[float] = None         # 胜率统计


class PromptBuilder:
    """Prompt构建器"""
    
    # 系统提示模板
    SYSTEM_PROMPT = """你是一个专业的中国象棋AI助手。
你的任务是分析棋局并从给定的合法走法中选择一个最佳走法。

核心原则:
1. 你只能从提供的合法走法列表中选择
2. 不要尝试判断走法的合法性,所有走法都已经过验证
3. 专注于战术和战略分析
4. 简洁回答,直接给出选择

你的回答格式必须严格遵守:
- 首先给出选择的走法编号(如: 1, 2, 3...)
- 然后简要说明理由(不超过100字)

示例回答:
3
理由: 此走法可以控制中路,为后续进攻创造条件。
"""

    # 利用模式提示
    EXPLOITATION_TEMPLATE = """## 当前局面

{board_text}

## 对局信息
- 当前行动方: {current_player}
- 回合数: {move_count}
- 对局阶段: {game_phase}

## 合法走法列表
{moves_list}

## 相似局面经验
{experience_section}

## 任务
请从上述合法走法中选择一个最优走法。
重点考虑:
1. 战术优势(将军、吃子、控制要点)
2. 战略布局(子力协调、阵型完整)
3. 历史经验(相似局面的成功走法)

请回答: 选择哪个走法编号?
"""

    # 探索模式提示
    EXPLORATION_TEMPLATE = """## 当前局面

{board_text}

## 对局信息
- 当前行动方: {current_player}
- 回合数: {move_count}
- 对局阶段: {game_phase}

## 合法走法列表
{moves_list}

## 历史尝试统计
{history_section}

## 任务 (探索模式)
请从合法走法中选择一个**较少尝试**或**有潜力但未充分探索**的走法。

探索策略:
1. 优先选择尝试次数少的走法
2. 考虑非常规但合理的走法
3. 避免重复选择已知劣势走法
4. 在保证不明显送子的前提下大胆尝试

请回答: 选择哪个走法编号?
"""

    # 评估模式提示
    EVALUATION_TEMPLATE = """## 局面评估任务

{board_text}

## 对局信息
- 当前行动方: {current_player}
- 回合数: {move_count}
- 对局阶段: {game_phase}

## 任务
请评估当前局面的优劣,从当前行动方的角度给出评分。

评估维度:
1. 子力优势: 双方子力对比
2. 位置优势: 子力位置、控制要点
3. 战术机会: 是否有将军、吃子等战术
4. 安全性: 己方将帅安全程度

请给出:
1. 评分: -100到100之间的整数(负数表示劣势,正数表示优势,0表示均势)
2. 简要分析: 不超过150字

回答格式:
评分: [数字]
分析: [文字说明]
"""

    def __init__(self):
        """初始化构建器"""
        pass
    
    def build_move_selection_prompt(
        self,
        context: MoveContext,
        mode: PromptMode = PromptMode.EXPLOITATION,
        experience: Optional[ExperienceContext] = None
    ) -> Dict[str, str]:
        """
        构建走法选择Prompt
        
        Args:
            context: 走法上下文
            mode: Prompt模式
            experience: 经验上下文(可选)
            
        Returns:
            包含system和user prompt的字典
        """
        # 格式化走法列表
        moves_list = self._format_moves_list(
            context.legal_moves,
            context.move_descriptions
        )
        
        # 根据模式选择模板
        if mode == PromptMode.EXPLOITATION:
            template = self.EXPLOITATION_TEMPLATE
            experience_section = self._format_experience(experience) if experience else "暂无相似局面经验"
            
            user_prompt = template.format(
                board_text=context.board_text,
                current_player=context.current_player,
                move_count=context.move_count,
                game_phase=context.game_phase,
                moves_list=moves_list,
                experience_section=experience_section
            )
        
        elif mode == PromptMode.EXPLORATION:
            template = self.EXPLORATION_TEMPLATE
            history_section = self._format_exploration_history(experience) if experience else "暂无历史数据"
            
            user_prompt = template.format(
                board_text=context.board_text,
                current_player=context.current_player,
                move_count=context.move_count,
                game_phase=context.game_phase,
                moves_list=moves_list,
                history_section=history_section
            )
        
        else:
            raise ValueError(f"不支持的模式: {mode}")
        
        return {
            "system": self.SYSTEM_PROMPT,
            "user": user_prompt
        }
    
    def build_evaluation_prompt(
        self,
        context: MoveContext
    ) -> Dict[str, str]:
        """
        构建局面评估Prompt
        
        Args:
            context: 走法上下文
            
        Returns:
            包含system和user prompt的字典
        """
        user_prompt = self.EVALUATION_TEMPLATE.format(
            board_text=context.board_text,
            current_player=context.current_player,
            move_count=context.move_count,
            game_phase=context.game_phase
        )
        
        return {
            "system": self.SYSTEM_PROMPT,
            "user": user_prompt
        }
    
    def build_simple_prompt(
        self,
        board_text: str,
        legal_moves: List[str],
        instruction: str = "请选择一个走法"
    ) -> Dict[str, str]:
        """
        构建简化版Prompt(用于快速测试)
        
        Args:
            board_text: 棋盘文本
            legal_moves: 合法走法
            instruction: 指令
            
        Returns:
            包含system和user prompt的字典
        """
        moves_list = "\n".join([
            f"{i+1}. {move}" for i, move in enumerate(legal_moves)
        ])
        
        user_prompt = f"""当前棋盘:
{board_text}

合法走法:
{moves_list}

{instruction}

请回答走法编号。
"""
        
        return {
            "system": self.SYSTEM_PROMPT,
            "user": user_prompt
        }
    
    # ============ 内部辅助方法 ============
    
    def _format_moves_list(
        self,
        moves: List[str],
        descriptions: List[str]
    ) -> str:
        """
        格式化走法列表
        
        Args:
            moves: 坐标格式走法
            descriptions: 中文描述
            
        Returns:
            格式化的字符串
        """
        if len(moves) != len(descriptions):
            # 如果描述数量不匹配,只显示坐标
            return "\n".join([
                f"{i+1}. {move}" for i, move in enumerate(moves)
            ])
        
        lines = []
        for i, (move, desc) in enumerate(zip(moves, descriptions), 1):
            lines.append(f"{i}. {move} ({desc})")
        
        return "\n".join(lines)
    
    def _format_experience(self, experience: Optional[ExperienceContext]) -> str:
        """
        格式化经验信息
        
        Args:
            experience: 经验上下文
            
        Returns:
            格式化的字符串
        """
        if not experience or not experience.similar_positions:
            return "暂无相似局面经验"
        
        lines = []
        
        # 胜率统计
        if experience.win_rate is not None:
            lines.append(f"相似局面胜率: {experience.win_rate:.1%}")
        
        # 历史成功走法
        if experience.historical_moves:
            lines.append("\n历史成功走法:")
            for i, move_data in enumerate(experience.historical_moves[:3], 1):
                move = move_data.get("move", "未知")
                reward = move_data.get("reward", 0)
                lines.append(f"  {i}. {move} (奖励: {reward:.2f})")
        
        return "\n".join(lines) if lines else "暂无详细经验数据"
    
    def _format_exploration_history(self, experience: Optional[ExperienceContext]) -> str:
        """
        格式化探索历史信息
        
        Args:
            experience: 经验上下文
            
        Returns:
            格式化的字符串
        """
        if not experience or not experience.historical_moves:
            return "暂无历史尝试记录"
        
        lines = []
        lines.append("各走法尝试统计:")
        
        # 统计各走法尝试次数
        move_counts = {}
        for move_data in experience.historical_moves:
            move = move_data.get("move", "未知")
            move_counts[move] = move_counts.get(move, 0) + 1
        
        # 排序显示
        sorted_moves = sorted(move_counts.items(), key=lambda x: x[1], reverse=True)
        for move, count in sorted_moves[:5]:
            lines.append(f"  - {move}: 尝试{count}次")
        
        return "\n".join(lines)


class PromptParser:
    """Prompt响应解析器"""
    
    @staticmethod
    def parse_move_selection(response: str, num_moves: int) -> Optional[int]:
        """
        解析走法选择响应
        
        Args:
            response: LLM响应文本
            num_moves: 合法走法总数
            
        Returns:
            选择的走法索引(0-based),解析失败返回None
        """
        # 移除空白字符
        response = response.strip()
        
        # 尝试提取数字
        import re
        
        # 模式1: 开头的数字
        match = re.match(r'^(\d+)', response)
        if match:
            move_num = int(match.group(1))
            # 转换为0-based索引
            move_idx = move_num - 1
            if 0 <= move_idx < num_moves:
                return move_idx
        
        # 模式2: "选择X" 或 "第X个"
        patterns = [
            r'选择\s*(\d+)',
            r'第\s*(\d+)\s*个',
            r'编号\s*(\d+)',
            r'走法\s*(\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response)
            if match:
                move_num = int(match.group(1))
                move_idx = move_num - 1
                if 0 <= move_idx < num_moves:
                    return move_idx
        
        return None
    
    @staticmethod
    def parse_evaluation(response: str) -> Optional[Dict[str, Any]]:
        """
        解析局面评估响应
        
        Args:
            response: LLM响应文本
            
        Returns:
            包含score和analysis的字典,解析失败返回None
        """
        import re
        
        # 提取评分
        score_pattern = r'评分\s*[:：]\s*(-?\d+)'
        score_match = re.search(score_pattern, response)
        
        if not score_match:
            return None
        
        score = int(score_match.group(1))
        
        # 提取分析
        analysis_pattern = r'分析\s*[:：]\s*(.+?)(?:\n|$)'
        analysis_match = re.search(analysis_pattern, response, re.DOTALL)
        
        analysis = analysis_match.group(1).strip() if analysis_match else ""
        
        return {
            "score": score,
            "analysis": analysis
        }


# ============ 便捷函数 ============

_builder = PromptBuilder()
_parser = PromptParser()


def create_move_prompt(
    context: MoveContext,
    mode: PromptMode = PromptMode.EXPLOITATION,
    experience: Optional[ExperienceContext] = None
) -> Dict[str, str]:
    """
    创建走法选择Prompt(便捷函数)
    
    Args:
        context: 走法上下文
        mode: 模式
        experience: 经验上下文
        
    Returns:
        Prompt字典
    """
    return _builder.build_move_selection_prompt(context, mode, experience)


def create_evaluation_prompt(context: MoveContext) -> Dict[str, str]:
    """
    创建评估Prompt(便捷函数)
    
    Args:
        context: 走法上下文
        
    Returns:
        Prompt字典
    """
    return _builder.build_evaluation_prompt(context)


def parse_move_response(response: str, num_moves: int) -> Optional[int]:
    """
    解析走法响应(便捷函数)
    
    Args:
        response: LLM响应
        num_moves: 走法总数
        
    Returns:
        走法索引
    """
    return _parser.parse_move_selection(response, num_moves)


def parse_evaluation_response(response: str) -> Optional[Dict[str, Any]]:
    """
    解析评估响应(便捷函数)
    
    Args:
        response: LLM响应
        
    Returns:
        评估结果字典
    """
    return _parser.parse_evaluation(response)


def create_prompt_builder() -> PromptBuilder:
    """工厂函数: 创建Prompt构建器"""
    return PromptBuilder()


def create_prompt_parser() -> PromptParser:
    """工厂函数: 创建Prompt解析器"""
    return PromptParser()
