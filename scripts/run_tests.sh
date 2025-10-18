#!/bin/bash
# 运行测试脚本

set -e

echo "========================================="
echo "VirtualChemLab 测试套件"
echo "========================================="
echo ""

# 激活虚拟环境(如果存在)
if [ -d "venv" ]; then
    echo "激活虚拟环境..."
    source venv/bin/activate
fi

# 运行代码检查
echo "1. 运行代码检查(ruff)..."
ruff check src/ tests/ || true
echo ""

# 运行类型检查
echo "2. 运行类型检查(mypy)..."
mypy src/ || true
echo ""

# 运行单元测试
echo "3. 运行单元测试(pytest)..."
pytest tests/ -v --cov=src --cov-report=html --cov-report=term
echo ""

# 生成测试报告
echo "========================================="
echo "测试完成!"
echo "HTML覆盖率报告: htmlcov/index.html"
echo "========================================="




