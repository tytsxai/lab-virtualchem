#!/bin/bash
# ============================================================================
# VirtualChemLab macOS 自动化打包脚本
# 版本: 自动读取 src/__init__.py
# ============================================================================

set -e  # 遇到错误立即退出

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 版本配置
VERSION="unknown"
APP_NAME="VirtualChemLab"
BUNDLE_ID="com.virtualchemlab.app"
ENTRY_SCRIPT="main.py"
PYINSTALLER_VERSION="6.3.0"

# ============================================================================
# 辅助函数
# ============================================================================

print_header() {
    echo ""
    echo "========================================"
    echo "  $1"
    echo "========================================"
    echo ""
}

print_step() {
    echo -e "${BLUE}[$1]${NC} $2"
}

print_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[⚠]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# ============================================================================
# 步骤 1/9: 环境检查
# ============================================================================
print_step "1/9" "检查Python环境..."

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
    print_error "未找到Python 3！请先安装Python 3.10+"
    exit 1
fi

PYTHON_VERSION=$("$PYTHON_BIN" --version 2>&1)
print_success "Python环境: ${PYTHON_VERSION}"

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
print_success "应用版本: ${VERSION}"
print_header "VirtualChemLab macOS 打包工具 v${VERSION}"

# ============================================================================
# 步骤 2/9: 依赖安装（锁定版本）
# ============================================================================
print_step "2/9" "安装项目依赖..."

if [ ! -f "${SCRIPT_DIR}/requirements.lock" ]; then
    print_error "未找到 requirements.lock，无法按锁文件安装依赖"
    exit 1
fi

"$PYTHON_BIN" -m pip install --upgrade pip
"$PYTHON_BIN" -m pip install --require-hashes -r "${SCRIPT_DIR}/requirements.lock"
"$PYTHON_BIN" -m pip install "pyinstaller==${PYINSTALLER_VERSION}"
print_success "依赖安装完成（基于锁文件）"

# ============================================================================
# 步骤 3/9: 清理旧构建
# ============================================================================
print_step "3/9" "清理旧构建文件..."

if [ -d "build" ]; then
    print_warning "删除 build 目录..."
    rm -rf build
fi

if [ -d "dist" ]; then
    print_warning "删除 dist 目录..."
    rm -rf dist
fi

print_success "清理完成"

# ============================================================================
# 步骤 4/9: 检查图标文件
# ============================================================================
print_step "4/9" "检查应用图标..."

ICON_DIR="assets/icons"
ICON_FILE="${ICON_DIR}/app.icns"

if [ ! -d "${ICON_DIR}" ]; then
    mkdir -p "${ICON_DIR}"
fi

ICON_FLAG=()
if [ -f "${ICON_FILE}" ]; then
    ICON_FLAG=(--icon="${ICON_FILE}")
    print_success "找到应用图标: ${ICON_FILE}"
else
    print_warning "未找到 app.icns，将使用默认图标"
    print_warning "提示：可以使用以下命令创建图标："
    print_warning "  iconutil -c icns icon.iconset"
fi

# ============================================================================
# 步骤 5/9: 创建权限配置文件
# ============================================================================
print_step "5/9" "创建macOS权限配置..."

cat > entitlements.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>com.apple.security.cs.allow-jit</key>
    <true/>
    <key>com.apple.security.cs.allow-unsigned-executable-memory</key>
    <true/>
    <key>com.apple.security.cs.disable-library-validation</key>
    <true/>
    <key>com.apple.security.network.client</key>
    <true/>
    <key>com.apple.security.network.server</key>
    <true/>
    <key>com.apple.security.files.user-selected.read-write</key>
    <true/>
</dict>
</plist>
EOF

print_success "权限配置文件已创建"

# ============================================================================
# 步骤 6/9: 运行PyInstaller
# ============================================================================
print_step "6/9" "开始打包应用（这可能需要几分钟）..."

PYINSTALLER_CMD=(
    "$PYTHON_BIN"
    -m
    PyInstaller
    --clean
    --noconfirm
    "${SCRIPT_DIR}/VirtualChemLab.spec"
)

print_warning "使用 VirtualChemLab.spec 打包..."
"${PYINSTALLER_CMD[@]}"

if [ $? -ne 0 ]; then
    print_error "打包失败！请检查错误信息"
    exit 1
