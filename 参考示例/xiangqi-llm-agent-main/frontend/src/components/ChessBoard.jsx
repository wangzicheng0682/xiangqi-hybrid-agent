import React, { useState, useEffect } from 'react';
import './ChessBoard.css';

/**
 * 中国象棋棋盘组件
 */
const ChessBoard = ({ 
  fen, 
  onMove, 
  legalMoves = [],
  interactive = true,
  showCoordinates = true 
}) => {
  const [selectedSquare, setSelectedSquare] = useState(null);
  const [board, setBoard] = useState(parseFEN(fen));

  useEffect(() => {
    setBoard(parseFEN(fen));
  }, [fen]);

  // 解析FEN字符串
  function parseFEN(fen) {
    const position = fen.split(' ')[0];
    const rows = position.split('/');
    const board = Array(10).fill(null).map(() => Array(9).fill(null));

    rows.forEach((row, rank) => {
      let file = 0;
      for (let char of row) {
        if (char >= '1' && char <= '9') {
          file += parseInt(char);
        } else {
          board[rank][file] = char;
          file++;
        }
      }
    });

    return board;
  }

  // 棋子符号映射
  const pieceMap = {
    'r': '車', 'n': '馬', 'b': '象', 'a': '士', 'k': '將',
    'c': '砲', 'p': '卒',
    'R': '俥', 'N': '傌', 'B': '相', 'A': '仕', 'K': '帥',
    'C': '炮', 'P': '兵'
  };

  // 获取棋子颜色
  function getPieceColor(piece) {
    if (!piece) return null;
    return piece === piece.toUpperCase() ? 'red' : 'black';
  }

  // 坐标转换 (rank, file) -> 标准坐标
  function toStandardNotation(rank, file) {
    const files = 'abcdefghi';
    return `${files[file]}${9 - rank}`;
  }

  // 处理点击
  function handleSquareClick(rank, file) {
    if (!interactive) return;

    const square = toStandardNotation(rank, file);
    const piece = board[rank][file];

    if (selectedSquare) {
      // 尝试走子
      const move = `${selectedSquare}${square}`;
      if (legalMoves.includes(move) || legalMoves.length === 0) {
        onMove(move);
        setSelectedSquare(null);
      } else {
        // 选择新棋子
        if (piece) {
          setSelectedSquare(square);
        } else {
          setSelectedSquare(null);
        }
      }
    } else {
      // 选择棋子
      if (piece) {
        setSelectedSquare(square);
      }
    }
  }

  // 判断是否为合法目标
  function isLegalTarget(rank, file) {
    if (!selectedSquare) return false;
    const target = toStandardNotation(rank, file);
    const move = `${selectedSquare}${target}`;
    return legalMoves.includes(move);
  }

  return (
    <div className="chess-board-container">
      <div className="chess-board">
        {/* 文件标签 (a-i) */}
        {showCoordinates && (
          <div className="file-labels">
            {['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i'].map((file, i) => (
              <div key={i} className="file-label">{file}</div>
            ))}
          </div>
        )}

        {/* 棋盘主体 */}
        <div className="board-grid">
          {board.map((row, rank) => (
            <React.Fragment key={rank}>
              {/* 行标签 (0-9) */}
              {showCoordinates && (
                <div className="rank-label">{9 - rank}</div>
              )}
              
              {/* 棋盘格子 */}
              {row.map((piece, file) => {
                const square = toStandardNotation(rank, file);
                const isSelected = selectedSquare === square;
                const isLegal = isLegalTarget(rank, file);
                const pieceColor = getPieceColor(piece);

                return (
                  <div
                    key={`${rank}-${file}`}
                    className={`square ${pieceColor || ''} ${isSelected ? 'selected' : ''} ${isLegal ? 'legal-target' : ''}`}
                    onClick={() => handleSquareClick(rank, file)}
                  >
                    {piece && (
                      <span className={`piece ${pieceColor}`}>
                        {pieceMap[piece] || piece}
                      </span>
                    )}
                    {/* 楚河汉界标记 */}
                    {rank === 4 && (
                      <div className="river-mark">楚河</div>
                    )}
                    {rank === 5 && (
                      <div className="river-mark">汉界</div>
                    )}
                  </div>
                );
              })}
              
              {showCoordinates && (
                <div className="rank-label">{9 - rank}</div>
              )}
            </React.Fragment>
          ))}
        </div>

        {/* 文件标签 (底部) */}
        {showCoordinates && (
          <div className="file-labels">
            {['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i'].map((file, i) => (
              <div key={i} className="file-label">{file}</div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default ChessBoard;

