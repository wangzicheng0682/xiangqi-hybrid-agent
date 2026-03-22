"""
象棋AI混合代理 - 现代化前端

使用Flask + HTML + JavaScript
不使用Gradio
"""

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass, field
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.rules.xiangqi_rules import XiangqiRulesEngine
from core.opening import get_opening_evaluation, get_opening_name, identify_position_type
from core.engine import MockEngine

app = Flask(__name__)
CORS(app)


PIECE_NAMES = {
    'K': '帅', 'k': '将', 'A': '仕', 'a': '士',
    'B': '相', 'b': '象', 'R': '车', 'r': '車',
    'C': '炮', 'c': '砲', 'N': '马', 'n': '馬',
    'P': '兵', 'p': '卒',
}

INITIAL_BOARD = [
    ['r', 'n', 'b', 'a', 'k', 'a', 'b', 'n', 'r'],
    ['', '', '', '', '', '', '', '', '', ''],
    ['', 'c', '', '', '', '', '', 'c', ''],
    ['p', '', 'p', '', 'p', '', 'p', '', 'p'],
    ['', '', '', '', '', '', '', '', '', ''],
    ['', '', '', '', '', '', '', '', '', ''],
    ['P', '', 'P', '', 'P', '', 'P', '', 'P'],
    ['', 'C', '', '', '', '', '', 'C', ''],
    ['', '', '', '', '', '', '', '', '', ''],
    ['R', 'N', 'B', 'A', 'K', 'A', 'B', 'N', 'R'],
]


@dataclass
class GameState:
    board: List[List[str]] = field(default_factory=lambda: [row[:] for row in INITIAL_BOARD])
    red_to_move: bool = True
    selected_pos: Optional[Tuple[int, int]] = None
    legal_moves: List[Tuple[int, int]] = field(default_factory=list)
    move_history: List[str] = field(default_factory=list)
    game_over: bool = False
    winner: Optional[str] = None


# 全局游戏状态
game_state = GameState()
engine = MockEngine()


@app.route('/')
def index():
    """主页"""
    try:
        return render_template('chess.html')
    except Exception as e:
        return f"Template error: {str(e)}", 500


@app.route('/api/initial', methods=['GET'])
def get_initial_state():
    """获取初始游戏状态"""
    try:
        return jsonify({
            'board': INITIAL_BOARD,
            'red_to_move': True,
            'selected_pos': None,
            'legal_moves': [],
            'move_history': [],
            'game_over': False,
            'winner': None
        })
    except Exception as e:
        return jsonify({'error': f'获取初始状态失败: {str(e)}'}), 500


@app.route('/api/click', methods=['POST'])
def handle_click():
    """处理棋盘点击"""
    try:
        data = request.json
        row = data.get('row')
        col = data.get('col')

        if not (0 <= row < 10 and 0 <= col < 9):
            return jsonify({'error': '无效位置'}), 400

        board = game_state.board
        piece = board[row][col]

        if game_state.selected_pos:
            # 尝试走棋
            sr, sc = game_state.selected_pos
            if (row, col) in game_state.legal_moves:
                # 执行走棋
                captured = board[row][col]
                moving_piece = board[sr][sc]
                board[sr][sc] = ''
                board[row][col] = moving_piece

                from_coord = f"{chr(sc + ord('a'))}{9 - sr}"
                to_coord = f"{chr(col + ord('a'))}{9 - row}"
                player = "红方" if not game_state.red_to_move else "黑方"
                piece_name = PIECE_NAMES.get(moving_piece, moving_piece)

                move_str = f"{player}: {piece_name} {from_coord}{to_coord}"
                game_state.move_history.append(move_str)
                game_state.selected_pos = None
                game_state.legal_moves = []
                game_state.red_to_move = not game_state.red_to_move

                # 检查游戏结束
                if captured and captured.lower() == 'k':
                    game_state.game_over = True
                    game_state.winner = "红方" if not game_state.red_to_move else "黑方"

                return jsonify({
                    'board': board,
                    'selected_pos': None,
                    'legal_moves': [],
                    'move_history': game_state.move_history,
                    'game_over': game_state.game_over,
                    'winner': game_state.winner,
                    'message': "走棋成功"
                })
            else:
                # 取消选择
                game_state.selected_pos = None
                game_state.legal_moves = []
                return jsonify({
                    'board': board,
                    'selected_pos': None,
                    'legal_moves': [],
                    'move_history': game_state.move_history,
                    'message': '取消选择'
                })
        else:
            # 尝试选中棋子
            if piece:
                is_red = piece.isupper()
                if is_red == game_state.red_to_move:
                    legal_moves = XiangqiRulesEngine.get_legal_moves(board, row, col)
                    if legal_moves:
                        game_state.selected_pos = (row, col)
                        game_state.legal_moves = legal_moves
                        return jsonify({
                            'board': board,
                            'selected_pos': (row, col),
                            'legal_moves': legal_moves,
                            'move_history': game_state.move_history,
                            'message': f"选中 {PIECE_NAMES.get(piece, piece)}"
                        })
                    else:
                        return jsonify({'message': '该棋子没有可走的合法位置'}), 400
                else:
                    return jsonify({'message': '不是你的回合'}), 400
            else:
                return jsonify({'message': '空格，请选择棋子'}), 400
    except Exception as e:
        return jsonify({'error': f'请求处理失败: {str(e)}'}), 500


@app.route('/api/new_game', methods=['POST'])
def new_game():
    """新游戏"""
    try:
        game_state.board = [row[:] for row in INITIAL_BOARD]
        game_state.red_to_move = True
        game_state.selected_pos = None
        game_state.legal_moves = []
        game_state.move_history = []
        game_state.game_over = False
        game_state.winner = None

        return jsonify({
            'board': INITIAL_BOARD,
            'red_to_move': True,
            'selected_pos': None,
            'legal_moves': [],
            'move_history': [],
            'game_over': False,
            'winner': None,
            'message': '新游戏开始'
        })
    except Exception as e:
        return jsonify({'error': f'新游戏失败: {str(e)}'}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
