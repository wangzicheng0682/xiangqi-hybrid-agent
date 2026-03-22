const PIECE_NAMES: Record<string, string> = {
  'K': '帅', 'k': '将', 'A': '仕', 'a': '士',
  'B': '相', 'b': '象', 'R': '车', 'r': '車',
  'C': '炮', 'c': '砲', 'N': '马', 'n': '馬',
  'P': '兵', 'p': '卒',
};

export const renderPieceName = (piece: string): string => {
  return PIECE_NAMES[piece] || piece;
};
