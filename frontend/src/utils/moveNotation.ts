export interface MoveEntry {
  index: number;
  raw: string;
  text: string;
  side: 'red' | 'black';
}

export interface MovePair {
  round: number;
  red: MoveEntry | null;
  black: MoveEntry | null;
}

const INITIAL_BOARD: string[][] = [
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

const RED_NUMERALS = ['一', '二', '三', '四', '五', '六', '七', '八', '九'];
const BLACK_NUMERALS = ['1', '2', '3', '4', '5', '6', '7', '8', '9'];

const PIECE_LABELS: Record<string, string> = {
  K: '帅',
  A: '仕',
  B: '相',
  N: '马',
  R: '车',
  C: '炮',
  P: '兵',
  k: '将',
  a: '士',
  b: '象',
  n: '马',
  r: '车',
  c: '炮',
  p: '卒',
};

const LINEAR_TARGET_PIECES = new Set(['K', 'k', 'R', 'r', 'C', 'c', 'P', 'p']);

const isIccsMove = (move: string): boolean => /^[a-i][0-9][a-i][0-9]$/i.test(move);

const cloneBoard = (board: string[][]): string[][] => board.map((row) => row.slice());

const fileLabel = (col: number, isRed: boolean): string => {
  return isRed ? RED_NUMERALS[8 - col] : BLACK_NUMERALS[col];
};

const stepLabel = (step: number, isRed: boolean): string => {
  if (step <= 0 || step > 9) return String(step);
  return isRed ? RED_NUMERALS[step - 1] : BLACK_NUMERALS[step - 1];
};

const parseIccsMove = (move: string) => {
  const normalized = move.toLowerCase();
  return {
    fromCol: normalized.charCodeAt(0) - 97,
    fromRow: 9 - Number(normalized[1]),
    toCol: normalized.charCodeAt(2) - 97,
    toRow: 9 - Number(normalized[3]),
  };
};

const piecePrefix = (board: string[][], piece: string, row: number, col: number): string => {
  const isRed = piece === piece.toUpperCase();
  const peers: number[] = [];

  for (let i = 0; i < board.length; i += 1) {
    if (i !== row && board[i][col] === piece) {
      peers.push(i);
    }
  }

  if (peers.length === 0) {
    return `${PIECE_LABELS[piece]}${fileLabel(col, isRed)}`;
  }

  const ordered = [...peers, row].sort((a, b) => (isRed ? a - b : b - a));
  const index = ordered.indexOf(row);
  const disambiguation = ordered.length === 2
    ? ['前', '后']
    : ordered.length === 3
      ? ['前', '中', '后']
      : null;

  if (!disambiguation || index < 0 || index >= disambiguation.length) {
    return `${PIECE_LABELS[piece]}${fileLabel(col, isRed)}`;
  }

  return `${disambiguation[index]}${PIECE_LABELS[piece]}`;
};

const formatIccsMove = (board: string[][], move: string): string => {
  if (!isIccsMove(move)) {
    return move;
  }

  const { fromCol, fromRow, toCol, toRow } = parseIccsMove(move);
  const piece = board[fromRow]?.[fromCol];
  if (!piece) {
    return move;
  }

  const isRed = piece === piece.toUpperCase();
  const prefix = piecePrefix(board, piece, fromRow, fromCol);
  const rowDelta = toRow - fromRow;
  const isForward = isRed ? rowDelta < 0 : rowDelta > 0;

  if (fromRow === toRow) {
    return `${prefix}平${fileLabel(toCol, isRed)}`;
  }

  const action = isForward ? '进' : '退';
  const destination = LINEAR_TARGET_PIECES.has(piece)
    ? stepLabel(Math.abs(rowDelta), isRed)
    : fileLabel(toCol, isRed);

  return `${prefix}${action}${destination}`;
};

const applyMove = (board: string[][], move: string): string[][] => {
  if (!isIccsMove(move)) {
    return board;
  }

  const next = cloneBoard(board);
  const { fromCol, fromRow, toCol, toRow } = parseIccsMove(move);
  next[toRow][toCol] = next[fromRow][fromCol];
  next[fromRow][fromCol] = '';
  return next;
};

export const formatMovePairs = (moves: string[]): MovePair[] => {
  let board = cloneBoard(INITIAL_BOARD);
  const entries: MoveEntry[] = [];

  moves.forEach((move, index) => {
    const text = formatIccsMove(board, move);
    entries.push({
      index,
      raw: move,
      text,
      side: index % 2 === 0 ? 'red' : 'black',
    });
    board = applyMove(board, move);
  });

  const pairs: MovePair[] = [];
  for (let i = 0; i < entries.length; i += 2) {
    pairs.push({
      round: Math.floor(i / 2) + 1,
      red: entries[i] ?? null,
      black: entries[i + 1] ?? null,
    });
  }

  return pairs;
};
