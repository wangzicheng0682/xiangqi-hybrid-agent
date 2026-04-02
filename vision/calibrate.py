"""
Template Calibration Tool - 模板标定工具

用途：一次性测量棋盘模板的90个格点坐标，保存为JSON，永久复用

使用方法:
    # 方式1: 命令行交互标定
    python -m core.vision.calibrate --input board.jpg --output templates/my_board.json

    # 方式2: GUI可视化标定（推荐）
    python -m core.vision.calibrate --gui --input board.jpg --output templates/my_board.json

    # 方式3: 批量标注（已知外框角点）
    python -m core.vision.calibrate --input board.jpg --output templates/my_board.json
           --box-tl 100 100 --box-tr 1000 100 --box-bl 100 900 --box-br 1000 900

标定流程:
    Step 1: 测量外框4个角（带留白的最外围4个角）
    Step 2: 依次点击90个格点（从最右上角开始，从右往左、从上往下）
    Step 3: 保存模板JSON
"""

import os
import sys
import json
import argparse
from pathlib import Path

# 尝试导入GUI库
try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

from .template_data import ChessTemplate, BoardBox


def parse_box_args(args) -> BoardBox:
    """从命令行参数解析外框角点"""
    return BoardBox(
        tl=(int(args.box_tl[0]), int(args.box_tl[1])),
        tr=(int(args.box_tr[0]), int(args.box_tr[1])),
        bl=(int(args.box_bl[0]), int(args.box_bl[1])),
        br=(int(args.box_br[0]), int(args.box_br[1])),
    )


def compute_template_size(box: BoardBox):
    """根据外框计算模板尺寸"""
    width = max(box.tr[0], box.br[0]) - min(box.tl[0], box.bl[0])
    height = max(box.bl[1], box.br[1]) - min(box.tl[1], box.tr[1])
    return width, height


def create_template_from_measurements(name: str, box: BoardBox,
                                       measurements: list) -> ChessTemplate:
    """
    根据测量数据创建模板
    measurements: 90个格点坐标的扁平列表，顺序为：
                  先从右往左(col 8→0)，每列从上往下(row 0→9)
                  总计 9×10=90 个坐标
    """
    width, height = compute_template_size(box)

    # 构建grid: grid[col][row] = (x, y)
    # measurements顺序: 先col=8从上到下，再col=7从上到下，...，最后col=0从上到下
    grid = [[None for _ in range(10)] for _ in range(9)]

    idx = 0
    for col in range(9):  # col 0~8
        for row in range(10):  # row 0~9
            if idx < len(measurements):
                grid[col][row] = (int(measurements[idx][0]), int(measurements[idx][1]))
            idx += 1

    return ChessTemplate(
        name=name,
        total_width=width,
        total_height=height,
        box=box,
        grid=grid,
        scale_ref=1.0,
    )


def simple_cli_calibrate(input_path: str, output_path: str):
    """
    简单的命令行标定流程
    用户手动输入90个格点坐标
    """
    print(f"\n{'='*60}")
    print("中国象棋棋盘模板标定工具")
    print(f"{'='*60}")
    print(f"\n读取图片: {input_path}")
    print("\n标定说明:")
    print("  - 先测量外框4个角（带留白的最外围4个角）")
    print("  - 再依次测量90个格点坐标")
    print("  - 顺序: 从最右上角开始，从右往左(col 8→0)，每列从上往下(row 0→9)")
    print("  - 建议用 https://pixspy.com/ 查看像素坐标\n")

    # 测量外框4个角
    print("=" * 60)
    print("Step 1: 测量外框4个角")
    print("=" * 60)
    box_tl = _input_point("左上角 (W_TL)")
    box_tr = _input_point("右上角 (W_TR)")
    box_bl = _input_point("左下角 (W_BL)")
    box_br = _input_point("右下角 (W_BR)")
    box = BoardBox(tl=box_tl, tr=box_tr, bl=box_bl, br=box_br)

    width, height = compute_template_size(box)
    print(f"\n外框尺寸: {width} x {height}")

    # 测量90个格点
    print("\n" + "=" * 60)
    print("Step 2: 测量90个格点坐标")
    print("顺序: col 8→0，每列 row 0→9")
    print("=" * 60)

    measurements = []
    for col in range(9):
        for row in range(10):
            prompt = f"  格点 [{col},{row}] (col={8-col}/9, row={row}/10): "
            point = _input_point(prompt)
            measurements.append(point)

            # 每10个点显示进度
            if (col * 10 + row + 1) % 10 == 0:
                print(f"    已完成 {col*10+row+1}/90")

    # 创建模板
    name = Path(input_path).stem
    template = create_template_from_measurements(name, box, measurements)

    # 保存
    from .template_data import save_template
    save_template(template, output_path)
    print(f"\n✅ 模板已保存: {output_path}")

    # 验证
    print(f"\n验证信息:")
    print(f"  - 外框尺寸: {template.total_width} x {template.total_height}")
    print(f"  - 格点数量: {len(template.grid) * len(template.grid[0])}")
    print(f"  - 右上格点 grid[8][0]: {template.grid[8][0]}")
    print(f"  - 左下格点 grid[0][9]: {template.grid[0][9]}")
    print(f"  - 红方帅位置 grid[4][9]: {template.grid[4][9]}")

    return template


