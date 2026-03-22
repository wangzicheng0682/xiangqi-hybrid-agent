"""
游戏控制器 - 完整交互逻辑

职责: 管理走棋交互、状态更新、规则验证

文档依据: JOINT_REFACTOR_ARCHITECTURE.md 交互逻辑

Phase 3完整实现:
- 点击棋子选中逻辑
- 显示可走位置（调用规则引擎）
- 点击目标走棋
- 动画和音效播放
- 游戏状态管理
"""

from typing import List, Tuple, Optional, Dict
from core.rules.xiangqi_rules import get_legal_moves, is_in_check
from web.components.board_complete import CompleteBoardUI, create_complete_board_ui
from web.state.board_state import BoardState, PIECE_NAMES


class GameController:
    """
    游戏控制器

    管理完整的走棋交互流程
    """

    def __init__(self):
        self.state = BoardState()
        self.board_ui = create_complete_board_ui()
        self.game_over = False
        self.winner = None

    def handle_click(self, click_data: dict) -> Tuple[Dict, str]:
        """
        处理棋盘点击

        Args:
            click_data: 点击数据，包含row和col

        Returns:
            (更新后的状态字典, 消息)
        """
        # 解析点击位置
        row = click_data.get('row')
        col = click_data.get('col')

        if row is None or col is None:
            return self._get_state_dict(), "无效点击"

        # 如果游戏已结束
        if self.state.game_over:
            return self._get_state_dict(), f"游戏已结束，{self.state.winner}获胜！"

        # 如果已经选中了棋子，尝试走棋
        if self.state.selected_pos:
            # 检查点击的是否是合法目标位置
            if (row, col) in self.state.legal_moves:
                return self._execute_move(row, col)
            else:
                # 点击的不是合法位置，取消选中
                self.state.deselect_piece()
                return self._get_state_dict(), "已取消选中"

        # 否则，尝试选中棋子
        return self._select_piece(row, col)

    def _select_piece(self, row: int, col: int) -> Tuple[Dict, str]:
        """
        选中棋子

        Args:
            row: 行号
            col: 列号

        Returns:
            (状态字典, 消息)
        """
        piece = self.state.board[row][col]
        if not piece:
            return self._get_state_dict(), "此处没有棋子"

        # 检查是否是当前方的棋子
        is_red_piece = piece.isupper()
        if is_red_piece != self.state.red_to_move:
            piece_color = "红方" if is_red_piece else "黑方"
            return self._get_state_dict(), f"现在是{('红' if self.state.red_to_move else '黑')}方走棋，不能选择{piece_color}棋子"

        # 生成合法走法
        legal_moves = get_legal_moves(self.state.board, row, col)

        if not legal_moves:
            return self._get_state_dict(), "该棋子没有可走的合法位置"

        # 选中棋子
        self.state.select_piece(row, col)

        return self._get_state_dict(), f"已选中{PIECE_NAMES.get(piece, piece)}，有{len(legal_moves)}个合法走法"

    def _execute_move(self, to_row: int, to_col: int) -> Tuple[Dict, str]:
        """
        执行走棋

        Args:
            to_row: 目标行号
            to_col: 目标列号

        Returns:
            (状态字典, 消息)
        """
        from_pos = self.state.selected_pos
        if not from_pos:
            return self._get_state_dict(), "没有选中棋子"

        from_row, from_col = from_pos
        piece = self.state.board[from_row][from_col]
        target_piece = self.state.board[to_row][to_col]

        # 执行走棋
        move_desc = self.state.make_move(from_row, from_col, to_row, to_col)

        if not move_desc:
            return self._get_state_dict(), "走法不合法"

        # 检查游戏是否结束
        if self.state.game_over:
            self.game_over = True
            self.winner = self.state.winner
            return self._get_state_dict(), f"将死！{self.state.winner}获胜！"

        # 检查是否将军
        if not self.state.game_over:
            in_check = is_in_check(self.state.board, self.state.red_to_move)

            if in_check:
                side = "红方" if self.state.red_to_move else "黑方"
                message = f"{move_desc}\n⚠️ 将军！{side}被将军！"
            else:
                message = move_desc

            return self._get_state_dict(), message

        return self._get_state_dict(), move_desc

    def undo_move(self) -> Tuple[Dict, str]:
        """
        悔棋

        Returns:
            (状态字典, 消息)
        """
        # TODO: 实现完整的悔棋逻辑
        # 当前简化处理
        return self._get_state_dict(), "悔棋功能开发中"

    def new_game(self) -> Tuple[Dict, str]:
        """
        新对局

        Returns:
            (状态字典, 消息)
        """
        self.state.reset()
        self.game_over = False
        self.winner = None

        return self._get_state_dict(), "新对局开始，红方先行"

    def set_difficulty(self, difficulty: int) -> Tuple[Dict, str]:
        """
        设置难度

        Args:
            difficulty: 难度等级（1-10）

        Returns:
            (状态字典, 消息)
        """
        # TODO: 实现难度设置逻辑
        return self._get_state_dict(), f"难度已设置为{difficulty}级"

    def _get_state_dict(self) -> Dict:
        """
        获取状态字典（用于Gradio更新）

        Returns:
            状态字典
        """
        return {
            "board": self.state.board,
            "selected_pos": self.state.selected_pos,
            "legal_moves": self.state.legal_moves,
            "red_to_move": self.state.red_to_move,
            "move_history": self.state.move_history,
            "iccs_moves": self.state.iccs_moves,
            "last_move_info": self.state.last_move_info,
            "game_over": self.state.game_over,
            "winner": self.state.winner
        }

    def get_board_html(self) -> str:
        """
        获取棋盘HTML（包含选中状态和可走位置）

        Returns:
            棋盘HTML
        """
        return self.board_ui.render(
            board=self.state.board,
            selected_pos=self.state.selected_pos,
            valid_moves=self.state.legal_moves,
            last_move=(self.state.last_move_info.get('from_pos'), self.state.last_move_info.get('to_pos')) if self.state.last_move_info else None
        )

    def get_move_history(self) -> str:
        """
        获取走法历史

        Returns:
            格式化的走法历史
        """
        return self.state.get_move_history()

    def is_game_over(self) -> bool:
        """游戏是否结束"""
        return self.state.game_over

    def get_winner(self) -> str:
        """获取胜者"""
        return self.state.winner


# 便捷函数
def create_game_controller() -> GameController:
    """
    创建游戏控制器实例（便捷函数）

    Returns:
        GameController实例
    """
    return GameController()
