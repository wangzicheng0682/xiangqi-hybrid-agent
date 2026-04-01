#!/usr/bin/env python3
"""
文档格式检查脚本

检查docs目录下的Markdown文档是否满足格式规范。

用法:
    python scripts/check_docs.py [--fix]
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple

# 文档目录
DOCS_DIR = Path(__file__).parent.parent / "docs"

# 必须包含frontmatter的文档类型
REQUIRED_FRONTMATTER_TYPES = ["dna", "state", "reference", "guide", "plan"]

# Frontmatter模板
FRONTMATTER_TEMPLATE = """---
name: {name}
type: [{types}]
version: {version}
date: {date}
owner: AI（自动维护）
changelog:
  - v{version} ({date}): {change}
---

"""


def check_frontmatter(doc_path: Path) -> List[str]:
    """检查文档是否包含正确的frontmatter"""
    errors = []

    content = doc_path.read_text(encoding="utf-8")

    # 检查是否有frontmatter
    if not content.startswith("---"):
        errors.append(f"缺少frontmatter: {doc_path.relative_to(DOCS_DIR)}")
        return errors

    # 提取frontmatter
    lines = content.split("\n")
    end_idx = -1
    for i, line in enumerate(lines[1:], 1):
        if line.strip() == "---":
            end_idx = i
            break

    if end_idx == -1:
        errors.append(f"frontmatter未正确闭合: {doc_path.relative_to(DOCS_DIR)}")
        return errors

    frontmatter_lines = lines[1:end_idx]
    frontmatter = {}
    for line in frontmatter_lines:
        if ":" in line:
            key, value = line.split(":", 1)
            frontmatter[key.strip()] = value.strip()

    # 检查必需字段
    required_fields = ["name", "type", "version", "date"]
    for field in required_fields:
        if field not in frontmatter:
            errors.append(f"缺少字段 '{field}': {doc_path.relative_to(DOCS_DIR)}")

    # 检查type是否有效
    if "type" in frontmatter:
        doc_type = frontmatter["type"].strip("[]")
        if doc_type not in REQUIRED_FRONTMATTER_TYPES:
            errors.append(f"无效的type '{doc_type}': {doc_path.relative_to(DOCS_DIR)}")

    return errors


def check_dead_links(doc_path: Path) -> List[str]:
    """检查文档中的链接是否有效"""
    errors = []

    content = doc_path.read_text(encoding="utf-8")

    # 匹配markdown链接
    link_pattern = r"\[([^\]]+)\]\(([^\)]+)\)"
    links = re.findall(link_pattern, content)

    doc_dir = doc_path.parent

    for _, link in links:
        # 跳过外部链接
        if link.startswith("http") or link.startswith("//"):
            continue

        # 跳过锚点
        if link.startswith("#"):
            continue

        # 解析相对路径
        link_path = (doc_dir / link).resolve()
        if not link_path.exists():
            # 尝试添加.md后缀
            if not link.endswith(".md"):
                link_path = (doc_dir / (link + ".md")).resolve()

            if not link_path.exists():
                errors.append(f"死链接: {link} -> {doc_path.relative_to(DOCS_DIR)}")

    return errors


def check_docs(docs_dir: Path) -> Tuple[int, int]:
    """检查所有文档"""
    total = 0
    errors_found = []

    for md_file in docs_dir.rglob("*.md"):
        # 跳过_archived目录中的检查（这些是旧文档）
        if "_archived" in md_file.parts:
            continue

        total += 1

        # 只检查guides和plans目录中的文档必须有frontmatter
        if "guides" in md_file.parts or "plans" in md_file.parts:
            # 检查frontmatter
            errors_found.extend(check_frontmatter(md_file))

        # 检查死链接
        errors_found.extend(check_dead_links(md_file))

    return total, errors_found


def main():
    """主函数"""
    fix = "--fix" in sys.argv

    print("检查文档格式...")
    print(f"文档目录: {DOCS_DIR}")
    print()

    total, errors = check_docs(DOCS_DIR)

    print(f"检查了 {total} 个文档")

    if errors:
        print(f"\n[ERROR] Found {len(errors)} issues:")
        for error in errors:
            print(f"  - {error}")
        return 1
    else:
        print("\n[PASS] All checks passed!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
