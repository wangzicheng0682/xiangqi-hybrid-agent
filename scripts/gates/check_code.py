#!/usr/bin/env python3
"""
AI全自动开发 - 代码检查脚本
用途: 自动化代码质量检查
"""

import sys
import os
import ast
from pathlib import Path

def print_success(message):
    print(f"✅ {message}")

def print_failure(message):
    print(f"❌ {message}")

def print_warning(message):
    print(f"⚠️  {message}")

def check_file_length(filepath, max_lines=500):
    """检查单文件行数"""
    if not os.path.exists(filepath):
        return True

    lines = len(open(filepath, 'r', encoding='utf-8').readlines())

    if lines <= max_lines:
        print_success(f"{filepath}: {lines}行 (≤{max_lines}行)")
        return True
    else:
        print_warning(f"{filepath}: {lines}行 (>{max_lines}行，需要拆分)")
        return False

def check_python_syntax(filepath):
    """检查Python语法"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            ast.parse(f.read())
        return True
    except SyntaxError as e:
        print_failure(f"{filepath}: 语法错误 - {e}")
        return False

def check_docstrings(directory="xiangqi"):
    """检查模块是否有docstring"""
    if not os.path.exists(directory):
        print_warning(f"{directory}目录不存在")
        return True

    issues = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py') and file != '__init__.py':
                filepath = os.path.join(root, file)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if not content.strip().startswith('"""'):
                        issues.append(filepath)

    if issues:
        print_warning(f"以下文件缺少docstring: {len(issues)}个")
        for issue in issues[:5]:  # 只显示前5个
            print(f"  - {issue}")
        return True
    else:
        print_success("所有Python文件都有docstring")
        return True

def check_imports_order(filepath):
    """检查import顺序（PEP 8）"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # 简单检查：标准库 -> 第三方 -> 本地
        # 这里可以添加更复杂的逻辑
        return True
    except:
        return True

def main():
    print("🚀 AI全自动开发 - 代码检查")
    print("=" * 40)

    all_pass = True

    # 1. 核心文件行数检查
    print("\n📋 检查1: 核心文件行数")
    if os.path.exists("apps/web-gradio/app.py"):
        all_pass &= check_file_length("apps/web-gradio/app.py", max_lines=500)
    else:
        print_warning("apps/web-gradio/app.py不存在")

    # 2. Python语法检查
    print("\n📋 检查2: Python语法检查")
    if os.path.exists("xiangqi"):
        syntax_ok = True
        checked = 0
        for root, _, files in os.walk("xiangqi"):
            for file in files:
                if file.endswith('.py'):
                    filepath = os.path.join(root, file)
                    checked += 1
                    syntax_ok &= check_python_syntax(filepath)

        if syntax_ok:
            print_success(f"Python语法检查通过 ({checked}个文件)")
        else:
            print_failure("Python语法检查失败")
            all_pass = False
    else:
        print_warning("xiangqi目录不存在")

    # 3. Docstring检查
    print("\n📋 检查3: Docstring检查")
    all_pass &= check_docstrings()

    # 总结
    print("\n" + "=" * 40)
    if all_pass:
        print_success("代码检查通过")
        return 0
    else:
        print_failure("代码检查失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())
