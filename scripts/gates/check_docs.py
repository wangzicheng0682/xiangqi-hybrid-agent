#!/usr/bin/env python3
"""
AI全自动开发 - 文档检查脚本
用途: 自动化文档检查，确保文档同步
"""

import sys
import os
from pathlib import Path

def print_success(message):
    print(f"✅ {message}")

def print_failure(message):
    print(f"❌ {message}")

def print_warning(message):
    print(f"⚠️  {message}")

def check_file_exists(filepath, description):
    """检查文件是否存在"""
    if os.path.exists(filepath):
        print_success(f"{description}: 存在")
        return True
    else:
        print_failure(f"{description}: 不存在")
        return False

def check_file_min_size(filepath, max_size, description):
    """检查文件行数是否超过阈值"""
    if not os.path.exists(filepath):
        return True  # 文件不存在不算失败

    with open(filepath, 'r', encoding='utf-8') as f:
        lines = len(f.readlines())

    if lines <= max_size:
        print_success(f"{description}: {lines}行 (≤{max_size}行)")
        return True
    else:
        print_warning(f"{description}: {lines}行 (>{max_size}行，需要压缩)")
        return False

def check_sync_state_code():
    """检查STATE.md与代码是否同步"""
    # 检查是否有未记录的功能
    # 这里可以添加更复杂的逻辑
    print_success("STATE.md与代码同步检查: 跳过（需要人工验证）")
    return True

def check_traceability():
    """检查TRACEABILITY.md的完整性"""
    filepath = "docs/TRACEABILITY.md"
    if not os.path.exists(filepath):
        print_warning("TRACEABILITY.md不存在")
        return False

    # 检查是否有最近更新的记录
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 简单检查：是否有"今日"或最近的日期
    today_str = "2026-03-09"
    if today_str in content:
        print_success("TRACEABILITY.md有今日更新")
        return True
    else:
        print_warning("TRACEABILITY.md可能需要更新")
        return True  # 不算失败

def main():
    print("🚀 AI全自动开发 - 文档检查")
    print("=" * 40)

    all_pass = True

    # 1. 核心文档存在性检查
    print("\n📋 检查1: 核心文档存在性")
    all_pass &= check_file_exists("docs/STATE.md", "STATE.md")
    all_pass &= check_file_exists("docs/REQUIREMENTS.md", "REQUIREMENTS.md")
    all_pass &= check_file_exists("docs/ARCHITECTURE.md", "ARCHITECTURE.md")
    all_pass &= check_file_exists("docs/ROADMAP.md", "ROADMAP.md")

    # 2. 核心文档大小检查
    print("\n📋 检查2: 核心文档大小")
    all_pass &= check_file_min_size("docs/STATE.md", 200, "STATE.md")
    all_pass &= check_file_min_size("docs/REQUIREMENTS.md", 500, "REQUIREMENTS.md")
    all_pass &= check_file_min_size("docs/ARCHITECTURE.md", 300, "ARCHITECTURE.md")
    all_pass &= check_file_min_size("docs/ROADMAP.md", 200, "ROADMAP.md")

    # 3. 文档同步检查
    print("\n📋 检查3: 文档与代码同步")
    all_pass &= check_sync_state_code()
    all_pass &= check_traceability()

    # 总结
    print("\n" + "=" * 40)
    if all_pass:
        print_success("文档检查通过")
        return 0
    else:
        print_failure("文档检查失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())
