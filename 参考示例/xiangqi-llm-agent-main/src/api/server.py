"""
FastAPI 服务器
提供象棋AI的HTTP API接口
"""
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import logging
import os
import json
import uuid
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Set

from src.game.board import Board
from src.game.engine_adapter import ChessEngineAdapter, GameResult
from src.llm.client import create_default_client, BaseLLMClient, LLMConfig
from src.self_play.player import Player, PlayerConfig, PlayerColor
from src.self_play.game_runner import GameRunner, GameRecord
from src.memory.store import ExperienceStore
from src.retrieval.index import VectorIndex, create_index, IndexConfig
from src.retrieval.encoder import create_encoder, EncoderConfig
from src.retrieval.bias import BiasGenerator, BiasConfig
from src.evaluation.elo import EloManager, GameResult as EloGameResult, create_elo_manager

logger = logging.getLogger(__name__)


# ============ 请求/响应模型 ============

class MoveRequest(BaseModel):
    """走法请求"""
    fen: str = Field(..., description="FEN格式的棋盘状态")
    player_color: Optional[str] = Field("RED", description="玩家颜色: RED 或 BLACK")
    move_history: Optional[List[str]] = Field(default_factory=list, description="走法历史")
    use_retrieval: Optional[bool] = Field(True, description="是否使用经验检索")
    temperature: Optional[float] = Field(None, description="LLM温度(可选)")
    top_k: Optional[int] = Field(None, description="返回Top-K走法数量(可选)")


class MoveResponse(BaseModel):
    """走法响应"""
    move: str = Field(..., description="选中的走法")
    moves: Optional[List[str]] = Field(None, description="Top-K走法列表")
    board_text: Optional[str] = Field(None, description="棋盘文本表示")
    legal_moves_count: Optional[int] = Field(None, description="合法走法数量")
    game_phase: Optional[str] = Field(None, description="对局阶段")
    retrieval_used: Optional[bool] = Field(None, description="是否使用了经验检索")


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    version: str
    components: Dict[str, str]


class GameRecordResponse(BaseModel):
    """对局记录响应"""
    game_id: str
    red_player: str
    black_player: str
    result: str
    total_moves: int
    duration: float
    start_time: str
    end_time: str
    steps: List[Dict[str, Any]]


class EloHistoryResponse(BaseModel):
    """ELO历史响应"""
    agent_id: str
    name: str
    version: str
    history: List[Dict[str, Any]]


# ============ 应用状态 ============

@dataclass
class AppState:
    """应用状态"""
    llm_client: Optional[BaseLLMClient] = None
    engine: Optional[ChessEngineAdapter] = None
    player: Optional[Player] = None
    experience_store: Optional[ExperienceStore] = None
    vector_index: Optional[VectorIndex] = None
    encoder: Optional[Any] = None
    bias_generator: Optional[BiasGenerator] = None
    elo_manager: Optional[EloManager] = None
    game_runner: Optional[GameRunner] = None
    active_games: Dict[str, Any] = field(default_factory=dict)  # 活跃游戏
    websocket_connections: Set[WebSocket] = field(default_factory=set)  # WebSocket连接
    initialized: bool = False


app_state = AppState()


# ============ 生命周期管理 ============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    logger.info("初始化应用组件...")
    try:
        initialize_app()
        logger.info("应用初始化完成")
    except Exception as e:
        logger.error(f"应用初始化失败: {e}")
        raise
    
    yield
    
    # 关闭时清理
    logger.info("清理应用资源...")
    cleanup_app()
    logger.info("应用资源清理完成")


# ============ FastAPI 应用 ============

app = FastAPI(
    title="中国象棋AI API",
    description="基于LLM的中国象棋AI服务",
    version="1.0.0",
    lifespan=lifespan
)

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件服务(用于前端)
static_dir = os.path.join(os.path.dirname(__file__), "../../frontend")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


# ============ 初始化函数 ============

