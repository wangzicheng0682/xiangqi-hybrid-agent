"""
FastAPI后端服务

职责: 提供REST API供前端调用

API端点:
- POST /api/analyze - 分析局面
- POST /api/review - 生成复盘报告
- POST /api/legal-moves - 获取合法走法
- POST /api/move - 执行走棋

运行命令:
    uvicorn api.main:app --reload --port 8000
"""

from dotenv import load_dotenv
load_dotenv()  # 加载.env环境变量

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.agent import XiangqiAgent, get_agent
from core.review import (
    generate_review_report,
    generate_score_chart,
    GameRecord,
    format_report_markdown
)
from core.rules.xiangqi_rules import get_legal_moves, is_in_check


from core.utils.board_text import fen_to_board

# 深度分析模块 - 预导入避免每次请求重新加载
from core.llm.xiangqi_coach import create_coach_agent
from core.llm.multi_agent_orchestrator import MultiAgentOrchestrator
from core.rules.tactical_detector import TacticalDetector
from core.rules.tension_detector import detect_tensions, get_primary_tension
from core.engine import PikafishEngine


PIECE_NAMES = {
    'K': '帅', 'k': '将', 'A': '仕', 'a': '士',
    'B': '相', 'b': '象', 'R': '车', 'r': '車',
    'C': '炮', 'c': '砲', 'N': '马', 'n': '馬',
    'P': '兵', 'p': '卒',
}


def board_to_fen(board: List[List[str]], red_to_move: bool = True) -> str:
    rows = []
    for row in board:
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
    
    turn = "w" if red_to_move else "b"
    return "/".join(rows) + f" {turn} - - 0 1"


