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

# 选择Python（优先使用 3.12/3.11/3.10，避免系统默认 python3 漂移到过新版本）
PYTHON_BIN="${PYTHON_BIN:-}"
if [ -z "$PYTHON_BIN" ]; then
    for candidate in python3.12 python3.11 python3.10 python3; do
        if command -v "$candidate" >/dev/null 2>&1; then
            PYTHON_BIN="$candidate"
            break
        fi
    done
fi

if [ -z "$PYTHON_BIN" ]; then
    echo "[错误] 未找到Python3,请先安装Python 3.10+"
    exit 1
fi

PYTHON_VERSION=$("$PYTHON_BIN" --version 2>&1)
echo "Python环境: ${PYTHON_VERSION}"

"$PYTHON_BIN" - <<'PY'
import sys

if sys.version_info < (3, 10):
    raise SystemExit("Python 版本过低，要求 Python 3.10+")
PY

cd "$SCRIPT_DIR"

VERSION=$(SCRIPT_DIR="$SCRIPT_DIR" "$PYTHON_BIN" - <<'PY'
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
"$PYTHON_BIN" -m pip install --upgrade pip
"$PYTHON_BIN" -m pip install --require-hashes -r "${SCRIPT_DIR}/requirements.lock"
"$PYTHON_BIN" -m pip install "pyinstaller==${PYINSTALLER_VERSION}"

echo ""
echo "[2/6] 清理旧的构建文件..."
rm -rf build dist

echo ""
echo "[3/6] 开始打包..."
echo "这可能需要几分钟,请耐心等待..."

"$PYTHON_BIN" -m PyInstaller --clean --noconfirm "${SCRIPT_DIR}/VirtualChemLab.spec"

echo ""
echo "[4/6] 测试可执行文件..."
if [ "$(uname -s)" = "Darwin" ]; then
    if [ ! -d "dist/${APP_NAME}.app" ]; then
        echo "[错误] 未找到生成的应用程序: dist/${APP_NAME}.app"
        exit 1
    fi
    echo "[提示] 应用程序已生成: dist/${APP_NAME}.app"
else
    if [ ! -f "dist/${APP_NAME}/${APP_NAME}" ]; then
        echo "[错误] 未找到生成的可执行文件!"
        exit 1
    fi
    echo "[提示] 可执行文件已生成: dist/${APP_NAME}/${APP_NAME}"
fi

echo ""
echo "[5/6] 创建发布包..."
ARCHIVE_NAME="${APP_NAME}_Release_v${VERSION}.tar.gz"
cd dist
if [ "$(uname -s)" = "Darwin" ]; then
    tar -czf "../${ARCHIVE_NAME}" "${APP_NAME}.app"
else
    tar -czf "../${ARCHIVE_NAME}" "${APP_NAME}/"
fi
cd ..

echo ""
echo "================================================"
echo "打包完成!"
echo "================================================"
echo ""
echo "发布文件位置:"
if [ "$(uname -s)" = "Darwin" ]; then
    echo "  - 应用程序: dist/VirtualChemLab.app"
else
    echo "  - 文件夹: dist/VirtualChemLab/"
fi
echo "  - 压缩包: ${ARCHIVE_NAME}"
echo ""
echo "测试方法:"
if [ "$(uname -s)" = "Darwin" ]; then
    echo "  open \"./dist/VirtualChemLab.app\""
else
    echo "  ./dist/VirtualChemLab/VirtualChemLab"
fi
echo ""