def initialize_app():
    """初始化应用组件"""
    try:
        # 初始化LLM客户端
        logger.info("初始化LLM客户端...")
        app_state.llm_client = create_default_client()
        
        # 初始化象棋引擎
        logger.info("初始化象棋引擎...")
        app_state.engine = ChessEngineAdapter()
        
        # 初始化经验存储(可选)
        db_path = os.getenv("EXPERIENCE_DB_PATH", "data/experiences.db")
        try:
            logger.info(f"初始化经验存储: {db_path}")
            app_state.experience_store = ExperienceStore(db_path)
            
            # 初始化向量索引(可选)
            index_path = os.getenv("VECTOR_INDEX_PATH", "data/index")
            encoder_type = os.getenv("ENCODER_TYPE", "fen")
            
            try:
                logger.info(f"初始化向量索引: {index_path}")
                encoder_config = EncoderConfig(
                    encoder_type=encoder_type,
                    vector_dim=int(os.getenv("VECTOR_DIM", "128"))
                )
                app_state.encoder = create_encoder(encoder_type, encoder_config)
                
                index_config = IndexConfig(
                    index_type=os.getenv("INDEX_TYPE", "flat"),
                    vector_dim=encoder_config.vector_dim,
                    index_path=index_path
                )
                app_state.vector_index = create_index(config=index_config)
                
                # 尝试加载已有索引
                try:
                    app_state.vector_index.load(index_path)
                except Exception as e:
                    logger.warning(f"加载索引失败(将创建新索引): {e}")
                
                # 初始化偏置生成器
                bias_config = BiasConfig()
                app_state.bias_generator = BiasGenerator(
                    app_state.vector_index,
                    app_state.experience_store,
                    bias_config
                )
                
                logger.info("向量检索系统初始化完成")
            except Exception as e:
                logger.warning(f"向量索引初始化失败(将不使用检索): {e}")
                app_state.vector_index = None
                app_state.bias_generator = None
            
        except Exception as e:
            logger.warning(f"经验存储初始化失败(将不使用检索): {e}")
            app_state.experience_store = None
        
        # 初始化玩家
        logger.info("初始化AI玩家...")
        player_config = PlayerConfig(
            color=PlayerColor.RED,
            use_retrieval=app_state.experience_store is not None
        )
        
        # 设置检索回调(如果可用)
        retrieval_callback = None
        if app_state.bias_generator and app_state.encoder:
            retrieval_callback = create_retrieval_callback(
                app_state.encoder,
                app_state.vector_index,
                app_state.bias_generator
            )
        
        app_state.player = Player(
            name="API_Player",
            llm_client=app_state.llm_client,
            engine=app_state.engine,
            config=player_config,
            retrieval_callback=retrieval_callback
        )
        
        # 初始化游戏运行器
        logger.info("初始化游戏运行器...")
        from src.self_play.game_runner import GameRunnerConfig
        runner_config = GameRunnerConfig()
        app_state.game_runner = GameRunner(app_state.engine, runner_config)
        
        # 初始化ELO管理器
        elo_db_path = os.getenv("ELO_DB_PATH", "data/elo.db")
        try:
            logger.info(f"初始化ELO管理器: {elo_db_path}")
            app_state.elo_manager = create_elo_manager(elo_db_path)
        except Exception as e:
            logger.warning(f"ELO管理器初始化失败: {e}")
            app_state.elo_manager = None
        
        app_state.initialized = True
        logger.info("应用组件初始化完成")
        
    except Exception as e:
        logger.error(f"应用初始化失败: {e}")
        app_state.initialized = False
        raise


def cleanup_app():
    """清理应用资源"""
    if app_state.experience_store:
        try:
            app_state.experience_store.close()
        except Exception as e:
            logger.warning(f"关闭经验存储失败: {e}")
    
    if app_state.vector_index:
        try:
            app_state.vector_index.save()
        except Exception as e:
            logger.warning(f"保存向量索引失败: {e}")


def create_retrieval_callback(encoder, index, bias_generator):
    """创建检索回调函数"""
    def retrieval_callback(board: Board):
        """检索相似经验"""
        try:
            # 编码棋盘状态
            board_text = board.to_text(include_history=True)
            vector = encoder.encode(board_text)
            
            # 检索相似局面
            search_result = index.search(vector, k=10)
            
            # 生成偏置
            current_player = "RED" if "w" in board.fen else "BLACK"
            bias_result = bias_generator.generate_bias(
                search_result,
                current_player=current_player
            )
            
            # 转换为RetrievedExperience格式
            return bias_generator.to_retrieved_experience(bias_result)
        except Exception as e:
            logger.warning(f"经验检索失败: {e}")
            return None
    
    return retrieval_callback


# ============ 依赖注入 ============

def get_player() -> Player:
    """获取玩家实例"""
    if not app_state.initialized or not app_state.player:
        raise HTTPException(
            status_code=503,
            detail="服务未初始化或玩家未就绪"
        )
    return app_state.player


def get_engine() -> ChessEngineAdapter:
    """获取引擎实例"""
    if not app_state.initialized or not app_state.engine:
        raise HTTPException(
            status_code=503,
            detail="服务未初始化或引擎未就绪"
        )
    return app_state.engine


