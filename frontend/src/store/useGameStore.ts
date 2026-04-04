import { create } from 'zustand';
import { api, AIMoveResponse, BestMovesResponse, GameSearchResult, GameDetailResponse } from '../services/api';

export interface EvalPoint {
  depth: number;
  cp: number;
  move: string;
}

const initialBoard: string[][] = [
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
];

type GameMode = 'analysis' | 'pvp' | 'pve_red' | 'pve_black' | 'replay';

interface ReplayState {
  games: GameSearchResult[];
  selectedGame: GameDetailResponse | null;
  currentIndex: number;
  totalMoves: number;
  moves: string[];
  source: 'neo4j' | 'pgn' | null;
  isLoadingGames: boolean;
}

interface EnginePanelState {
  fen: string;
  bestmove: string;
  score: number;
  depth: number;
  pv: string[];
  turn: string;
  legalMoveCount: number;
  isCheck: boolean;
  isCheckmate: boolean;
  isLoading: boolean;
  error: string | null;
}

interface CheckAlertState {
  id: number;
  attacker: 'red' | 'black';
  target: 'red' | 'black';
  row: number;
  col: number;
  isCheckmate: boolean;
}

interface CaptureEffectState {
  id: number;
  row: number;
  col: number;
  piece: string;
  attacker: 'red' | 'black';
}

interface InvalidMoveState {
  id: number;
  row: number;
  col: number;
  message: string;
}

interface GameState {
  board: string[][];
  fen: string;
  previousFen: string;  // 走法之前的FEN，用于深度分析
  history: string[];
  legalMoves: string[];
  selectedPos: { row: number; col: number } | null;
  isLoading: boolean;
  redToMove: boolean;
  error: string | null;
  gameMode: GameMode;
  lastMove: { from: { row: number; col: number }, to: { row: number; col: number } } | null;
  flipped: boolean;
  showArrows: boolean;
  isBoardCollapsed: boolean;
  setBoardCollapsed: (v: boolean) => void;
  toggleBoardCollapsed: () => void;
  aiDifficulty: number;
  setAiDifficulty: (d: number) => void;
  bestMoves: BestMovesResponse | null;
  replayState: ReplayState;
  highlightedPieces: { row: number; col: number; type: 'attack' | 'target' | 'defense' }[];
  connectionLines: { from: { row: number; col: number }; to: { row: number; col: number }; type: 'attack' | 'defense' | 'pin' }[];
  evalHistory: EvalPoint[];
  enginePanel: EnginePanelState;
  checkAlert: CheckAlertState | null;
  captureEffect: CaptureEffectState | null;
  invalidMove: InvalidMoveState | null;

  selectPiece: (row: number, col: number) => Promise<void>;
  movePiece: (toRow: number, toCol: number) => Promise<void>;
  setGameMode: (mode: GameMode) => void;
  resetGame: () => void;
  clearError: () => void;
  aiMove: () => Promise<void>;
  toggleFlip: () => void;
  toggleShowArrows: () => void;
  fetchBestMoves: () => Promise<void>;
  setHighlightedPieces: (pieces: { row: number; col: number; type: 'attack' | 'target' | 'defense' }[]) => void;
  setConnectionLines: (lines: { from: { row: number; col: number }; to: { row: number; col: number }; type: 'attack' | 'defense' | 'pin' }[]) => void;
  clearHighlights: () => void;
  addEvalPoint: (point: EvalPoint) => void;
  clearEvalHistory: () => void;
  refreshEngineEvaluation: (fen?: string) => Promise<void>;
  triggerInvalidMove: (row: number, col: number, message: string) => void;
  clearInvalidMove: () => void;
  clearCheckAlert: () => void;
  clearCaptureEffect: () => void;

  searchGames: (player?: string, event?: string) => Promise<void>;
  loadGameFromNeo4j: (gameId: number) => Promise<void>;
  loadGameFromPGN: (pgnContent: string) => Promise<void>;
  navigateReplay: (direction: 'prev' | 'next' | 'start' | 'end' | 'goto', index?: number) => Promise<void>;
  exitReplay: () => void;
  loadFromRecognition: (board: string[][], fen: string) => void;
}

function flipBoard(board: string[][]): string[][] {
  return board.slice().reverse().map(row => row.slice().reverse());
}

function findKingPosition(board: string[][], side: 'red' | 'black') {
  const king = side === 'red' ? 'K' : 'k';
  for (let row = 0; row < board.length; row += 1) {
    for (let col = 0; col < board[row].length; col += 1) {
      if (board[row][col] === king) {
        return { row, col };
      }
    }
  }
  return null;
}

