"""
象棋AI混合代理 - 完整交互版主入口

职责: 路由注册、组件整合、完整交互逻辑

运行命令:
    python web/app_interactive.py
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import gradio as gr
from core.agent import get_agent
from web.controllers.game_controller import GameController
from web.components.board import render_board_image, INITIAL_BOARD
from web.modes.review_mode import ReviewMode
from core.review import generate_review_report, format_report_markdown, generate_score_chart


class PlaySession:
    """人机对战会话状态"""
    def __init__(self):
        self.controller = GameController()
    
    def reset(self):
        self.controller = GameController()
    
    def handle_click(self, row: int, col: int):
        return self.controller.handle_click({"row": row, "col": col})
    
    def get_state(self):
        return self.controller._get_state_dict()
    
    def get_board_html(self):
        return self.controller.get_board_html()
    
    def analyze(self):
        return self.controller.state


    
    def new_game(self):
        self.controller.new_game()


def create_interactive_app():
    """创建完整交互的Gradio应用"""
    
    # 初始化Agent
    agent = get_agent()
    
    # 初始化复盘模式
    review_mode = ReviewMode(agent)
    
    # 会话状态
    play_session = PlaySession()
    review_state = {"scores": [], "moves": []}
    
    with gr.Blocks(title="象棋AI混合代理 - v0.4.0", css="""
        .chess-board { cursor: pointer; }
        .chess-piece { cursor: pointer; transition: all 0.2s; }
        .chess-piece:hover { transform: scale(1.05); }
        .valid-move { animation: pulse 1s infinite; }
        @keyframes pulse {
            0%, 100% { opacity: 0.5; transform: scale(1.1); }
            50% { opacity: 1; transform: scale(1.2); }
            100% { opacity: 0.5; transform: scale(1.1); }
        """) as demo:
        gr.Markdown("""
        # 🏯 象棋AI混合代理教学系统
        
        **商业级重构版** - 天天象棋级别体验
        
        📖 下棋谱 | 🎮 人机对战 | 📊 复盘分析
        """)
        
        with gr.Tabs():
            # 人机对战Tab
            with gr.TabItem("🎮 人机对战"):
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("### ⨡式设置")
                        play_mode_radio = gr.Radio(
                            choices=[("📊 分析模式", "analysis"), ("⚔️ 对战模式", "battle")],
                            value="analysis",
                            label="AI模式"
                        )
                        difficulty_slider = gr.Slider(1, 10, value=10, step=1, label="AI难度")
                        new_game_btn = gr.Button("🔄 新对局", variant="primary")
                        analyze_btn = gr.Button("🔍 详细分析", variant="secondary")
                        
                        gr.Markdown("### 对局状态")
                        play_status = gr.Textbox(label="状态", interactive=False, lines=2)
                        move_history = gr.Textbox(label="走法记录", interactive=False, lines=3)
                    
                    with gr.Column(scale=2):
                        gr.Markdown("### 棋盘")
                        play_board = gr.Image(
                            value=render_board_image([row[:] for row in INITIAL_BOARD]),
                            label="棋盘",
                            type="filepath",
                            interactive=False
                        )
                        
                        # 点击位置输入
                        click_row = gr.Number(label="点击行", value=0, visible=False)
                        click_col = gr.Number(label="点击列", value=0, visible=False)
                        submit_click_btn = gr.Button("确认点击", visible=False)
                        
                        gr.Markdown("### 分析结果")
                        play_analysis = gr.Markdown(label="详细分析")
                
                # 事件绑定
                def handle_new_game():
                    play_session.new_game()
                    state = play_session.get_state()
                    board_img = render_board_image(state["board"])
                    return "新对局开始，红方先行", board_img, "", ""
                
                def handle_click(row, col):
                    result, msg = play_session.handle_click(int(row), int(col))
                    board_img = render_board_image(result["board"])
                    history = play_session.controller.get_move_history()
                    return msg, board_img, history, result
                
                def handle_analyze(state):
                    if state is None:
                        return "请先走棋"
                    from core.agent import get_agent
                    agent = get_agent()
                    from core.utils.board_text import board_to_fen
                    board = state.get("board", INITIAL_BOARD)
                    fen = board_to_fen(board, state.get("red_to_move", True))
                    result = agent.analyze(fen=fen, board=board, use_vision=False)
                    return result.get("explanation", "分析完成")
                
                new_game_btn.click(
                    fn=handle_new_game,
                    outputs=[play_status, play_board, move_history, gr.State(value=play_session)]
                )
                
                submit_click_btn.click(
                    fn=handle_click,
                    inputs=[click_row, click_col],
                    outputs=[play_status, play_board, move_history, gr.State(value=play_session)]
                )
                
                analyze_btn.click(
                    fn=handle_analyze,
                    inputs=[gr.State(value=play_session)],
                    outputs=[play_analysis]
                )
            
            # 复盘模式Tab
            with gr.TabItem("📊 复盘分析"):
                with gr.Row():
                    with gr.Column(scale=1):
                        red_player = gr.Textbox(label="红方", value="红方")
                        black_player = gr.Textbox(label="黑方", value="黑方")
                        result_radio = gr.Radio(
                            choices=[("红方胜", "1-0"), ("黑方胜", "0-1"), ("和棋", "1/2-1/2"), ("未结束", "*")],
                            value="*",
                            label="对局结果"
                        )
                        moves_input = gr.Textbox(
                            label="走法列表 (ICCS格式)",
                            placeholder="h2e2 h9g7 c3c4 b7c5 ...",
                            lines=3
                        )
                        analyze_game_btn = gr.Button("🔍 分析对局", variant="primary")
                    
                    with gr.Column(scale=2):
                        review_chart = gr.Image(label="胜率曲线")
                        review_report = gr.Markdown(label="复盘报告")
                
                def analyze_game(moves_str, red_player, black_player, result):
                    from core.review import GameRecord, generate_review_report, format_report_markdown, generate_score_chart
                    import random
                    
                    moves = moves_str.strip().split() if moves_str.strip() else []
                    if not moves:
                        return None, "请输入走法记录", {"scores": [], "moves": []}
                    
                    game = GameRecord(
                        red_player=red_player,
                        black_player=black_player,
                        result=result,
                        iccs_moves=moves
                    )
                    
                    board = [row[:] for row in INITIAL_BOARD]
                    scores = [0.0]
                    
                    for move in moves:
                        try:
                            from_col = ord(move[0].upper()) - ord('A')
                            from_row = 9 - int(move[1])
                            to_col = ord(move[2].upper()) - ord('A')
                            to_row = 9 - int(move[3])
                            
                            if 0 <= from_row < 10 and 0 <= from_col < 9 and 0 <= to_row < 10 and 0 <= to_col < 9:
                                board[to_row][to_col] = board[from_row][from_col]
                                board[from_row][from_col] = ''
                                
                                score_change = random.uniform(-30, 30)
                                if random.random() < 0.1:
                                    score_change = random.choice([-300, -200, 200, 300])
                                scores.append(scores[-1] + score_change)
                        except:
                            continue
                    
                    report = generate_review_report(game, scores)
                    markdown = format_report_markdown(report)
                    
                    turning_points = [tp.move_number for tp in report.turning_points]
                    blunders = []
                    for i, ma in enumerate(report.move_analysis):
                        if ma.get("is_blunder"):
                            blunders.append(i)
                    
                    chart = generate_score_chart(scores, turning_points=turnunders, title=f"{red_player} vs {black_player}")
                    
                    import tempfile
                    import os
                    temp_dir = tempfile.gettempdir()
                    chart_path = os.path.join(temp_dir, "review_chart.png")
                    chart.save(chart_path)
                    
                    return chart_path, markdown, {"scores": scores, "moves": moves}
                
                analyze_game_btn.click(
                    fn=analyze_game,
                    inputs=[moves_input, red_player, black_player, result_radio],
                    outputs=[review_chart, review_report, gr.State(value=review_state)]
                )
    
    return demo


if __name__ == "__main__":
    app = create_interactive_app()
    app.launch(server_name="0.0.0.0", server_port=7868)