# ============ API 路由 ============

@app.get("/", tags=["基础"])
async def root():
    """根路径"""
    return {
        "name": "中国象棋AI API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health", response_model=HealthResponse, tags=["基础"])
async def health_check():
    """健康检查"""
    components = {}
    
    if app_state.llm_client:
        components["llm_client"] = "ready"
    else:
        components["llm_client"] = "not_initialized"
    
    if app_state.engine:
        components["engine"] = "ready"
    else:
        components["engine"] = "not_initialized"
    
    if app_state.player:
        components["player"] = "ready"
    else:
        components["player"] = "not_initialized"
    
    if app_state.experience_store:
        components["experience_store"] = "ready"
    else:
        components["experience_store"] = "not_available"
    
    if app_state.vector_index:
        components["vector_index"] = "ready"
    else:
        components["vector_index"] = "not_available"
    
    return HealthResponse(
        status="healthy" if app_state.initialized else "initializing",
        version="1.0.0",
        components=components
    )


@app.post("/move", response_model=MoveResponse, tags=["游戏"])
async def select_move(
    request: MoveRequest,
    player: Player = Depends(get_player),
    engine: ChessEngineAdapter = Depends(get_engine)
):
    """
    选择走法
    
    根据当前棋盘状态,使用AI选择最佳走法
    """
    try:
        # 解析玩家颜色
        player_color = PlayerColor.RED if request.player_color.upper() == "RED" else PlayerColor.BLACK
        
        # 创建棋盘对象
        # 注意: engine_adapter 的 legal_moves 接受 Board 对象，只需要 fen 属性
        # 为了兼容性，我们创建一个简单的 Board 对象
        from src.game.engine_adapter import Board as EngineBoard
        engine_board = EngineBoard(
            fen=request.fen,
            move_history=request.move_history or []
        )
        
        # 验证FEN格式
        legal_moves = engine.legal_moves(engine_board)
        
        # 创建完整的 Board 对象用于后续处理
        board = Board(
            fen=request.fen,
            move_history=request.move_history or []
        )
        if not legal_moves:
            raise HTTPException(
                status_code=400,
                detail="无效的FEN格式或没有合法走法"
            )
        
        # 临时修改玩家配置(如果提供了参数)
        original_config = player.config
        if request.temperature is not None:
            player.move_selector.config.temperature = request.temperature
        if request.top_k is not None:
            player.move_selector.config.top_k = request.top_k
        
        try:
            # 选择走法
            if request.top_k and request.top_k > 1:
                # 返回Top-K走法
                moves = player.select_move_batch(board, top_k=request.top_k)
                selected_move = moves[0] if moves else None
            else:
                # 返回单个走法
                selected_move = player.select_move(board)
                moves = [selected_move]
            
            if not selected_move:
                raise HTTPException(
                    status_code=500,
                    detail="走法选择失败"
                )
            
            # 获取棋盘文本表示
            board_text = board.to_text(include_history=True)
            
            # 判断对局阶段
            move_count = len(board.move_history)
            if move_count < 10:
                game_phase = "开局"
            elif move_count < 40:
                game_phase = "中局"
            else:
                game_phase = "残局"
            
            # 检查是否使用了检索
            retrieval_used = (
                app_state.experience_store is not None and
                app_state.vector_index is not None and
                request.use_retrieval
            )
            
            return MoveResponse(
                move=selected_move,
                moves=moves if request.top_k and request.top_k > 1 else None,
                board_text=board_text,
                legal_moves_count=len(legal_moves),
                game_phase=game_phase,
                retrieval_used=retrieval_used
            )
        
        finally:
            # 恢复原始配置
            player.config = original_config
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"走法选择失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"内部错误: {str(e)}"
        )


@app.get("/legal_moves", tags=["游戏"])
async def get_legal_moves(
    fen: str,
    engine: ChessEngineAdapter = Depends(get_engine)
):
    """
    获取合法走法列表
    
    Args:
        fen: FEN格式的棋盘状态
        
    Returns:
        合法走法列表
    """
    try:
        from src.game.engine_adapter import Board as EngineBoard
        engine_board = EngineBoard(fen=fen, move_history=[])
        legal_moves = engine.legal_moves(engine_board)
        
        return {
            "fen": fen,
            "legal_moves": legal_moves,
            "count": len(legal_moves)
        }
    except Exception as e:
        logger.error(f"获取合法走法失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"内部错误: {str(e)}"
        )


