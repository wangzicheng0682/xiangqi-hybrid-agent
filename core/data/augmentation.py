"""
数据增强模块
实现视角归一、左右镜像等数据增强策略
"""

from typing import Tuple, Optional
import re


def normalize_perspective(fen: str) -> str:
    """
    视角归一化
    
    将"黑方行棋"的FEN做180°旋转+红黑交换，
    让模型始终在「我方=行棋方」坐标系学习
    
    Args:
        fen: 原始FEN
        
    Returns:
        str: 归一化后的FEN
    """
    parts = fen.split()
    if len(parts) < 2:
        return fen
    
    # 判断当前行棋方
    side = parts[1]
    
    if side == 'w':  # 红方行棋，无需转换
        return fen
    
    # 黑方行棋，需要转换
    # 1. 旋转棋盘180°
    # 2. 交换红黑棋子
    
    board = parts[0]
    rows = board.split('/')
    
    # 反转行顺序（180°旋转）
    rows = rows[::-1]
    
    # 交换红黑棋子并反转每行
    new_rows = []
    for row in rows:
        new_row = swap_colors(row)[::-1]
        new_rows.append(new_row)
    
    # 组装新FEN
    new_board = '/'.join(new_rows)
    new_fen = f"{new_board} w"
    
    # 保留其他部分
    if len(parts) >= 3:
        new_fen += f" {parts[2]}"  # 王车易位（中国象棋通常为空）
    if len(parts) >= 4:
        new_fen += f" {parts[3]}"  # 吃过路兵（中国象棋通常为空）
    if len(parts) >= 5:
        new_fen += f" {parts[4]}"  # 半回合计数
    if len(parts) >= 6:
        new_fen += f" {parts[5]}"  # 全回合计数
    
    return new_fen


def swap_colors(piece_str: str) -> str:
    """
    交换红黑棋子
    
    大写（红方）↔ 小写（黑方）
    """
    result = []
    for char in piece_str:
        if char.isalpha():
            if char.isupper():
                result.append(char.lower())
            else:
                result.append(char.upper())
        else:
            result.append(char)
    return ''.join(result)


def mirror_horizontal(fen: str) -> str:
    """
    左右镜像
    
    交换棋盘左右翼，用于提升模型泛化
    
    Args:
        fen: 原始FEN
        
    Returns:
        str: 镜像后的FEN
    """
    parts = fen.split()
    board = parts[0]
    rows = board.split('/')
    
    # 每行左右反转
    new_rows = []
    for row in rows:
        # 需要正确处理数字（连续空位）
        new_row = reverse_row(row)
        new_rows.append(new_row)
    
    # 组装新FEN
    new_board = '/'.join(new_rows)
    new_fen = new_board
    
    # 保留其他部分
    for i in range(1, len(parts)):
        new_fen += f" {parts[i]}"
    
    return new_fen


def reverse_row(row: str) -> str:
    """
    反转单行（左右镜像）
    
    需要正确处理数字表示的连续空位
    """
    # 将行展开为9个格子
    expanded = []
    for char in row:
        if char.isdigit():
            expanded.extend(['.'] * int(char))
        else:
            expanded.append(char)
    
    # 反转
    expanded = expanded[::-1]
    
    # 压缩回FEN格式
    compressed = []
    empty_count = 0
    
    for char in expanded:
        if char == '.':
            empty_count += 1
        else:
            if empty_count > 0:
                compressed.append(str(empty_count))
                empty_count = 0
            compressed.append(char)
    
    if empty_count > 0:
        compressed.append(str(empty_count))
    
    return ''.join(compressed)


def augment_position(fen: str, augmentations: list = None) -> list:
    """
    对局面进行数据增强
    
    Args:
        fen: 原始FEN
        augmentations: 增强操作列表 ['normalize', 'mirror']
        
    Returns:
        list: 增强后的FEN列表
    """
    if augmentations is None:
        augmentations = ['normalize']
    
    results = [fen]  # 原始局面
    
    for aug in augmentations:
        if aug == 'normalize':
            normalized = normalize_perspective(fen)
            if normalized != fen:
                results.append(normalized)
        
        elif aug == 'mirror':
            mirrored = mirror_horizontal(fen)
            if mirrored != fen:
                results.append(mirrored)
        
        elif aug == 'both':
            # 先归一化，再镜像
            normalized = normalize_perspective(fen)
            if normalized != fen:
                results.append(normalized)
                mirrored_normalized = mirror_horizontal(normalized)
                results.append(mirrored_normalized)
            
            # 先镜像，再归一化
            mirrored = mirror_horizontal(fen)
            if mirrored != fen:
                results.append(mirrored)
                normalized_mirrored = normalize_perspective(mirrored)
                if normalized_mirrored != mirrored:
                    results.append(normalized_mirrored)
    
    return list(set(results))  # 去重


def coord_transform(coord: Tuple[int, int], transform_type: str, side: str = 'red') -> Tuple[int, int]:
    """
    坐标变换
    
    Args:
        coord: (x, y) 坐标，x为1-9列，y为1-10行
        transform_type: 变换类型 'normalize', 'mirror'
        side: 当前行棋方 'red' 或 'black'
        
    Returns:
        Tuple[int, int]: 变换后的坐标
    """
    x, y = coord
    
    if transform_type == 'normalize':
        # 视角归一化：黑方视角需要180°旋转
        if side == 'black':
            x = 10 - x
            y = 11 - y
    
    elif transform_type == 'mirror':
        # 左右镜像
        x = 10 - x
    
    return (x, y)


def move_transform(move: str, transform_type: str) -> str:
    """
    走法变换（配合坐标变换）
    
    Args:
        move: 原始走法（中国象棋记谱法）
        transform_type: 变换类型
        
    Returns:
        str: 变换后的走法
    """
    # TODO: 实现走法变换
    # 需要根据具体记谱法规则进行转换
    return move


if __name__ == "__main__":
    # 测试
    test_fen = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"
    
    print("原始FEN:")
    print(test_fen)
    
    print("\n左右镜像:")
    mirrored = mirror_horizontal(test_fen)
    print(mirrored)
    
    # 测试黑方行棋
    black_fen = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR b - - 0 1"
    print("\n黑方行棋FEN:")
    print(black_fen)
    
    print("\n视角归一化:")
    normalized = normalize_perspective(black_fen)
    print(normalized)
    
    print("\n数据增强（all）:")
    augmented = augment_position(test_fen, ['normalize', 'mirror', 'both'])
    for i, fen in enumerate(augmented):
        print(f"  {i}: {fen}")
