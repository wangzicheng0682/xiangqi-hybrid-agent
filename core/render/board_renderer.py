"""
Chess Board Renderer for Xiangqi.

Reference:
  - PRD: Sprint 1 / 棋盘可视化
  - TECH: FEN解析与棋盘生成
"""

from PIL import Image, ImageDraw, ImageFont
from typing import Tuple


# Piece symbol mapping
PIECE_SYMBOLS = {
    # Red pieces (uppercase in FEN)
    'K': '帅',
    'A': '仕',
    'B': '相',  # Sometimes 'E' for Elephant
    'E': '相',
    'R': '車',
    'C': '炮',
    'H': '馬',
    'P': '兵',
    # Black pieces (lowercase in FEN)
    'k': '将',
    'a': '士',
    'b': '象',  # Sometimes 'e' for elephant
    'e': '象',
    'r': '車',
    'c': '炮',
    'h': '马',
    'p': '卒',
}


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
    # Create board image
    img = Image.new('RGB', (width, height), color='#F5DEB3')  # Wheat color
    draw = ImageDraw.Draw(img)

    # Calculate grid
    margin = 30
    board_width = width - 2 * margin
    board_height = height - 2 * margin
    cell_width = board_width // 8
    cell_height = board_height // 9

    # Draw grid lines
    # Vertical lines (9 files)
    for i in range(9):
        x = margin + i * cell_width
        draw.line([(x, margin), (x, margin + board_height)], fill='black', width=2)

    # Horizontal lines (10 ranks)
    for i in range(10):
        y = margin + i * cell_height
        draw.line([(margin, y), (margin + board_width, y)], fill='black', width=2)

    # Draw river (楚河汉界)
    river_y = margin + 4 * cell_height + cell_height // 2
    draw.rectangle(
        [(margin, margin + 4 * cell_height), (margin + board_width, margin + 5 * cell_height)],
        fill='#F5DEB3'
    )
    # Optional: add river text
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
    except:
        font = ImageFont.load_default()

    draw.text((margin + cell_width * 2, river_y - 10), "楚河", fill='black', font=font)
    draw.text((margin + cell_width * 5, river_y - 10), "汉界", fill='black', font=font)

    # Parse FEN and place pieces
    position = fen.split()[0]
    ranks = position.split('/')

    # Note: FEN ranks are from top (rank 10) to bottom (rank 1)
    # We draw from top to bottom
    for rank_idx, rank in enumerate(ranks):
        file_idx = 0
        y = margin + rank_idx * cell_height

        for char in rank:
            if char.isdigit():
                file_idx += int(char)
            else:
                # Place piece
                x = margin + file_idx * cell_width

                # Get piece symbol
                piece_symbol = PIECE_SYMBOLS.get(char, char)

                # Determine color
                color = 'red' if char.isupper() else 'black'

                # Draw piece circle
                radius = min(cell_width, cell_height) // 3
                draw.ellipse(
                    [(x - radius, y - radius), (x + radius, y + radius)],
                    fill='#FFE4B5',
                    outline=color,
                    width=2
                )

                # Draw piece text
                draw.text((x - 12, y - 12), piece_symbol, fill=color, font=font)

                file_idx += 1

    # Save if path provided
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
