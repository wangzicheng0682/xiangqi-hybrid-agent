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
from core.llm.move_candidate_service import MoveCandidateService
from core.rag.position_similarity import get_position_retriever


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
        self.move_candidates = MoveCandidateService()

    # =========================================================================
    # 第零类：候选走法服务
    # =========================================================================

    def get_move_candidates(self, fen: str, limit: int = 12) -> ToolResult:
        """
        获取当前局面的合法候选走法，供后续工具使用 candidate_id。

        Args:
            fen: 当前局面FEN
            limit: 返回候选数上限

        Returns:
            ToolResult: 包含 candidate_id -> move 映射
        """
        try:
            candidates = self.move_candidates.get_candidates(fen, limit=limit)
            return ToolResult(
                success=True,
                data={
                    "candidates": [candidate.__dict__ for candidate in candidates],
                    "count": len(candidates),
                },
                message="\n".join(
                    f"{candidate.candidate_id}: {candidate.display}" for candidate in candidates
                ) if candidates else "无合法候选走法",
                thinking_hint=f"获取到{len(candidates)}个合法候选走法",
            )
        except Exception as e:
            return ToolResult(
                success=False,
                data={},
                message=f"获取候选走法失败: {str(e)}",
                thinking_hint="获取候选走法时出错",
            )

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

    def analyze_move(self, fen: str, move: str = None, candidate_id: str = None) -> ToolResult:
        """
        深度分析某步棋的效果

        Args:
            fen: 走法前的局面FEN
            move: UCI格式走法 (如 "h2e2")
            candidate_id: 候选走法ID，优先于 move

        Returns:
            ToolResult: 包含走法分析结果
        """
        try:
            resolved_move = self.move_candidates.resolve_move(fen, move=move, candidate_id=candidate_id)
            if not resolved_move:
                return ToolResult(
                    success=False,
                    data={},
                    message=f"无法解析候选走法: move={move}, candidate_id={candidate_id}",
                    thinking_hint="未提供合法候选走法",
                )

            board = self.detector._fen_to_board(fen)
            is_red_turn = self.detector._is_red_turn(fen)

            # 解析走法
            (from_row, from_col), (to_row, to_col) = self.detector._parse_uci(resolved_move)
            moving_piece = board[from_row][from_col]

            if not moving_piece:
                return ToolResult(
                    success=False,
                    data={},
                    message=f"无效走法: {resolved_move}",
                    thinking_hint=f"解析走法 {resolved_move} 失败"
                )

            piece_name = self._get_piece_name(moving_piece)
            move_chinese = self._to_chinese_move(board, resolved_move, moving_piece)

            # 执行走法
            new_board = self.detector._apply_move(board, resolved_move)

            # 分析走法质量
            quality_tags = self.detector.detect_move_quality(fen, resolved_move)
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
                    "resolved_move": resolved_move,
                    "candidate_id": candidate_id,
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

    def compare_moves(self, fen: str, moves: List[str] = None, candidate_ids: List[str] = None) -> ToolResult:
        """
        对比多步棋的优劣

        Args:
            fen: 局面FEN
            moves: UCI格式走法列表
            candidate_ids: 候选走法ID列表

        Returns:
            ToolResult: 包含对比结果
        """
        try:
            comparisons = []

            resolved_moves: List[str] = []
            if candidate_ids:
                for candidate_id in candidate_ids:
                    resolved = self.move_candidates.resolve_move(fen, candidate_id=candidate_id)
                    if resolved:
                        resolved_moves.append(resolved)
            if moves:
                for move_item in moves:
                    resolved = self.move_candidates.resolve_move(fen, move=move_item)
                    if resolved:
                        resolved_moves.append(resolved)

            seen = set()
            normalized_moves = []
            for resolved in resolved_moves:
                if resolved not in seen:
                    normalized_moves.append(resolved)
                    seen.add(resolved)

            for move_item in normalized_moves:
                result = self.analyze_move(fen, move=move_item)
                if result.success:
                    comparisons.append({
                        "move": move_item,
                        "move_chinese": result.data.get("move_chinese", move_item),
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
                    "reason": reason,
                    "candidate_ids": candidate_ids or [],
                },
                message=f"对比{len(comparisons)}步棋，最佳: {best}",
                thinking_hint=f"对比分析{len(normalized_moves)}步候选走法"
            )

        except Exception as e:
            return ToolResult(
                success=False,
                data={},
                message=f"对比失败: {str(e)}",
                thinking_hint=f"对比走法时出错"
            )

    def get_forcing_sequence(self, fen: str, move: str = None, depth: int = 3, candidate_id: str = None) -> ToolResult:
        """
        分析走法后的强制序列（递归追踪将军-应将链）

        Args:
            fen: 走法前的局面FEN
            move: UCI格式走法
            depth: 追踪深度（半步数）
            candidate_id: 候选走法ID，优先于 move

        Returns:
            ToolResult: 包含强制序列
        """
        try:
            resolved_move = self.move_candidates.resolve_move(fen, move=move, candidate_id=candidate_id)
            if not resolved_move:
                return ToolResult(
                    success=False,
                    data={},
                    message=f"无法解析候选走法: move={move}, candidate_id={candidate_id}",
                    thinking_hint="未提供合法候选走法",
                )
            board = self.detector._fen_to_board(fen)
            is_red_turn = self.detector._is_red_turn(fen)

            sequence = []
            current_board = board
            current_turn = is_red_turn
            current_move = resolved_move
            is_forcing = False
            outcome = "非强制序列"

            for ply in range(depth):
                try:
                    src, dst = self.detector._parse_uci(current_move)
                    piece = current_board[src[0]][src[1]]
                    if piece == '.':
                        break
                    new_board = self.detector._apply_move(current_board, current_move)
                    move_chinese = self._to_chinese_move(current_board, current_move, piece)

                    gives_check = self.detector._is_in_check(new_board, not current_turn)
                    is_capture = current_board[dst[0]][dst[1]] != '.'

                    move_type = "check" if gives_check else ("capture" if is_capture else "normal")

                    sequence.append({
                        "ply": ply + 1,
                        "move": current_move,
                        "move_chinese": move_chinese,
                        "type": move_type,
                        "must_respond": gives_check,
                        "side": "红" if (is_red_turn == (ply % 2 == 0)) else "黑",
                    })

                    if ply == 0 and gives_check:
                        is_forcing = True

                    if not gives_check and ply > 0:
                        # 不再是将军链，停止追踪
                        break

                    # 找对方应将/最佳回应
                    if ply + 1 < depth:
                        next_turn = not current_turn
                        # 用引擎找最佳应着（如果引擎可用），否则用规则找应将着法
                        response_move = self._find_best_response(new_board, next_turn)
                        if response_move is None:
                            # 无合法走法 = 将杀
                            if gives_check:
                                outcome = "将杀！对方无合法应将"
                                is_forcing = True
                            break
                        current_board = new_board
                        current_turn = next_turn
                        current_move = response_move
                    else:
                        current_board = new_board
                        break

                except Exception:
                    break

            if is_forcing and outcome == "非强制序列":
                checks_in_seq = sum(1 for s in sequence if s["type"] == "check")
                outcome = f"强制序列：{checks_in_seq}步将军" + ("，对方必须逐一应将" if checks_in_seq > 1 else "，对方必须应将")

            return ToolResult(
                success=True,
                data={
                    "is_forcing": is_forcing,
                    "sequence": sequence,
                    "depth_analyzed": len(sequence),
                    "outcome": outcome,
                },
                message=f"分析完成: {'强制序列' if is_forcing else '非强制'}，深度{len(sequence)}",
                thinking_hint=f"分析走法后的强制序列"
            )

        except Exception as e:
            return ToolResult(
                success=False,
                data={},
                message=f"分析失败: {str(e)}",
                thinking_hint=f"分析强制序列时出错"
            )

    def _find_best_response(self, board, is_red_turn: bool) -> Optional[str]:
        """找到最佳应着（优先引擎，降级为规则找合法走法）"""
        try:
            # 尝试用引擎
            from core.engine.pool import EnginePool
            # 重建 FEN
            fen = self._board_to_fen(board, is_red_turn)
            pool = EnginePool.get_pool()
            result = pool.analyze(fen, depth=10)
            if result.bestmove:
                return result.bestmove
        except Exception:
            pass

        # 降级：规则层找合法走法（暴力搜索所有己方棋子的合法走法）
        return self._find_any_legal_move(board, is_red_turn)

    def _find_any_legal_move(self, board, is_red_turn: bool) -> Optional[str]:
        """找到一个合法走法（暴力搜索）"""
        for r in range(10):
            for c in range(9):
                piece = board[r][c]
                if piece == '.':
                    continue
                if is_red_turn and not piece.isupper():
                    continue
                if not is_red_turn and not piece.islower():
                    continue
                # 生成该棋子的所有目标位置并检查合法性
                targets = self._get_piece_moves(board, r, c, piece)
                for tr, tc in targets:
                    move_uci = f"{chr(ord('a') + c)}{9 - r}{chr(ord('a') + tc)}{9 - tr}"
                    try:
                        new_board = self.detector._apply_move(board, move_uci)
                        # 走后自己不能被将
                        if not self.detector._is_in_check(new_board, is_red_turn):
                            return move_uci
                    except Exception:
                        continue
        return None

    def _get_piece_moves(self, board, row: int, col: int, piece: str):
        """获取棋子的候选目标格（简化版，不做完全合法性检查）"""
        p = piece.upper()
        targets = []
        if p == 'R':  # 车
            for d in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                r, c = row + d[0], col + d[1]
                while 0 <= r < 10 and 0 <= c < 9:
                    if board[r][c] == '.':
                        targets.append((r, c))
                    else:
                        # 可以吃对方棋子
                        if piece.isupper() != board[r][c].isupper():
                            targets.append((r, c))
                        break
                    r += d[0]
                    c += d[1]
        elif p == 'N':  # 马
            for dr, dc, br, bc in [(-2, -1, -1, 0), (-2, 1, -1, 0), (2, -1, 1, 0), (2, 1, 1, 0),
                                     (-1, -2, 0, -1), (-1, 2, 0, 1), (1, -2, 0, -1), (1, 2, 0, 1)]:
                nr, nc = row + dr, col + dc
                block_r, block_c = row + br, col + bc
                if 0 <= nr < 10 and 0 <= nc < 9 and board[block_r][block_c] == '.':
                    if board[nr][nc] == '.' or (piece.isupper() != board[nr][nc].isupper()):
                        targets.append((nr, nc))
        elif p == 'C':  # 炮
            for d in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                r, c = row + d[0], col + d[1]
                found_platform = False
                while 0 <= r < 10 and 0 <= c < 9:
                    if not found_platform:
                        if board[r][c] == '.':
                            targets.append((r, c))
                        else:
                            found_platform = True
                    else:
                        if board[r][c] != '.':
                            if piece.isupper() != board[r][c].isupper():
                                targets.append((r, c))
                            break
                    r += d[0]
                    c += d[1]
        elif p == 'P':  # 兵/卒
            if piece.isupper():  # 红兵，向上走
                if row - 1 >= 0:
                    targets.append((row - 1, col))
                if row <= 4:  # 过河后可以横走
                    if col - 1 >= 0:
                        targets.append((row, col - 1))
                    if col + 1 < 9:
                        targets.append((row, col + 1))
            else:  # 黑卒，向下走
                if row + 1 < 10:
                    targets.append((row + 1, col))
                if row >= 5:  # 过河后可以横走
                    if col - 1 >= 0:
                        targets.append((row, col - 1))
                    if col + 1 < 9:
                        targets.append((row, col + 1))
        elif p == 'K':  # 将/帅
            for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nr, nc = row + dr, col + dc
                if piece.isupper():  # 帅在行7-9，列3-5
                    if 7 <= nr <= 9 and 3 <= nc <= 5:
                        targets.append((nr, nc))
                else:  # 将在行0-2，列3-5
                    if 0 <= nr <= 2 and 3 <= nc <= 5:
                        targets.append((nr, nc))
        elif p == 'A':  # 士/仕
            for dr, dc in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
                nr, nc = row + dr, col + dc
                if piece.isupper():
                    if 7 <= nr <= 9 and 3 <= nc <= 5:
                        targets.append((nr, nc))
                else:
                    if 0 <= nr <= 2 and 3 <= nc <= 5:
                        targets.append((nr, nc))
        elif p == 'B':  # 相/象
            for dr, dc, er, ec in [(-2, -2, -1, -1), (-2, 2, -1, 1), (2, -2, 1, -1), (2, 2, 1, 1)]:
                nr, nc = row + dr, col + dc
                eye_r, eye_c = row + er, col + ec
                if 0 <= nr < 10 and 0 <= nc < 9 and board[eye_r][eye_c] == '.':
                    if piece.isupper() and nr >= 5:
                        targets.append((nr, nc))
                    elif piece.islower() and nr <= 4:
                        targets.append((nr, nc))
        # 过滤：不能吃自己的子
        return [(r, c) for r, c in targets if board[r][c] == '.' or (piece.isupper() != board[r][c].isupper())]

    def _board_to_fen(self, board, is_red_turn: bool) -> str:
        """将棋盘数组重建为FEN字符串"""
        rows = []
        for r in range(10):
            empty = 0
            row_str = ""
            for c in range(9):
                if board[r][c] == '.':
                    empty += 1
                else:
                    if empty > 0:
                        row_str += str(empty)
                        empty = 0
                    row_str += board[r][c]
            if empty > 0:
                row_str += str(empty)
            rows.append(row_str)
        return "/".join(rows) + (" w" if is_red_turn else " b") + " - - 0 1"

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
                from core.engine.pool import EnginePool
                pool = EnginePool.get_pool()
                result = pool.analyze(fen, depth=depth)
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
        引擎候选走法对比（使用 MultiPV 获取真实 top-N）

        Args:
            fen: 局面FEN
            top_n: 返回的候选数量

        Returns:
            ToolResult: 包含候选走法
        """
        try:
            try:
                from core.engine.pool import EnginePool
                pool = EnginePool.get_pool()

                # 使用 MultiPV 获取真实多候选
                results = pool.analyze_multipv(fen, depth=18, num_pv=min(top_n, 5))

                moves_data = []
                for i, r in enumerate(results):
                    if not r.bestmove:
                        continue
                    move_chinese = self._to_chinese_move_from_fen(fen, r.bestmove)
                    eval_cp = int(r.score * 100)
                    moves_data.append({
                        "rank": i + 1,
                        "move": r.bestmove,
                        "move_chinese": move_chinese,
                        "eval_cp": eval_cp,
                        "pv": " ".join(r.pv[:6]),
                        "explanation": self._explain_move(fen, r.bestmove),
                        "risk": "low" if abs(eval_cp) < 100 else ("medium" if abs(eval_cp) < 300 else "high")
                    })

                if moves_data:
                    best = moves_data[0]
                    recommendation = f"最佳: {best['move_chinese']}({best['move']})，评分{best['eval_cp']}分"
                    if len(moves_data) > 1:
                        diff = abs(moves_data[0]["eval_cp"] - moves_data[1]["eval_cp"])
                        if diff < 30:
                            recommendation += f"；次选{moves_data[1]['move_chinese']}评分接近，差距仅{diff}分"
                else:
                    recommendation = "引擎无法获取候选走法"

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

            focus_tags = self._focus_tags_for_phase(detected_tags, phase)

            # 提取关键特征
            key_features = []
            if "controls_open_file" in focus_tags:
                key_features.append("控制开放线")
            if "has_active_pieces" in focus_tags:
                key_features.append("子力活跃")
            if "piece_coordination" in focus_tags:
                key_features.append("子力协同")
            if "is_attack_unprotected" in focus_tags:
                key_features.append("存在攻击无根子")
            if "is_pinned" in focus_tags:
                key_features.append("存在牵制")
            if phase != "开局" and "cannon_battery" in focus_tags:
                key_features.append("重炮阵型")

            if not key_features:
                key_features.append("局面相对平稳")

            # 生成建议计划
            suggested_plans = []
            if phase == "开局":
                suggested_plans.append("优先按主流定式完成出子顺序，不要脱谱乱走")
                suggested_plans.append("先确认当前是否仍在熟悉主线，再决定是否转入个人变化")
            elif is_red_turn:
                if "has_initiative" in focus_tags:
                    suggested_plans.append("红方应保持主动，寻找进攻机会")
                if "is_attack_unprotected" in focus_tags:
                    suggested_plans.append("红方可以捉对方无根子")
            else:
                if "has_initiative" in focus_tags:
                    suggested_plans.append("黑方应保持主动，寻找进攻机会")

            if not suggested_plans:
                suggested_plans.append("稳步发展，等待时机")

            semantic_query = self._build_semantic_query_tags(focus_tags, phase)
            similar_positions = self._retrieve_similar_positions(fen, semantic_query, top_k=3)
            knowledge_bundle = self._collect_strategy_knowledge(focus_tags, phase)

            if similar_positions:
                top_plan = similar_positions[0].get("best_move")
                if top_plan:
                    suggested_plans.append(f"可参考相似局面的高频应对：{top_plan}")

            return ToolResult(
                success=True,
                data={
                    "phase": phase,
                    "initiative": initiative,
                    "king_safety": king_safety,
                    "key_features": key_features,
                    "suggested_plans": suggested_plans,
                    "detected_tags": detected_tags,
                    "focus_tags": focus_tags,
                    "knowledge_principles": knowledge_bundle["principles"],
                    "tension_type": knowledge_bundle["tension_type"],
                    "similar_positions": similar_positions,
                },
                message=(
                    f"战略分析: {phase}，{initiative}握有主动权；"
                    f"匹配原则{len(knowledge_bundle['principles'])}条；"
                    f"相似局面{len(similar_positions)}例"
                ),
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
    # 第五类：走法模拟（走一步看变化）
    # =========================================================================

    def simulate_move(self, fen: str, move: str = None, candidate_id: str = None) -> ToolResult:
        """
        模拟走一步棋，对比走棋前后的局面变化

        这个工具回答"如果走这步，局面会怎样变化？"

        Args:
            fen: 当前局面FEN
            move: UCI格式走法，如 h2e2
            candidate_id: 候选走法ID，优先于 move

        Returns:
            ToolResult: 包含走棋前后标签差异、子力变化
        """
        try:
            resolved_move = self.move_candidates.resolve_move(fen, move=move, candidate_id=candidate_id)
            if not resolved_move:
                return ToolResult(
                    success=False, data={},
                    message=f"无法解析候选走法: move={move}, candidate_id={candidate_id}",
                    thinking_hint="走法格式错误"
                )
            board_before = self.detector._fen_to_board(fen)
            is_red_turn = self.detector._is_red_turn(fen)

            # 验证走法格式
            parsed = self.detector._parse_uci(resolved_move)
            if not parsed:
                return ToolResult(
                    success=False, data={},
                    message=f"无法解析走法: {resolved_move}",
                    thinking_hint="走法格式错误"
                )

            (from_row, from_col), (to_row, to_col) = parsed
            moving_piece = board_before[from_row][from_col]
            if not moving_piece:
                return ToolResult(
                    success=False, data={},
                    message=f"起始位置无棋子: {resolved_move}",
                    thinking_hint="起始位置没有棋子"
                )

            captured_piece = board_before[to_row][to_col]
            move_chinese = self._to_chinese_move(board_before, resolved_move, moving_piece)

            # 走棋前标签
            tags_before = self.detector.detect_static(fen)
            before_names = {t.tag.name for t in tags_before.tags if t.detected}

            # 执行走棋
            board_after = self.detector._apply_move(board_before, resolved_move)

            # 构造走棋后的FEN
            rows = []
            for row in board_after:
                fen_row = ""
                empty = 0
                for cell in row:
                    if cell:
                        if empty:
                            fen_row += str(empty)
                            empty = 0
                        fen_row += cell
                    else:
                        empty += 1
                if empty:
                    fen_row += str(empty)
                rows.append(fen_row)
            next_turn = "b" if is_red_turn else "w"
            fen_after = "/".join(rows) + f" {next_turn} - - 0 1"

            # 走棋后标签
            tags_after = self.detector.detect_static(fen_after)
            after_names = {t.tag.name for t in tags_after.tags if t.detected}

            # 计算差异
            new_tags = after_names - before_names
            lost_tags = before_names - after_names

            # 吃子信息
            captured_info = None
            if captured_piece:
                cap_name = self._get_piece_name(captured_piece)
                cap_value = self.PIECE_VALUES.get(captured_piece.lower(), 0)
                captured_info = {"piece": cap_name, "value": cap_value}

            # 检查是否将军
            gives_check = self.detector._is_in_check(board_after, not is_red_turn)

            # 生成人类可读摘要
            summary_parts = [f"{move_chinese}"]
            if captured_info:
                summary_parts.append(f"吃{captured_info['piece']}(值{captured_info['value']})")
            if gives_check:
                summary_parts.append("形成将军")
            if new_tags:
                summary_parts.append(f"新增标签: {', '.join(list(new_tags)[:3])}")
            if lost_tags:
                summary_parts.append(f"消失标签: {', '.join(list(lost_tags)[:3])}")

            return ToolResult(
                success=True,
                data={
                    "move": resolved_move,
                    "candidate_id": candidate_id,
                    "move_chinese": move_chinese,
                    "captured": captured_info,
                    "gives_check": gives_check,
                    "tags_before": sorted(before_names),
                    "tags_after": sorted(after_names),
                    "new_tags": sorted(new_tags),
                    "lost_tags": sorted(lost_tags),
                    "fen_after": fen_after,
                },
                message="→".join(summary_parts),
                thinking_hint=f"模拟{move_chinese}后局面变化"
            )

        except Exception as e:
            return ToolResult(
                success=False, data={},
                message=f"模拟走法失败: {str(e)}",
                thinking_hint="模拟走法时出错"
            )

    # =========================================================================
    # 第六类：知识检索
    # =========================================================================

    def query_chess_principles(self, fen: str, tension_type: str = None) -> ToolResult:
        """
        根据当前局面的张力类型查询适用的象棋原则

        Args:
            fen: 当前局面FEN
            tension_type: 张力类型（可选，如 material_vs_initiative, hidden_imbalance 等）

        Returns:
            ToolResult: 包含适用的棋理原则
        """
        try:
            from core.llm.knowledge_retriever import ChessKnowledgeBase
            kb = ChessKnowledgeBase()

            principles = []

            if tension_type:
                tension_principles = kb.query_for_tension(tension_type)
                principles.extend(tension_principles)

            # 补充通用原则
            general = kb.query_general_principles(2)
            principles.extend(general)

            if not principles:
                return ToolResult(
                    success=True,
                    data={"principles": [], "count": 0},
                    message="未找到特定原则，使用通用分析",
                    thinking_hint="当前张力类型无特定原则"
                )

            principles_data = []
            principles_text = []
            for i, p in enumerate(principles[:5], 1):
                principles_data.append(p.to_dict())
                text = f"{i}. {p.content}（{p.applies_when}）"
                if p.counter_case and p.counter_case != "无":
                    text += f" [例外: {p.counter_case}]"
                principles_text.append(text)

            return ToolResult(
                success=True,
                data={
                    "principles": principles_data,
                    "count": len(principles_data),
                    "tension_type": tension_type or "general",
                },
                message="\n".join(principles_text),
                thinking_hint=f"检索到{len(principles_data)}条棋理原则"
            )

        except Exception as e:
            return ToolResult(
                success=False, data={},
                message=f"知识检索失败: {str(e)}",
                thinking_hint="检索棋理原则时出错"
            )

    def search_chess_knowledge(self, fen: str = None, query: str = "", top_k: int = 5) -> ToolResult:
        """
        语义检索象棋知识库（棋理原则 + 经典棋谱开局）

        Args:
            fen: 当前局面FEN（兼容统一工具调度器，实际不使用）
            query: 自然语言查询（如"中炮开局"、"马后炮杀法"、"车马冷着配合"）
            top_k: 返回数量

        Returns:
            ToolResult: 包含检索结果
        """
        try:
            if not query:
                return ToolResult(
                    success=False,
                    data={},
                    message="知识库检索失败: 缺少 query 参数",
                    thinking_hint="知识检索需要查询语句"
                )

            from core.rag.chroma_rag import ChromaRAG
            rag = ChromaRAG()
            detected_tags = []
            phase = ""
            expanded_query = query
            similar_positions = []
            principles_data = []

            if fen:
                static_result = self.detector.detect_static(fen)
                detected_tags = [t.tag.name for t in static_result.tags if t.detected]
                if "phase_opening" in detected_tags:
                    phase = "opening"
                elif "phase_endgame" in detected_tags:
                    phase = "endgame"
                else:
                    phase = "middlegame"

                focus_tags = self._focus_tags_for_phase(detected_tags, self._phase_to_cn(phase))

                semantic_query = self._build_semantic_query_tags(focus_tags, self._phase_to_cn(phase))
                similar_positions = self._retrieve_similar_positions(fen, semantic_query, top_k=min(3, top_k))
                knowledge_bundle = self._collect_strategy_knowledge(focus_tags, self._phase_to_cn(phase))
                principles_data = knowledge_bundle["principles"]

                if phase:
                    expanded_query = f"{query} {phase} {' '.join(focus_tags[:6])}".strip()

            phase_results = rag.retrieve_by_phase(expanded_query, phase, top_k=top_k) if phase else []
            general_results = rag.retrieve(expanded_query, top_k=top_k)
            results = self._merge_rag_results(phase_results + general_results, top_k=top_k)

            if not results:
                return ToolResult(
                    success=True,
                    data={"results": [], "count": 0, "similar_positions": similar_positions, "principles": principles_data},
                    message="未检索到相关知识",
                    thinking_hint="知识库中无匹配内容"
                )

            results_data = []
            results_text = []
            for i, r in enumerate(results, 1):
                results_data.append({
                    "source": r.book_name,
                    "content": r.content,
                    "relevance": r.relevance,
                })
                results_text.append(
                    f"{i}. [{r.book_name}] {r.content[:150]}（相关度: {r.relevance:.2f}）"
                )

            if principles_data:
                results_text.append("原则补充：")
                for idx, principle in enumerate(principles_data[:3], 1):
                    results_text.append(f"P{idx}. {principle['content']}")

            if similar_positions:
                results_text.append("相似局面：")
                for idx, position in enumerate(similar_positions, 1):
                    summary = f"S{idx}. 相似度{position['similarity']:.2f}，阶段={position['phase']}"
                    if position.get("best_move"):
                        summary += f"，参考着法={position['best_move']}"
                    if position.get("total_games"):
                        summary += f"，样本数={position['total_games']}"
                    results_text.append(summary)

            return ToolResult(
                success=True,
                data={
                    "results": results_data,
                    "count": len(results_data),
                    "query": query,
                    "phase": phase,
                    "principles": principles_data,
                    "similar_positions": similar_positions,
                },
                message="\n".join(results_text),
                thinking_hint=f"检索到{len(results_data)}条知识，补充{len(similar_positions)}个相似局面"
            )

        except Exception as e:
            return ToolResult(
                success=False, data={},
                message=f"知识库检索失败: {str(e)}",
                thinking_hint="检索知识库时出错"
            )

    # =========================================================================
    # 辅助方法
    # =========================================================================

    def _merge_rag_results(self, results: List[Any], top_k: int) -> List[Any]:
        merged = []
        seen = set()
        for item in results:
            key = (item.book_name, item.content)
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)
            if len(merged) >= top_k:
                break
        return merged

    def _phase_to_cn(self, phase: str) -> str:
        mapping = {"opening": "开局", "middlegame": "中局", "endgame": "残局"}
        return mapping.get(phase, phase or "中局")

    def _focus_tags_for_phase(self, detected_tags: List[str], phase: str) -> List[str]:
        if phase in {"开局", "布局"}:
            return [tag for tag in detected_tags if tag != "cannon_battery"]
        return detected_tags

    def _build_semantic_query_tags(self, detected_tags: List[str], phase: str) -> Dict[str, float]:
        phase_key = phase
        if phase in {"开局", "布局"}:
            phase_key = "opening"
        elif phase in {"残局", "收官"}:
            phase_key = "endgame"
        elif phase in {"中局", "中盘"}:
            phase_key = "middlegame"

        semantic = {
            "opening": 0.0,
            "middlegame": 0.0,
            "endgame": 0.0,
        }
        if phase_key in semantic:
            semantic[phase_key] = 0.9

        tag_map = {
            "controls_open_file": "open_file",
            "is_pinned": "pinned_piece",
            "has_active_pieces": "active_rook",
            "move_improves_position": "improving_move",
            "critical_position": "critical_position",
            "passed_pawn": "passed_pawn",
        }
        for tag in detected_tags:
            mapped = tag_map.get(tag)
            if mapped:
                semantic[mapped] = 0.9

        tactical_tags = [tag for tag in detected_tags if tag.startswith("is_")]
        if len(tactical_tags) <= 1:
            semantic["quiet_position"] = 0.7

        return semantic

    def _infer_tension_type(self, detected_tags: List[str], phase: str) -> Optional[str]:
        tag_set = set(detected_tags)
        if "is_check" in tag_set or "king_safety_critical" in tag_set:
            return "crisis_with_resources"
        if "is_attack_unprotected" in tag_set or "has_initiative" in tag_set:
            return "material_vs_initiative"
        if "is_pinned" in tag_set or "piece_coordination" in tag_set:
            return "hidden_imbalance"
        if phase in {"开局", "布局"}:
            return "phase_mismatch"
        if "has_active_pieces" not in tag_set:
            return "sleeping_piece"
        return None

    def _collect_strategy_knowledge(self, detected_tags: List[str], phase: str) -> Dict[str, Any]:
        from core.llm.knowledge_retriever import ChessKnowledgeBase

        kb = ChessKnowledgeBase()
        tension_type = self._infer_tension_type(detected_tags, phase)
        principles = []
        seen = set()

        if tension_type:
            for principle in kb.query_for_tension(tension_type, phase):
                if principle.content in seen:
                    continue
                principles.append(principle.to_dict())
                seen.add(principle.content)
                if len(principles) >= 3:
                    break

        for principle in kb.query_by_tags(detected_tags, phase):
            if principle.content in seen:
                continue
            principles.append(principle.to_dict())
            seen.add(principle.content)
            if len(principles) >= 5:
                break

        if len(principles) < 3:
            for principle in kb.query_general_principles(3):
                if principle.content in seen:
                    continue
                principles.append(principle.to_dict())
                seen.add(principle.content)
                if len(principles) >= 5:
                    break

        return {"tension_type": tension_type or "general", "principles": principles}

    def _retrieve_similar_positions(self, fen: str, semantic_query: Dict[str, float], top_k: int = 3) -> List[Dict[str, Any]]:
        retriever = get_position_retriever()
        results = retriever.retrieve(fen, semantic_tags=semantic_query, top_k=top_k)
        return [
            {
                "fen": item.fen,
                "similarity": item.similarity,
                "phase": item.phase,
                "best_move": item.best_move,
                "score": item.score,
                "total_games": item.total_games,
                "tags": item.tags,
            }
            for item in results
        ]

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
        result = self.analyze_move(fen, move=move)
        if result.success:
            return result.data.get("why", "正常走法")
        return "无法分析"


# =============================================================================
# 工具注册表（供LLM调用）
# =============================================================================

AGENT_TOOLS = {
    "get_move_candidates": {
        "function": AgentTools.get_move_candidates,
        "description": "获取当前局面的合法候选走法列表，返回稳定的 candidate_id。后续分析走法时应优先使用 candidate_id。",
        "parameters": ["fen", "limit"]
    },
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
    },
    # 走法模拟
    "simulate_move": {
        "function": AgentTools.simulate_move,
        "description": "模拟走一步棋，对比走棋前后的局面标签变化。",
        "parameters": ["fen", "move"]
    },
    # 知识检索
    "query_chess_principles": {
        "function": AgentTools.query_chess_principles,
        "description": "根据张力类型查询适用的象棋原则和棋理。",
        "parameters": ["fen", "tension_type"]
    },
    "search_chess_knowledge": {
        "function": AgentTools.search_chess_knowledge,
        "description": "语义检索象棋知识库，可查询棋理原则和经典棋谱开局。",
        "parameters": ["query", "top_k"]
    },
}


def get_tool_descriptions() -> str:
    """获取所有工具的描述（供LLM系统提示使用）"""
    descriptions = []
    for name, info in AGENT_TOOLS.items():
        params = ", ".join(info["parameters"])
        descriptions.append(f"- {name}({params}): {info['description']}")
    return "\n".join(descriptions)