export const useGameStore = create<GameState>((set, get) => ({
  board: initialBoard,
  fen: 'rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w',
  previousFen: '',
  history: [],
  legalMoves: [],
  selectedPos: null,
  isLoading: false,
  redToMove: true,
  error: null,
  gameMode: 'analysis',
  lastMove: null,
  flipped: false,
  showArrows: false,
  bestMoves: null,
  isBoardCollapsed: false,
  setBoardCollapsed: (v) => set({ isBoardCollapsed: v }),
  toggleBoardCollapsed: () => set(s => ({ isBoardCollapsed: !s.isBoardCollapsed })),
  aiDifficulty: 10,
  setAiDifficulty: (d) => set({ aiDifficulty: d }),
  replayState: {
    games: [],
    selectedGame: null,
    currentIndex: 0,
    totalMoves: 0,
    moves: [],
    source: null,
    isLoadingGames: false
  },
  highlightedPieces: [],
  connectionLines: [],
  evalHistory: [],
  enginePanel: {
    fen: '',
    bestmove: '',
    score: 0,
    depth: 0,
    pv: [],
    turn: 'red',
    legalMoveCount: 0,
    isCheck: false,
    isCheckmate: false,
    isLoading: false,
    error: null,
  },
  checkAlert: null,
  captureEffect: null,
  invalidMove: null,

  setHighlightedPieces: (pieces) => {
    set({ highlightedPieces: pieces });
  },

  setConnectionLines: (lines) => {
    set({ connectionLines: lines });
  },

  clearHighlights: () => {
    set({ highlightedPieces: [], connectionLines: [] });
  },

  addEvalPoint: (point) => {
    set(state => ({ evalHistory: [...state.evalHistory, point] }));
  },

  clearEvalHistory: () => {
    set({ evalHistory: [] });
  },

  triggerInvalidMove: (row, col, message) => {
    set({
      invalidMove: {
        id: Date.now(),
        row,
        col,
        message,
      }
    });
  },

  clearInvalidMove: () => {
    set({ invalidMove: null });
  },

  clearCheckAlert: () => {
    set({ checkAlert: null });
  },

  clearCaptureEffect: () => {
    set({ captureEffect: null });
  },

  refreshEngineEvaluation: async (fenOverride?: string) => {
    const targetFen = fenOverride || get().fen;
    if (!targetFen) return;
    const { board, redToMove } = get();

    set(state => ({
      enginePanel: {
        ...state.enginePanel,
        isLoading: true,
        error: null,
      }
    }));

    try {
      const result = await api.getEngineEvaluation(targetFen, board, redToMove);
      if (get().fen !== targetFen) {
        return;
      }

      const cp = Math.round(result.score * 100);
      const nextPoint: EvalPoint = {
        cp,
        depth: result.depth,
        move: result.bestmove,
      };

      set(state => {
        const lastPoint = state.evalHistory[state.evalHistory.length - 1];
        const nextHistory =
          state.enginePanel.fen === targetFen ||
          (lastPoint && lastPoint.cp === nextPoint.cp && lastPoint.depth === nextPoint.depth && lastPoint.move === nextPoint.move)
            ? state.evalHistory
            : [...state.evalHistory, nextPoint].slice(-24);

        return {
          evalHistory: nextHistory,
          enginePanel: {
            fen: targetFen,
            bestmove: result.bestmove,
            score: result.score,
            depth: result.depth,
            pv: result.pv,
            turn: result.turn,
            legalMoveCount: result.legalMoveCount,
            isCheck: result.isCheck,
            isCheckmate: result.isCheckmate,
            isLoading: false,
            error: null,
          }
        };
      });
    } catch (e: any) {
      if (get().fen !== targetFen) {
        return;
      }

      set(state => ({
        enginePanel: {
          ...state.enginePanel,
          fen: targetFen,
          isLoading: false,
          error: e?.response?.data?.detail || e?.message || '引擎评估失败',
        }
      }));
    }
  },

  toggleFlip: () => {
    set(state => ({ flipped: !state.flipped }));
  },

  toggleShowArrows: () => {
    const newShowArrows = !get().showArrows;
    set({ showArrows: newShowArrows });
    if (newShowArrows) {
      get().fetchBestMoves();
    }
  },

  fetchBestMoves: async () => {
    const { board, redToMove, flipped } = get();
    
    let actualBoard = board;
    if (flipped) {
      actualBoard = flipBoard(board);
    }

    try {
      const res = await api.getBestMoves({
        board: actualBoard,
        red_to_move: redToMove,
        difficulty: 15
      });
      set({ bestMoves: res });
    } catch (e) {
      console.error('获取最优解失败:', e);
    }
  },

  setGameMode: (mode) => {
    const flipped = mode === 'pve_black';
    set({ gameMode: mode, selectedPos: null, legalMoves: [], flipped });
  },

  selectPiece: async (row, col) => {
    const { board, redToMove, gameMode, flipped } = get();
    
    let actualRow = row;
    let actualCol = col;
    let actualBoard = board;
    
    if (flipped) {
      actualRow = 9 - row;
      actualCol = 8 - col;
      actualBoard = flipBoard(board);
    }
    
    const piece = actualBoard[actualRow][actualCol];
    if (!piece) return;
    
    const isRedPiece = piece === piece.toUpperCase();
    
    if (gameMode === 'pve_red' && !isRedPiece) return;
    if (gameMode === 'pve_black' && isRedPiece) return;
    
    if (isRedPiece !== redToMove && (gameMode === 'analysis' || gameMode === 'pvp')) return;

    set({ selectedPos: { row: actualRow, col: actualCol }, legalMoves: [], error: null });
    
    try {
      const response = await api.getLegalMoves({ board: actualBoard, row: actualRow, col: actualCol });
      set({ legalMoves: response.moves });
    } catch (e: any) {
      set({ legalMoves: [], error: e.response?.data?.detail || '获取合法走法失败' });
    }
  },

  movePiece: async (toRow, toCol) => {
    const { selectedPos, board, history, redToMove, gameMode, flipped, fen: currentFen } = get();
    if (!selectedPos) return;

    let actualToRow = toRow;
    let actualToCol = toCol;
    let actualBoard = board;
    
    if (flipped) {
      actualToRow = 9 - toRow;
      actualToCol = 8 - toCol;
      actualBoard = flipBoard(board);
    }

    set({ isLoading: true, error: null });
    
    const previousFen = currentFen;

    try {
      const res = await api.makeMove({
        board: actualBoard,
        from_row: selectedPos.row,
        from_col: selectedPos.col,
        to_row: actualToRow,
        to_col: actualToCol,
        red_to_move: redToMove
      });

      const fromColChar = String.fromCharCode(97 + selectedPos.col);
      const fromRowNum = 9 - selectedPos.row;
      const toColChar = String.fromCharCode(97 + actualToCol);
      const toRowNum = 9 - actualToRow;
      const moveStr = `${fromColChar}${fromRowNum}${toColChar}${toRowNum}`;
      const attacker = redToMove ? 'red' : 'black';
      const target = redToMove ? 'black' : 'red';
      const checkedKing = res.in_check ? findKingPosition(res.board, target) : null;

      const newLastMove = {
        from: { row: selectedPos.row, col: selectedPos.col },
        to: { row: actualToRow, col: actualToCol }
      };

      let newBoard = res.board;
      if (flipped) {
        newBoard = flipBoard(res.board);
      }

      set({
        board: newBoard,
        fen: res.fen,
        previousFen: previousFen,
        selectedPos: null,
        legalMoves: [],
        isLoading: false,
        redToMove: !redToMove,
        history: [...history, moveStr],
        lastMove: newLastMove,
        captureEffect: res.captured ? {
          id: Date.now(),
          row: actualToRow,
          col: actualToCol,
          piece: res.captured,
          attacker,
        } : null,
        checkAlert: res.in_check && checkedKing ? {
          id: Date.now() + 1,
          attacker,
          target,
          row: checkedKing.row,
          col: checkedKing.col,
          isCheckmate: res.game_over,
        } : null,
        invalidMove: null,
      });

      // 在分析模式下，如果开启了箭头，获取最佳走法
      if (gameMode === 'analysis' && get().showArrows) {
        get().fetchBestMoves();
      }

      // 走棋后刷新引擎评估
      get().refreshEngineEvaluation(res.fen);

      if (gameMode === 'pve_red' || gameMode === 'pve_black') {
        setTimeout(() => {
          get().aiMove();
        }, 500);
      }
    } catch (e: any) {
      const errorMsg = e.response?.data?.detail || '移动失败';
      set({
        isLoading: false,
        error: errorMsg,
        selectedPos: null,
        legalMoves: [],
        invalidMove: {
          id: Date.now(),
          row: actualToRow,
          col: actualToCol,
          message: errorMsg,
        }
      });
    }
  },

  aiMove: async () => {
    const { board, redToMove, gameMode, flipped, fen: currentFen } = get();
    
    if ((gameMode === 'pve_red' && redToMove) || (gameMode === 'pve_black' && !redToMove)) {
      return;
    }

    let actualBoard = board;
    if (flipped) {
      actualBoard = flipBoard(board);
    }

    set({ isLoading: true, error: null });
    try {
      const res: AIMoveResponse = await api.aiMove({
        board: actualBoard,
        red_to_move: redToMove,
        difficulty: get().aiDifficulty
      });

      const fromColChar = String.fromCharCode(97 + res.from_col);
      const fromRowNum = 9 - res.from_row;
      const toColChar = String.fromCharCode(97 + res.to_col);
      const toRowNum = 9 - res.to_row;
      const moveStr = `${fromColChar}${fromRowNum}${toColChar}${toRowNum}`;
      const attacker = redToMove ? 'red' : 'black';
      const target = redToMove ? 'black' : 'red';
      const capturedPiece = actualBoard[res.to_row][res.to_col];
      const checkedKing = res.in_check ? findKingPosition(res.board, target) : null;

      const newLastMove = {
        from: { row: res.from_row, col: res.from_col },
        to: { row: res.to_row, col: res.to_col }
      };

      let newBoard = res.board;
      if (flipped) {
        newBoard = flipBoard(res.board);
      }

      set({
        board: newBoard,
        fen: res.fen,
        previousFen: currentFen,
        selectedPos: null,
        legalMoves: [],
        isLoading: false,
        redToMove: !redToMove,
        history: [...get().history, moveStr],
        lastMove: newLastMove,
        captureEffect: capturedPiece ? {
          id: Date.now(),
          row: res.to_row,
          col: res.to_col,
          piece: capturedPiece,
          attacker,
        } : null,
        checkAlert: res.in_check && checkedKing ? {
          id: Date.now() + 1,
          attacker,
          target,
          row: checkedKing.row,
          col: checkedKing.col,
          isCheckmate: res.game_over,
        } : null,
        invalidMove: null,
      });

      // AI走棋后刷新引擎评估
      get().refreshEngineEvaluation(res.fen);
    } catch (e: any) {
      set({ isLoading: false, error: e.response?.data?.detail || 'AI走棋失败' });
    }
  },

  resetGame: () => {
    set({
      board: initialBoard,
      fen: 'rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w',
      previousFen: '',
      history: [],
      legalMoves: [],
      selectedPos: null,
      isLoading: false,
      redToMove: true,
      error: null,
      lastMove: null,
      bestMoves: null,
      checkAlert: null,
      captureEffect: null,
      invalidMove: null,
      evalHistory: [],
      enginePanel: {
        ...get().enginePanel,
        fen: '',
        bestmove: '',
        score: 0,
        depth: 0,
        pv: [],
        legalMoveCount: 0,
        isCheck: false,
        isCheckmate: false,
        isLoading: false,
        error: null,
      }
    });
    
    if (get().showArrows) {
      get().fetchBestMoves();
    }
  },

  clearError: () => {
    set({ error: null });
  },

  searchGames: async (player?: string, event?: string) => {
    set({ replayState: { ...get().replayState, isLoadingGames: true } });
    try {
      const res = await api.searchGames({ player, event, limit: 50 });
      set({ replayState: { ...get().replayState, games: res.games, isLoadingGames: false } });
    } catch (e) {
      console.error('搜索对局失败:', e);
      set({ replayState: { ...get().replayState, isLoadingGames: false, games: [] } });
    }
  },

  loadGameFromNeo4j: async (gameId: number) => {
    set({ isLoading: true, error: null });
    try {
      const gameDetail = await api.getGameDetail(gameId);
      
      set({
        board: initialBoard,
        fen: 'rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w',
        previousFen: '',
        history: [],
        redToMove: true,
        selectedPos: null,
        legalMoves: [],
        lastMove: null,
        checkAlert: null,
        captureEffect: null,
        invalidMove: null,
        evalHistory: [],
        enginePanel: {
          ...get().enginePanel,
          fen: '',
          bestmove: '',
          score: 0,
          depth: 0,
          pv: [],
          legalMoveCount: 0,
          isCheck: false,
          isCheckmate: false,
          isLoading: false,
          error: null,
        },
        isLoading: false,
        replayState: {
          ...get().replayState,
          selectedGame: gameDetail,
          moves: gameDetail.moves,
          currentIndex: 0,
          totalMoves: gameDetail.moves.length,
          source: 'neo4j'
        }
      });
    } catch (e: any) {
      set({ isLoading: false, error: e.response?.data?.detail || '加载对局失败' });
    }
  },

  loadGameFromPGN: async (pgnContent: string) => {
    set({ isLoading: true, error: null });
    try {
      const pgnRes = await api.pgnLoad(pgnContent);
      
      if (pgnRes.games.length === 0) {
        set({ isLoading: false, error: '未找到有效对局' });
        return;
      }
      
      const firstGame = pgnRes.games[0];
      const gameDetail: GameDetailResponse = {
        game_id: -1,
        red: firstGame.red_player,
        black: firstGame.black_player,
        event: firstGame.event,
        date: firstGame.date,
        result: firstGame.result,
        moves: firstGame.moves
      };
      
      set({
        board: initialBoard,
        fen: 'rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w',
        previousFen: '',
        history: [],
        redToMove: true,
        selectedPos: null,
        legalMoves: [],
        lastMove: null,
        checkAlert: null,
        captureEffect: null,
        invalidMove: null,
        isLoading: false,
        replayState: {
          ...get().replayState,
          selectedGame: gameDetail,
          moves: firstGame.moves,
          currentIndex: 0,
          totalMoves: firstGame.moves.length,
          source: 'pgn',
          games: pgnRes.games.map((g, i) => ({
            game_id: i,
            red: g.red_player,
            black: g.black_player,
            event: g.event,
            date: g.date,
            result: g.result
          }))
        }
      });
    } catch (e: any) {
      set({ isLoading: false, error: e.response?.data?.detail || '解析PGN失败' });
    }
  },

  navigateReplay: async (direction: 'prev' | 'next' | 'start' | 'end' | 'goto', index?: number) => {
    const { replayState } = get();
    const { moves, currentIndex } = replayState;
    
    if (!moves.length) return;
    
    let newIndex = currentIndex;
    
    switch (direction) {
      case 'prev':
        newIndex = Math.max(0, currentIndex - 1);
        break;
      case 'next':
        newIndex = Math.min(moves.length, currentIndex + 1);
        break;
      case 'start':
        newIndex = 0;
        break;
      case 'end':
        newIndex = moves.length;
        break;
      case 'goto':
        newIndex = index !== undefined ? Math.max(0, Math.min(moves.length, index)) : currentIndex;
        break;
    }
    
    try {
      const navRes = await api.pgnNavigate({
        moves: moves,
        current_index: newIndex,
        direction: 'goto'
      });
      
      const lastMoveInfo = newIndex > 0 && newIndex <= moves.length ? {
        from: { row: 0, col: 0 },
        to: { row: 0, col: 0 }
      } : null;
      
      set({
        board: navRes.board,
        fen: navRes.fen,
        previousFen: '',
        redToMove: newIndex % 2 === 0,
        history: moves.slice(0, newIndex),
        lastMove: lastMoveInfo,
        checkAlert: null,
        captureEffect: null,
        invalidMove: null,
        replayState: {
          ...replayState,
          currentIndex: newIndex
        }
      });
    } catch (e) {
      console.error('导航失败:', e);
    }
  },

  exitReplay: () => {
    set({
      board: initialBoard,
      fen: 'rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w',
      previousFen: '',
      history: [],
      redToMove: true,
      selectedPos: null,
      legalMoves: [],
      lastMove: null,
      checkAlert: null,
      captureEffect: null,
      invalidMove: null,
        evalHistory: [],
        enginePanel: {
          ...get().enginePanel,
          fen: '',
          bestmove: '',
          score: 0,
          depth: 0,
          pv: [],
          legalMoveCount: 0,
          isCheck: false,
          isCheckmate: false,
          isLoading: false,
          error: null,
        },
      replayState: {
        games: [],
        selectedGame: null,
        currentIndex: 0,
        totalMoves: 0,
        moves: [],
        source: null,
        isLoadingGames: false
      }
    });
  },

  loadFromRecognition: (board: string[][], fen: string) => {
    const isRedTurn = fen.includes(' w ') || fen.endsWith(' w');
    set({
      board,
      fen,
      previousFen: '',
      history: [],
      legalMoves: [],
      selectedPos: null,
      isLoading: false,
      redToMove: isRedTurn,
      error: null,
      lastMove: null,
      bestMoves: null,
      checkAlert: null,
      captureEffect: null,
      invalidMove: null,
      evalHistory: [],
      gameMode: 'analysis',
      enginePanel: {
        ...get().enginePanel,
        fen: '',
        bestmove: '',
        score: 0,
        depth: 0,
        pv: [],
        legalMoveCount: 0,
        isCheck: false,
        isCheckmate: false,
        isLoading: false,
        error: null,
      },
    });
    get().refreshEngineEvaluation(fen);
    if (get().showArrows) {
      get().fetchBestMoves();
    }
  },
}));
