#!/bin/bash
# AI全自动开发 - 质量门禁检查脚本
# 用途: 自动化质量检查，AI无需人工判断
# 使用: scripts/gates/check.sh

set -e  # 遇到错误立即退出

echo "🚀 AI全自动开发 - 质量门禁检查"
echo "=================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 函数: 打印成功
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

# 函数: 打印失败
print_failure() {
    echo -e "${RED}❌ $1${NC}"
}

# 函数: 打印警告
print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# 函数: 打印章节
print_section() {
    echo ""
    echo "📋 $1"
    echo "--------------------------------"
}

# ============================================================================
# 门禁1: 测试检查
# ============================================================================
print_section "门禁1: 测试检查"

if python -m pytest tests/ -q --tb=short; then
    print_success "pytest测试通过"
else
    print_failure "pytest测试失败"
    echo ""
    echo "❌ 门禁不通过！请修复测试后重试。"
    exit 1
fi

# ============================================================================
# 门禁2: 类型检查（可选，不强制）
# ============================================================================
print_section "门禁2: 类型检查（mypy）"

if command -v mypy &> /dev/null; then
    if mypy xiangqi/ --ignore-missing-imports; then
        print_success "mypy类型检查通过"
    else
        print_warning "mypy类型检查有警告（非强制）"
    fi
else
    print_warning "mypy未安装，跳过类型检查"
fi

# ============================================================================
# 门禁3: 代码格式检查（可选，不强制）
# ============================================================================
print_section "门禁3: 代码格式检查（black）"

if command -v black &> /dev/null; then
    if black --check xiangqi/ --diff; then
        print_success "black代码格式检查通过"
    else
        print_warning "black代码格式检查未通过（非强制）"
        echo "   运行 'black xiangqi/' 格式化代码"
    fi
else
    print_warning "black未安装，跳过格式检查"
fi

# ============================================================================
# 门禁4: 文档检查
# ============================================================================
print_section "门禁4: 文档检查"

if python scripts/gates/check_docs.py; then
    print_success "文档检查通过"
else
    print_failure "文档检查失败"
    echo ""
    echo "❌ 门禁不通过！请更新文档后重试。"
    exit 1
fi

# ============================================================================
# 门禁5: 代码复杂度检查（可选）
# ============================================================================
print_section "门禁5: 代码复杂度检查（radon）"

if command -v radon &> /dev/null; then
    COMPLEXITY=$(radon cc xiangqi/ -a | tail -1)
    print_success "平均复杂度: $COMPLEXITY"

    # 检查是否有超过阈值的文件
    if radon cc xiangqi/ -nb | grep -q "C"; then
        print_warning "发现复杂度较高的模块（非强制）"
    else
        print_success "所有模块复杂度合理"
    fi
else
    print_warning "radon未安装，跳过复杂度检查"
fi

# ============================================================================
# 门禁6: 单文件大小检查
# ============================================================================
print_section "门禁6: 单文件大小检查"

MAX_LINES=500
VIOLATIONS=$(find xiangqi/ -name "*.py" -exec wc -l {} + | awk -v max=$MAX_LINES '$1 > max {print $1, $2}')

if [ -z "$VIOLATIONS" ]; then
    print_success "所有Python文件行数合理（<$MAX_LINES行）"
else
    print_warning "以下文件超过${MAX_LINES}行，建议拆分："
    echo "$VIOLATIONS"
fi

# ============================================================================
# 总结
# ============================================================================
print_section "门禁检查总结"

echo -e "${GREEN}✅ 所有强制门禁通过！${NC}"
echo ""
echo "📊 检查结果汇总:"
echo "  ✅ pytest测试: 通过"
echo "  ⚠️  mypy类型检查: 非强制"
echo "  ⚠️  black格式检查: 非强制"
echo "  ✅ 文档检查: 通过"
echo "  ⚠️  代码复杂度: 非强制"
echo "  ⚠️  单文件大小: 非强制"
echo ""
echo -e "${GREEN}🎉 可以提交代码！${NC}"