@app.get("/games", tags=["游戏"])
async def list_games(
    limit: int = 20,
    experience_store: Optional[ExperienceStore] = None
):
    """
    获取对局列表
    
    Args:
        limit: 返回数量限制
        
    Returns:
        对局列表
    """
    if not app_state.experience_store:
        return {"games": [], "total": 0}
    
    try:
        # 这里需要从数据库获取游戏记录
        # 简化实现，实际应从 ExperienceStore 或专门的游戏存储获取
        return {"games": [], "total": 0, "message": "游戏记录功能待实现"}
    except Exception as e:
        logger.error(f"获取对局列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/games/{game_id}", response_model=GameRecordResponse, tags=["游戏"])
async def get_game_record(game_id: str):
    """
    获取对局记录
    
    Args:
        game_id: 对局ID
        
    Returns:
        对局记录
    """
    # 这里需要从存储中获取游戏记录
    # 简化实现
    raise HTTPException(status_code=404, detail="对局记录未找到")


@app.get("/elo/leaderboard", tags=["ELO"])
async def get_elo_leaderboard(limit: int = 20):
    """
    获取ELO排行榜
    
    Args:
        limit: 返回数量
        
    Returns:
        排行榜列表
    """
    if not app_state.elo_manager:
        raise HTTPException(status_code=503, detail="ELO管理器未初始化")
    
    try:
        leaderboard = app_state.elo_manager.get_leaderboard(limit=limit)
        return {"leaderboard": leaderboard}
    except Exception as e:
        logger.error(f"获取排行榜失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/elo/history/{agent_id}", response_model=EloHistoryResponse, tags=["ELO"])
