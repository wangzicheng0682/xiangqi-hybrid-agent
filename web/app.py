"""
象棋AI混合代理 - 重构版主入口

职责: 路由注册、组件整合

文档依据: JOINT_REFACTOR_ARCHITECTURE.md 主入口设计

架构:
- < 100行，仅负责路由注册
- 使用模块化架构（routes、components、modes）
- 集成LangGraph Agent工作流

运行命令:
    python web/app.py
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import gradio as gr
from core.agent import get_agent
from web.state.board_state import BoardState
from web.modes.pgn_mode import PGNMode
from web.modes.play_mode import PlayMode
from web.modes.review_mode import ReviewMode
from web.routes.pgn import PGNRoute
from web.routes.play import PlayRoute
from web.routes.review import ReviewRoute
from web.components.board import render_board_image, INITIAL_BOARD


def main():
    """主函数"""
    # 初始化Agent
    agent = get_agent()

    # 初始化模式
    pgn_mode = PGNMode(agent)
    play_mode = PlayMode(agent)
    review_mode = ReviewMode(agent)

    # 初始化路由
    pgn_route = PGNRoute(agent, pgn_mode)
    play_route = PlayRoute(agent, play_mode)
    review_route = ReviewRoute(agent, review_mode)

    # 初始化状态
    play_state = BoardState()
    review_state = {"scores": [], "moves": []}

    # 构建Gradio应用
    with gr.Blocks(title="象棋AI混合代理 - v0.4.0") as demo:
        gr.Markdown("""
        # 🏯 象棋AI混合代理教学系统

        **商业级重构版** - 天天象棋级别体验

        📖 下棋谱 | 🎮 人机对战 | 📊 复盘分析
        """)

        with gr.Tabs():
            # PGN模式Tab
            with gr.TabItem("📖 下棋谱"):
                with gr.Row():
                    with gr.Column(scale=1):
                        pgn_file = gr.File(label="上传PGN文件", file_types=[".pgn"])
                        pgn_game_list = gr.Markdown(label="对局列表")
                        with gr.Row():
                            pgn_next_btn = gr.Button("下一步 ▶")
                            pgn_prev_btn = gr.Button("◀ 上一步")
                        pgn_status = gr.Textbox(label="状态", interactive=False)

                    with gr.Column(scale=2):
                        pgn_board = gr.Image(label="棋盘", type="filepath", interactive=False)

                # 事件绑定
                pgn_file.upload(
                    fn=pgn_route.handle_file_upload,
                    inputs=[pgn_file],
                    outputs=[pgn_game_list, pgn_board, pgn_status]
                )
                pgn_next_btn.click(
                    fn=pgn_route.handle_next_move,
                    outputs=[gr.Number(label="当前着法"), pgn_board, pgn_status]
                )
                pgn_prev_btn.click(
                    fn=pgn_route.handle_prev_move,
                    outputs=[gr.Number(label="当前着法"), pgn_board, pgn_status]
                )

            # 人机对战Tab
            with gr.TabItem("🎮 人机对战"):
                with gr.Row():
                    with gr.Column(scale=1):
                        play_mode_radio = gr.Radio(
                            choices=[
                                ("📊 分析模式", "analysis"),
                                ("⚔️ 对战模式", "battle")
                            ],
                            value="analysis",
                            label="AI模式"
                        )
                        difficulty_slider = gr.Slider(1, 10, value=10, step=1, label="AI难度")
                        play_status = gr.Textbox(label="对局状态", interactive=False)
                        new_game_btn = gr.Button("🔄 新对局", variant="primary")
                        analyze_btn = gr.Button("🔍 详细分析", variant="secondary")

                    with gr.Column(scale=2):
                        play_board = gr.Image(
                            value=render_board_image([row[:] for row in INITIAL_BOARD]),
                            label="棋盘",
                            type="filepath",
                            interactive=False
                        )
                        play_analysis = gr.Markdown(label="详细分析")

                # 事件绑定
                play_mode_radio.change(
                    fn=play_route.handle_set_ai_mode,
                    inputs=[play_mode_radio],
                    outputs=[play_status]
                )
                difficulty_slider.change(
                    fn=play_route.handle_difficulty_change,
                    inputs=[difficulty_slider],
                    outputs=[play_status]
                )
                new_game_btn.click(
                    fn=play_route.handle_new_game,
                    outputs=[play_status, play_board]
                )
                analyze_btn.click(
                    fn=play_route.handle_analyze,
                    inputs=[gr.State(value=play_state)],
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

                # 事件绑定
                analyze_game_btn.click(
                    fn=review_route.handle_analyze_game,
                    inputs=[moves_input, red_player, black_player, result_radio],
                    outputs=[review_chart, review_report, gr.State(value=review_state)]
                )

    # 启动应用
    demo.launch(server_name="0.0.0.0", server_port=7868)


if __name__ == "__main__":
    main()
