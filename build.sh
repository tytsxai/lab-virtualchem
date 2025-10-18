#!/bin/bash
# VirtualChemLab 一键打包脚本 (Linux/macOS)
# 使用方法: chmod +x build.sh && ./build.sh

set -e

echo "================================================"
echo "VirtualChemLab 打包工具"
echo "================================================"
echo ""

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未找到Python3,请先安装Python 3.10+"
    exit 1
fi

echo "[1/5] 检查依赖..."
if ! pip show pyinstaller &> /dev/null; then
    echo "[提示] 正在安装PyInstaller..."
    pip install pyinstaller
fi

echo ""
echo "[2/5] 清理旧的构建文件..."
rm -rf build dist

echo ""
echo "[3/5] 开始打包..."
echo "这可能需要几分钟,请耐心等待..."
pyinstaller VirtualChemLab.spec

echo ""
echo "[4/5] 测试可执行文件..."
if [ ! -f "dist/VirtualChemLab/VirtualChemLab" ]; then
    echo "[错误] 未找到生成的可执行文件!"
    exit 1
fi

echo "[提示] 可执行文件已生成: dist/VirtualChemLab/VirtualChemLab"

echo ""
echo "[5/5] 创建发布包..."
cd dist
tar -czf ../VirtualChemLab_Release.tar.gz VirtualChemLab/
cd ..

echo ""
echo "================================================"
echo "打包完成!"
echo "================================================"
echo ""
echo "发布文件位置:"
echo "  - 文件夹: dist/VirtualChemLab/"
echo "  - 压缩包: VirtualChemLab_Release.tar.gz"
echo ""
echo "测试方法:"
echo "  ./dist/VirtualChemLab/VirtualChemLab"
echo ""




