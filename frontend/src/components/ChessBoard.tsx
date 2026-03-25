import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useGameStore } from '../store/useGameStore';
import { renderPieceName } from '../utils/pieces';

const BASE_CELL = 55;
const BASE_PAD = 32;
const COLS = 9;
const ROWS = 10;

export default function ChessBoard() {
  const [boardSize, setBoardSize] = useState({ cell: BASE_CELL, pad: BASE_PAD });

  useEffect(() => {
    const updateSize = () => {
      const padding = 32;
      const availableWidth = window.innerWidth - padding;
      const availableHeight = window.innerHeight - padding;

      // 棋盘占宽度的80%，然后根据高度调整
      const targetWidth = availableWidth * 0.8;
      const targetHeight = availableHeight * 0.85;

      // 根据目标尺寸计算 cell 大小
      const cellByWidth = (targetWidth - BASE_PAD * 2) / (COLS - 1);
      const cellByHeight = (targetHeight - BASE_PAD * 2) / (ROWS - 1);

      // 取较小值确保棋盘完整显示，然后限制范围
      const newCell = Math.min(cellByWidth, cellByHeight, 150);
      const newPad = Math.max(newCell * 0.5, 16);

      setBoardSize({ cell: newCell, pad: newPad });
    };

    updateSize();
    window.addEventListener('resize', updateSize);
    return () => window.removeEventListener('resize', updateSize);
  }, []);

  const CELL = boardSize.cell;
  const PAD = boardSize.pad;
  const {
    board,
    selectPiece,
    movePiece,
    selectedPos,
    legalMoves,
    isLoading,
    error,
    clearError,
    lastMove,
    flipped,
    showArrows,
    bestMoves,
    highlightedPieces,
    connectionLines
  } = useGameStore();

  const handleClick = (row: number, col: number) => {
    const piece = board[row][col];
    const pos = `${String.fromCharCode(97 + col)}${9 - row}`;
    const canMove = legalMoves.some(m => m.endsWith(pos));

    if (selectedPos && canMove) {
      movePiece(row, col);
    } else if (piece) {
      selectPiece(row, col);
    }
  };

  const canMoveTo = (row: number, col: number) => {
    const pos = `${String.fromCharCode(97 + col)}${9 - row}`;
    return legalMoves.some(m => m.endsWith(pos));
  };

  const selected = (row: number, col: number) =>
    selectedPos?.row === row && selectedPos?.col === col;

  const isLastMoveFrom = (row: number, col: number) =>
    lastMove?.from.row === row && lastMove?.from.col === col;

  const isLastMoveTo = (row: number, col: number) =>
    lastMove?.to.row === row && lastMove?.to.col === col;

  const getHighlightInfo = (row: number, col: number) => {
    const info = highlightedPieces.find(h => h.row === row && h.col === col);
    return info;
  };

  const displayBoard = flipped ? board.slice().reverse().map(row => row.slice().reverse()) : board;

  const W = (COLS - 1) * CELL + PAD * 2;
  const H = (ROWS - 1) * CELL + PAD * 2;

  const getArrowCoords = (fromRow: number, fromCol: number, toRow: number, toCol: number) => {
    let x1 = PAD + fromCol * CELL;
    let y1 = PAD + fromRow * CELL;
    let x2 = PAD + toCol * CELL;
    let y2 = PAD + toRow * CELL;

    if (flipped) {
      x1 = PAD + (8 - fromCol) * CELL;
      y1 = PAD + (9 - fromRow) * CELL;
      x2 = PAD + (8 - toCol) * CELL;
      y2 = PAD + (9 - toRow) * CELL;
    }

    return { x1, y1, x2, y2 };
  };

  const drawArrow = (x1: number, y1: number, x2: number, y2: number, color: string, label: string, score?: number) => {
    const angle = Math.atan2(y2 - y1, x2 - x1);

    const startOffset = 20;
    const newX1 = x1 + Math.cos(angle) * startOffset;
    const newY1 = y1 + Math.sin(angle) * startOffset;

    const midX = (x1 + x2) / 2;
    const midY = (y1 + y2) / 2;

    return (
      <g key={`arrow-${label}`}>
        <defs>
          <marker
            id={`arrowhead-${label}`}
            markerWidth="8"
            markerHeight="8"
            refX="6"
            refY="4"
            orient="auto"
          >
            <polygon points="0 0, 8 4, 0 8" fill={color} />
          </marker>
        </defs>
        <line
          x1={newX1}
          y1={newY1}
          x2={x2}
          y2={y2}
          stroke={color}
          strokeWidth="4"
          markerEnd={`url(#arrowhead-${label})`}
          opacity="0.85"
        />
        <circle cx={x1} cy={y1} r="14" fill={color} opacity="0.9" />
        <text x={x1} y={y1 + 5} textAnchor="middle" fill="white" fontSize="13" fontWeight="bold">
          {label}
        </text>
        {score !== undefined && (
          <g>
            <rect
              x={midX - 18}
              y={midY - 10}
              width="36"
              height="20"
              rx="4"
              fill={color}
              opacity="0.95"
            />
            <text
              x={midX}
              y={midY + 4}
              textAnchor="middle"
              fill="white"
              fontSize="11"
              fontWeight="bold"
            >
              {score > 0 ? '+' : ''}{score.toFixed(1)}
            </text>
          </g>
        )}
      </g>
    );
  };

  const drawConnectionLine = (fromRow: number, fromCol: number, toRow: number, toCol: number, type: 'attack' | 'defense' | 'pin') => {
    let x1 = PAD + fromCol * CELL;
    let y1 = PAD + fromRow * CELL;
    let x2 = PAD + toCol * CELL;
    let y2 = PAD + toRow * CELL;

    if (flipped) {
      x1 = PAD + (8 - fromCol) * CELL;
      y1 = PAD + (9 - fromRow) * CELL;
      x2 = PAD + (8 - toCol) * CELL;
      y2 = PAD + (9 - toRow) * CELL;
    }

    const colors = {
      attack: '#FF6B6B',
      defense: '#4CAF50',
      pin: '#FF9800'
    };

    const color = colors[type];
    const dashArray = type === 'pin' ? '8,4' : '5,5';

    return (
      <g key={`connection-${fromRow}-${fromCol}-${toRow}-${toCol}`}>
        <defs>
          <marker
            id={`conn-arrowhead-${fromRow}-${fromCol}-${toRow}-${toCol}`}
            markerWidth="6"
            markerHeight="6"
            refX="5"
            refY="3"
            orient="auto"
          >
            <polygon points="0 0, 6 3, 0 6" fill={color} />
          </marker>
        </defs>
        <line
          x1={x1}
          y1={y1}
          x2={x2}
          y2={y2}
          stroke={color}
          strokeWidth="3"
          strokeDasharray={dashArray}
          markerEnd={`url(#conn-arrowhead-${fromRow}-${fromCol}-${toRow}-${toCol})`}
          opacity="0.8"
        />
      </g>
    );
  };

  return (
    <div style={styles.boardContainer}>
      {/* 外框装饰 */}
      <div style={styles.outerFrame}>
        {/* 内框 */}
        <div style={styles.innerFrame}>
          <svg width={W} height={H} style={styles.boardSvg}>
            {/* 棋盘背景（墨韵青灯版） */}
            <defs>
              <linearGradient id="boardGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#1a1410" />
                <stop offset="50%" stopColor="#15100a" />
                <stop offset="100%" stopColor="#1a1410" />
              </linearGradient>
              <filter id="boardShadow">
                <feDropShadow dx="0" dy="4" stdDeviation="8" floodOpacity="0.5"/>
              </filter>
            </defs>

            {/* 主背景 */}
            <rect x={0} y={0} width={W} height={H} fill="#0B132B" rx={4} />
            <rect x={PAD - 8} y={PAD - 8} width={W - PAD * 2 + 16} height={H - PAD * 2 + 16}
              fill="url(#boardGradient)" stroke="#B87333" strokeWidth="2" rx={2} filter="url(#boardShadow)" />

            {/* 横线 */}
            {[...Array(ROWS)].map((_, i) => (
              <line
                key={`h${i}`}
                x1={PAD} y1={PAD + i * CELL}
                x2={W - PAD} y2={PAD + i * CELL}
                stroke="rgba(184,115,51,0.40)"
                strokeWidth="1.5"
              />
            ))}

            {/* 竖线（注意楚河汉界断开） */}
            {[...Array(COLS)].map((_, i) => (
              <React.Fragment key={`v${i}`}>
                <line x1={PAD + i * CELL} y1={PAD} x2={PAD + i * CELL} y2={PAD + 4 * CELL} stroke="rgba(184,115,51,0.40)" strokeWidth="1.5" />
                <line x1={PAD + i * CELL} y1={PAD + 5 * CELL} x2={PAD + i * CELL} y2={H - PAD} stroke="rgba(184,115,51,0.40)" strokeWidth="1.5" />
              </React.Fragment>
            ))}

            {/* 九宫格斜线 */}
            <line x1={PAD + 3 * CELL} y1={PAD} x2={PAD + 5 * CELL} y2={PAD + 2 * CELL} stroke="rgba(184,115,51,0.40)" strokeWidth="1.5" />
            <line x1={PAD + 5 * CELL} y1={PAD} x2={PAD + 3 * CELL} y2={PAD + 2 * CELL} stroke="rgba(184,115,51,0.40)" strokeWidth="1.5" />
            <line x1={PAD + 3 * CELL} y1={PAD + 7 * CELL} x2={PAD + 5 * CELL} y2={PAD + 9 * CELL} stroke="rgba(184,115,51,0.40)" strokeWidth="1.5" />
            <line x1={PAD + 5 * CELL} y1={PAD + 7 * CELL} x2={PAD + 3 * CELL} y2={PAD + 9 * CELL} stroke="rgba(184,115,51,0.40)" strokeWidth="1.5" />

            {/* 楚河汉界 */}
            <text x={PAD + 1.5 * CELL} y={PAD + 4.6 * CELL} textAnchor="middle" fill="rgba(184,115,51,0.60)" fontSize="22" fontFamily="'KaiTi', 'STKaiti', serif" fontWeight="bold">
              {flipped ? '汉 界' : '楚 河'}
            </text>
            <text x={PAD + 6.5 * CELL} y={PAD + 4.6 * CELL} textAnchor="middle" fill="rgba(184,115,51,0.60)" fontSize="22" fontFamily="'KaiTi', 'STKaiti', serif" fontWeight="bold">
              {flipped ? '楚 河' : '汉 界'}
            </text>

            {/* 提示箭头 */}
            {showArrows && bestMoves && bestMoves.red_best_move && (
              drawArrow(
                getArrowCoords(bestMoves.red_best_from_row, bestMoves.red_best_from_col, bestMoves.red_best_to_row, bestMoves.red_best_to_col).x1,
                getArrowCoords(bestMoves.red_best_from_row, bestMoves.red_best_from_col, bestMoves.red_best_to_row, bestMoves.red_best_to_col).y1,
                getArrowCoords(bestMoves.red_best_from_row, bestMoves.red_best_from_col, bestMoves.red_best_to_row, bestMoves.red_best_to_col).x2,
                getArrowCoords(bestMoves.red_best_from_row, bestMoves.red_best_from_col, bestMoves.red_best_to_row, bestMoves.red_best_to_col).y2,
                '#FF6B6B',
                '1',
                bestMoves.red_score
              )
            )}

            {showArrows && bestMoves && bestMoves.black_best_move && (
              drawArrow(
                getArrowCoords(bestMoves.black_best_from_row, bestMoves.black_best_from_col, bestMoves.black_best_to_row, bestMoves.black_best_to_col).x1,
                getArrowCoords(bestMoves.black_best_from_row, bestMoves.black_best_from_col, bestMoves.black_best_to_row, bestMoves.black_best_to_col).y1,
                getArrowCoords(bestMoves.black_best_from_row, bestMoves.black_best_from_col, bestMoves.black_best_to_row, bestMoves.black_best_to_col).x2,
                getArrowCoords(bestMoves.black_best_from_row, bestMoves.black_best_from_col, bestMoves.black_best_to_row, bestMoves.black_best_to_col).y2,
                '#6B9FFF',
                '2',
                bestMoves.black_score
              )
            )}

            {/* 战术标签连线 */}
            {connectionLines.map((line) => (
              drawConnectionLine(line.from.row, line.from.col, line.to.row, line.to.col, line.type)
            ))}
          </svg>

          {/* 棋子层 */}
          <div style={{ ...styles.piecesLayer, width: W, height: H, marginTop: -H }}>
            {displayBoard.map((row, r) => row.map((piece, c) => {
              const actualRow = flipped ? 9 - r : r;
              const actualCol = flipped ? 8 - c : c;

              const x = PAD + c * CELL;
              const y = PAD + r * CELL;
              const sel = selected(actualRow, actualCol);
              const can = canMoveTo(actualRow, actualCol);
              const isFrom = isLastMoveFrom(actualRow, actualCol);
              const isTo = isLastMoveTo(actualRow, actualCol);
              const highlightInfo = getHighlightInfo(actualRow, actualCol);

              return (
                <div
                  key={`${r}-${c}`}
                  onClick={() => handleClick(actualRow, actualCol)}
                  style={{
                    ...styles.cell,
                    left: x - CELL / 2,
                    top: y - CELL / 2,
                    width: CELL,
                    height: CELL,
                    zIndex: sel ? 20 : 10,
                  }}
                >
                  {/* 上一步标记 */}
                  {(isFrom || isTo) && (
                    <div style={{
                      ...styles.lastMoveMark,
                      width: CELL,
                      height: CELL,
                      background: isFrom ? 'rgba(255,193,7,0.5)' : 'rgba(76,175,80,0.5)',
                    }} />
                  )}

                  {/* 战术标签高亮 */}
                  {highlightInfo && (
                    <div style={{
                      ...styles.tacticalHighlight,
                      width: CELL + 4,
                      height: CELL + 4,
                      borderColor: highlightInfo.type === 'attack' ? '#FF6B6B' : 
                                   highlightInfo.type === 'defense' ? '#4CAF50' : '#FF9800',
                      background: highlightInfo.type === 'attack' ? 'rgba(255,107,107,0.2)' : 
                                  highlightInfo.type === 'defense' ? 'rgba(76,175,80,0.2)' : 'rgba(255,152,0,0.2)',
                    }} />
                  )}

                  {/* 可移动提示 */}
                  {can && (
                    <div style={{
                      ...styles.legalMoveDot,
                      width: CELL * 0.3,
                      height: CELL * 0.3,
                    }} />
                  )}

                  {/* 棋子 */}
                  {piece && (
                    <motion.div
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      style={{
                        ...styles.piece,
                        width: CELL * 0.84,
                        height: CELL * 0.84,
                        fontSize: CELL * 0.33,
                        background: piece === piece.toUpperCase()
                          ? 'linear-gradient(145deg, #2a1a12, #1a1008)'
                          : 'linear-gradient(145deg, #1a1a1a, #0a0a0a)',
                        color: piece === piece.toUpperCase() ? '#e53935' : '#e0e0e0',
                        border: `3px solid ${piece === piece.toUpperCase() ? '#B87333' : '#888'}`,
                        boxShadow: sel
                          ? '0 0 0 4px rgba(184,115,51,0.50), 0 8px 20px rgba(0,0,0,0.5)'
                          : '0 4px 12px rgba(0,0,0,0.4)',
                        transform: sel ? 'scale(1.12)' : 'scale(1)',
                      }}
                    >
                      {renderPieceName(piece)}
                    </motion.div>
                  )}
                </div>
              );
            }))}
          </div>

          {/* 加载遮罩 */}
          {isLoading && (
            <div style={styles.loadingOverlay}>
              <div style={styles.loadingContent}>
                <div style={styles.loadingSpinner}>⏳</div>
                <div>分析中...</div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 错误提示 */}
      {error && (
        <div style={styles.errorPopup}>
          <span>{error}</span>
          <button className="liquid-glass-btn sm" onClick={clearError}>✕</button>
        </div>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  boardContainer: {
    position: 'relative',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  outerFrame: {
    padding: 12,
    background: 'linear-gradient(145deg, #1a1410, #0e0c14)',
    borderRadius: 12,
    boxShadow: `
      0 0 0 1px rgba(184,115,51,0.20),
      0 0 60px rgba(184,115,51,0.08),
      inset 0 0 40px rgba(0,0,0,0.30),
      0 20px 60px rgba(0,0,0,0.50),
      inset 0 1px 0 rgba(184,115,51,0.15)
    `,
    border: '1px solid rgba(184,115,51,0.18)',
  },
  innerFrame: {
    padding: 4,
    background: '#0a0a0f',
    borderRadius: 8,
    border: '1px solid rgba(255,255,255,0.05)',
  },
  boardSvg: {
    display: 'block',
    background: '#0B132B',
    borderRadius: 4,
  },
  piecesLayer: {
    position: 'relative',
  },
  cell: {
    position: 'absolute',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    cursor: 'pointer',
  },
  lastMoveMark: {
    position: 'absolute',
    width: 50,
    height: 50,
    borderRadius: 6,
    pointerEvents: 'none',
  },
  tacticalHighlight: {
    position: 'absolute',
    width: 52,
    height: 52,
    borderRadius: 8,
    border: '3px solid',
    pointerEvents: 'none',
    animation: 'pulse 1.5s ease-in-out infinite',
  },
  legalMoveDot: {
    position: 'absolute',
    width: 16,
    height: 16,
    borderRadius: '50%',
    background: 'rgba(34,197,94,0.85)',
    boxShadow: '0 0 12px rgba(34,197,94,0.9)',
    pointerEvents: 'none',
  },
  piece: {
    width: 46,
    height: 46,
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontFamily: "'KaiTi', 'STKaiti', 'SimSun', serif",
    fontWeight: 'bold',
    fontSize: 18,
    transition: 'all 0.15s cubic-bezier(0.4, 0, 0.2, 1)',
    cursor: 'pointer',
  },
  loadingOverlay: {
    position: 'absolute',
    inset: 0,
    background: 'rgba(0,0,0,0.7)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 8,
    zIndex: 100,
  },
  loadingContent: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: 10,
    color: '#fff',
    fontSize: 16,
  },
  loadingSpinner: {
    fontSize: 36,
    animation: 'pulse 1.5s ease-in-out infinite',
  },
  errorPopup: {
    position: 'absolute',
    top: '50%',
    left: '50%',
    transform: 'translate(-50%, -50%)',
    background: 'rgba(200,0,0,0.95)',
    color: 'white',
    padding: '16px 24px',
    borderRadius: 10,
    fontSize: 14,
    zIndex: 200,
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    boxShadow: '0 8px 30px rgba(0,0,0,0.4)',
  },
  errorClose: {
    background: 'transparent',
    border: 'none',
    color: 'white',
    cursor: 'pointer',
    fontSize: 18,
    padding: 4,
  },
};