async def get_elo_history(agent_id: str):
    """
    获取Agent的ELO历史
    
    Args:
        agent_id: Agent ID
        
    Returns:
        ELO历史数据
    """
    if not app_state.elo_manager:
        raise HTTPException(status_code=503, detail="ELO管理器未初始化")
    
    try:
        agent = app_state.elo_manager.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent未找到")
        
        # 获取对局历史
        matches = app_state.elo_manager.get_match_history(agent_id=agent_id)
        
        # 构建历史数据点
        history = []
        current_elo = app_state.elo_manager.config.initial_elo
        
        for match in reversed(matches):  # 从旧到新
            if match.agent1_id == agent_id:
                current_elo = match.agent1_elo_after
            else:
                current_elo = match.agent2_elo_after
            
            history.append({
                "match_id": match.match_id,
                "elo": current_elo,
                "played_at": match.played_at.isoformat(),
                "opponent": match.agent2_id if match.agent1_id == agent_id else match.agent1_id,
                "result": match.result.value
            })
        
        return EloHistoryResponse(
            agent_id=agent.agent_id,
            name=agent.name,
            version=agent.version,
            history=history
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取ELO历史失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/board_info", tags=["游戏"])
async def get_board_info(
    fen: str,
    engine: ChessEngineAdapter = Depends(get_engine)
):
    """
    获取棋盘信息
    
    Args:
        fen: FEN格式的棋盘状态
        
    Returns:
        棋盘详细信息
    """
    try:
        from src.game.engine_adapter import Board as EngineBoard
        engine_board = EngineBoard(fen=fen, move_history=[])
        legal_moves = engine.legal_moves(engine_board)
        current_player = engine.get_current_player(engine_board)
        
        # 创建完整的 Board 对象用于文本生成
        board = Board(fen=fen, move_history=[])
        board_text = board.to_text(include_history=True)
        
        move_count = len(board.move_history)
        if move_count < 10:
            game_phase = "开局"
        elif move_count < 40:
            game_phase = "中局"
        else:
            game_phase = "残局"
        
        return {
            "fen": fen,
            "board_text": board_text,
            "current_player": current_player,
            "legal_moves_count": len(legal_moves),
            "legal_moves": legal_moves,
            "game_phase": game_phase,
            "move_count": move_count
        }
    except Exception as e:
        logger.error(f"获取棋盘信息失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"内部错误: {str(e)}"
        )


# ============ WebSocket 路由 ============

@app.websocket("/ws/game/{game_id}")
async def websocket_game(websocket: WebSocket, game_id: str):
    """
    WebSocket实时对弈
    
    支持:
    - 实时接收走法
    - 实时发送AI响应
    - 游戏状态更新
    """
    await websocket.accept()
    app_state.websocket_connections.add(websocket)
    
    try:
        # 初始化游戏
        if game_id not in app_state.active_games:
            initial_fen = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"
            board = Board(fen=initial_fen, move_history=[])
            app_state.active_games[game_id] = {
                "board": board,
                "current_player": "RED",
                "status": "playing",
                "moves": []
            }
        
        game_state = app_state.active_games[game_id]
        
        # 发送初始状态
        await websocket.send_json({
            "type": "game_state",
            "game_id": game_id,
            "fen": game_state["board"].fen,
            "current_player": game_state["current_player"],
            "moves": game_state["moves"]
        })
        
        while True:
            # 接收消息
            data = await websocket.receive_json()
            msg_type = data.get("type")
            
            if msg_type == "make_move":
                # 玩家走法
                move = data.get("move")
                fen = data.get("fen")
                
                if not move or not fen:
                    await websocket.send_json({
                        "type": "error",
                        "message": "缺少走法或FEN"
                    })
                    continue
                
                # 更新棋盘
                from src.game.engine_adapter import Board as EngineBoard
                engine_board = EngineBoard(fen=fen, move_history=game_state["moves"])
                new_board = app_state.engine.apply_move(engine_board, move)
                
                game_state["moves"].append(move)
                game_state["board"] = Board(fen=new_board.fen, move_history=game_state["moves"])
                game_state["current_player"] = "BLACK" if game_state["current_player"] == "RED" else "RED"
                
                # 检查游戏是否结束
                result = app_state.engine.get_game_result(new_board)
                if result != GameResult.ONGOING:
                    game_state["status"] = "finished"
                    game_state["result"] = result.value
                    
                    await websocket.send_json({
                        "type": "game_over",
                        "result": result.value,
                        "fen": new_board.fen
                    })
                    break
                
                # 发送更新
                await websocket.send_json({
                    "type": "move_made",
                    "move": move,
                    "fen": new_board.fen,
                    "current_player": game_state["current_player"]
                })
                
                # AI自动响应
                if game_state["status"] == "playing":
                    try:
                        ai_board = Board(fen=new_board.fen, move_history=game_state["moves"])
                        ai_move = app_state.player.select_move(ai_board)
                        
                        # 应用AI走法
                        ai_engine_board = EngineBoard(fen=new_board.fen, move_history=game_state["moves"])
                        ai_new_board = app_state.engine.apply_move(ai_engine_board, ai_move)
                        
                        game_state["moves"].append(ai_move)
                        game_state["board"] = Board(fen=ai_new_board.fen, move_history=game_state["moves"])
                        game_state["current_player"] = "RED"
                        
                        # 检查游戏是否结束
                        ai_result = app_state.engine.get_game_result(ai_new_board)
                        if ai_result != GameResult.ONGOING:
                            game_state["status"] = "finished"
                            game_state["result"] = ai_result.value
                            
                            await websocket.send_json({
                                "type": "game_over",
                                "result": ai_result.value,
                                "fen": ai_new_board.fen,
                                "ai_move": ai_move
                            })
                            break
                        
                        await websocket.send_json({
                            "type": "ai_move",
                            "move": ai_move,
                            "fen": ai_new_board.fen,
                            "current_player": "RED"
                        })
                    except Exception as e:
                        logger.error(f"AI走法失败: {e}", exc_info=True)
                        await websocket.send_json({
                            "type": "error",
                            "message": f"AI走法失败: {str(e)}"
                        })
            
            elif msg_type == "get_state":
                # 获取当前状态
                await websocket.send_json({
                    "type": "game_state",
                    "game_id": game_id,
                    "fen": game_state["board"].fen,
                    "current_player": game_state["current_player"],
                    "moves": game_state["moves"],
                    "status": game_state["status"]
                })
            
            elif msg_type == "reset":
                # 重置游戏
                initial_fen = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"
                game_state["board"] = Board(fen=initial_fen, move_history=[])
                game_state["current_player"] = "RED"
                game_state["status"] = "playing"
                game_state["moves"] = []
                
                await websocket.send_json({
                    "type": "game_reset",
                    "fen": initial_fen
                })
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket断开: {game_id}")
    except Exception as e:
        logger.error(f"WebSocket错误: {e}", exc_info=True)
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })
    finally:
        app_state.websocket_connections.discard(websocket)
        if game_id in app_state.active_games:
            del app_state.active_games[game_id]


# ============ 主函数 ============

if __name__ == "__main__":
    import uvicorn
    
    # 从环境变量读取配置
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    reload = os.getenv("API_RELOAD", "false").lower() == "true"
    
    uvicorn.run(
        "src.api.server:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )

