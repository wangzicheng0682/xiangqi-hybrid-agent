"""
FEN to Text Board Converter

将FEN转换为人类可读的文本棋盘，供LLM理解局面

Reference: PRD 3.1, TECH 5.4
"""

from typing import List, Dict, Tuple, Optional


PIECE_NAMES_CN = {
    'K': '帅', 'k': '将',
    'A': '仕', 'a': '士',
    'B': '相', 'b': '象',
    'R': '车', 'r': '車',
    'C': '炮', 'c': '砲',
    'N': '马', 'n': '馬',
    'P': '兵', 'p': '卒',
}

PIECE_NAMES_EN = {
    'K': 'R_King', 'k': 'B_King',
    'A': 'R_Advisor', 'a': 'B_Advisor',
    'B': 'R_Bishop', 'b': 'B_Bishop',
    'R': 'R_Rook', 'c': 'B_Cannon',
    'C': 'R_Cannon', 'r': 'B_Rook',
    'N': 'R_Knight', 'n': 'B_Knight',
    'P': 'R_Pawn', 'p': 'B_Pawn',
}

COL_NAMES = 'abcdefghi'
ROW_NAMES = '9876543210'


def fen_to_board(fen: str) -> List[List[str]]:
    if not fen:
        return []
    
    board_fen = fen.split()[0] if ' ' in fen else fen
    rows = board_fen.split('/')
    board = []
    
    for row in rows:
        board_row = []
        for char in row:
            if char.isdigit():
                board_row.extend([''] * int(char))
            else:
                board_row.append(char)
        board.append(board_row)
    
    return board


def board_to_text_chinese(board: List[List[str]]) -> str:
    lines = []
    lines.append("  ┌──┬──┬──┬──┬──┬──┬──┬──┬──┐")
    lines.append("  │  │ 一│ 二│ 三│ 四│ 五│ 六│ 七│ 八│ 九│  ← 红方")
    
    for i, row in enumerate(board):
        row_num = 10 - i
        row_display = row_num if row_num <= 5 else row_num
        
        cells = []
        for cell in row:
            if cell:
                cells.append(PIECE_NAMES_CN.get(cell, cell))
            else:
                cells.append('　')
        
        row_str = '│'.join(cells)
        lines.append(f"{row_num} │{row_str}│")
        
        if i < 9:
            lines.append("  ├──┼──┼──┼──┼──┼──┼──┼──┤")
    
    lines.append("  │  │ 一│ 二│ 三│ 四│ 五│ 六│ 七│ 八│ 九│  ← 黑方")
    lines.append("  └──┴──┴──┴──┴──┴──┴──┴──┴──┘")
    
    return '\n'.join(lines)


def board_to_text_simple(board: List[List[str]]) -> str:
    lines = []
    lines.append("    a   b   c   d   e   f   g   h   i")
    lines.append("  +---+---+---+---+---+---+---+---+---+")
    
    for i, row in enumerate(board):
        row_num = 10 - i
        cells = []
        for cell in row:
            if cell:
                cells.append(f' {cell} ')
            else:
                cells.append('   ')
        row_str = '|'.join(cells)
        lines.append(f"{row_num} |{row_str}|")
        lines.append("  +---+---+---+---+---+---+---+---+---+")
    
    lines.append("    a   b   c   d   e   f   g   h   i")
    
    return '\n'.join(lines)


def fen_to_text_board(fen: str, use_chinese: bool = True) -> str:
    board = fen_to_board(fen)
    if not board:
        return "空棋盘"
    
    if use_chinese:
        return board_to_text_chinese(board)
    else:
        return board_to_text_simple(board)


def get_piece_positions(board: List[List[str]]) -> Dict[str, List[Tuple[int, int, str]]]:
    positions = {
        'red': [],
        'black': []
    }
    
    for i, row in enumerate(board):
        for j, cell in enumerate(row):
            if cell:
                col_name = COL_NAMES[j]
                row_name = ROW_NAMES[i]
                coord = f"{col_name}{row_name}"
                piece_cn = PIECE_NAMES_CN.get(cell, cell)
                
                if cell.isupper():
                    positions['red'].append((i, j, f"{piece_cn}({coord})"))
                else:
                    positions['black'].append((i, j, f"{piece_cn}({coord})"))
    
    return positions