fi

if [ ! -d "dist/${APP_NAME}.app" ]; then
    print_error "未找到打包输出 dist/${APP_NAME}.app"
    exit 1
fi

print_success "打包完成"

# ============================================================================
# 步骤 7/9: 代码签名
# ============================================================================
print_step "7/9" "代码签名..."

if [ -n "$APPLE_DEVELOPER_ID" ]; then
    print_success "开始代码签名..."

    codesign --deep --force --verify --verbose \
        --sign "$APPLE_DEVELOPER_ID" \
        --options runtime \
        --entitlements entitlements.plist \
        "dist/${APP_NAME}.app"

    if [ $? -eq 0 ]; then
        print_success "代码签名完成"
    else
        print_error "代码签名失败"
    fi
else
    print_warning "跳过代码签名（未设置 APPLE_DEVELOPER_ID）"
    print_warning "提示：设置环境变量以启用代码签名："
    print_warning "  export APPLE_DEVELOPER_ID='Developer ID Application: Your Name (TEAM_ID)'"
fi

# ============================================================================
# 步骤 8/9: 创建DMG镜像
# ============================================================================
print_step "8/9" "创建DMG镜像..."

DMG_NAME="${APP_NAME}-${VERSION}.dmg"

if [ -f "dist/${DMG_NAME}" ]; then
    rm -f "dist/${DMG_NAME}"
fi

hdiutil create -volname "${APP_NAME}" \
    -srcfolder "dist/${APP_NAME}.app" \
    -ov -format UDZO \
    "dist/${DMG_NAME}"

if [ $? -eq 0 ]; then
    print_success "DMG镜像创建完成"
else
    print_error "DMG镜像创建失败"
fi

# ============================================================================
# 步骤 9/9: 公证（Notarization）
# ============================================================================
print_step "9/9" "应用公证..."

if [ -n "$APPLE_ID" ] && [ -n "$APPLE_APP_PASSWORD" ] && [ -n "$APPLE_TEAM_ID" ]; then
    print_success "开始公证流程..."

    xcrun notarytool submit "dist/${DMG_NAME}" \
        --apple-id "$APPLE_ID" \
        --password "$APPLE_APP_PASSWORD" \
        --team-id "$APPLE_TEAM_ID" \
        --wait

    if [ $? -eq 0 ]; then
        print_success "公证成功，正在附加票据..."
        xcrun stapler staple "dist/${DMG_NAME}"
        print_success "公证完成"
    else
        print_error "公证失败"
    fi
else
    print_warning "跳过公证（未设置Apple凭证）"
    print_warning "提示：设置以下环境变量以启用公证："
    print_warning "  export APPLE_ID='your@email.com'"
    print_warning "  export APPLE_APP_PASSWORD='app-specific-password'"
    print_warning "  export APPLE_TEAM_ID='TEAM_ID'"
fi

# ============================================================================
# 生成报告
# ============================================================================
echo ""
print_header "构建完成！"

echo "应用程序位置:"
echo "  dist/${APP_NAME}.app"
echo ""

if [ -f "dist/${DMG_NAME}" ]; then
    echo "DMG镜像位置:"
    echo "  dist/${DMG_NAME}"
    echo ""

    # 显示文件大小
    DMG_SIZE=$(du -h "dist/${DMG_NAME}" | cut -f1)
    echo "DMG文件大小: ${DMG_SIZE}"
    echo ""
fi

print_header "测试说明"

echo "1. 直接运行测试:"
echo "   open dist/${APP_NAME}.app"
echo ""
echo "2. 安装DMG测试:"
echo "   open dist/${DMG_NAME}"
echo ""
echo "3. 如果运行出错，请检查:"
echo "   - 是否缺少必要的依赖"
echo "   - 是否有安全限制（需要在系统偏好设置中允许）"
echo "   - 查看控制台日志获取详细信息"
echo ""

# ============================================================================
# 生成运行脚本
# ============================================================================
cat > "dist/运行${APP_NAME}.command" << EOF
#!/bin/bash
cd "\$(dirname "\$0")"
open "${APP_NAME}.app"
EOF

chmod +x "dist/运行${APP_NAME}.command"
print_success "已生成快捷启动脚本"

echo ""
print_success "全部完成！"
echo ""