def _input_point(prompt: str) -> tuple:
    """交互式输入坐标"""
    while True:
        try:
            s = input(prompt + " (x,y): ").strip()
            if not s:
                print("  请输入坐标，如: 500 300")
                continue
            parts = s.replace(',', ' ').split()
            if len(parts) >= 2:
                return (int(parts[0]), int(parts[1]))
            print("  格式错误，请输入: x y 或 x,y")
        except (ValueError, EOFError):
            print("  输入错误，请重试")


def create_example_template() -> ChessTemplate:
    """
    创建一个示例模板（用于测试）
    假设棋盘图片 1200×1300 像素，外框占满画面
    """
    # 外框4个角
    box = BoardBox(tl=(50, 50), tr=(1150, 50), bl=(50, 1250), br=(1150, 1250))
    width, height = compute_template_size(box)  # 1100, 1200

    # 估算90个格点位置（9列×10行均匀分布）
    # 列间距: 1100/8 = 137.5
    # 行间距: 1200/9 = 133.3
    grid = [[None for _ in range(10)] for _ in range(9)]

    col_spacing = width / 8  # 137.5
    row_spacing = height / 9  # 133.3

    for col in range(9):
        for row in range(10):
            x = int(box.tl[0] + col * col_spacing)
            y = int(box.tl[1] + row * row_spacing)
            grid[col][row] = (x, y)

    return ChessTemplate(
        name="example_1200x1300",
        total_width=width,
        total_height=height,
        box=box,
        grid=grid,
        scale_ref=1.0,
    )


def main():
    parser = argparse.ArgumentParser(
        description="中国象棋棋盘模板标定工具 - 测量90个格点坐标，永久复用"
    )
    parser.add_argument("--input", "-i", help="输入棋盘图片路径")
    parser.add_argument("--output", "-o", help="输出模板JSON路径")
    parser.add_argument("--gui", "-g", action="store_true", help="启用GUI可视化标定")
    parser.add_argument("--box-tl", nargs=2, help="外框左上角坐标")
    parser.add_argument("--box-tr", nargs=2, help="外框右上角坐标")
    parser.add_argument("--box-bl", nargs=2, help="外框左下角坐标")
    parser.add_argument("--box-br", nargs=2, help="外框右下角坐标")
    parser.add_argument("--name", "-n", default="my_template", help="模板名称")
    parser.add_argument("--generate-example", action="store_true", help="生成示例模板")

    args = parser.parse_args()

    if args.generate_example:
        from .template_data import save_template
        template = create_example_template()
        output = args.output or "templates/example_template.json"
        save_template(template, output)
        print(f"✅ 示例模板已生成: {output}")
        return

    if args.input:
        if args.output:
            simple_cli_calibrate(args.input, args.output)
        else:
            print("错误: 需要指定 --output 参数")
            parser.print_help()
    else:
        parser.print_help()
        print("\n示例:")
        print("  python -m core.vision.calibrate -i board.jpg -o templates/my_board.json")
        print("  python -m core.vision.calibrate --generate-example -o templates/example.json")


if __name__ == "__main__":
    main()