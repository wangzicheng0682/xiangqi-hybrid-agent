"""
Agent工具函数 - 深度思考模式

这些工具供LLM Agent在深度思考模式下调用，用于主动分析棋局。

设计原则:
- 原子化：每个工具只做一件事
- 可组合：工具之间可以串联使用
- 返回结构化：方便LLM理解和展示
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.rules.tactical_detector import TacticalDetector
from core.rules.xiangqi_rules import XiangqiRulesEngine


@dataclass
class ToolResult:
    """工具调用结果"""
    success: bool
    data: Dict[str, Any]
    message: str
    thinking_hint: str  # 用于展示思考过程


class AgentTools:
    """Agent可调用的工具集"""

    PIECE_NAMES = {
        'K': ('帅', '红'), 'k': ('将', '黑'),
        'A': ('仕', '红'), 'a': ('士', '黑'),
        'B': ('相', '红'), 'b': ('象', '黑'),
        'N': ('马', '红'), 'n': ('马', '黑'),
        'R': ('车', '红'), 'r': ('车', '黑'),
        'C': ('炮', '红'), 'c': ('炮', '黑'),
        'P': ('兵', '红'), 'p': ('卒', '黑'),
    }

    PIECE_VALUES = {
        'k': 10000, 'r': 900, 'n': 450, 'c': 450, 'b': 200, 'a': 200, 'p': 100
    }

    def __init__(self):
        self.detector = TacticalDetector()
        self.rules_engine = XiangqiRulesEngine()

    # =========================================================================
    # 第一类：棋子关系查询（原子工具）
    # =========================================================================

    def get_piece_attacks(self, fen: str, piece: str) -> ToolResult:
        """
        查询某棋子的攻击范围

        Args:
            fen: 局面FEN
            piece: 棋子标识，如 "红车" "r" "(5,8)" 或组合 "红车(5,8)"

        Returns:
            ToolResult: 包含攻击范围信息
        """
        try:
            board = self.detector._fen_to_board(fen)
            pos = self._parse_piece_identifier(board, piece)

            if not pos:
                return ToolResult(
                    success=False,
                    data={},
                    message=f"未找到棋子: {piece}",
                    thinking_hint=f"查找棋子 {piece} 失败"
                )

            row, col = pos
            piece_char = board[row][col]
            piece_name = self._get_piece_name(piece_char)

            attacks = self.detector._get_attacks(board, row, col)

            # 格式化攻击目标
            attack_list = []
            total_value = 0
            for ar, ac in attacks:
                target = board[ar][ac]
                if target:
                    target_name = self._get_piece_name(target)
                    attack_list.append(f"{target_name}({ac+1},{10-ar})")
                    total_value += self.PIECE_VALUES.get(target.lower(), 0)
                else:
                    attack_list.append(f"空位({ac+1},{10-ar})")

            # 分离敌方棋子和空位
            enemy_targets = [a for a in attack_list if not a.startswith("空位")]
            empty_targets = [a for a in attack_list if a.startswith("空位")]

            # 构建精确的message
            if enemy_targets:
                target_detail = f"攻击敌方: {', '.join(enemy_targets[:5])}"
                if len(enemy_targets) > 5:
                    target_detail += f"等{len(enemy_targets)}子"
            else:
                target_detail = f"攻击{len(empty_targets)}个空位，无敌方目标"

            return ToolResult(
                success=True,
                data={
                    "piece": f"{piece_name}({col+1},{10-row})",
                    "attacks": attack_list,
                    "enemy_targets": enemy_targets,
                    "empty_targets": empty_targets,
                    "attack_count": len(attacks),
                    "attack_value": total_value,
                    "has_valuable_target": total_value > 0
                },
                message=f"{piece_name}: {target_detail}",
                thinking_hint=f"分析{piece_name}的攻击范围，发现{len(enemy_targets)}个敌方目标"
            )

        except Exception as e:
            return ToolResult(
                success=False,
                data={},
                message=f"查询失败: {str(e)}",
                thinking_hint=f"查询棋子攻击范围时出错"
            )

    def get_piece_defenders(self, fen: str, piece: str) -> ToolResult:
        """
        查询谁在保护某个棋子

        Args:
            fen: 局面FEN
            piece: 棋子标识

        Returns:
            ToolResult: 包含防守信息
        """
        try:
            board = self.detector._fen_to_board(fen)
            pos = self._parse_piece_identifier(board, piece)

            if not pos:
                return ToolResult(
                    success=False,
                    data={},
                    message=f"未找到棋子: {piece}",
                    thinking_hint=f"查找棋子 {piece} 失败"
                )

            row, col = pos
            piece_char = board[row][col]
            piece_name = self._get_piece_name(piece_char)
            is_red = self.detector._is_red(piece_char)

            # 查找所有保护者
            defenders = []
            for r in range(10):
                for c in range(9):
                    p = board[r][c]
                    if p and self.detector._is_red(p) == is_red and (r, c) != (row, col):
                        attacks = self.detector._get_attacks(board, r, c)
                        if (row, col) in attacks:
                            defender_name = self._get_piece_name(p)
                            defenders.append(f"{defender_name}({c+1},{10-r})")

            is_well_protected = len(defenders) >= 2

            return ToolResult(
                success=True,
                data={
                    "piece": f"{piece_name}({col+1},{10-row})",
                    "defenders": defenders,
                    "defender_count": len(defenders),
                    "is_well_protected": is_well_protected,
                    "is_unprotected": len(defenders) == 0
                },
                message=f"{piece_name}被{len(defenders)}个子保护",
                thinking_hint=f"分析{piece_name}的防守情况，发现{len(defenders)}个保护者"
            )

        except Exception as e:
            return ToolResult(
                success=False,
                data={},
                message=f"查询失败: {str(e)}",
                thinking_hint=f"查询棋子防守情况时出错"
            )

    def get_threats_to_piece(self, fen: str, piece: str) -> ToolResult:
        """
        查询谁在威胁某个棋子

        Args:
            fen: 局面FEN
            piece: 棋子标识

        Returns:
            ToolResult: 包含威胁信息
        """
        try:
            board = self.detector._fen_to_board(fen)
            pos = self._parse_piece_identifier(board, piece)

            if not pos:
                return ToolResult(
                    success=False,
                    data={},
                    message=f"未找到棋子: {piece}",
                    thinking_hint=f"查找棋子 {piece} 失败"
                )

            row, col = pos
            piece_char = board[row][col]
            piece_name = self._get_piece_name(piece_char)
            is_red = self.detector._is_red(piece_char)

            # 查找所有威胁者
            threats = []
            for r in range(10):
                for c in range(9):
                    p = board[r][c]
                    if p and self.detector._is_red(p) != is_red:
                        attacks = self.detector._get_attacks(board, r, c)
                        if (row, col) in attacks:
                            threat_name = self._get_piece_name(p)
                            threats.append({
                                "attacker": f"{threat_name}({c+1},{10-r})",
                                "can_capture": True
                            })

            # 判断危险等级
            if len(threats) >= 2:
                danger_level = "high"
            elif len(threats) == 1:
                danger_level = "medium"
            else:
                danger_level = "low"

            return ToolResult(
                success=True,
                data={
                    "piece": f"{piece_name}({col+1},{10-row})",
                    "threats": threats,
                    "threat_count": len(threats),
                    "danger_level": danger_level,
                    "is_safe": len(threats) == 0
                },
                message=f"{piece_name}受到{len(threats)}个威胁，危险等级: {danger_level}",
                thinking_hint=f"分析{piece_name}面临的威胁，发现{len(threats)}个攻击者"
            )

        except Exception as e:
            return ToolResult(
                success=False,
                data={},
                message=f"查询失败: {str(e)}",
                thinking_hint=f"查询棋子威胁情况时出错"
            )

    def get_piece_relations(self, fen: str, piece: str) -> ToolResult:
        """
        综合查询：攻击、防守、威胁一站式返回

        Args:
            fen: 局面FEN
            piece: 棋子标识

        Returns:
            ToolResult: 包含完整关系信息
        """
        try:
            board = self.detector._fen_to_board(fen)
            pos = self._parse_piece_identifier(board, piece)

            if not pos:
                return ToolResult(
                    success=False,
                    data={},
                    message=f"未找到棋子: {piece}",
                    thinking_hint=f"查找棋子 {piece} 失败"
                )

            # 组合三个查询结果
            attacks_result = self.get_piece_attacks(fen, piece)
            defenders_result = self.get_piece_defenders(fen, piece)
            threats_result = self.get_threats_to_piece(fen, piece)

            # 生成精确摘要 - 包含具体威胁来源
            summary_parts = []

            # 攻击信息：包含具体目标
            if attacks_result.success and attacks_result.data.get("enemy_targets"):
                targets = attacks_result.data["enemy_targets"][:3]
                summary_parts.append(f"可攻击: {', '.join(targets)}")

            # 威胁信息：包含具体威胁来源
            if threats_result.success and threats_result.data.get("threat_count", 0) > 0:
                threat_names = [t["attacker"] for t in threats_result.data.get("threats", [])[:3]]
                summary_parts.append(f"被威胁: {', '.join(threat_names)}")

            # 保护信息
            if defenders_result.success and defenders_result.data.get("is_unprotected"):
                summary_parts.append("无根(无保护)")
            elif defenders_result.success and defenders_result.data.get("defender_count", 0) > 0:
                summary_parts.append(f"有{defenders_result.data['defender_count']}子保护")

            summary = " | ".join(summary_parts) if summary_parts else "位置安全，无明显威胁"

            return ToolResult(
                success=True,
                data={
                    "piece": attacks_result.data.get("piece", piece),
                    "attacks": attacks_result.data.get("attacks", []),
                    "enemy_targets": attacks_result.data.get("enemy_targets", []),
                    "attack_value": attacks_result.data.get("attack_value", 0),
                    "defended_by": defenders_result.data.get("defenders", []),
                    "defender_count": defenders_result.data.get("defender_count", 0),
                    "threatened_by": [t["attacker"] for t in threats_result.data.get("threats", [])],
                    "threat_count": threats_result.data.get("threat_count", 0),
                    "danger_level": threats_result.data.get("danger_level", "low"),
                    "is_unprotected": defenders_result.data.get("is_unprotected", False),
                    "summary": summary
                },
                message=f"综合分析: {summary}",
                thinking_hint=f"综合分析{piece}的关系网络"
            )

        except Exception as e:
            return ToolResult(
                success=False,
                data={},
                message=f"查询失败: {str(e)}",
                thinking_hint=f"综合查询棋子关系时出错"
            )

    # =========================================================================
    # 第二类：走法分析工具
    # =========================================================================

    def analyze_move(self, fen: str, move: str) -> ToolResult:
        """
        深度分析某步棋的效果

        Args:
            fen: 走法前的局面FEN
            move: UCI格式走法 (如 "h2e2")

        Returns:
            ToolResult: 包含走法分析结果
        """
        try:
            board = self.detector._fen_to_board(fen)
            is_red_turn = self.detector._is_red_turn(fen)

            # 解析走法
            (from_row, from_col), (to_row, to_col) = self.detector._parse_uci(move)
            moving_piece = board[from_row][from_col]

            if not moving_piece:
                return ToolResult(
                    success=False,
                    data={},
                    message=f"无效走法: {move}",
                    thinking_hint=f"解析走法 {move} 失败"
                )

            piece_name = self._get_piece_name(moving_piece)
            move_chinese = self._to_chinese_move(board, move, moving_piece)

            # 执行走法
            new_board = self.detector._apply_move(board, move)

            # 分析走法质量
            quality_tags = self.detector.detect_move_quality(fen, move)
            detected_tags = [t.tag.name for t in quality_tags if t.detected]

            # 检测是否是开局阶段（简化判断：看棋子数量）
            piece_count = sum(1 for r in range(10) for c in range(9) if board[r][c])
            is_opening = piece_count >= 28

            # 开局走法检测
            opening_move_type = None

            # 1. 中路控制（炮移动到5线）
            if moving_piece.upper() == 'C' and to_col == 4:
                if is_opening:
                    opening_move_type = "center_cannon"  # 当头炮

            # 2. 屏风马（马跳到3路或7路的防守位置）
            if moving_piece.upper() == 'N' and is_opening:
                # 红马跳到(3,3)或(7,3)，对应board的(row=7, col=2)或(row=7, col=6)
                # 黑马跳到(3,8)或(7,8)，对应board的(row=2, col=2)或(row=2, col=6)
                if is_red_turn:
                    if (to_col, to_row) in [(2, 7), (6, 7)]:  # 红马跳到防守位置
                        opening_move_type = "screen_horse"  # 屏风马
                else:
                    if (to_col, to_row) in [(2, 2), (6, 2)]:  # 黑马跳到防守位置
                        opening_move_type = "screen_horse"  # 屏风马

            # 3. 仙人指路（兵/卒挺进三或七路线）
            if moving_piece.upper() == 'P' and is_opening:
                # 检测是否是从原始位置前进
                if abs(to_row - from_row) == 1 and from_col == to_col:
                    # 检测是否是三路或七路兵
                    if from_col in [2, 6]:  # 三路或七路（索引2和6）
                        opening_move_type = "immortal_finger"  # 仙人指路

            # 4. 出车（车从原始位置出动）
            if moving_piece.upper() == 'R' and is_opening:
                # 检测是否是从底线原始位置移动
                if (is_red_turn and from_row == 9) or (not is_red_turn and from_row == 0):
                    if from_col in [0, 8]:  # 左右车的原始位置
                        opening_move_type = "chariot_deployment"  # 出车

            # 5. 飞相局（相飞到中路保护）
            if moving_piece.upper() == 'B' and is_opening:
                if to_col == 4:  # 飞到中路
                    opening_move_type = "elephant_defense"  # 飞相局

            # 确定走法质量
            if "move_is_blunder" in detected_tags:
                quality = "blunder"
            elif "move_gives_check" in detected_tags or "move_is_capture" in detected_tags:
                quality = "excellent"
            elif opening_move_type in ["center_cannon", "screen_horse", "chariot_deployment"]:
                quality = "excellent"  # 开局核心走法
            elif opening_move_type in ["immortal_finger", "elephant_defense"]:
                quality = "good"  # 开局稳健走法
            elif "move_defends_piece" in detected_tags or "move_escapes_threat" in detected_tags:
                quality = "good"
            elif "move_improves_position" in detected_tags:
                quality = "good"
            else:
                quality = "ok"

            # 收集变化
            changes = {
                "material_delta": 0,
                "new_threats_created": [],
                "threats_avoided": [],
                "position_improvement": 0
            }

            for t in quality_tags:
                if t.detected and t.metadata:
                    if t.tag.name == "move_is_capture":
                        changes["material_delta"] = t.metadata.get("captured_value", 0)
                    elif t.tag.name == "move_improves_position":
                        changes["position_improvement"] = t.metadata.get("improvement", 0)
                    elif t.tag.name == "move_escapes_threat":
                        changes["threats_avoided"].append("成功逃脱攻击")

            # 生成解释（优先使用更准确的描述）
            why_parts = []
            if "move_is_capture" in detected_tags:
                why_parts.append(f"吃子得{changes['material_delta']}分")

            # 开局走法描述（优先级最高）
            if opening_move_type == "center_cannon":
                why_parts.append("当头炮控制中路，威胁对方中卒")
            elif opening_move_type == "screen_horse":
                why_parts.append("屏风马巩固防守，准备反击")
            elif opening_move_type == "immortal_finger":
                why_parts.append("仙人指路试探虚实，灵活多变")
            elif opening_move_type == "chariot_deployment":
                why_parts.append("快速出车，抢占要道")
            elif opening_move_type == "elephant_defense":
                why_parts.append("飞相固防，稳扎稳打")

            # 将军描述（如果没有开局走法描述才单独显示）
            if "move_gives_check" in detected_tags:
                if not opening_move_type:
                    why_parts.append("将军对方")
                # 如果有开局走法，将军是额外效果，在后面补充
                elif opening_move_type:
                    why_parts.append("兼有将军")

            if "move_defends_piece" in detected_tags:
                why_parts.append("保护己方棋子")
            if "move_escapes_threat" in detected_tags:
                why_parts.append("逃脱威胁")
            if "move_improves_position" in detected_tags:
                why_parts.append(f"活跃度提升{changes['position_improvement']}点")

            why = "，".join(why_parts) if why_parts else "正常走法"

            return ToolResult(
                success=True,
                data={
                    "move": move,
                    "move_chinese": move_chinese,
                    "piece": piece_name,
                    "quality": quality,
                    "quality_tags": detected_tags,
                    "changes": changes,
                    "why": why
                },
                message=f"{move_chinese}: {quality} - {why}",
                thinking_hint=f"分析走法 {move_chinese}，评估为 {quality}"
            )

        except Exception as e:
            return ToolResult(
                success=False,
                data={},
                message=f"分析失败: {str(e)}",
                thinking_hint=f"分析走法时出错"
            )

    def compare_moves(self, fen: str, moves: List[str]) -> ToolResult:
        """
        对比多步棋的优劣

        Args:
            fen: 局面FEN
            moves: UCI格式走法列表

        Returns:
            ToolResult: 包含对比结果
        """
        try:
            comparisons = []

            for move in moves:
                result = self.analyze_move(fen, move)
                if result.success:
                    comparisons.append({
                        "move": move,
                        "move_chinese": result.data.get("move_chinese", move),
                        "quality": result.data.get("quality", "unknown"),
                        "score": self._quality_to_score(result.data.get("quality", "ok")),
                        "pros": result.data.get("why", "").split("，") if result.data.get("why") else [],
                        "cons": []
                    })

            # 排序找出最佳
            if comparisons:
                comparisons.sort(key=lambda x: x["score"], reverse=True)
                best = comparisons[0]["move"]
                reason = comparisons[0]["pros"][0] if comparisons[0]["pros"] else "综合评估最优"
            else:
                best = None
                reason = "无可比较的走法"

            return ToolResult(
                success=True,
                data={
                    "comparisons": comparisons,
                    "best": best,
                    "reason": reason
                },
                message=f"对比{len(comparisons)}步棋，最佳: {best}",
                thinking_hint=f"对比分析{len(moves)}步候选走法"
            )

        except Exception as e:
            return ToolResult(
                success=False,
                data={},
                message=f"对比失败: {str(e)}",
                thinking_hint=f"对比走法时出错"
            )

    def get_forcing_sequence(self, fen: str, move: str, depth: int = 3) -> ToolResult:
        """
        分析走法后的强制序列

        Args:
            fen: 走法前的局面FEN
            move: UCI格式走法
            depth: 分析深度

        Returns:
            ToolResult: 包含强制序列
        """
        try:
            board = self.detector._fen_to_board(fen)
            is_red_turn = self.detector._is_red_turn(fen)

            sequence = []
            current_board = board
            current_turn = is_red_turn
            current_fen = fen

            # 执行第一步
            new_board = self.detector._apply_move(current_board, move)
            move_chinese = self._to_chinese_move(current_board, move, current_board[self.detector._parse_uci(move)[0][0]][self.detector._parse_uci(move)[0][1]])

            # 检查是否将军
            gives_check = self.detector._is_in_check(new_board, not current_turn)

            sequence.append({
                "move": move,
                "move_chinese": move_chinese,
                "type": "check" if gives_check else "normal",
                "must_respond": gives_check
            })

            is_forcing = gives_check

            return ToolResult(
                success=True,
                data={
                    "is_forcing": is_forcing,
                    "sequence": sequence,
                    "depth_analyzed": 1,
                    "outcome": "形成将军，对方必须应将" if is_forcing else "非强制序列"
                },
                message=f"分析完成: {'强制序列' if is_forcing else '非强制'}",
                thinking_hint=f"分析走法后的强制序列"
            )

        except Exception as e:
            return ToolResult(
                success=False,
                data={},
                message=f"分析失败: {str(e)}",
                thinking_hint=f"分析强制序列时出错"
            )

    # =========================================================================
    # 第三类：引擎深度分析
    # =========================================================================

    def engine_deep_analysis(self, fen: str, depth: int = 20) -> ToolResult:
        """
        引擎深度分析

        Args:
            fen: 局面FEN
            depth: 分析深度

        Returns:
            ToolResult: 包含引擎分析结果
        """
        try:
            # 尝试导入引擎
            try:
                from core.engine import PikafishEngine
                engine = PikafishEngine()

                result = engine.analyze(fen, depth=depth)
                # EngineResult 是 dataclass，用属性访问而非字典
                eval_cp = int(result.score * 100) if result.score else 0  # score是浮点，转为cp
                best_move = result.bestmove if result.bestmove else ""
                best_line = result.pv if result.pv else []

                # 转换评估为人类可读
                if eval_cp > 500:
                    eval_human = "红方胜势"
                elif eval_cp > 200:
                    eval_human = "红方明显优势"
                elif eval_cp > 50:
                    eval_human = "红方略优"
                elif eval_cp > -50:
                    eval_human = "均势"
                elif eval_cp > -200:
                    eval_human = "黑方略优"
                elif eval_cp > -500:
                    eval_human = "黑方明显优势"
                else:
                    eval_human = "黑方胜势"

                # 判断是否关键局面
                critical = abs(eval_cp) > 100

            except Exception as e:
                # 引擎不可用时返回基本信息
                eval_cp = 0
                eval_human = "引擎不可用"
                best_move = ""
                best_line = []
                critical = False

            return ToolResult(
                success=True,
                data={
                    "eval_cp": eval_cp,
                    "eval_human": eval_human,
                    "best_move": best_move,
                    "best_line": best_line[:5] if best_line else [],
                    "critical_position": critical,
                    "depth": depth
                },
                message=f"引擎分析: {eval_human} ({eval_cp}分)",
                thinking_hint=f"引擎深度分析(depth={depth})"
            )

        except Exception as e:
            return ToolResult(
                success=False,
                data={},
                message=f"引擎分析失败: {str(e)}",
                thinking_hint=f"引擎分析时出错"
            )

    def engine_alternatives(self, fen: str, top_n: int = 3) -> ToolResult:
        """
        引擎候选走法对比

        Args:
            fen: 局面FEN
            top_n: 返回的候选数量

        Returns:
            ToolResult: 包含候选走法
        """
        try:
            try:
                from core.engine import PikafishEngine
                engine = PikafishEngine()

                # 获取多个候选
                moves_data = []
                # 这里简化处理，实际引擎可能需要多次调用
                result = engine.analyze(fen, depth=18)
                best_move = result.bestmove if result.bestmove else ""
                eval_cp = int(result.score) if result.score else 0

                if best_move:
                    move_chinese = self._to_chinese_move_from_fen(fen, best_move)
                    moves_data.append({
                        "move": best_move,
                        "move_chinese": move_chinese,
                        "eval_cp": eval_cp,
                        "explanation": self._explain_move(fen, best_move),
                        "risk": "low" if abs(eval_cp) < 100 else "medium"
                    })

                recommendation = f"{best_move}是最佳选择" if best_move else "无法获取推荐"

            except Exception:
                moves_data = []
                recommendation = "引擎不可用"

            return ToolResult(
                success=True,
                data={
                    "moves": moves_data,
                    "top_n": top_n,
                    "recommendation": recommendation
                },
                message=f"获取{len(moves_data)}个候选走法",
                thinking_hint=f"获取引擎top{top_n}候选走法"
            )

        except Exception as e:
            return ToolResult(
                success=False,
                data={},
                message=f"获取候选失败: {str(e)}",
                thinking_hint=f"获取候选走法时出错"
            )

    # =========================================================================
    # 第四类：局面战略分析
    # =========================================================================

    def analyze_position_strategy(self, fen: str) -> ToolResult:
        """
        局面战略分析

        Args:
            fen: 局面FEN

        Returns:
            ToolResult: 包含战略分析
        """
        try:
            board = self.detector._fen_to_board(fen)
            is_red_turn = self.detector._is_red_turn(fen)

            # 获取静态检测结果
            static_result = self.detector.detect_static(fen)
            detected_tags = [t.tag.name for t in static_result.tags if t.detected]

            # 判断阶段
            if "phase_opening" in detected_tags:
                phase = "开局"
            elif "phase_endgame" in detected_tags:
                phase = "残局"
            else:
                phase = "中局"

            # 判断主动权
            initiative = "均势"
            if "has_initiative" in detected_tags:
                initiative = "红方" if is_red_turn else "黑方"

            # 将帅安全
            king_safety = {"red": "安全", "black": "安全"}
            if "king_safety_critical" in detected_tags:
                king_safety["red" if is_red_turn else "black"] = "有隐患"

            # 提取关键特征
            key_features = []
            if "controls_open_file" in detected_tags:
                key_features.append("控制开放线")
            if "has_active_pieces" in detected_tags:
                key_features.append("子力活跃")
            if "piece_coordination" in detected_tags:
                key_features.append("子力协同")
            if "is_attack_unprotected" in detected_tags:
                key_features.append("存在攻击无根子")
            if "is_pinned" in detected_tags:
                key_features.append("存在牵制")
            if "cannon_battery" in detected_tags:
                key_features.append("重炮阵型")

            if not key_features:
                key_features.append("局面相对平稳")

            # 生成建议计划
            suggested_plans = []
            if is_red_turn:
                if "has_initiative" in detected_tags:
                    suggested_plans.append("红方应保持主动，寻找进攻机会")
                if "is_attack_unprotected" in detected_tags:
                    suggested_plans.append("红方可以捉对方无根子")
            else:
                if "has_initiative" in detected_tags:
                    suggested_plans.append("黑方应保持主动，寻找进攻机会")

            if not suggested_plans:
                suggested_plans.append("稳步发展，等待时机")

            return ToolResult(
                success=True,
                data={
                    "phase": phase,
                    "initiative": initiative,
                    "king_safety": king_safety,
                    "key_features": key_features,
                    "suggested_plans": suggested_plans,
                    "detected_tags": detected_tags
                },
                message=f"战略分析: {phase}，{initiative}握有主动权",
                thinking_hint=f"综合分析局面战略特征"
            )

        except Exception as e:
            return ToolResult(
                success=False,
                data={},
                message=f"分析失败: {str(e)}",
                thinking_hint=f"战略分析时出错"
            )

    # =========================================================================
    # 辅助方法
    # =========================================================================

    def _parse_piece_identifier(self, board: List[List[str]], piece: str) -> Optional[Tuple[int, int]]:
        """解析棋子标识符，返回位置

        支持格式：
        - "红车-(1,1)" 或 "黑车-(1,10)" （棋盘布局格式）
        - "(1,1)" （纯坐标格式）
        - "红车" 或 "r" （棋子名称格式）
        """
        import re

        # 1. 尝试解析 "名称-(x,y)" 格式（棋盘布局输出的格式）
        match = re.match(r'^(红|黑)(车|马|炮|相|象|仕|士|帅|将|兵|卒)-?\(?(\d+),(\d+)\)?$', piece)
        if match:
            col = int(match.group(3)) - 1
            row = 10 - int(match.group(4))
            if 0 <= row < 10 and 0 <= col < 9:
                return (row, col)

        # 2. 尝试解析纯坐标格式 (x,y)
        if piece.startswith("(") and "," in piece and piece.endswith(")"):
            try:
                parts = piece[1:-1].split(",")
                col = int(parts[0]) - 1
                row = 10 - int(parts[1])
                if 0 <= row < 10 and 0 <= col < 9:
                    return (row, col)
            except:
                pass

        # 3. 尝试解析棋子名称（优先精确匹配）
        # 先去掉可能的后缀如 "-(x,y)"
        piece_clean = re.sub(r'-?\(\d+,\d+\)$', '', piece)

        # 精确匹配
        for r in range(10):
            for c in range(9):
                p = board[r][c]
                if p:
                    name = self._get_piece_name(p)
                    if piece_clean == name or piece_clean == p or piece_clean.lower() == p.lower():
                        return (r, c)

        # 模糊匹配（包含关系）
        for r in range(10):
            for c in range(9):
                p = board[r][c]
                if p:
                    name = self._get_piece_name(p)
                    if piece_clean in name:
                        return (r, c)

        return None

    def _get_piece_name(self, piece: str) -> str:
        """获取棋子中文名称"""
        info = self.PIECE_NAMES.get(piece, ('未知', '红' if piece.isupper() else '黑'))
        return f"{info[1]}{info[0]}"

    def _to_chinese_move(self, board: List[List[str]], move: str, piece: str) -> str:
        """将UCI走法转换为中文"""
        try:
            (from_row, from_col), (to_row, to_col) = self.detector._parse_uci(move)
            piece_name = self._get_piece_name(piece)
            return f"{piece_name}({from_col+1},{10-from_row})→({to_col+1},{10-to_row})"
        except:
            return move

    def _to_chinese_move_from_fen(self, fen: str, move: str) -> str:
        """从FEN转换UCI走法为中文"""
        try:
            board = self.detector._fen_to_board(fen)
            (from_row, from_col), _ = self.detector._parse_uci(move)
            piece = board[from_row][from_col]
            return self._to_chinese_move(board, move, piece)
        except:
            return move

    def _quality_to_score(self, quality: str) -> int:
        """将质量转换为分数"""
        scores = {
            "excellent": 100,
            "good": 70,
            "ok": 50,
            "blunder": 0
        }
        return scores.get(quality, 50)

    def _explain_move(self, fen: str, move: str) -> str:
        """生成走法解释"""
        result = self.analyze_move(fen, move)
        if result.success:
            return result.data.get("why", "正常走法")
        return "无法分析"


# =============================================================================
# 工具注册表（供LLM调用）
# =============================================================================

AGENT_TOOLS = {
    # 棋子关系查询
    "get_piece_attacks": {
        "function": AgentTools.get_piece_attacks,
        "description": "查询某棋子的攻击范围。当你需要分析某子的攻击能力时使用。",
        "parameters": ["fen", "piece"]
    },
    "get_piece_defenders": {
        "function": AgentTools.get_piece_defenders,
        "description": "查询谁在保护某个棋子。当你需要分析某子是否安全时使用。",
        "parameters": ["fen", "piece"]
    },
    "get_threats_to_piece": {
        "function": AgentTools.get_threats_to_piece,
        "description": "查询谁在威胁某个棋子。当你需要分析某子面临的危险时使用。",
        "parameters": ["fen", "piece"]
    },
    "get_piece_relations": {
        "function": AgentTools.get_piece_relations,
        "description": "综合查询某棋子的攻击、防守、威胁信息。一站式获取完整关系。",
        "parameters": ["fen", "piece"]
    },
    # 走法分析
    "analyze_move": {
        "function": AgentTools.analyze_move,
        "description": "深度分析某步棋的效果。当你需要解释某步棋为什么好或坏时使用。",
        "parameters": ["fen", "move"]
    },
    "compare_moves": {
        "function": AgentTools.compare_moves,
        "description": "对比多步棋的优劣。当你需要分析为什么选A而不是B时使用。",
        "parameters": ["fen", "moves"]
    },
    "get_forcing_sequence": {
        "function": AgentTools.get_forcing_sequence,
        "description": "分析走法后的强制序列。当你需要分析将军或强制应着时使用。",
        "parameters": ["fen", "move"]
    },
    # 引擎分析
    "engine_deep_analysis": {
        "function": AgentTools.engine_deep_analysis,
        "description": "引擎深度分析。获取引擎评估和最佳走法。",
        "parameters": ["fen", "depth"]
    },
    "engine_alternatives": {
        "function": AgentTools.engine_alternatives,
        "description": "获取引擎的多个候选走法对比。",
        "parameters": ["fen", "top_n"]
    },
    # 战略分析
    "analyze_position_strategy": {
        "function": AgentTools.analyze_position_strategy,
        "description": "局面战略分析。获取阶段、主动权、关键特征等信息。",
        "parameters": ["fen"]
    }
}


def get_tool_descriptions() -> str:
    """获取所有工具的描述（供LLM系统提示使用）"""
    descriptions = []
    for name, info in AGENT_TOOLS.items():
        params = ", ".join(info["parameters"])
        descriptions.append(f"- {name}({params}): {info['description']}")
    return "\n".join(descriptions)
