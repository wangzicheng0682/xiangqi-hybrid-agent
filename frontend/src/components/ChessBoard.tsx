import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useGameStore } from '../store/useGameStore';
import { renderPieceName } from '../utils/pieces';

const BASE_CELL = 55;
const BASE_PAD = 32;
const COLS = 9;
const ROWS = 10;
const STAR_POINTS = [
  { col: 1, row: 2 },
  { col: 7, row: 2 },
  { col: 0, row: 3 },
  { col: 2, row: 3 },
  { col: 4, row: 3 },
  { col: 6, row: 3 },
  { col: 8, row: 3 },
  { col: 1, row: 7 },
  { col: 7, row: 7 },
  { col: 0, row: 6 },
  { col: 2, row: 6 },
  { col: 4, row: 6 },
  { col: 6, row: 6 },
  { col: 8, row: 6 },
];

export default function ChessBoard() {
  const [boardSize, setBoardSize] = useState({ cell: BASE_CELL, pad: BASE_PAD });
  const [hoveredCell, setHoveredCell] = useState<{ row: number; col: number } | null>(null);

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
    connectionLines,
    checkAlert,
    captureEffect,
    invalidMove,
    triggerInvalidMove,
    clearInvalidMove,
    clearCheckAlert,
    clearCaptureEffect,
  } = useGameStore();

  useEffect(() => {
    if (!invalidMove) return;
    const timer = window.setTimeout(() => clearInvalidMove(), 1200);
    return () => window.clearTimeout(timer);
  }, [invalidMove, clearInvalidMove]);

  useEffect(() => {
    if (!checkAlert) return;
    const timer = window.setTimeout(() => clearCheckAlert(), checkAlert.isCheckmate ? 2200 : 1800);
    return () => window.clearTimeout(timer);
  }, [checkAlert, clearCheckAlert]);

  useEffect(() => {
    if (!captureEffect) return;
    const timer = window.setTimeout(() => clearCaptureEffect(), 780);
    return () => window.clearTimeout(timer);
  }, [captureEffect, clearCaptureEffect]);

  const handleClick = (row: number, col: number) => {
    const piece = board[row][col];
    const pos = `${String.fromCharCode(97 + col)}${9 - row}`;
    const canMove = legalMoves.some(m => m.endsWith(pos));
    const selectedPiece = selectedPos ? board[selectedPos.row][selectedPos.col] : '';
    const sameSide = Boolean(piece && selectedPiece && (piece === piece.toUpperCase()) === (selectedPiece === selectedPiece.toUpperCase()));

    if (selectedPos && canMove) {
      movePiece(row, col);
    } else if (piece) {
      if (selectedPos && !sameSide) {
        triggerInvalidMove(row, col, '该棋子当前不能这样吃');
        return;
      }
      selectPiece(row, col);
    } else if (selectedPos) {
      triggerInvalidMove(row, col, '该落点不是合法走法');
    }
  };

  const canMoveTo = (row: number, col: number) => {
    const pos = `${String.fromCharCode(97 + col)}${9 - row}`;
    return legalMoves.some(m => m.endsWith(pos));
  };

  const selected = (row: number, col: number) =>
    selectedPos?.row === row && selectedPos?.col === col;

  const hovered = (row: number, col: number) =>
    hoveredCell?.row === row && hoveredCell?.col === col;

  const isLastMoveFrom = (row: number, col: number) =>
    lastMove?.from.row === row && lastMove?.from.col === col;

  const isLastMoveTo = (row: number, col: number) =>
    lastMove?.to.row === row && lastMove?.to.col === col;

  const isCheckedKing = (row: number, col: number) =>
    checkAlert?.row === row && checkAlert?.col === col;

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

  const drawStarMark = (col: number, row: number) => {
    const x = PAD + col * CELL;
    const y = PAD + row * CELL;
    const arm = Math.max(5, CELL * 0.11);
    const gap = Math.max(3, CELL * 0.06);
    const stroke = 'rgba(191, 151, 98, 0.82)';

    const segments = [
      [x - arm - gap, y - arm, x - gap, y - arm],
      [x - arm - gap, y + arm, x - gap, y + arm],
      [x - arm, y - arm - gap, x - arm, y - gap],
      [x - arm, y + gap, x - arm, y + arm + gap],
      [x + gap, y - arm, x + arm + gap, y - arm],
      [x + gap, y + arm, x + arm + gap, y + arm],
      [x + arm, y - arm - gap, x + arm, y - gap],
      [x + arm, y + gap, x + arm, y + arm + gap],
    ];

    return (
      <g key={`star-${col}-${row}`} opacity={0.82}>
        {segments.map((segment, index) => (
          <line
            key={`star-seg-${col}-${row}-${index}`}
            x1={segment[0]}
            y1={segment[1]}
            x2={segment[2]}
            y2={segment[3]}
            stroke={stroke}
            strokeWidth="1.2"
            strokeLinecap="round"
          />
        ))}
      </g>
    );
  };

  return (
    <div style={styles.boardContainer}>
      {/* 外框装饰 */}
      <motion.div
        style={styles.outerFrame}
        initial={{ opacity: 0, y: 18, scale: 0.985 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.48, ease: [0.16, 1, 0.3, 1] }}
      >
        {/* 内框 */}
        <div style={styles.innerFrame}>
          <svg width={W} height={H} style={styles.boardSvg}>
            <defs>
              <linearGradient id="boardSurface" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#101a2a" />
                <stop offset="45%" stopColor="#142236" />
                <stop offset="100%" stopColor="#0b1320" />
              </linearGradient>
              <radialGradient id="boardFalloff" cx="50%" cy="45%" r="76%">
                <stop offset="0%" stopColor="rgba(255, 240, 214, 0.025)" />
                <stop offset="50%" stopColor="rgba(60, 82, 112, 0.035)" />
                <stop offset="100%" stopColor="rgba(6, 10, 18, 0.0)" />
              </radialGradient>
              <linearGradient id="outerFrameStroke" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="rgba(70, 94, 126, 0.55)" />
                <stop offset="100%" stopColor="rgba(34, 47, 68, 0.35)" />
              </linearGradient>
              <linearGradient id="innerFrameStroke" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="rgba(197, 160, 105, 0.36)" />
                <stop offset="100%" stopColor="rgba(115, 88, 55, 0.22)" />
              </linearGradient>
              <linearGradient id="riverWash" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="rgba(255,255,255,0)" />
                <stop offset="15%" stopColor="rgba(105, 122, 151, 0.06)" />
                <stop offset="50%" stopColor="rgba(191, 151, 98, 0.09)" />
                <stop offset="85%" stopColor="rgba(105, 122, 151, 0.06)" />
                <stop offset="100%" stopColor="rgba(255,255,255,0)" />
              </linearGradient>
              <linearGradient id="riverSweep" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="rgba(255,255,255,0)" />
                <stop offset="50%" stopColor="rgba(214, 191, 144, 0.18)" />
                <stop offset="100%" stopColor="rgba(255,255,255,0)" />
              </linearGradient>
              <filter id="boardShadow" x="-20%" y="-20%" width="140%" height="140%">
                <feDropShadow dx="0" dy="14" stdDeviation="16" floodColor="#000814" floodOpacity="0.28"/>
              </filter>
              <filter id="boardTexture" x="-20%" y="-20%" width="140%" height="140%">
                <feTurbulence type="fractalNoise" baseFrequency="0.58" numOctaves="2" seed="17" result="noise"/>
                <feColorMatrix in="noise" type="saturate" values="0" result="monoNoise"/>
                <feComponentTransfer in="monoNoise" result="fadedNoise">
                  <feFuncA type="table" tableValues="0 0 0.018 0.032"/>
                </feComponentTransfer>
              </filter>
              <filter id="riverBlur" x="-10%" y="-200%" width="120%" height="500%">
                <feGaussianBlur stdDeviation="5" result="blur"/>
                <feMerge>
                  <feMergeNode in="blur"/>
                  <feMergeNode in="SourceGraphic"/>
                </feMerge>
              </filter>
            </defs>

            <rect x={0} y={0} width={W} height={H} rx={20} fill="#08111b" />
            <rect
              x={2}
              y={2}
              width={W - 4}
              height={H - 4}
              rx={18}
              fill="transparent"
              stroke="url(#outerFrameStroke)"
              strokeWidth="1"
              opacity="0.9"
            />
            <rect
              x={PAD - 11}
              y={PAD - 11}
              width={W - PAD * 2 + 22}
              height={H - PAD * 2 + 22}
              rx={8}
              fill="url(#boardSurface)"
              stroke="url(#innerFrameStroke)"
              strokeWidth="1.2"
              filter="url(#boardShadow)"
            />
            <rect
              x={PAD - 11}
              y={PAD - 11}
              width={W - PAD * 2 + 22}
              height={H - PAD * 2 + 22}
              rx={8}
              fill="url(#boardFalloff)"
            />
            <rect
              x={PAD - 11}
              y={PAD - 11}
              width={W - PAD * 2 + 22}
              height={H - PAD * 2 + 22}
              rx={8}
              fill="rgba(255,255,255,0.02)"
              filter="url(#boardTexture)"
            />
            <rect
              x={PAD + CELL * 0.2}
              y={PAD + 4.42 * CELL}
              width={W - PAD * 2 - CELL * 0.4}
              height={CELL * 0.34}
              rx={2}
              fill="url(#riverWash)"
              filter="url(#riverBlur)"
            />
            <motion.rect
              x={PAD + CELL * 0.8}
              y={PAD + 4.44 * CELL}
              width={Math.max(CELL * 1.8, (W - PAD * 2) * 0.22)}
              height={CELL * 0.26}
              rx={2}
              fill="url(#riverSweep)"
              opacity={0.34}
              filter="url(#riverBlur)"
              animate={{ x: [PAD + CELL * 0.6, W - PAD - CELL * 2.4, PAD + CELL * 0.6] }}
              transition={{ duration: 10, repeat: Infinity, ease: 'easeInOut' }}
            />

            {[...Array(ROWS)].map((_, i) => (
              <React.Fragment key={`h${i}`}>
                <line
                  x1={PAD}
                  y1={PAD + i * CELL}
                  x2={W - PAD}
                  y2={PAD + i * CELL}
                  stroke="rgba(188, 150, 98, 0.48)"
                  strokeWidth={i === 0 || i === ROWS - 1 ? '1.45' : '1.1'}
                  opacity={i === 0 || i === ROWS - 1 ? 0.95 : 0.82}
                />
              </React.Fragment>
            ))}

            {[...Array(COLS)].map((_, i) => (
              <React.Fragment key={`v${i}`}>
                <line
                  x1={PAD + i * CELL}
                  y1={PAD}
                  x2={PAD + i * CELL}
                  y2={PAD + 4 * CELL}
                  stroke="rgba(188, 150, 98, 0.48)"
                  strokeWidth={i === 0 || i === COLS - 1 ? '1.45' : '1.1'}
                  opacity={i === 0 || i === COLS - 1 ? 0.95 : 0.82}
                />
                <line
                  x1={PAD + i * CELL}
                  y1={PAD + 5 * CELL}
                  x2={PAD + i * CELL}
                  y2={H - PAD}
                  stroke="rgba(188, 150, 98, 0.48)"
                  strokeWidth={i === 0 || i === COLS - 1 ? '1.45' : '1.1'}
                  opacity={i === 0 || i === COLS - 1 ? 0.95 : 0.82}
                />
              </React.Fragment>
            ))}

            <line x1={PAD + 3 * CELL} y1={PAD} x2={PAD + 5 * CELL} y2={PAD + 2 * CELL} stroke="rgba(188, 150, 98, 0.52)" strokeWidth="1.1" opacity="0.9" />
            <line x1={PAD + 5 * CELL} y1={PAD} x2={PAD + 3 * CELL} y2={PAD + 2 * CELL} stroke="rgba(188, 150, 98, 0.52)" strokeWidth="1.1" opacity="0.9" />
            <line x1={PAD + 3 * CELL} y1={PAD + 7 * CELL} x2={PAD + 5 * CELL} y2={PAD + 9 * CELL} stroke="rgba(188, 150, 98, 0.52)" strokeWidth="1.1" opacity="0.9" />
            <line x1={PAD + 5 * CELL} y1={PAD + 7 * CELL} x2={PAD + 3 * CELL} y2={PAD + 9 * CELL} stroke="rgba(188, 150, 98, 0.52)" strokeWidth="1.1" opacity="0.9" />

            {STAR_POINTS.map((point) => drawStarMark(point.col, point.row))}

            <text
              x={W / 2}
              y={PAD + 4.59 * CELL}
              textAnchor="middle"
              fill="rgba(204, 180, 132, 0.16)"
              fontSize={Math.max(16, CELL * 0.24)}
              fontFamily="'PingFang SC', 'Microsoft YaHei', sans-serif"
              fontWeight="600"
              letterSpacing="0.16em"
            >
              楚河智境
            </text>
            <text
              x={W / 2}
              y={PAD + 4.53 * CELL}
              textAnchor="middle"
              fill="rgba(191, 151, 98, 0.84)"
              fontSize={Math.max(18, CELL * 0.27)}
              fontFamily="'PingFang SC', 'Microsoft YaHei', sans-serif"
              fontWeight="600"
              letterSpacing="0.24em"
            >
              楚河智境
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
            <AnimatePresence>
              {checkAlert && (
                <motion.div
                  initial={{ opacity: 0, y: -16, scale: 0.96 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -10, scale: 0.98 }}
                  transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
                  style={styles.checkBanner}
                >
                  <span style={styles.checkBannerEyebrow}>{checkAlert.attacker === 'red' ? '红方施压' : '黑方施压'}</span>
                  <span style={styles.checkBannerTitle}>{checkAlert.isCheckmate ? '将死' : '将军'}</span>
                </motion.div>
              )}
            </AnimatePresence>

            {displayBoard.map((row, r) => row.map((piece, c) => {
              const actualRow = flipped ? 9 - r : r;
              const actualCol = flipped ? 8 - c : c;

              const x = PAD + c * CELL;
              const y = PAD + r * CELL;
              const sel = selected(actualRow, actualCol);
              const can = canMoveTo(actualRow, actualCol);
              const isFrom = isLastMoveFrom(actualRow, actualCol);
              const isTo = isLastMoveTo(actualRow, actualCol);
              const isChecked = isCheckedKing(actualRow, actualCol);
              const highlightInfo = getHighlightInfo(actualRow, actualCol);

              return (
                <div
                  key={`${r}-${c}`}
                  onClick={() => handleClick(actualRow, actualCol)}
                  onMouseEnter={() => setHoveredCell({ row: actualRow, col: actualCol })}
                  onMouseLeave={() => setHoveredCell((current) => (
                    current?.row === actualRow && current?.col === actualCol ? null : current
                  ))}
                  style={{
                    ...styles.cell,
                    left: x - CELL / 2,
                    top: y - CELL / 2,
                    width: CELL,
                    height: CELL,
                    zIndex: sel ? 20 : 10,
                    animation: invalidMove?.row === actualRow && invalidMove?.col === actualCol
                      ? 'boardIllegalShake 0.34s cubic-bezier(0.36, 0.07, 0.19, 0.97)'
                      : undefined,
                  }}
                >
                  {/* 上一步标记 */}
                  {(isFrom || isTo) && (
                    <div style={{
                      ...styles.lastMoveMark,
                      width: CELL,
                      height: CELL,
                      borderColor: isFrom ? 'rgba(191, 151, 98, 0.72)' : 'rgba(129, 187, 198, 0.72)',
                      boxShadow: isFrom
                        ? '0 0 0 1px rgba(191, 151, 98, 0.14) inset, 0 0 12px rgba(191, 151, 98, 0.18)'
                        : '0 0 0 1px rgba(129, 187, 198, 0.14) inset, 0 0 12px rgba(129, 187, 198, 0.18)',
                    }} />
                  )}

                  {(hovered(actualRow, actualCol) || sel) && (
                    <div style={{
                      ...styles.hoverMark,
                      width: CELL * 0.96,
                      height: CELL * 0.96,
                      borderColor: sel
                        ? 'rgba(129, 187, 198, 0.42)'
                        : 'rgba(191, 151, 98, 0.28)',
                    }} />
                  )}

                  {isChecked && (
                    <div style={{
                      ...styles.checkPulse,
                      width: CELL * 1.08,
                      height: CELL * 1.08,
                    }} />
                  )}

                  {invalidMove?.row === actualRow && invalidMove?.col === actualCol && (
                    <div style={styles.invalidMark}>×</div>
                  )}

                  {captureEffect?.row === actualRow && captureEffect?.col === actualCol && (
                    <>
                      <div style={{
                        ...styles.captureFlash,
                        width: CELL * 1.05,
                        height: CELL * 1.05,
                        borderColor: captureEffect.attacker === 'red' ? 'rgba(184, 80, 58, 0.58)' : 'rgba(102, 141, 194, 0.58)',
                      }} />
                      {Array.from({ length: 6 }).map((_, index) => (
                        <span
                          key={`capture-particle-${index}`}
                          style={{
                            ...styles.captureParticle,
                            transform: `rotate(${index * 60}deg) translateY(-${CELL * 0.42}px)`,
                            background: captureEffect.attacker === 'red'
                              ? 'linear-gradient(180deg, rgba(238, 202, 138, 0.96), rgba(184, 80, 58, 0.14))'
                              : 'linear-gradient(180deg, rgba(213, 229, 255, 0.96), rgba(89, 122, 188, 0.14))',
                          }}
                        />
                      ))}
                    </>
                  )}

                  {/* 战术标签高亮 */}
                  {highlightInfo && (
                    <div style={{
                      ...styles.tacticalHighlight,
                      width: CELL + 4,
                      height: CELL + 4,
                      borderColor: highlightInfo.type === 'attack' ? 'rgba(186, 92, 78, 0.9)' : 
                                   highlightInfo.type === 'defense' ? 'rgba(99, 156, 135, 0.9)' : 'rgba(191, 151, 98, 0.9)',
                      background: highlightInfo.type === 'attack' ? 'rgba(186, 92, 78, 0.06)' : 
                                  highlightInfo.type === 'defense' ? 'rgba(99, 156, 135, 0.06)' : 'rgba(191, 151, 98, 0.06)',
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
                      animate={{ scale: sel ? 1.08 : 1, y: sel ? -CELL * 0.04 : 0 }}
                      transition={{ type: 'spring', stiffness: 320, damping: 24 }}
                      whileHover={{ y: sel ? -CELL * 0.05 : -CELL * 0.028, scale: sel ? 1.1 : 1.035 }}
                      whileTap={{ scale: 0.985, y: -CELL * 0.01 }}
                      style={{
                        ...styles.piece,
                        width: CELL * 0.82,
                        height: CELL * 0.82,
                        fontSize: CELL * 0.34,
                        background: 'radial-gradient(circle at 34% 30%, rgba(250, 244, 231, 1) 0%, rgba(239, 230, 215, 0.98) 62%, rgba(220, 205, 183, 0.98) 100%)',
                        color: piece === piece.toUpperCase() ? '#a23b2f' : '#323844',
                        border: '1.8px solid rgba(177, 144, 102, 0.72)',
                        boxShadow: sel
                          ? '0 0 0 3px rgba(129, 187, 198, 0.20), 0 8px 14px rgba(8, 10, 14, 0.16), inset 0 1px 0 rgba(255,255,255,0.44), inset 0 -2px 4px rgba(116, 96, 69, 0.08)'
                          : '0 3px 8px rgba(8, 10, 14, 0.14), inset 0 1px 0 rgba(255,255,255,0.42), inset 0 -2px 4px rgba(116, 96, 69, 0.08)',
                        textShadow: '0 1px 0 rgba(255,255,255,0.18)',
                      }}
                    >
                      {renderPieceName(piece)}
                    </motion.div>
                  )}
                </div>
              );
            }))}

            <AnimatePresence>
              {invalidMove && (
                <motion.div
                  initial={{ opacity: 0, y: 6, scale: 0.94 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: 4, scale: 0.98 }}
                  transition={{ duration: 0.18 }}
                  style={{
                    ...styles.invalidToast,
                    left: PAD + (flipped ? 8 - invalidMove.col : invalidMove.col) * CELL,
                    top: PAD + (flipped ? 9 - invalidMove.row : invalidMove.row) * CELL - CELL * 0.82,
                  }}
                >
                  {invalidMove.message}
                </motion.div>
              )}
            </AnimatePresence>
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
      </motion.div>

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
    filter: 'drop-shadow(0 14px 24px rgba(0, 6, 16, 0.16))',
  },
  outerFrame: {
    padding: 12,
    background: 'linear-gradient(145deg, rgba(12,18,30,0.82), rgba(8,12,22,0.9))',
    borderRadius: 18,
    boxShadow: `
      0 0 0 1px rgba(255,255,255,0.04),
      0 10px 20px rgba(0,0,0,0.16),
      inset 0 1px 0 rgba(255,255,255,0.05),
      inset 0 -8px 16px rgba(0,0,0,0.12)
    `,
    border: '1px solid rgba(255,255,255,0.04)',
    backdropFilter: 'blur(10px) saturate(108%)',
    WebkitBackdropFilter: 'blur(10px) saturate(108%)',
  },
  innerFrame: {
    padding: 5,
    background: 'linear-gradient(180deg, rgba(8, 13, 24, 0.98) 0%, rgba(4, 8, 16, 0.98) 100%)',
    borderRadius: 14,
    border: '1px solid rgba(255,255,255,0.05)',
    boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.04)',
  },
  boardSvg: {
    display: 'block',
    background: 'transparent',
    borderRadius: 18,
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
    borderRadius: '50%',
    border: '1.5px solid',
    background: 'radial-gradient(circle, rgba(255,255,255,0.06) 0%, rgba(255,255,255,0.01) 56%, rgba(255,255,255,0) 72%)',
    pointerEvents: 'none',
    animation: 'boardPulseRing 2.1s ease-in-out infinite',
  },
  hoverMark: {
    position: 'absolute',
    borderRadius: '50%',
    border: '1px solid',
    background: 'radial-gradient(circle, rgba(255,255,255,0.03) 0%, rgba(255,255,255,0) 70%)',
    pointerEvents: 'none',
    animation: 'boardHoverHalo 1.8s ease-in-out infinite',
  },
  checkPulse: {
    position: 'absolute',
    borderRadius: '50%',
    border: '1.5px solid rgba(188, 73, 52, 0.72)',
    background: 'radial-gradient(circle, rgba(210, 94, 68, 0.18) 0%, rgba(210, 94, 68, 0.05) 48%, rgba(210, 94, 68, 0) 76%)',
    pointerEvents: 'none',
    animation: 'boardCheckPulse 0.9s ease-out infinite',
  },
  tacticalHighlight: {
    position: 'absolute',
    width: 52,
    height: 52,
    borderRadius: '50%',
    border: '2px solid',
    pointerEvents: 'none',
    animation: 'boardPulseRing 1.8s ease-in-out infinite',
    boxShadow: '0 0 8px rgba(255,255,255,0.03)',
  },
  legalMoveDot: {
    position: 'absolute',
    width: 16,
    height: 16,
    borderRadius: '50%',
    background: 'radial-gradient(circle, rgba(201, 166, 109, 0.95) 0%, rgba(191, 151, 98, 0.72) 45%, rgba(191, 151, 98, 0.06) 100%)',
    boxShadow: '0 0 10px rgba(191, 151, 98, 0.22)',
    pointerEvents: 'none',
    animation: 'boardBreath 1.6s ease-in-out infinite',
  },
  piece: {
    width: 46,
    height: 46,
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontFamily: "'Microsoft YaHei', 'SimHei', 'KaiTi', 'SimSun', sans-serif",
    fontWeight: 'bold',
    fontSize: 18,
    transition: 'box-shadow 0.18s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.18s cubic-bezier(0.16, 1, 0.3, 1), color 0.18s cubic-bezier(0.16, 1, 0.3, 1)',
    cursor: 'pointer',
    position: 'relative',
    letterSpacing: '0.02em',
  },
  checkBanner: {
    position: 'absolute',
    top: 10,
    left: '50%',
    transform: 'translateX(-50%)',
    zIndex: 30,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: 4,
    minWidth: 122,
    padding: '10px 18px 11px',
    borderRadius: 16,
    background: 'linear-gradient(180deg, rgba(58, 10, 13, 0.9) 0%, rgba(106, 26, 26, 0.94) 100%)',
    border: '1px solid rgba(255,255,255,0.1)',
    boxShadow: '0 12px 26px rgba(0, 0, 0, 0.26), inset 0 1px 0 rgba(255,255,255,0.12)',
    pointerEvents: 'none',
  },
  checkBannerEyebrow: {
    fontSize: 10,
    letterSpacing: '0.18em',
    textTransform: 'uppercase',
    color: 'rgba(255, 226, 211, 0.72)',
  },
  checkBannerTitle: {
    fontSize: 24,
    lineHeight: 1,
    fontFamily: "'Microsoft YaHei', 'SimHei', 'KaiTi', 'SimSun', sans-serif",
    color: 'rgba(255, 245, 238, 0.96)',
    textShadow: '0 0 18px rgba(255, 122, 79, 0.32)',
  },
  invalidMark: {
    position: 'absolute',
    top: '50%',
    left: '50%',
    transform: 'translate(-50%, -50%)',
    color: 'rgba(211, 92, 74, 0.94)',
    fontSize: 24,
    fontWeight: 700,
    textShadow: '0 0 14px rgba(211, 92, 74, 0.28)',
    pointerEvents: 'none',
  },
  invalidToast: {
    position: 'absolute',
    transform: 'translate(-50%, -100%)',
    zIndex: 40,
    padding: '8px 12px',
    borderRadius: 12,
    background: 'linear-gradient(180deg, rgba(103, 21, 26, 0.94) 0%, rgba(74, 14, 19, 0.98) 100%)',
    color: 'rgba(255, 240, 236, 0.96)',
    border: '1px solid rgba(255,255,255,0.08)',
    boxShadow: '0 10px 24px rgba(0, 0, 0, 0.22)',
    whiteSpace: 'nowrap',
    pointerEvents: 'none',
    fontSize: 12,
  },
  captureFlash: {
    position: 'absolute',
    borderRadius: '50%',
    border: '1.5px solid',
    background: 'radial-gradient(circle, rgba(255, 236, 189, 0.28) 0%, rgba(255, 236, 189, 0.05) 48%, rgba(255, 236, 189, 0) 72%)',
    animation: 'boardCapturePulse 0.75s ease-out forwards',
    pointerEvents: 'none',
  },
  captureParticle: {
    position: 'absolute',
    width: 3,
    height: 16,
    borderRadius: 999,
    animation: 'boardCaptureSpark 0.7s ease-out forwards',
    transformOrigin: 'center center',
    pointerEvents: 'none',
    opacity: 0.92,
  },
  loadingOverlay: {
    position: 'absolute',
    inset: 0,
    background: 'rgba(3, 8, 18, 0.62)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 18,
    zIndex: 100,
    backdropFilter: 'blur(8px)',
  },
  loadingContent: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: 10,
    color: 'rgba(244, 241, 222, 0.92)',
    fontSize: 16,
  },
  loadingSpinner: {
    fontSize: 36,
    animation: 'boardBreath 1.5s ease-in-out infinite',
  },
  errorPopup: {
    position: 'absolute',
    top: '50%',
    left: '50%',
    transform: 'translate(-50%, -50%)',
    background: 'linear-gradient(180deg, rgba(117, 18, 28, 0.94) 0%, rgba(83, 13, 21, 0.98) 100%)',
    color: 'white',
    padding: '16px 24px',
    borderRadius: 16,
    fontSize: 14,
    zIndex: 200,
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    boxShadow: '0 16px 40px rgba(0,0,0,0.38), inset 0 1px 0 rgba(255,255,255,0.12)',
    border: '1px solid rgba(255,255,255,0.08)',
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
