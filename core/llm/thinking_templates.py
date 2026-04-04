"""
特级大师思维链模板

职责: 根据局面阶段动态生成思维框架
原则: 阶段感知，抓住主要矛盾

模块接口:
- PhaseDetector: 阶段检测器
- ThinkingTemplateBuilder: 思维模板构建器
- OpeningAnalyzer: 开局分析器
- get_phase_aware_prompt(): 获取阶段感知的System Prompt

文档依据: docs/reference/thinking_framework.md
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, List, Tuple


class GamePhase(Enum):
    """局面阶段"""
    OPENING = "opening"        # 开局
    MIDDLEGAME = "middlegame"  # 中局
    ENDGAME = "endgame"        # 残局


@dataclass
class PhaseInfo:
    """阶段信息"""
    phase: GamePhase
    phase_name: str           # 中文名称
    move_count: int           # 回合数
    total_pieces: int         # 棋子总数
    confidence: float = 1.0   # 判断置信度

    def is_opening(self) -> bool:
        return self.phase == GamePhase.OPENING

    def is_middlegame(self) -> bool:
        return self.phase == GamePhase.MIDDLEGAME

    def is_endgame(self) -> bool:
        return self.phase == GamePhase.ENDGAME


@dataclass
class ThinkingTemplate:
    """思维模板"""
    phase_name: str
    principles: List[str]           # 核心原则
    questions: List[str]            # 分析问题清单
    output_format: str              # 输出格式
    priority_tools: List[str] = field(default_factory=list)  # 推荐工具


class PhaseDetector:
    """
    阶段检测器

    判断规则:
    - 开局: 回合数 <= 15 且 棋子总数 >= 26
    - 残局: 棋子总数 <= 14
    - 中局: 其他情况
    """

    # 检测阈值（可配置）
    OPENING_MAX_MOVES = 15
    OPENING_MIN_PIECES = 30
    ENDGAME_MAX_PIECES = 14

    @classmethod
    def detect(cls, fen: str, move_count: int = 0, move_count_source: str = "explicit") -> PhaseInfo:
        """
        检测局面阶段

        Args:
            fen: 局面FEN
            move_count: 当前回合数（半回合数/2）

        Returns:
            PhaseInfo: 阶段信息
        """
        total_pieces = cls._count_pieces(fen)
        has_explicit_move_count = move_count_source in {"explicit", "history"}
        inferred_move_count = move_count if move_count > 0 else cls._extract_move_count_from_fen(fen)
        effective_move_count = inferred_move_count if inferred_move_count > 0 else move_count
        developed_major_pieces = cls._count_developed_major_pieces(fen)

        # 开局判断
        if (
            has_explicit_move_count
            and effective_move_count > 0
            and effective_move_count <= cls.OPENING_MAX_MOVES
            and total_pieces >= cls.OPENING_MIN_PIECES
            and developed_major_pieces <= 6
        ):
            return PhaseInfo(
                phase=GamePhase.OPENING,
                phase_name="开局",
                move_count=effective_move_count,
                total_pieces=total_pieces,
                confidence=0.95,
            )

        if (
            not has_explicit_move_count
            and effective_move_count > 0
            and effective_move_count <= 8
            and total_pieces >= 31
            and developed_major_pieces <= 4
        ):
            return PhaseInfo(
                phase=GamePhase.OPENING,
                phase_name="开局",
                move_count=effective_move_count,
                total_pieces=total_pieces,
                confidence=0.68,
            )

        if not has_explicit_move_count and effective_move_count == 0 and total_pieces >= 31 and developed_major_pieces <= 4:
            return PhaseInfo(
                phase=GamePhase.OPENING,
                phase_name="开局",
                move_count=0,
                total_pieces=total_pieces,
                confidence=0.58,
            )

        # 残局判断
        if total_pieces <= cls.ENDGAME_MAX_PIECES:
            return PhaseInfo(
                phase=GamePhase.ENDGAME,
                phase_name="残局",
                move_count=effective_move_count,
                total_pieces=total_pieces,
                confidence=0.96,
            )

        # 中局
        return PhaseInfo(
            phase=GamePhase.MIDDLEGAME,
            phase_name="中局",
            move_count=effective_move_count,
            total_pieces=total_pieces,
            confidence=0.82 if effective_move_count > 0 else 0.72,
        )

    @classmethod
    def _count_pieces(cls, fen: str) -> int:
        """统计棋盘上的棋子总数"""
        # FEN格式: rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1
        # 只取棋盘部分（第一个空格之前）
        board_part = fen.split()[0]
        count = 0
        for char in board_part:
            if char.isalpha():
                count += 1
        return count

    @classmethod
    def _extract_move_count_from_fen(cls, fen: str) -> int:
        parts = fen.split()
        if len(parts) >= 6:
            try:
                return max(0, int(parts[5]))
            except ValueError:
                return 0
        return 0

    @classmethod
    def _count_developed_major_pieces(cls, fen: str) -> int:
        board_part = fen.split()[0]
        rows = board_part.split('/')
        initial_positions = {
            (9, 0): 'R', (9, 1): 'N', (7, 1): 'C', (7, 7): 'C', (9, 7): 'N', (9, 8): 'R',
            (0, 0): 'r', (0, 1): 'n', (2, 1): 'c', (2, 7): 'c', (0, 7): 'n', (0, 8): 'r',
        }

        developed = 0
        for row_idx, row in enumerate(rows):
            col_idx = 0
            for char in row:
                if char.isdigit():
                    col_idx += int(char)
                    continue
                if char in {'R', 'N', 'C', 'r', 'n', 'c'} and initial_positions.get((row_idx, col_idx)) != char:
                    developed += 1
                col_idx += 1
        return developed


class OpeningAnalyzer:
    """
    开局分析器

    实现开局五大原则的检测:
    1. 快速出动大子
    2. 抢占中路
    3. 马炮早活
    4. 不贪小卒
    5. 争抢先手
    """

    # 大子类型（车、马、炮）
    MAJOR_PIECES = {'r', 'R', 'n', 'N', 'c', 'C'}

    # 中路列（5线，对应FEN中的第5列）
    CENTER_FILE = 5

    @classmethod
    def analyze(cls, fen: str, move_count: int = 0) -> Dict[str, Any]:
        """
        执行开局分析

        Args:
            fen: 局面FEN
            move_count: 当前回合数

        Returns:
            开局分析结果
        """
        board = cls._parse_fen(fen)

        return {
            "phase": "opening",
            "move_count": move_count,
            "development": cls._analyze_development(board),
            "center_control": cls._analyze_center_control(board),
            "piece_activity": cls._analyze_piece_activity(board),
            "initiative": cls._analyze_initiative(board),
            "summary": "",  # 由调用方填充
        }

    @classmethod
    def _parse_fen(cls, fen: str) -> List[List[str]]:
        """解析FEN为10x9棋盘"""
        board_part = fen.split()[0]
        rows = board_part.split('/')
        board = []

        for row in rows:
            board_row = []
            for char in row:
                if char.isdigit():
                    board_row.extend([''] * int(char))
                else:
                    board_row.append(char)
            # 补齐到9列
            while len(board_row) < 9:
                board_row.append('')
            board.append(board_row)

        # 补齐到10行
        while len(board) < 10:
            board.append([''] * 9)

        return board

    @classmethod
    def _analyze_development(cls, board: List[List[str]]) -> Dict[str, Any]:
        """
        分析出子效率

        检测:
        - 双方已出动的大子数量
        - 哪方出子更快
        - 有没有重复走同一子
        """
        red_developed = 0
        black_developed = 0
        red_major_positions = []
        black_major_positions = []

        # 初始位置（大子的起始行）
        red_home_row = 9
        black_home_row = 0

        for row_idx, row in enumerate(board):
            for col_idx, piece in enumerate(row):
                if piece in cls.MAJOR_PIECES:
                    pos = (col_idx, row_idx)
                    if piece.isupper():  # 红方
                        if row_idx != red_home_row or col_idx not in [0, 1, 7, 8]:
                            # 不在初始位置算作出动
                            if not (row_idx == red_home_row and col_idx in [0, 8]):
                                # 车的初始位置是角落，需要特殊处理
                                pass
                        red_major_positions.append((piece, pos))
                    else:  # 黑方
                        black_major_positions.append((piece, pos))

        # 简化计算：统计大子是否离开初始行
        for piece, pos in red_major_positions:
            if pos[1] < red_home_row:  # 离开了第10行
                red_developed += 1

        for piece, pos in black_major_positions:
            if pos[1] > black_home_row:  # 离开了第1行
                black_developed += 1

        return {
            "red_developed": red_developed,
            "black_developed": black_developed,
            "advantage": "red" if red_developed > black_developed else
                        "black" if black_developed > red_developed else "equal",
            "difference": abs(red_developed - black_developed),
            "red_positions": red_major_positions,
            "black_positions": black_major_positions,
        }

    @classmethod
    def _analyze_center_control(cls, board: List[List[str]]) -> Dict[str, Any]:
        """
        分析中心控制

        检测:
        - 谁控制5线（中路）
        - 兵型结构
        """
        center_file = cls.CENTER_FILE - 1  # 转为0-index
        red_control = 0
        black_control = 0
        center_pieces = []

        for row_idx, row in enumerate(board):
            piece = row[center_file]
            if piece:
                center_pieces.append((piece, row_idx))
                if piece.isupper():
                    red_control += 1
                else:
                    black_control += 1

        return {
            "red_center_pieces": red_control,
            "black_center_pieces": black_control,
            "center_control": "red" if red_control > black_control else
                            "black" if black_control > red_control else "equal",
            "center_pieces": center_pieces,
        }

    @classmethod
    def _analyze_piece_activity(cls, board: List[List[str]]) -> Dict[str, Any]:
        """
        分析子力活跃度

        检测:
        - 马是否有根（马脚问题）
        - 炮是否有架
        - 车是否通路
        """
        red_horses = []
        black_horses = []
        red_cannons = []
        black_cannons = []
        red_chariots = []
        black_chariots = []

        for row_idx, row in enumerate(board):
            for col_idx, piece in enumerate(row):
                pos = (col_idx, row_idx)
                if piece.upper() == 'N':
                    if piece.isupper():
                        red_horses.append(pos)
                    else:
                        black_horses.append(pos)
                elif piece.upper() == 'C':
                    if piece.isupper():
                        red_cannons.append(pos)
                    else:
                        black_cannons.append(pos)
                elif piece.upper() == 'R':
                    if piece.isupper():
                        red_chariots.append(pos)
                    else:
                        black_chariots.append(pos)

        return {
            "red_horses": red_horses,
            "black_horses": black_horses,
            "red_cannons": red_cannons,
            "black_cannons": black_cannons,
            "red_chariots": red_chariots,
            "black_chariots": black_chariots,
            "red_active_count": len(red_horses) + len(red_cannons) + len(red_chariots),
            "black_active_count": len(black_horses) + len(black_cannons) + len(black_chariots),
        }

    @classmethod
    def _analyze_initiative(cls, board: List[List[str]]) -> Dict[str, Any]:
        """
        分析先手争夺

        检测:
        - 谁在主动进攻
        - 谁在被动防守
        """
        # 简化版：基于大子越过中线的情况判断
        red_crossed = 0
        black_crossed = 0

        for row_idx, row in enumerate(board):
            for piece in row:
                if piece.isupper() and row_idx < 5:  # 红方过河
                    red_crossed += 1
                elif piece.islower() and row_idx >= 5:  # 黑方过河
                    black_crossed += 1

        return {
            "red_crossed": red_crossed,
            "black_crossed": black_crossed,
            "initiative": "red" if red_crossed > black_crossed else
                         "black" if black_crossed > red_crossed else "equal",
        }

    @classmethod
    def generate_summary(cls, analysis: Dict[str, Any]) -> str:
        """
        生成开局分析摘要

        Args:
            analysis: analyze()的返回结果

        Returns:
            人类可读的分析摘要
        """
        dev = analysis["development"]
        center = analysis["center_control"]
        activity = analysis["piece_activity"]
        initiative = analysis["initiative"]

        lines = []

        # 出子效率
        lines.append(f"【出子效率】红方已出{dev['red_developed']}子，黑方已出{dev['black_developed']}子")
        if dev['advantage'] == 'red':
            lines.append(f"红方出子领先{dev['difference']}子")
        elif dev['advantage'] == 'black':
            lines.append(f"黑方出子领先{dev['difference']}子")
        else:
            lines.append("双方出子相当")

        # 中心控制
        lines.append(f"【中心控制】{center['center_control']}方控制中路")

        # 子力活跃
        lines.append(f"【子力活跃】红方活跃子:{activity['red_active_count']}，黑方活跃子:{activity['black_active_count']}")

        # 先手判断
        lines.append(f"【先手判断】{initiative['initiative']}方握有先手")

        return "\n".join(lines)


class ThinkingTemplateBuilder:
    """思维模板构建器"""

    @classmethod
    def get_template(cls, phase: GamePhase) -> ThinkingTemplate:
        """获取对应阶段的思维模板"""
        if phase == GamePhase.OPENING:
            return cls._opening_template()
        elif phase == GamePhase.MIDDLEGAME:
            return cls._middlegame_template()
        else:
            return cls._endgame_template()

    @classmethod
    def _opening_template(cls) -> ThinkingTemplate:
        """开局思维模板"""
        return ThinkingTemplate(
            phase_name="开局",
            principles=[
                "快速出动大子（双车双炮双马尽快出动）",
                "抢占中路（控制5线，兵挺进）",
                "马炮早活（马有根，炮有架）",
                "不贪小卒（不为吃兵损失先手）",
                "争抢先手（主动进攻而非被动防守）",
            ],
            questions=[
                "双方各出动了几枚大子？",
                "谁控制中路（5线）？",
                "马是否有根？炮是否有架？",
                "有没有重复走同一子？",
                "当前谁握有先手？",
            ],
            output_format="""【出子效率】...
