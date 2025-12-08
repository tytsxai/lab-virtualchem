#!/bin/bash
# VirtualChemLab 一键打包脚本 (Linux/macOS)
# 使用方法: chmod +x build.sh && ./build.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_NAME="VirtualChemLab"
ENTRY_SCRIPT="main.py"
PYINSTALLER_VERSION="6.3.0"

echo "================================================"
echo "VirtualChemLab 打包工具"
echo "================================================"
echo ""

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未找到Python3,请先安装Python 3.10+"
    exit 1
fi

cd "$SCRIPT_DIR"

VERSION=$(SCRIPT_DIR="$SCRIPT_DIR" python3 - <<'PY'
import os
import sys
from pathlib import Path

root = Path(os.environ["SCRIPT_DIR"])
sys.path.insert(0, str(root))
sys.path.insert(0, str(root / "src"))

from src import __version__  # noqa: E402

print(__version__)
PY
)

echo "版本: v${VERSION}"

if [ ! -f "${SCRIPT_DIR}/requirements.lock" ]; then
    echo "[错误] 未找到 requirements.lock，无法按锁文件安装依赖"
    exit 1
fi

echo "[1/6] 安装依赖（锁定版本）..."
python3 -m pip install --upgrade pip
python3 -m pip install --require-hashes -r "${SCRIPT_DIR}/requirements.lock"
python3 -m pip install "pyinstaller==${PYINSTALLER_VERSION}"

echo ""
echo "[2/6] 清理旧的构建文件..."
rm -rf build dist "${APP_NAME}.spec"

echo ""
echo "[3/6] 开始打包..."
echo "这可能需要几分钟,请耐心等待..."

ICON_FLAG=()
if [ -f "${SCRIPT_DIR}/assets/icons/app.ico" ]; then
    ICON_FLAG=(--icon="${SCRIPT_DIR}/assets/icons/app.ico")
fi

pyinstaller \
    --name="${APP_NAME}" \
    --windowed \
    --onedir \
    --clean \
    --noconfirm \
    --paths "${SCRIPT_DIR}" \
    --paths "${SCRIPT_DIR}/src" \
    "${ICON_FLAG[@]}" \
    --add-data "${SCRIPT_DIR}/assets:assets" \
    --add-data "${SCRIPT_DIR}/config:config" \
    --add-data "${SCRIPT_DIR}/config.json:." \
    --hidden-import=PySide6.QtCore \
    --hidden-import=PySide6.QtGui \
    --hidden-import=PySide6.QtWidgets \
    --hidden-import=pymunk \
    --hidden-import=numba \
    --hidden-import=sqlalchemy \
    --exclude-module=matplotlib \
    --exclude-module=pandas \
    --exclude-module=pytest \
    "${SCRIPT_DIR}/${ENTRY_SCRIPT}"

echo ""
echo "[4/6] 测试可执行文件..."
if [ ! -f "dist/${APP_NAME}/${APP_NAME}" ]; then
    echo "[错误] 未找到生成的可执行文件!"
    exit 1
fi

echo "[提示] 可执行文件已生成: dist/${APP_NAME}/${APP_NAME}"

echo ""
echo "[5/6] 创建发布包..."
ARCHIVE_NAME="${APP_NAME}_Release_v${VERSION}.tar.gz"
cd dist
tar -czf "../${ARCHIVE_NAME}" "${APP_NAME}/"
cd ..

echo ""
echo "================================================"
echo "打包完成!"
echo "================================================"
echo ""
echo "发布文件位置:"
echo "  - 文件夹: dist/VirtualChemLab/"
echo "  - 压缩包: ${ARCHIVE_NAME}"
echo ""
echo "测试方法:"
echo "  ./dist/VirtualChemLab/VirtualChemLab"
echo ""

