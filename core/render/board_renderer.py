"""
Chess Board Renderer for Xiangqi.

Reference:
  - PRD: Sprint 1 / 棋盘可视化
  - TECH: FEN解析与棋盘生成
"""

import platform
from PIL import Image, ImageDraw, ImageFont
from typing import Tuple


# Piece symbol mapping
PIECE_SYMBOLS = {
    # Red pieces (uppercase in FEN)
    'K': '帅',
    'A': '仕',
    'B': '相',
    'E': '相',
    'R': '車',
    'C': '炮',
    'H': '馬',
    'N': '馬',
    'P': '兵',
    # Black pieces (lowercase in FEN)
    'k': '将',
    'a': '士',
    'b': '象',
    'e': '象',
    'r': '車',
    'c': '炮',
    'h': '马',
    'n': '马',
    'p': '卒',
}


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    """Load a CJK-capable font, with platform-aware fallbacks."""
    candidates = []
    if platform.system() == "Windows":
        candidates = [
            "C:\\Windows\\Fonts\\simhei.ttf",
            "C:\\Windows\\Fonts\\msyh.ttc",
            "C:\\Windows\\Fonts\\simsun.ttc",
        ]
    else:
        candidates = [
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except (IOError, OSError):
            continue
    return ImageFont.load_default()


def render_board(
    fen: str,
    width: int = 540,
    height: int = 600,
    output_path: str = None
) -> Image.Image:
    """
    Render a Xiangqi board from FEN.

    Args:
        fen: FEN string (only position part is used)
        width: Board width in pixels
        height: Board height in pixels
        output_path: Optional path to save the image

    Returns:
        PIL Image object
    """
    img = Image.new('RGB', (width, height), color='#F5DEB3')
    draw = ImageDraw.Draw(img)

    margin_x = int(width * 0.08)
    margin_top = int(height * 0.06)
    margin_bot = int(height * 0.06)
    board_w = width - 2 * margin_x
    board_h = height - margin_top - margin_bot
    cell_w = board_w / 8
    cell_h = board_h / 9

    def gx(file_idx):
        return margin_x + file_idx * cell_w

    def gy(rank_idx):
        return margin_top + rank_idx * cell_h

    # ── Draw grid lines ──
    line_color = '#4A3728'

    # Horizontal lines (10 ranks)
    for r in range(10):
        y = gy(r)
        draw.line([(gx(0), y), (gx(8), y)], fill=line_color, width=2)

    # Vertical lines — full on left/right edges, split by river in middle
    for f in range(9):
        x = gx(f)
        if f == 0 or f == 8:
            # Edge lines run full height
            draw.line([(x, gy(0)), (x, gy(9))], fill=line_color, width=2)
        else:
            # Split at river (ranks 4–5)
            draw.line([(x, gy(0)), (x, gy(4))], fill=line_color, width=2)
            draw.line([(x, gy(5)), (x, gy(9))], fill=line_color, width=2)

    # ── Palace diagonals (九宫格) ──
    # Black palace: files 3-5, ranks 0-2
    draw.line([(gx(3), gy(0)), (gx(5), gy(2))], fill=line_color, width=2)
    draw.line([(gx(5), gy(0)), (gx(3), gy(2))], fill=line_color, width=2)
    # Red palace: files 3-5, ranks 7-9
    draw.line([(gx(3), gy(7)), (gx(5), gy(9))], fill=line_color, width=2)
    draw.line([(gx(5), gy(7)), (gx(3), gy(9))], fill=line_color, width=2)

    # ── River text (楚河汉界) ──
    river_font = _load_font(max(14, int(cell_h * 0.38)))
    river_y_center = (gy(4) + gy(5)) / 2
    for text, cx in [("楚 河", gx(2)), ("漢 界", gx(6))]:
        bbox = draw.textbbox((0, 0), text, font=river_font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text((cx - tw / 2, river_y_center - th / 2), text, fill='#8B7355', font=river_font)

    # ── Piece rendering ──
    piece_font_size = max(14, int(min(cell_w, cell_h) * 0.52))
    piece_font = _load_font(piece_font_size)
    radius = min(cell_w, cell_h) * 0.40

    position = fen.split()[0]
    ranks = position.split('/')

    for rank_idx, rank in enumerate(ranks):
        file_idx = 0
        for char in rank:
            if char.isdigit():
                file_idx += int(char)
            else:
                cx = gx(file_idx)
                cy = gy(rank_idx)
                piece_symbol = PIECE_SYMBOLS.get(char, char)
                is_red = char.isupper()
                piece_color = '#CC0000' if is_red else '#1A1A1A'
                outline_color = '#CC0000' if is_red else '#1A1A1A'

                # Background circle with border
                draw.ellipse(
                    [(cx - radius, cy - radius), (cx + radius, cy + radius)],
                    fill='#FAEBD7',
                    outline=outline_color,
                    width=3,
                )
                # Inner border ring
                inner_r = radius - 4
                draw.ellipse(
                    [(cx - inner_r, cy - inner_r), (cx + inner_r, cy + inner_r)],
                    outline=outline_color,
                    width=1,
                )

                # Center text using textbbox
                bbox = draw.textbbox((0, 0), piece_symbol, font=piece_font)
                tw = bbox[2] - bbox[0]
                th = bbox[3] - bbox[1]
                tx = cx - tw / 2 - bbox[0]
                ty = cy - th / 2 - bbox[1]
                draw.text((tx, ty), piece_symbol, fill=piece_color, font=piece_font)

                file_idx += 1

    if output_path:
        img.save(output_path)

    return img


def render_board_to_file(fen: str, output_path: str) -> str:
    """
    Render board to file and return path.

    Args:
        fen: FEN string
        output_path: Path to save image

    Returns:
        Path to saved image
    """
    render_board(fen, output_path=output_path)
    return output_path
