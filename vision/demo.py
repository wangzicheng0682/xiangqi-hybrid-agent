"""
模板比对法棋盘识别 - 演示脚本

演示完整流程：
1. 创建示例模板
2. 模拟YOLO检测结果
3. 测量新图外框
4. 识别棋盘
5. 输出FEN
"""

import sys
sys.path.insert(0, '.')

from core.vision.template_data import ChessTemplate, BoardBox, save_template
from core.vision.board_recognizer import BoardRecognizer
from core.vision.calibrate import create_example_template
from core.vision.fen_builder import verify_fen, count_pieces


def demo():
    print("=" * 60)
    print("中国象棋棋盘识别 - 模板比对法演示")
    print("=" * 60)

    # Step 1: 创建示例模板
    print("\n[Step 1] 创建示例模板")
    template = create_example_template()
    template_path = "templates/example_template.json"
    save_template(template, template_path)
    print(f"  模板已保存: {template_path}")
    print(f"  外框尺寸: {template.total_width} x {template.total_height}")
    print(f"  格点数量: 9×10={len(template.grid)*len(template.grid[0])}")

    # Step 2: 创建识别器
    print("\n[Step 2] 创建识别器")
    recognizer = BoardRecognizer(template_path=template_path)
    print(f"  模板: {recognizer.matcher.template.name}")

    # Step 3: 模拟YOLO检测结果
    # 标准开局：红方在下，黑方在上
    # 棋盘坐标：col 0~8(右→左), row 0~9(上→下)
    print("\n[Step 3] 模拟YOLO检测结果（标准开局）")
    yolo_results = [
        # 红方 (row=9)
        {"x": 100, "y": 1300, "category": "r_che", "confidence": 0.95},    # 最左车
        {"x": 225, "y": 1300, "category": "r_ma", "confidence": 0.95},     # 最左马
        {"x": 350, "y": 1300, "category": "r_xiang", "confidence": 0.95}, # 最左相
        {"x": 475, "y": 1300, "category": "r_shi", "confidence": 0.95},   # 最左仕
        {"x": 600, "y": 1300, "category": "r_shuai", "confidence": 0.95}, # 帅
        {"x": 725, "y": 1300, "category": "r_shi", "confidence": 0.95},    # 最右仕
        {"x": 850, "y": 1300, "category": "r_xiang", "confidence": 0.95},  # 最右相
        {"x": 975, "y": 1300, "category": "r_ma", "confidence": 0.95},     # 最右马
        {"x": 1100, "y": 1300, "category": "r_che", "confidence": 0.95},   # 最右车
        {"x": 200, "y": 1167, "category": "r_pao", "confidence": 0.95},     # 左炮
        {"x": 1000, "y": 1167, "category": "r_pao", "confidence": 0.95},    # 右炮
        # 红方兵 (row=6, 实际应该在 row=5, 但这里简化)
        {"x": 200, "y": 1033, "category": "r_bing", "confidence": 0.95},
        {"x": 400, "y": 1033, "category": "r_bing", "confidence": 0.95},
        {"x": 600, "y": 1033, "category": "r_bing", "confidence": 0.95},
        {"x": 800, "y": 1033, "category": "r_bing", "confidence": 0.95},
        {"x": 1000, "y": 1033, "category": "r_bing", "confidence": 0.95},

        # 黑方 (row=0)
        {"x": 100, "y": 100, "category": "b_che", "confidence": 0.95},     # 最左车
        {"x": 225, "y": 100, "category": "b_ma", "confidence": 0.95},       # 最左马
        {"x": 350, "y": 100, "category": "b_xiang", "confidence": 0.95},     # 最左象
        {"x": 475, "y": 100, "category": "b_shi", "confidence": 0.95},       # 最左士
        {"x": 600, "y": 100, "category": "b_jiang", "confidence": 0.95},    # 将
        {"x": 725, "y": 100, "category": "b_shi", "confidence": 0.95},     # 最右士
        {"x": 850, "y": 100, "category": "b_xiang", "confidence": 0.95},    # 最右象
        {"x": 975, "y": 100, "category": "b_ma", "confidence": 0.95},      # 最右马
        {"x": 1100, "y": 100, "category": "b_che", "confidence": 0.95},     # 最右车
        {"x": 200, "y": 233, "category": "b_pao", "confidence": 0.95},      # 左炮
        {"x": 1000, "y": 233, "category": "b_pao", "confidence": 0.95},    # 右炮
        # 黑方卒
        {"x": 200, "y": 367, "category": "b_zu", "confidence": 0.95},
        {"x": 400, "y": 367, "category": "b_zu", "confidence": 0.95},
        {"x": 600, "y": 367, "category": "b_zu", "confidence": 0.95},
        {"x": 800, "y": 367, "category": "b_zu", "confidence": 0.95},
        {"x": 1000, "y": 367, "category": "b_zu", "confidence": 0.95},
    ]
    print(f"  YOLO检测到 {len(yolo_results)} 个棋子")

    # Step 4: 测量新图外框（与模板相同尺寸）
    print("\n[Step 4] 测量新图外框4个角")
    new_box = BoardBox(
        tl=template.box.tl,
        tr=template.box.tr,
        bl=template.box.bl,
        br=template.box.br,
    )
    print(f"  tl: {new_box.tl}")
    print(f"  tr: {new_box.tr}")
    print(f"  bl: {new_box.bl}")
    print(f"  br: {new_box.br}")

    # Step 5: 识别
    print("\n[Step 5] 识别棋盘")
    result = recognizer.recognize(
        yolo_results=yolo_results,
        new_board_corners=new_box,
        side_to_move="w",
    )

    # Step 6: 输出结果
    print("\n" + "=" * 60)
    print("识别结果")
    print("=" * 60)
    print(f"FEN: {result.fen}")
    print(f"验证: {' ' if result.verified else ' '}")
    print(f"棋子数: {result.pieces_count}")
    print(f"置信度: {result.confidence:.2f}")
    print(f"描述: {result.description}")

    # 展示部分匹配结果
    print("\n部分棋子匹配结果:")
    for p in result.pieces[:5]:
        print(f"  {p.category} -> ({p.col},{p.row}) {p.fen_char}")

    # 验证FEN
    print("\n" + "-" * 60)
    if verify_fen(result.fen):
        print(" FEN格式验证")
    else:
        print(" FEN格式验证")

    print(f"\n预期标准开局:")
    print("rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1")


if __name__ == "__main__":
    import os
    os.makedirs("templates", exist_ok=True)
    demo()