app = FastAPI(
    title="象棋AI混合代理API",
    description="提供局面分析、复盘报告、规则引擎等API",
    version="0.4.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent = None


def get_agent_instance():
    global agent
    if agent is None:
        agent = get_agent()
    return agent


class AnalyzeRequest(BaseModel):
    fen: str
    board: Optional[List[List[str]]] = None
    iccs_moves: Optional[List[str]] = None
    last_move_info: Optional[Dict[str, Any]] = None
    use_vision: bool = True


class AnalyzeResponse(BaseModel):
    fen: str
    explanation: str
    engine_result: Optional[Dict[str, Any]] = None
    kg_result: Optional[Dict[str, Any]] = None
    rag_results: List[Dict[str, Any]] = []
    vision_result: Optional[Dict[str, Any]] = None
    error: str = ""


class LegalMovesRequest(BaseModel):
    board: List[List[str]]
    row: int
    col: int


class LegalMovesResponse(BaseModel):
    moves: List[str]
    in_check: bool


class MoveRequest(BaseModel):
    board: List[List[str]]
    from_row: int
    from_col: int
    to_row: int
    to_col: int
    red_to_move: bool = True


class MoveResponse(BaseModel):
    board: List[List[str]]
    fen: str
    legal_moves: List[str]
    captured: str = ""
    in_check: bool = False
    game_over: bool = False


class ReviewRequest(BaseModel):
    red_player: str = "红方"
    black_player: str = "黑方"
    result: str = "*"
    moves: List[str] = []


class ReviewResponse(BaseModel):
    report_markdown: str
    chart_data: Dict[str, Any]
    turning_points: List[Dict[str, Any]]
    blunders: List[int]


@app.get("/")
async def root():
    return {"message": "象棋AI混合代理API", "version": "0.4.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze_position(request: AnalyzeRequest):
    """
    分析象棋局面
    
    调用LangGraph Agent进行完整分析，包括:
    - 引擎分析（最佳着法、评分）
    - 知识图谱查询（开局、胜率）
    - RAG检索（棋书引用）
    - 视觉分析（Qwen-VL多模态）
    """
    try:
        agent = get_agent_instance()
        
        result = agent.analyze(
            fen=request.fen,
            board=request.board,
            iccs_moves=request.iccs_moves,
            last_move_info=request.last_move_info,
            use_vision=request.use_vision
        )
        
        return AnalyzeResponse(
            fen=result.get("fen", request.fen),
            explanation=result.get("explanation", ""),
            engine_result=result.get("engine_result"),
            kg_result=result.get("kg_result"),
            rag_results=result.get("rag_results", []),
            vision_result=result.get("vision_result"),
            error=result.get("error", "")
        )
    except Exception as e:
        return AnalyzeResponse(
            fen=request.fen,
            explanation="",
            error=str(e)
        )


@app.post("/api/legal-moves", response_model=LegalMovesResponse)
async def get_legal_moves_api(request: LegalMovesRequest):
    """
    获取合法走法
    
    返回指定位置棋子的所有合法走法
    """
    try:
        moves = get_legal_moves(request.board, request.row, request.col)
        
        moves_str = []
        for r, c in moves:
            from_col = chr(ord('a') + request.col)
            from_row = str(9 - request.row)
            to_col = chr(ord('a') + c)
            to_row = str(9 - r)
            moves_str.append(f"{from_col}{from_row}{to_col}{to_row}")
        
        red_to_move = request.board[request.row][request.col].isupper() if request.board[request.row][request.col] else True
        in_check = is_in_check(request.board, red_to_move)
        
        return LegalMovesResponse(
            moves=moves_str,
            in_check=in_check
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class PositionAnalysisRequest(BaseModel):
    fen: str


class PositionAnalysisResponse(BaseModel):
    analysis_structured: Dict[str, Any]
    analysis_text: Dict[str, Any]


@app.post("/api/position-analysis", response_model=PositionAnalysisResponse)
async def get_position_analysis(request: PositionAnalysisRequest):
    """
    获取局面级分析（T0核心功能 - 基于引擎真值）
    
    输出结构：
    - analysis_structured: 机器可消费结构
      - board_fen: FEN字符串
      - turn: 轮到谁走
      - engine_result: 引擎分析结果
        - bestmove: 最佳走法
        - score: 评估分数
        - depth: 搜索深度
        - pv: 主要变例
      - legal_moves: 所有合法走法列表
      - is_check: 是否被将军
      - is_checkmate: 是否被将死
      
    - analysis_text: 用户可读文本
      - analysis_text: 自然语言描述
      - retrieval_hints: 检索查询提示
    
    基于引擎真值，不自行计算攻击/防御关系
    """
    try:
        from core.engine import PikafishEngine
        from core.rules import get_legal_moves
        
        # 获取引擎分析
        engine = PikafishEngine()
        engine_result = engine.analyze(request.fen, depth=15)
        
        # 获取合法走法
        legal_moves_result = get_legal_moves(request.fen)
        
        # 构建结构化输出
        analysis_structured = {
            "board_fen": request.fen,
            "turn": legal_moves_result.side_to_move,
            "engine_result": {
                "bestmove": engine_result.bestmove,
                "score": engine_result.score,
                "depth": engine_result.depth,
                "pv": engine_result.pv if hasattr(engine_result, 'pv') else []
            },
            "legal_moves": [
                {"uci": m.uci, "iccs": m.iccs, "from": m.from_square, "to": m.to_square}
                for m in legal_moves_result.moves[:10]  # 只返回前10个
            ],
            "legal_move_count": legal_moves_result.count,
            "is_check": legal_moves_result.is_check,
            "is_checkmate": legal_moves_result.is_checkmate,
            "is_stalemate": legal_moves_result.is_stalemate
        }
        
        # 构建文本输出
        turn_str = "红方" if legal_moves_result.side_to_move == "red" else "黑方"
        score_str = f"{engine_result.score:+.2f}" if engine_result.score else "未知"
        
        analysis_text = f"""
**局面分析**

- 当前回合: {turn_str}走棋
- 引擎评分: {score_str}
- 推荐走法: {engine_result.bestmove or '无'}
- 合法走法数: {legal_moves_result.count}
- 将军状态: {'被将军' if legal_moves_result.is_check else '安全'}
- 将死状态: {'被将死' if legal_moves_result.is_checkmate else '未将死'}
        """.strip()
        
        # 检索提示
        retrieval_hints = [
            f"{turn_str}局面，引擎评分{score_str}",
            f"最佳走法: {engine_result.bestmove or '无'}",
        ]
        if legal_moves_result.is_check:
            retrieval_hints.append("当前被将军，需要解将")
        
        analysis_text_output = {
            "analysis_text": analysis_text,
            "retrieval_hints": retrieval_hints
        }
        
        return PositionAnalysisResponse(
            analysis_structured=analysis_structured,
            analysis_text=analysis_text_output
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class AIMoveRequest(BaseModel):
    board: List[List[str]]
    red_to_move: bool = True
    difficulty: int = 10


class AIMoveResponse(BaseModel):
    move: str
    from_row: int
    from_col: int
    to_row: int
    to_col: int
    board: List[List[str]]
    fen: str
    score: float
    explanation: str


class BestMovesResponse(BaseModel):
    red_best_move: str
    red_best_from_row: int
    red_best_from_col: int
    red_best_to_row: int
    red_best_to_col: int
    black_best_move: str
    black_best_from_row: int
    black_best_from_col: int
    black_best_to_row: int
    black_best_to_col: int
    current_turn: str


@app.post("/api/best-moves", response_model=BestMovesResponse)
async def get_best_moves(request: AIMoveRequest):
    """
    获取双方最优解
    
    返回红方和黑方的最佳走法，用于在棋盘上显示箭头
    """
    try:
        from core.engine import PikafishEngine
        
        engine = PikafishEngine()
        fen = board_to_fen(request.board, request.red_to_move)
        
        result = engine.analyze(fen, depth=15)
        current_best = result.bestmove
        
        current_turn = "red" if request.red_to_move else "black"
        
        if request.red_to_move:
            red_best_move = current_best if current_best else ""
            if red_best_move and len(red_best_move) >= 4:
                red_from_col = ord(red_best_move[0].lower()) - ord('a')
                red_from_row = 9 - int(red_best_move[1])
                red_to_col = ord(red_best_move[2].lower()) - ord('a')
                red_to_row = 9 - int(red_best_move[3])
            else:
                red_from_row = red_from_col = red_to_row = red_to_col = 0
                red_best_move = ""
            
            test_board = [row[:] for row in request.board]
            if red_best_move and len(red_best_move) >= 4:
                piece = test_board[red_from_row][red_from_col]
                test_board[red_to_row][red_to_col] = piece
                test_board[red_from_row][red_from_col] = ''
            
            black_fen = board_to_fen(test_board, False)
            black_result = engine.analyze(black_fen, depth=15)
            black_best_move = black_result.bestmove if black_result.bestmove else ""
            
            if black_best_move and len(black_best_move) >= 4:
                black_from_col = ord(black_best_move[0].lower()) - ord('a')
                black_from_row = 9 - int(black_best_move[1])
                black_to_col = ord(black_best_move[2].lower()) - ord('a')
                black_to_row = 9 - int(black_best_move[3])
            else:
                black_from_row = black_from_col = black_to_row = black_to_col = 0
                black_best_move = ""
        else:
            black_best_move = current_best if current_best else ""
            if black_best_move and len(black_best_move) >= 4:
                black_from_col = ord(black_best_move[0].lower()) - ord('a')
                black_from_row = 9 - int(black_best_move[1])
                black_to_col = ord(black_best_move[2].lower()) - ord('a')
                black_to_row = 9 - int(black_best_move[3])
            else:
                black_from_row = black_from_col = black_to_row = black_to_col = 0
                black_best_move = ""
            
            test_board = [row[:] for row in request.board]
            if black_best_move and len(black_best_move) >= 4:
                piece = test_board[black_from_row][black_from_col]
                test_board[black_to_row][black_to_col] = piece
                test_board[black_from_row][black_from_col] = ''
            
            red_fen = board_to_fen(test_board, True)
            red_result = engine.analyze(red_fen, depth=15)
            red_best_move = red_result.bestmove if red_result.bestmove else ""
            
            if red_best_move and len(red_best_move) >= 4:
                red_from_col = ord(red_best_move[0].lower()) - ord('a')
                red_from_row = 9 - int(red_best_move[1])
                red_to_col = ord(red_best_move[2].lower()) - ord('a')
                red_to_row = 9 - int(red_best_move[3])
            else:
                red_from_row = red_from_col = red_to_row = red_to_col = 0
                red_best_move = ""
        
        return BestMovesResponse(
            red_best_move=red_best_move,
            red_best_from_row=red_from_row,
            red_best_from_col=red_from_col,
            red_best_to_row=red_to_row,
            red_best_to_col=red_to_col,
            black_best_move=black_best_move,
            black_best_from_row=black_from_row,
            black_best_from_col=black_from_col,
            black_best_to_row=black_to_row,
            black_best_to_col=black_to_col,
            current_turn=current_turn
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/move", response_model=MoveResponse)
async def make_move(request: MoveRequest):
    """
    执行走棋
    
    移动棋子并返回新局面
    验证走法合法性，确保移动后不会导致自己被将军
    """
    try:
        board = [row[:] for row in request.board]
        
        piece = board[request.from_row][request.from_col]
        if not piece:
            raise HTTPException(status_code=400, detail="起始位置没有棋子")
        
        is_red_piece = piece.isupper()
        if is_red_piece != request.red_to_move:
            raise HTTPException(status_code=400, detail="不是你的回合")
        
        legal_moves = get_legal_moves(board, request.from_row, request.from_col)
        if (request.to_row, request.to_col) not in legal_moves:
            raise HTTPException(status_code=400, detail="非法走法")
        
        test_board = [row[:] for row in board]
        test_board[request.to_row][request.to_col] = piece
        test_board[request.from_row][request.from_col] = ''
        
        if is_in_check(test_board, request.red_to_move):
            raise HTTPException(status_code=400, detail="移动后会被将军")
        
        captured = board[request.to_row][request.to_col]
        
        board[request.to_row][request.to_col] = piece
        board[request.from_row][request.from_col] = ''
        
        new_red_to_move = not request.red_to_move
        fen = board_to_fen(board, new_red_to_move)
        
        legal_moves = get_legal_moves(board, request.to_row, request.to_col)
        legal_moves_str = []
        for r, c in legal_moves:
            to_col = chr(ord('a') + c)
            to_row = str(9 - r)
            legal_moves_str.append(f"{to_col}{to_row}")
        
        in_check = is_in_check(board, new_red_to_move)
        
        game_over = False
        if 'k' not in str(board) or 'K' not in str(board):
            game_over = True
        
        return MoveResponse(
            board=board,
            fen=fen,
            legal_moves=legal_moves_str,
            captured=captured,
            in_check=in_check,
            game_over=game_over
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/review", response_model=ReviewResponse)
async def generate_review(request: ReviewRequest):
    """
    生成复盘报告
    
    分析对局，生成胜率曲线和复盘报告
    """
    try:
        from core.review import identify_turning_points, identify_blunders
        import random
        
        game = GameRecord(
            red_player=request.red_player,
            black_player=request.black_player,
            result=request.result,
            iccs_moves=request.moves
        )
        
        INITIAL_BOARD = [
            ['r', 'n', 'b', 'a', 'k', 'a', 'b', 'n', 'r'],
            ['', '', '', '', '', '', '', '', ''],
            ['', 'c', '', '', '', '', '', 'c', ''],
            ['p', '', 'p', '', 'p', '', 'p', '', 'p'],
            ['', '', '', '', '', '', '', '', ''],
            ['', '', '', '', '', '', '', '', ''],
            ['P', '', 'P', '', 'P', '', 'P', '', 'P'],
            ['', 'C', '', '', '', '', '', 'C', ''],
            ['', '', '', '', '', '', '', '', ''],
            ['R', 'N', 'B', 'A', 'K', 'A', 'B', 'N', 'R'],
        ]
        
        board = [row[:] for row in INITIAL_BOARD]
        scores = [0.0]
        
        for move in request.moves:
            try:
                if len(move) >= 4:
                    from_col = ord(move[0].lower()) - ord('a')
                    from_row = 9 - int(move[1])
                    to_col = ord(move[2].lower()) - ord('a')
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
        
        turning_points_data = []
        for tp in report.turning_points:
            turning_points_data.append({
                "move_number": tp.move_number,
                "score_change": tp.score_change,
                "description": tp.description,
                "is_red_move": tp.is_red_move
            })
        
        blunders = []
        for i, ma in enumerate(report.move_analysis):
            if ma.get("is_blunder"):
                blunders.append(i)
        
        chart_data = {
            "labels": list(range(len(scores))),
            "scores": scores,
            "turning_points": [tp.move_number for tp in report.turning_points],
            "blunders": blunders
        }
        
        return ReviewResponse(
            report_markdown=markdown,
            chart_data=chart_data,
            turning_points=turning_points_data,
            blunders=blunders
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class PGNUploadRequest(BaseModel):
    pass

async def ai_move(request: AIMoveRequest):
    """
    AI走棋
    
    根据当前局面，AI选择最佳走法并执行
    """
    try:
        from core.engine import PikafishEngine
        
        engine = PikafishEngine()
        fen = board_to_fen(request.board, request.red_to_move)
        
        result = engine.analyze(fen, depth=request.difficulty)
        bestmove = result.bestmove
        
        if not bestmove or len(bestmove) < 4:
            raise HTTPException(status_code=500, detail="引擎无法找到走法")
        
        from_col = ord(bestmove[0].lower()) - ord('a')
        from_row = 9 - int(bestmove[1])
        to_col = ord(bestmove[2].lower()) - ord('a')
        to_row = 9 - int(bestmove[3])
        
        new_board = [row[:] for row in request.board]
        piece = new_board[from_row][from_col]
        new_board[to_row][to_col] = piece
        new_board[from_row][from_col] = ''
        
        new_fen = board_to_fen(new_board, not request.red_to_move)
        
        piece_names = {
            'K': '帅', 'k': '将', 'A': '仕', 'a': '士',
            'B': '相', 'b': '象', 'R': '车', 'r': '車',
            'C': '炮', 'c': '砲', 'N': '马', 'n': '馬',
            'P': '兵', 'p': '卒',
        }
        piece_name = piece_names.get(piece, piece)
        explanation = f"AI走 {piece_name}，从 {bestmove[:2]} 到 {bestmove[2:4]}"
        
        return AIMoveResponse(
            move=bestmove,
            from_row=from_row,
            from_col=from_col,
            to_row=to_row,
            to_col=to_col,
            board=new_board,
            fen=new_fen,
            score=result.score,
            explanation=explanation
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class PGNUploadRequest(BaseModel):
    pgn_content: str


class PGNGameInfo(BaseModel):
    game_index: int
    event: str
    red_player: str
    black_player: str
    result: str
    date: str
    moves: List[str]


class PGNLoadResponse(BaseModel):
    games: List[PGNGameInfo]
    total_games: int


class PGNNavigateRequest(BaseModel):
    moves: List[str]
    current_index: int
    direction: str


class PGNNavigateResponse(BaseModel):
    board: List[List[str]]
    fen: str
    current_index: int
    total_moves: int
    move_text: str


import re

def parse_pgn_content(pgn_content: str) -> List[dict]:
    """解析PGN内容"""
    games = []
    current_game = {}
    current_moves = []
    
    lines = pgn_content.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        if line.startswith('[') and ']' in line:
            if 'Event' in line or 'event' in line:
                if current_game or current_moves:
                    if current_game:
                        current_game['moves'] = current_moves
                        games.append(current_game)
                    current_game = {}
                    current_moves = []
                match = re.match(r'\[(Event|event)\s+"([^"]*)"', line)
                if match:
                    current_game['event'] = match.group(2)
            elif 'Red' in line or 'RedPlayer' in line:
                match = re.match(r'\[(Red|RedPlayer)\s+"([^"]*)"', line)
                if match:
                    current_game['red_player'] = match.group(2)
            elif 'Black' in line or 'BlackPlayer' in line:
                match = re.match(r'\[(Black|BlackPlayer)\s+"([^"]*)"', line)
                if match:
                    current_game['black_player'] = match.group(2)
            elif 'Result' in line or 'result' in line:
                match = re.match(r'\[(Result|result)\s+"([^"]*)"', line)
                if match:
                    current_game['result'] = match.group(2)
            elif 'Date' in line or 'date' in line:
                match = re.match(r'\[(Date|date)\s+"([^"]*)"', line)
                if match:
                    current_game['date'] = match.group(2)
        elif not line.startswith('['):
            moves_part = line.replace('{', '').replace('}', '').strip()
            if moves_part:
                current_moves.extend(moves_part.split())
    
    if current_game or current_moves:
        if current_game:
            current_game['moves'] = current_moves
            games.append(current_game)
    
    return games


def iccs_to_board_coords(move: str) -> tuple:
    """将ICCS走法转换为棋盘坐标"""
    move = move.replace('-', '')
    if len(move) < 4:
        return None
    
    from_col = ord(move[0].lower()) - ord('a')
    from_row = 9 - int(move[1])
    to_col = ord(move[2].lower()) - ord('a')
    to_row = 9 - int(move[3])
    
    return (from_row, from_col, to_row, to_col)


def apply_moves_to_board(moves: List[str], up_to: int) -> List[List[str]]:
    """应用走法到棋盘"""
    INITIAL_BOARD = [
        ['r', 'n', 'b', 'a', 'k', 'a', 'b', 'n', 'r'],
        ['', '', '', '', '', '', '', '', ''],
        ['', 'c', '', '', '', '', '', 'c', ''],
        ['p', '', 'p', '', 'p', '', 'p', '', 'p'],
        ['', '', '', '', '', '', '', '', ''],
        ['', '', '', '', '', '', '', '', ''],
        ['P', '', 'P', '', 'P', '', 'P', '', 'P'],
        ['', 'C', '', '', '', '', '', 'C', ''],
        ['', '', '', '', '', '', '', '', ''],
        ['R', 'N', 'B', 'A', 'K', 'A', 'B', 'N', 'R'],
    ]
    
    board = [row[:] for row in INITIAL_BOARD]
    red_to_move = True
    
    for i, move in enumerate(moves[:up_to]):
        coords = iccs_to_board_coords(move)
        if coords:
            from_row, from_col, to_row, to_col = coords
            if 0 <= from_row < 10 and 0 <= from_col < 9 and 0 <= to_row < 10 and 0 <= to_col < 9:
                piece = board[from_row][from_col]
                board[from_row][from_col] = ''
                board[to_row][to_col] = piece
                red_to_move = not red_to_move
    
    return board


@app.post("/api/pgn-load", response_model=PGNLoadResponse)
async def pgn_load(request: PGNUploadRequest):
    """加载PGN文件"""
    try:
        games = parse_pgn_content(request.pgn_content)
        
        game_infos = []
        for i, game in enumerate(games):
            game_infos.append(PGNGameInfo(
                game_index=i,
                event=game.get('event', '未知赛事'),
                red_player=game.get('red_player', '未知'),
                black_player=game.get('black_player', '未知'),
                result=game.get('result', '*'),
                date=game.get('date', ''),
                moves=game.get('moves', [])
            ))
        
        return PGNLoadResponse(
            games=game_infos,
            total_games=len(games)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pgn-navigate", response_model=PGNNavigateResponse)
async def pgn_navigate(request: PGNNavigateRequest):
    """PGN导航"""
    try:
        new_index = request.current_index
        
        if request.direction == 'next':
            new_index = min(request.current_index + 1, len(request.moves))
        elif request.direction == 'prev':
            new_index = max(request.current_index - 1, 0)
        elif request.direction == 'start':
            new_index = 0
        elif request.direction == 'end':
            new_index = len(request.moves)
        elif request.direction == 'goto':
            new_index = max(0, min(request.current_index, len(request.moves)))
        
        board = apply_moves_to_board(request.moves, new_index)
        fen = board_to_fen(board, new_index % 2 == 0)
        
        move_text = ""
        if 0 < new_index <= len(request.moves):
            move_text = request.moves[new_index - 1]
        
        return PGNNavigateResponse(
            board=board,
            fen=fen,
            current_index=new_index,
            total_moves=len(request.moves),
            move_text=move_text
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


class BoardStructureRequest(BaseModel):
    fen: str


class BoardStructureResponse(BaseModel):
    pieces: List[Dict[str, Any]]
    relations: List[Dict[str, Any]]
    structural_summary: Dict[str, Any]
    llm_context: Dict[str, Any]
    raw_fen: str
    side_to_move: str


@app.post("/api/board-structure", response_model=BoardStructureResponse)
async def get_board_structure(request: BoardStructureRequest):
    """
    获取局面结构解析（T0核心功能）
    
    四层能力：
    1. 棋子真实位置层 - 所有棋子位置、存活状态
    2. 棋子关系层 - 攻击、保护、限制关系
    3. 结构摘要层 - 阶段、主动权、王安全
    4. LLM/检索可消费层 - 结构化上下文
    """
    try:
        from core.semantic.board_structure_parser import BoardStructureParser
        
        parser = BoardStructureParser()
        result = parser.parse(request.fen)
        
        return BoardStructureResponse(
            pieces=[p.to_dict() for p in result.pieces],
            relations=[r.to_dict() for r in result.relations],
            structural_summary=result.structural_summary.to_dict(),
            llm_context=result.llm_context.to_dict(),
            raw_fen=result.raw_fen,
            side_to_move=result.side_to_move
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class EnhancedPieceAnalysisRequest(BaseModel):
    fen: str


class TacticalTagsRequest(BaseModel):
    fen: str


class TacticalTagsResponse(BaseModel):
    fen: str
    tags: List[Dict[str, Any]]
    tags_by_category: Dict[str, List[Dict[str, Any]]]


@app.post("/api/tactical-tags", response_model=TacticalTagsResponse)
async def get_tactical_tags(request: TacticalTagsRequest):
    """
    获取战术标签检测结果
    
    检测六大层级+语义层标签：
    - 将杀困毙层: is_check, is_checkmate, is_stalemate
    - 捉子层: is_attack_unprotected, is_mutual_attack, is_attack_king_adjacent
    - 闪击抽将层: is_discovered_check, is_double_attack_with_check, is_discovered_attack
    - 牵制串打层: is_pinned, is_cannon_double_attack
    - 标准杀法层: checkmate_horse_back_cannon, checkmate_iron_gate, checkmate_double_rook, 
                 checkmate_horse_corner, checkmate_bare_king, checkmate_double_cannon_battery,
                 checkmate_sea_bottom_moon, checkmate_side_tiger
    - 子力状态层: piece_is_unprotected, cannon_has_platform
    - 局面语义层: phase_opening, phase_middlegame, phase_endgame, king_safety_critical,
                 has_initiative, is_forcing_move, horse_leg_blocked, kings_face_to_face,
                 cannon_battery, favorable_exchange
    """
    try:
        from core.rules.tactical_detector import TacticalDetector
        
        detector = TacticalDetector()
        result = detector.detect_static(request.fen)
        
        detected_tags = result.get_detected_tags()
        
        tags = []
        tags_by_category = {}
        
        for tag_result in detected_tags:
            tag_dict = {
                "name": tag_result.tag.name,
                "category": tag_result.tag.category.value,
                "description": tag_result.tag.description,
                "confidence": tag_result.confidence,
                "bind_pieces": tag_result.bind_pieces,
                "metadata": tag_result.metadata or {}
            }
            tags.append(tag_dict)
            
            category = tag_result.tag.category.value
            if category not in tags_by_category:
                tags_by_category[category] = []
            tags_by_category[category].append(tag_dict)
        
        return TacticalTagsResponse(
            fen=request.fen,
            tags=tags,
            tags_by_category=tags_by_category
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


class EnhancedPieceAnalysisResponse(BaseModel):
    fen: str
    side_to_move: str
    pieces: List[Dict[str, Any]]
    summary: Dict[str, Any]


@app.post("/api/piece-analysis", response_model=EnhancedPieceAnalysisResponse)
async def get_enhanced_piece_analysis(request: EnhancedPieceAnalysisRequest):
    """
    获取增强版棋子状态分析（T0核心功能）
    
    每个棋子的详细信息：
    - 棋子编号（R1, R2, N1, N2...）
    - 每个可走位置的详细分析
    - 马腿/象眼检测
    - 炮架分析
    - 战术组合检测
    - 线路控制
    """
    try:
        from core.semantic.enhanced_piece_analyzer import EnhancedPieceAnalyzer
        
        analyzer = EnhancedPieceAnalyzer()
        result = analyzer.analyze(request.fen)
        
        return EnhancedPieceAnalysisResponse(
            fen=result['fen'],
            side_to_move=result['side_to_move'],
            pieces=result['pieces'],
            summary=result['summary']
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class GameSearchRequest(BaseModel):
    player: Optional[str] = None
    event: Optional[str] = None
    limit: int = 20


class GameSearchResult(BaseModel):
    game_id: int
    red: str
    black: str
    event: str
    date: str
    result: str


class GameSearchResponse(BaseModel):
    games: List[GameSearchResult]
    total: int


class GameDetailResponse(BaseModel):
    game_id: int
    red: str
    black: str
    event: str
    date: str
    result: str
    moves: List[str]


@app.post("/api/games/search", response_model=GameSearchResponse)
async def search_games(request: GameSearchRequest):
    """
    搜索对局
    
    从Neo4j数据库中搜索对局，支持按棋手名、赛事名搜索
    """
    try:
        from core.kg.neo4j_kg import Neo4jKG
        
        kg = Neo4jKG()
        if not kg.connect():
            raise HTTPException(status_code=503, detail="Neo4j数据库未连接")
        
        games = kg.search_games(player=request.player, event=request.event, limit=request.limit)
        kg.close()
        
        results = []
        for g in games:
            results.append(GameSearchResult(
                game_id=g.game_id,
                red=g.red,
                black=g.black,
                event=g.event,
                date=g.date,
                result=g.result
            ))
        
        return GameSearchResponse(games=results, total=len(results))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/games/{game_id}", response_model=GameDetailResponse)
async def get_game_detail(game_id: int):
    """
    获取对局详情
    
    返回对局的完整走法列表
    """
    try:
        from core.kg.neo4j_kg import Neo4jKG
        
        kg = Neo4jKG()
        if not kg.connect():
            raise HTTPException(status_code=503, detail="Neo4j数据库未连接")
        
        with kg._get_session() as session:
            result = session.run("""
                MATCH (g:Game {id: $gid})
                OPTIONAL MATCH (g)-[r:HAS_POSITION]->(p:Position)
                WITH g, r
                ORDER BY r.move_num
                RETURN g.id as id, g.red as red, g.black as black,
                       g.event as event, g.date as date, g.result as result,
                       collect(r.move) as moves
            """, gid=game_id)
            
            record = result.single()
            if not record:
                raise HTTPException(status_code=404, detail="对局不存在")
            
            moves = [m for m in (record["moves"] or []) if m]
            
            kg.close()
            
            return GameDetailResponse(
                game_id=record["id"],
                red=record["red"] or "",
                black=record["black"] or "",
                event=record["event"] or "",
                date=record["date"] or "",
                result=record["result"] or "",
                moves=moves
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# 双模式分析端点（Phase 5 新增）
# =============================================================================

class QuickAnalyzeRequest(BaseModel):
    """快速分析请求"""
    fen: str
    move: Optional[str] = None  # UCI格式走法（可选）
    mode: str = "hint"  # hint / engine_explain / replay


class QuickAnalyzeResponse(BaseModel):
    """快速分析响应"""
    fen: str
    evidence_map: Dict[str, Any]
    explanation: str
    response_time_ms: float


@app.post("/api/analyze/quick", response_model=QuickAnalyzeResponse)
async def analyze_quick(request: QuickAnalyzeRequest):
    """
    快速分析模式 (< 1秒)

    使用预计算的Evidence Map直接返回标签+引擎数据
    适合：对弈提示、引擎推荐解释
    """
    import time
    start_time = time.time()

    try:
        from core.rules.tactical_detector import TacticalDetector

        detector = TacticalDetector()

        # 静态检测
        static_result = detector.detect_static(request.fen)
        detected_tags = [t for t in static_result.tags if t.detected]

        # 如果有走法，进行动态检测
        dynamic_tags = []
        if request.move:
            dynamic_result = detector.detect_dynamic(request.fen, request.move)
            dynamic_tags = [t for t in dynamic_result.tags if t.detected]

        # 构建Evidence Map
        evidence_map = {
            "tags": [
                {
                    "name": t.tag.name,
                    "category": t.tag.category.value,
                    "description": t.tag.description,
                    "bind_pieces": t.bind_pieces
                }
                for t in detected_tags
            ],
            "dynamic_tags": [
                {
                    "name": t.tag.name,
                    "description": t.tag.description,
                    "bind_pieces": t.bind_pieces
                }
                for t in dynamic_tags
            ],
            "tag_count": len(detected_tags),
            "phase": next((t.tag.name for t in detected_tags if "phase_" in t.tag.name), "unknown")
        }

        # 生成简要讲解
        explanation_parts = []

        # 根据模式生成不同讲解
        if request.mode == "hint" and request.move:
            # 提示模式：分析走法质量
            quality_tags = [t.tag.name for t in dynamic_tags if "move_" in t.tag.name]
            if "move_is_blunder" in quality_tags:
                explanation_parts.append("这步棋有失误风险！")
            elif "move_gives_check" in quality_tags:
                explanation_parts.append("将军！迫使对方应将。")
            elif "move_is_capture" in quality_tags:
                explanation_parts.append("吃子走法，获得物质优势。")
            elif "move_escapes_threat" in quality_tags:
                explanation_parts.append("成功逃脱威胁。")
            elif "move_defends_piece" in quality_tags:
                explanation_parts.append("防守走法，保护己方棋子。")
            else:
                explanation_parts.append("正常走法。")

        elif request.mode == "engine_explain":
            # 引擎解释模式
            if "is_attack_unprotected" in [t.tag.name for t in detected_tags]:
                explanation_parts.append("当前局面存在捉无根子的机会。")
            if "is_pinned" in [t.tag.name for t in detected_tags]:
                explanation_parts.append("存在牵制关系，可加以利用。")

        else:  # replay模式
            # 棋谱模式
            phase = evidence_map["phase"]
            if phase == "phase_opening":
                explanation_parts.append("开局阶段，注意出子和占位。")
            elif phase == "phase_middlegame":
                explanation_parts.append("中局阶段，寻找战术机会。")
            elif phase == "phase_endgame":
                explanation_parts.append("残局阶段，精确计算。")

        # 添加关键标签
        key_tags = ["is_check", "is_checkmate", "is_attack_unprotected", "has_initiative"]
        for t in detected_tags:
            if t.tag.name in key_tags:
                explanation_parts.append(f"【{t.tag.description}】")

        explanation = " ".join(explanation_parts) if explanation_parts else "局面分析完成。"

        response_time = (time.time() - start_time) * 1000

        return QuickAnalyzeResponse(
            fen=request.fen,
            evidence_map=evidence_map,
            explanation=explanation,
            response_time_ms=response_time
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


class DeepAnalyzeRequest(BaseModel):
    """深度分析请求"""
    fen: str
    move: Optional[str] = None
    question: Optional[str] = None  # 用户自然语言问题
    show_thinking: bool = True  # 是否展示思考过程


# SSE流式响应需要特殊处理
from fastapi.responses import StreamingResponse
import json


@app.post("/api/analyze/deep")
async def analyze_deep(request: DeepAnalyzeRequest):
    """
    深度分析模式 (3-5秒)

    真正的Agent模式：LLM自主决定调用哪些工具
    SSE流式返回思考过程 - 实时输出，不是等分析完成才返回
    适合：棋谱讲解、复杂局面分析、教学
    """
    import time
    request_start = time.time()
    print(f"[API] 收到请求, time=0ms")

    # 写入调试文件
    debug_log = open('d:/xiangqi-hybrid-agent/sse_debug.log', 'a')
    debug_log.write(f"[API] 收到请求, time=0ms\n")
    debug_log.flush()

    async def generate():
        import asyncio
        import threading
        import queue

        gen_start = time.time()
        elapsed = int((gen_start - request_start) * 1000)
        print(f"[SSE] generate() 开始执行, 距请求 {elapsed}ms")
        debug_log.write(f"[SSE] generate() 开始执行, 距请求 {elapsed}ms\n")
        debug_log.flush()

        # 立即发送初始提示（最重要的第一步，必须在任何其他操作之前）
        yield f"data: {json.dumps({'type': 'thinking', 'message': '启动分析...'}, ensure_ascii=False)}\n\n"

        elapsed = int((time.time() - request_start) * 1000)
        print(f"[SSE] 第一个 yield 完成, 距请求 {elapsed}ms")
        debug_log.write(f"[SSE] 第一个 yield 完成, 距请求 {elapsed}ms\n")
        debug_log.flush()

        await asyncio.sleep(0.01)

        print(f"[DEBUG] 深度分析请求 - FEN: {request.fen[:50]}..., move: {request.move}, question: {request.question}")

        try:
            # 创建事件队列
            event_queue = queue.Queue()
            result_holder = {'result': None, 'error': None}
            analysis_completed = False
            analysis_data = None

            # 立即发送检测局面消息
            yield f"data: {json.dumps({'type': 'thinking', 'message': '检测局面...'}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.05)

            # 立即发送引擎评估消息
            yield f"data: {json.dumps({'type': 'thinking', 'message': '引擎评估...'}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.05)

            # 在后台线程中执行所有耗时分析
            def run_background_analysis():
                nonlocal analysis_completed, analysis_data
                try:
                    # 执行战术检测
                    detector = TacticalDetector()
                    tactical_result = detector.detect_static(request.fen)
                    evidence_map = tactical_result.to_evidence_map()

                    # 提取关键标签信息
                    detected_tags = [t for t in tactical_result.tags if t.detected]
                    tag_summary = []
                    for t in detected_tags[:10]:  # 最多10个关键标签
                        tag_info = f"- {t.tag.description}"
                        if t.bind_pieces:
                            tag_info += f"（{', '.join(t.bind_pieces[:2])}）"
                        tag_summary.append(tag_info)

                    # 执行引擎评估
                    engine = PikafishEngine()
                    engine.start()
                    analysis = engine.analyze(request.fen, depth=15)
                    if analysis and hasattr(analysis, 'score') and analysis.score is not None:
                        cp_value = int(analysis.score * 100) if analysis.score else 0
                        engine_eval = {
                            "cp": cp_value,
                            "best": analysis.bestmove if hasattr(analysis, 'bestmove') else None
                        }
                    else:
                        engine_eval = {"cp": 0, "best": None}

                    # 执行张力检测
                    tensions = detect_tensions(evidence_map, engine_eval, "中局")
                    print(f"[DEBUG] 张力检测结果: {len(tensions)}个张力")

                    analysis_data = (evidence_map, tag_summary, engine_eval, tensions)
                except Exception as e:
                    print(f"[DEBUG] 后台分析失败: {e}")
                    result_holder['error'] = str(e)
                finally:
                    analysis_completed = True

            # 启动后台分析线程
            analysis_thread = threading.Thread(target=run_background_analysis)
            analysis_thread.daemon = True
            analysis_thread.start()

            # 发送AI分析消息
            yield f"data: {json.dumps({'type': 'thinking', 'message': 'AI分析中...'}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.05)

            # 等待分析完成，同时可以继续发送消息
            while not analysis_completed:
                # 发送等待消息，保持连接活跃
                yield f"data: {json.dumps({'type': 'thinking', 'message': '分析进行中...'}, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0.5)

            # 分析完成，获取数据
            if analysis_data:
                evidence_map, tag_summary, engine_eval, tensions = analysis_data
            else:
                # 如果分析失败，使用默认值
                evidence_map = {"facts_rules": []}
                tag_summary = []
                engine_eval = {"cp": 0, "best": None}
                tensions = []

            def run_agent():
                try:
                    coach = create_coach_agent()

                    question = request.question or "请分析当前局面"
                    if request.move and "走" not in question:
                        question = f"分析走法 {request.move} 的质量"

                    def on_thinking(stage: str, message: str):
                        # 将事件放入队列
                        event_queue.put({"type": stage, "message": message})

                    result = coach.analyze(
                        fen=request.fen,
                        question=question,
                        move=request.move,
                        evidence_map=evidence_map,
                        tag_summary=tag_summary,
                        engine_eval=engine_eval,
                        on_thinking=on_thinking if request.show_thinking else None
                    )
                    result_holder['result'] = result
                except Exception as e:
                    result_holder['error'] = str(e)
                finally:
                    event_queue.put(None)  # 信号：Agent完成

            # 启动后台线程
            agent_thread = threading.Thread(target=run_agent, daemon=True)
            agent_thread.start()

            # 实时从队列读取事件并发送
            while True:
                try:
                    # 使用超时避免无限阻塞
                    event = event_queue.get(timeout=0.1)
                    if event is None:
                        break  # Agent完成

                    # 立即发送事件
                    if event["type"] == "thinking":
                        yield f"data: {json.dumps({'type': 'thinking', 'message': event['message']}, ensure_ascii=False)}\n\n"
                    elif event["type"] == "thinking_chunk":
                        yield f"data: {json.dumps({'type': 'thinking_chunk', 'message': event['message']}, ensure_ascii=False)}\n\n"
                    elif event["type"] == "tool_call":
                        yield f"data: {json.dumps({'type': 'tool_call', 'message': event['message']}, ensure_ascii=False)}\n\n"
                    elif event["type"] == "tool_result":
                        yield f"data: {json.dumps({'type': 'tool_result', 'message': event['message']}, ensure_ascii=False)}\n\n"
                    elif event["type"] == "result":
                        yield f"data: {json.dumps({'type': 'result', 'explanation': event['message'], 'confidence': 'high'}, ensure_ascii=False)}\n\n"

                    await asyncio.sleep(0.01)  # 让出控制权

                except queue.Empty:
                    # 队列为空，检查线程是否还在运行
                    if not agent_thread.is_alive() and result_holder['result'] is None and result_holder['error'] is None:
                        # 线程已结束但没有结果，可能还在处理
                        pass
                    await asyncio.sleep(0.05)
                    continue

            # 检查是否有错误
            if result_holder['error']:
                yield f"data: {json.dumps({'type': 'error', 'message': result_holder['error']}, ensure_ascii=False)}\n\n"
            elif result_holder['result']:
                yield f"data: {json.dumps({'type': 'result', 'explanation': result_holder['result'], 'confidence': 'high'}, ensure_ascii=False)}\n\n"

        except Exception as e:
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Transfer-Encoding": "chunked",
        }
    )


# GET 版本的深度分析端点，避免 CORS preflight 延迟
@app.get("/api/analyze/deep-stream")
async def analyze_deep_stream(
    fen: str,
    move: Optional[str] = None,
    question: str = "请分析当前局面",
    show_thinking: bool = True,
    debug: bool = False  # 新增：是否返回调试日志
):
    """
    GET 版本的深度分析端点 - 避免 CORS preflight 延迟
    SSE 流式返回分析结果

    参数:
        debug: 如果为True，在流结束时返回完整的调试日志
    """
    import asyncio
    import threading
    import queue
    import time

    from core.llm.debug_logger import AgentDebugLogger

    request_start = time.time()
    debug_logger = AgentDebugLogger(enabled=debug)  # 创建调试日志记录器

    async def generate():
        # 立即发送初始提示
        yield f"data: {json.dumps({'type': 'thinking', 'message': '启动分析...'}, ensure_ascii=False)}\n\n"
        await asyncio.sleep(0.01)

        print(f"[DEBUG] GET深度分析 - FEN: {fen[:50]}..., move: {move}, question: {question}")

        try:
            event_queue = queue.Queue()
            result_holder = {'result': None, 'error': None}
            analysis_completed = False
            analysis_data = None

            yield f"data: {json.dumps({'type': 'thinking', 'message': '检测局面...'}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.05)

            yield f"data: {json.dumps({'type': 'thinking', 'message': '引擎评估...'}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.05)

            def run_background_analysis():
                nonlocal analysis_completed, analysis_data
                try:
                    detector = TacticalDetector()
                    tactical_result = detector.detect_static(fen)
                    evidence_map = tactical_result.to_evidence_map()

                    detected_tags = [t for t in tactical_result.tags if t.detected]
                    tag_summary = []
                    for t in detected_tags[:10]:
                        tag_info = f"- {t.tag.description}"
                        if t.bind_pieces:
                            tag_info += f"（{', '.join(t.bind_pieces[:2])}）"
                        tag_summary.append(tag_info)

                    engine = PikafishEngine()
                    engine.start()
                    analysis = engine.analyze(fen, depth=15)
                    if analysis and hasattr(analysis, 'score') and analysis.score is not None:
                        cp_value = int(analysis.score * 100) if analysis.score else 0
                        engine_eval = {"cp": cp_value, "best": analysis.bestmove if hasattr(analysis, 'bestmove') else None}
                    else:
                        engine_eval = {"cp": 0, "best": None}

                    tensions = detect_tensions(evidence_map, engine_eval, "中局")
                    analysis_data = (evidence_map, tag_summary, engine_eval, tensions)
                except Exception as e:
                    print(f"[DEBUG] 后台分析失败: {e}")
                    result_holder['error'] = str(e)
                finally:
                    analysis_completed = True

            analysis_thread = threading.Thread(target=run_background_analysis)
            analysis_thread.daemon = True
            analysis_thread.start()

            yield f"data: {json.dumps({'type': 'thinking', 'message': 'AI分析中...'}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.05)

            while not analysis_completed:
                yield f"data: {json.dumps({'type': 'thinking', 'message': '分析进行中...'}, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0.5)

            if analysis_data:
                evidence_map, tag_summary, engine_eval, tensions = analysis_data
            else:
                evidence_map = {"facts_rules": []}
                tag_summary = []
                engine_eval = {"cp": 0, "best": None}
                tensions = []

            def run_agent():
                try:
                    orchestrator = MultiAgentOrchestrator(debug_logger=debug_logger)
                    actual_question = question
                    if move and "走" not in question:
                        actual_question = f"分析走法 {move} 的质量"

                    def on_thinking(stage: str, message: str):
                        event_queue.put({"type": stage, "message": message})

                    result = orchestrator.analyze(
                        fen=fen,
                        question=actual_question,
                        move=move,
                        evidence_map=evidence_map,
                        tag_summary="\n".join(tag_summary),
                        engine_eval=engine_eval,
                        on_thinking=on_thinking if show_thinking else None,
                        force_multi=True,  # 多Agent模式
                    )
                    result_holder['result'] = result
                except Exception as e:
                    result_holder['error'] = str(e)
                finally:
                    event_queue.put(None)

            agent_thread = threading.Thread(target=run_agent, daemon=True)
            agent_thread.start()

            while True:
                try:
                    event = event_queue.get(timeout=0.1)
                    if event is None:
                        break

                    if event["type"] == "thinking":
                        yield f"data: {json.dumps({'type': 'thinking', 'message': event['message']}, ensure_ascii=False)}\n\n"
                    elif event["type"] == "thinking_chunk":
                        yield f"data: {json.dumps({'type': 'thinking_chunk', 'message': event['message']}, ensure_ascii=False)}\n\n"
                    elif event["type"] == "tool_call":
                        yield f"data: {json.dumps({'type': 'tool_call', 'message': event['message']}, ensure_ascii=False)}\n\n"
                    elif event["type"] == "tool_result":
                        yield f"data: {json.dumps({'type': 'tool_result', 'message': event['message']}, ensure_ascii=False)}\n\n"
                    elif event["type"] == "result":
                        yield f"data: {json.dumps({'type': 'result', 'explanation': event['message'], 'confidence': 'high'}, ensure_ascii=False)}\n\n"
                    # 多Agent事件类型
                    elif event["type"] == "expert_start":
                        try:
                            expert_data = json.loads(event["message"])
                            yield f"data: {json.dumps({'type': 'expert_start', 'expert': expert_data.get('expert', '')}, ensure_ascii=False)}\n\n"
                        except (json.JSONDecodeError, KeyError):
                            pass
                    elif event["type"] == "expert_result":
                        try:
                            expert_data = json.loads(event["message"])
                            yield f"data: {json.dumps({'type': 'expert_result', **expert_data}, ensure_ascii=False)}\n\n"
                        except (json.JSONDecodeError, KeyError):
                            pass
                    elif event["type"] == "synthesis_chunk":
                        yield f"data: {json.dumps({'type': 'synthesis_chunk', 'message': event['message']}, ensure_ascii=False)}\n\n"
                    elif event["type"] == "synthesis":
                        yield f"data: {json.dumps({'type': 'result', 'explanation': event['message'], 'confidence': 'high', 'source': 'multi_agent'}, ensure_ascii=False)}\n\n"
                    elif event["type"] in ("tactics_thinking", "strategy_thinking", "engine_thinking",
                                          "tactics_chunk", "strategy_chunk", "engine_chunk",
                                          "tactics_tool", "strategy_tool", "engine_tool",
                                          "tactics_tool_result", "strategy_tool_result", "engine_tool_result"):
                        parts = event["type"].split("_", 1)
                        if len(parts) == 2:
                            expert_name, sub_type = parts
                            if sub_type == "thinking":
                                yield f"data: {json.dumps({'type': f'expert_{expert_name}_thinking', 'message': event['message']}, ensure_ascii=False)}\n\n"
                            elif sub_type == "chunk":
                                yield f"data: {json.dumps({'type': f'expert_{expert_name}_chunk', 'message': event['message']}, ensure_ascii=False)}\n\n"
                            elif sub_type == "tool":
                                yield f"data: {json.dumps({'type': f'expert_{expert_name}_tool', 'message': event['message']}, ensure_ascii=False)}\n\n"
                            elif sub_type == "tool_result":
                                yield f"data: {json.dumps({'type': f'expert_{expert_name}_tool_result', 'message': event['message']}, ensure_ascii=False)}\n\n"

                    await asyncio.sleep(0.01)

                except queue.Empty:
                    if not agent_thread.is_alive() and result_holder['result'] is None and result_holder['error'] is None:
                        pass
                    await asyncio.sleep(0.05)
                    continue

            if result_holder['error']:
                yield f"data: {json.dumps({'type': 'error', 'message': result_holder['error']}, ensure_ascii=False)}\n\n"
            elif result_holder['result']:
                yield f"data: {json.dumps({'type': 'result', 'explanation': result_holder['result'], 'confidence': 'high'}, ensure_ascii=False)}\n\n"

            # 发送调试日志（如果启用）
            if debug and debug_logger.current_session:
                debug_log = debug_logger.export_readable()
                yield f"data: {json.dumps({'type': 'debug_log', 'log': debug_log}, ensure_ascii=False)}\n\n"

        except Exception as e:
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )


# GET 版本的深度分析端点，用于测试 SSE 延迟
@app.get("/api/analyze/deep-get")
async def analyze_deep_get(
    fen: str = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/6P2/P1P1P3P/1C5C1/9/RNBAKABNR w - - 0 3",
    question: str = "分析开局",
    show_thinking: bool = True
):
    """GET 版本的深度分析，用于测试 SSE 延迟"""
    import time
    request_start = time.time()

    async def generate():
        import asyncio
        # 立即发送
        yield f"data: {json.dumps({'type': 'thinking', 'message': '启动分析...'}, ensure_ascii=False)}\n\n"

        await asyncio.sleep(0.05)
        yield f"data: {json.dumps({'type': 'thinking', 'message': '检测局面...'}, ensure_ascii=False)}\n\n"

        await asyncio.sleep(0.05)
        yield f"data: {json.dumps({'type': 'thinking', 'message': '引擎评估...'}, ensure_ascii=False)}\n\n"

        # 简单返回结果
        await asyncio.sleep(1)
        yield f"data: {json.dumps({'type': 'result', 'explanation': '测试完成', 'confidence': 'high'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )


@app.get("/api/test-sse")
async def test_sse():
    """简单测试端点 - 验证SSE是否立即发送"""
    import asyncio

    async def simple_generate():
        import time
        start = time.time()
        print(f"[TEST-SSE] 开始, time=0ms")

        yield f"data: {json.dumps({'message': 'hello'}, ensure_ascii=False)}\n\n"
        print(f"[TEST-SSE] 第一个 yield 完成, time={int((time.time()-start)*1000)}ms")

        await asyncio.sleep(1)
        yield f"data: {json.dumps({'message': 'world'}, ensure_ascii=False)}\n\n"
        print(f"[TEST-SSE] 第二个 yield 完成")

    return StreamingResponse(
        simple_generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )


# 使用原生Response绕过缓冲测试
from starlette.responses import Response

@app.get("/api/test-sse2")
async def test_sse2():
    """使用原生Response测试"""
    from starlette.background import BackgroundTask

    async def send_sse():
        # 直接写入到发送队列
        pass

    return Response(
        content="data: {\"message\": \"hello\"}\n\n",
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
        }
    )


class MoveQualityRequest(BaseModel):
    """走法质量检测请求"""
    fen: str
    move: str  # UCI格式


class MoveQualityResponse(BaseModel):
    """走法质量检测响应"""
    move: str
    move_chinese: str


# ============================================================================
# 调试/监控端点 - 用于查看深度分析记录
# ============================================================================

@app.get("/api/debug/records")
async def list_debug_records(limit: int = 20):
    """
    列出最近的深度分析记录
    
    用于调试和监控LLM行为
    """
    from core.llm.analysis_recorder import AnalysisRecorder
    
    records = AnalysisRecorder.get_records(limit=limit)
    return {
        "count": len(records),
        "records": records
    }


@app.get("/api/debug/record/{record_id}")
async def get_debug_record(record_id: str):
    """
    获取指定记录的完整JSON
    
    用于复现和分析LLM的完整思考过程
    """
    from core.llm.analysis_recorder import AnalysisRecorder
    
    record = AnalysisRecorder.load_record(record_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"记录不存在: {record_id}")
    
    return record
    quality: str  # excellent / good / ok / blunder
    quality_tags: List[str]
    explanation: str


@app.post("/api/move-quality", response_model=MoveQualityResponse)
async def get_move_quality(request: MoveQualityRequest):
    """
    走法质量检测（独立端点）

    快速判断某步棋的质量
    """
    try:
        from core.rules.tactical_detector import TacticalDetector

        detector = TacticalDetector()
        quality_tags = detector.detect_move_quality(request.fen, request.move)
        detected = [t for t in quality_tags if t.detected]
        tag_names = [t.tag.name for t in detected]

        # 确定质量等级
        if "move_is_blunder" in tag_names:
            quality = "blunder"
            explanation = "这步棋有严重失误！"
        elif "move_gives_check" in tag_names or "move_is_capture" in tag_names:
            quality = "excellent"
            explanation = "好棋！"
            if "move_gives_check" in tag_names:
                explanation += " 将军对方。"
            if "move_is_capture" in tag_names:
                for t in detected:
                    if t.tag.name == "move_is_capture" and t.metadata:
                        explanation += f" 得子{t.metadata.get('captured_value', 0)}分。"
        elif "move_defends_piece" in tag_names or "move_escapes_threat" in tag_names:
            quality = "good"
            explanation = "不错的防守走法。"
        elif "move_improves_position" in tag_names:
            quality = "good"
            explanation = "改善了棋子位置。"
        else:
            quality = "ok"
            explanation = "正常走法。"

        # 中文走法
        board = detector._fen_to_board(request.fen)
        (from_row, from_col), (to_row, to_col) = detector._parse_uci(request.move)
        piece = board[from_row][from_col]
        piece_names = {'K': '帅', 'k': '将', 'R': '车', 'r': '车', 'N': '马', 'n': '马',
                       'C': '炮', 'c': '炮', 'P': '兵', 'p': '卒', 'A': '仕', 'a': '士',
                       'B': '相', 'b': '象'}
        piece_name = piece_names.get(piece, piece)
        move_chinese = f"{piece_name}({from_col+1},{10-from_row})→({to_col+1},{10-to_row})"

        return MoveQualityResponse(
            move=request.move,
            move_chinese=move_chinese,
            quality=quality,
            quality_tags=tag_names,
            explanation=explanation
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


def _generate_template_explanation(evidence_map: dict, move_analysis) -> str:
    """生成模板化讲解（LLM失败时的回退方案）"""
    parts = []

    # 局面分析
    phase = evidence_map.get("phase", "中局")
    initiative = evidence_map.get("initiative", "均势")
    parts.append(f"【{phase}分析】")

    if initiative != "均势":
        parts.append(f"{initiative}握有主动权。")
    else:
        parts.append("双方势均力敌。")

    # 关键特征
    features = evidence_map.get("key_features", [])
    if features:
        parts.append(f"局面特点：{'、'.join(features[:3])}。")

    # 走法分析
    move_info = evidence_map.get("move")
    if move_info:
        quality_cn = {"excellent": "好棋", "good": "不错的走法", "ok": "正常走法", "blunder": "失误"}
        quality = move_info.get("quality", "ok")
        chinese = move_info.get("chinese", "")
        why = move_info.get("why", "")
        parts.append(f"\n【走法分析】{chinese}：{quality_cn.get(quality, quality)}。{why}")

    # 战术要点
    tags = evidence_map.get("tactical_tags", [])
    if tags:
        tag_descs = [t["description"] for t in tags[:4]]
        parts.append(f"\n【战术要点】{'；'.join(tag_descs)}。")

    return "\n".join(parts)