def generate_position_description(fen: str) -> str:
    board = fen_to_board(fen)
    if not board:
        return ""
    
    desc_parts = []
    
    desc_parts.append("【棋盘布局】")
    desc_parts.append(fen_to_text_board(fen))
    
    positions = get_piece_positions(board)
    
    desc_parts.append("\n【红方子力】")
    if positions['red']:
        red_pieces = [p[2] for p in positions['red']]
        desc_parts.append('、'.join(red_pieces))
    else:
        desc_parts.append("无")
    
    desc_parts.append("\n【黑方子力】")
    if positions['black']:
        black_pieces = [p[2] for p in positions['black']]
        desc_parts.append('、'.join(black_pieces))
    else:
        desc_parts.append("无")
    
    parts = fen.split()
    if len(parts) >= 2:
        turn = "红方" if parts[1] == 'w' else "黑方"
        desc_parts.append(f"\n【当前回合】{turn}走棋")
    
    return '\n'.join(desc_parts)


def get_material_balance(board: List[List[str]]) -> Dict[str, any]:
    PIECE_VALUES = {
        'K': 10000, 'k': 10000,
        'R': 900, 'r': 900,
        'C': 450, 'c': 450,
        'N': 400, 'n': 400,
        'B': 200, 'b': 200,
        'A': 200, 'a': 200,
        'P': 100, 'p': 100,
    }
    
    red_value = 0
    black_value = 0
    red_pieces = {}
    black_pieces = {}
    
    for row in board:
        for cell in row:
            if cell:
                value = PIECE_VALUES.get(cell.upper(), 0)
                name = PIECE_NAMES_CN.get(cell.upper(), cell.upper())
                if cell.isupper():
                    red_value += value
                    red_pieces[name] = red_pieces.get(name, 0) + 1
                else:
                    black_value += value
                    black_pieces[name] = black_pieces.get(name, 0) + 1
    
    return {
        'red_value': red_value,
        'black_value': black_value,
        'balance': red_value - black_value,
        'red_pieces': red_pieces,
        'black_pieces': black_pieces
    }


def create_llm_context(fen: str, bestmove: str = None, score: float = None, last_move_info: Dict = None) -> str:
    board = fen_to_board(fen)
    context_parts = []
    
    parts = fen.split()
    turn = "红方" if (len(parts) < 2 or parts[1] == 'w') else "黑方"
    turn_en = "红" if turn == "红方" else "黑"
    opponent = "黑方" if turn == "红方" else "红方"
    
    context_parts.append(f"你是象棋教练。{opponent}刚走了一步棋，现在轮到{turn}走棋。\n")
    
    context_parts.append("【棋盘位置】（大写=红方棋子，小写=黑方棋子，列a-i从左到右，行0-9从下到上）\n")
    
    for row_idx in range(10):
        row = board[row_idx]
        row_display = f"行{9-row_idx}: "
        for col_idx, cell in enumerate(row):
            if cell:
                piece_name = PIECE_NAMES_CN.get(cell, cell)
                coord = f"{COL_NAMES[col_idx]}{9-row_idx}"
                row_display += f"{piece_name}({coord}) "
            else:
                row_display += "＋ "
        context_parts.append(row_display + "\n")
    
    if last_move_info:
        player = last_move_info.get("player", opponent)
        piece = last_move_info.get("piece", "")
        from_coord = last_move_info.get("from", "")
        to_coord = last_move_info.get("to", "")
        captured = last_move_info.get("captured", "")
        
        move_desc = f"\n【刚才的走法】{player}走了 {piece} 从 {from_coord} 到 {to_coord}"
        if captured:
            move_desc += f"，吃掉了{captured}"
        move_desc += "\n"
        context_parts.append(move_desc)
    
    if bestmove and len(bestmove) >= 4:
        from_col = ord(bestmove[0]) - ord('a')
        from_row = 9 - int(bestmove[1])
        to_col = ord(bestmove[2]) - ord('a')
        to_row = 9 - int(bestmove[3])
        
        if 0 <= from_row < 10 and 0 <= from_col < 9:
            piece = board[from_row][from_col]
            piece_name = PIECE_NAMES_CN.get(piece, piece)
            from_coord = f"{COL_NAMES[from_col]}{9-from_row}"
            to_coord = f"{COL_NAMES[to_col]}{9-to_row}"
            context_parts.append(f"【引擎推荐】{turn_en}方应走 {piece_name} 从 {from_coord} 到 {to_coord}\n")
    
    if score is not None:
        if abs(score) < 30:
            context_parts.append(f"【局面评估】均势\n")
        elif (turn == "红方" and score > 0) or (turn == "黑方" and score < 0):
            context_parts.append(f"【局面评估】{turn}方优势\n")
        else:
            context_parts.append(f"【局面评估】{turn}方劣势\n")
    
    context_parts.append("\n请分析：1)刚才那步棋的目的是什么？是好棋吗？2)引擎推荐的这步棋为什么好？用2-3句话回答。")
    
    return ''.join(context_parts)
