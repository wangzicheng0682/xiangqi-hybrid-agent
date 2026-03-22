import React, { useState, useEffect, useRef } from 'react';
import ChessBoard from '../components/ChessBoard';
import './GamePage.css';

/**
 * 实时对弈页面
 */
const GamePage = () => {
  const [fen, setFen] = useState('rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1');
  const [moves, setMoves] = useState([]);
  const [currentPlayer, setCurrentPlayer] = useState('RED');
  const [gameStatus, setGameStatus] = useState('playing');
  const [legalMoves, setLegalMoves] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const [gameId] = useState(() => `game_${Date.now()}`);
  const wsRef = useRef(null);

  useEffect(() => {
    // 连接WebSocket
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/game/${gameId}`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log('WebSocket连接已建立');
      setIsConnected(true);
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      handleWebSocketMessage(data);
    };

    ws.onerror = (error) => {
      console.error('WebSocket错误:', error);
    };

    ws.onclose = () => {
      console.log('WebSocket连接已关闭');
      setIsConnected(false);
    };

    wsRef.current = ws;

    return () => {
      if (ws) {
        ws.close();
      }
    };
  }, [gameId]);

  const handleWebSocketMessage = (data) => {
    switch (data.type) {
      case 'game_state':
        setFen(data.fen);
        setCurrentPlayer(data.current_player);
        setMoves(data.moves || []);
        fetchLegalMoves(data.fen);
        break;
      
      case 'move_made':
        setFen(data.fen);
        setCurrentPlayer(data.current_player);
        setMoves(prev => [...prev, data.move]);
        fetchLegalMoves(data.fen);
        break;
      
      case 'ai_move':
        setFen(data.fen);
        setCurrentPlayer(data.current_player);
        setMoves(prev => [...prev, data.move]);
        fetchLegalMoves(data.fen);
        break;
      
      case 'game_over':
        setGameStatus('finished');
        setFen(data.fen);
        break;
      
      case 'error':
        alert(`错误: ${data.message}`);
        break;
      
      default:
        console.log('未知消息类型:', data.type);
    }
  };

  const fetchLegalMoves = async (currentFen) => {
    try {
      const response = await fetch(`/legal_moves?fen=${encodeURIComponent(currentFen)}`);
      const data = await response.json();
      setLegalMoves(data.legal_moves || []);
    } catch (error) {
      console.error('获取合法走法失败:', error);
    }
  };

  const handleMove = (move) => {
    if (!isConnected || gameStatus !== 'playing' || currentPlayer !== 'RED') {
      return;
    }

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'make_move',
        move: move,
        fen: fen
      }));
    }
  };

  const handleReset = () => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'reset'
      }));
    }
  };

  return (
    <div className="game-page">
      <div className="game-header">
        <h1>中国象棋 - 实时对弈</h1>
        <div className="game-info">
          <span className={`status ${isConnected ? 'connected' : 'disconnected'}`}>
            {isConnected ? '● 已连接' : '○ 未连接'}
          </span>
          <span>当前玩家: {currentPlayer === 'RED' ? '红方' : '黑方'}</span>
          <span>步数: {moves.length}</span>
        </div>
      </div>

      <div className="game-content">
        <div className="board-section">
          <ChessBoard
            fen={fen}
            onMove={handleMove}
            legalMoves={legalMoves}
            interactive={gameStatus === 'playing' && currentPlayer === 'RED'}
            showCoordinates={true}
          />
        </div>

        <div className="info-section">
          <div className="move-history">
            <h3>走法历史</h3>
            <div className="moves-list">
              {moves.map((move, index) => (
                <div key={index} className="move-item">
                  {index + 1}. {move}
                </div>
              ))}
            </div>
          </div>

          <div className="game-controls">
            <button onClick={handleReset} disabled={!isConnected}>
              重新开始
            </button>
          </div>

          {gameStatus === 'finished' && (
            <div className="game-over">
              <h3>游戏结束</h3>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default GamePage;