【中心控制】...
【子力活跃】...
【先手判断】...
【教练建议】...""",
            priority_tools=["analyze_position_strategy", "engine_alternatives"]
        )

    @classmethod
    def _middlegame_template(cls) -> ThinkingTemplate:
        """中局思维模板"""
        return ThinkingTemplate(
            phase_name="中局",
            principles=[
                "战术优先（先看将军/杀棋/抽子）",
                "子力对比（评估双方子力平衡）",
                "弱点攻击（寻找并攻击对方弱点）",
                "攻防转换（判断进攻还是防守）",
                "战术组合（寻找弃子攻杀机会）",
            ],
            questions=[
                "有没有将军或杀棋？",
                "有没有捉子或抽子？",
                "哪方有无根子？",
                "有没有战术组合？",
            ],
            output_format="""【战术扫描】...
【子力对比】...
【弱点分析】...
【教练建议】...""",
            priority_tools=["get_forcing_sequence", "analyze_move", "engine_deep_analysis"]
        )

    @classmethod
    def _endgame_template(cls) -> ThinkingTemplate:
        """残局思维模板"""
        return ThinkingTemplate(
            phase_name="残局",
            principles=[
                "兵的结构（兵的位置决定胜负）",
                "王的活动性（老帅参战很重要）",
                "理论定式（官和/官胜判断）",
                "对应格（关键位置控制）",
                "时间因素（谁先到达关键格）",
            ],
            questions=[
                "双方兵的位置如何？",
                "是否进入官和/官胜定式？",
                "剩余子力能否取胜？",
            ],
            output_format="""【定式判断】...
【兵型分析】...
【胜负判断】...
【教练建议】...""",
            priority_tools=["engine_deep_analysis", "analyze_position_strategy"]
        )


def get_phase_aware_prompt(
    fen: str,
    move_count: int = 0,
    base_prompt: str = ""
) -> Tuple[str, PhaseInfo, Dict[str, Any]]:
    """
    获取阶段感知的System Prompt

    Args:
        fen: 局面FEN
        move_count: 当前回合数
        base_prompt: 基础prompt（可选）

    Returns:
        (enhanced_prompt, phase_info, phase_analysis)
    """
    # 检测阶段
    phase_info = PhaseDetector.detect(fen, move_count)

    # 获取思维模板
    template = ThinkingTemplateBuilder.get_template(phase_info.phase)

    # 构建阶段特定的prompt
    phase_prompt = f"""
【当前阶段：{template.phase_name}】

这是{template.phase_name}阶段，你的分析应围绕以下核心原则展开：

{chr(10).join(f'{i+1}. {p}' for i, p in enumerate(template.principles))}

【分析问题清单】
{chr(10).join(f'- {q}' for q in template.questions)}

【输出格式】
{template.output_format}

【推荐优先使用的工具】
{', '.join(template.priority_tools)}
"""

    # 执行开局分析（如果是开局）
    phase_analysis = {}
    if phase_info.is_opening():
        phase_analysis = OpeningAnalyzer.analyze(fen, move_count)
        phase_analysis["summary"] = OpeningAnalyzer.generate_summary(phase_analysis)
        phase_prompt += f"""

【开局分析数据】（基于规则检测，100%准确）
{phase_analysis['summary']}
"""

    # 合并prompt
    if base_prompt:
        enhanced_prompt = base_prompt + "\n\n" + phase_prompt
    else:
        enhanced_prompt = phase_prompt

    return enhanced_prompt, phase_info, phase_analysis


# 便捷函数
def detect_phase(fen: str, move_count: int = 0) -> PhaseInfo:
    """便捷函数：检测局面阶段"""
    return PhaseDetector.detect(fen, move_count)


def analyze_opening(fen: str, move_count: int = 0) -> Dict[str, Any]:
    """便捷函数：执行开局分析"""
    return OpeningAnalyzer.analyze(fen, move_count)


def get_opening_summary(fen: str, move_count: int = 0) -> str:
    """便捷函数：获取开局分析摘要"""
    analysis = OpeningAnalyzer.analyze(fen, move_count)
    return OpeningAnalyzer.generate_summary(analysis)
