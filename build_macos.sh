#!/bin/bash
# ============================================================================
# VirtualChemLab macOS 自动化打包脚本
# 版本: 2.0.0
# ============================================================================

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 版本配置
VERSION="2.0.0"
APP_NAME="VirtualChemLab"
BUNDLE_ID="com.virtualchemlab.app"

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
# 主流程
# ============================================================================

print_header "VirtualChemLab macOS 打包工具 v${VERSION}"

# ============================================================================
# 步骤 1/9: 环境检查
# ============================================================================
print_step "1/9" "检查Python环境..."

if ! command -v python3 &> /dev/null; then
    print_error "未找到Python 3！请先安装Python 3.8+"
    exit 1
fi

PYTHON_VERSION=$(python3 --version)
print_success "Python环境: ${PYTHON_VERSION}"

# ============================================================================
# 步骤 2/9: 依赖检查
# ============================================================================
print_step "2/9" "检查必要依赖..."

check_and_install() {
    local package=$1
    local version=$2

    if ! python3 -c "import ${package}" 2>/dev/null; then
        print_warning "缺少 ${package}，正在安装..."
        pip3 install "${package}==${version}"
    else
        print_success "${package} 已安装"
    fi
}

check_and_install "PySide6" "6.6.1"
check_and_install "pymunk" "6.6.0"
check_and_install "numba" "0.58.1"
check_and_install "sqlalchemy" "2.0.23"
check_and_install "PyInstaller" "6.3.0"

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

if [ -f "${APP_NAME}.spec" ]; then
    print_warning "删除旧的spec文件..."
    rm -f "${APP_NAME}.spec"
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

if [ ! -f "${ICON_FILE}" ]; then
    print_warning "未找到 app.icns，将使用默认图标"
    print_warning "提示：可以使用以下命令创建图标："
    print_warning "  iconutil -c icns icon.iconset"
else
    print_success "找到应用图标: ${ICON_FILE}"
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

if [ -f "VirtualChemLab-optimized.spec" ]; then
    print_success "使用优化的spec配置文件..."
    pyinstaller VirtualChemLab-optimized.spec --clean --noconfirm
else
    print_warning "使用默认配置打包..."
    pyinstaller \
        --name="${APP_NAME}" \
        --windowed \
        --onedir \
        --clean \
        --noconfirm \
        --icon="${ICON_FILE}" \
        --add-data "assets:assets" \
        --add-data "config:config" \
        --add-data "data/templates:data/templates" \
        --hidden-import=PySide6.QtCore \
        --hidden-import=PySide6.QtGui \
        --hidden-import=PySide6.QtWidgets \
        --hidden-import=pymunk \
        --hidden-import=numba \
        --hidden-import=sqlalchemy \
        --exclude-module=matplotlib \
        --exclude-module=pandas \
        --exclude-module=pytest \
        --osx-bundle-identifier="${BUNDLE_ID}" \
        --osx-entitlements-file=entitlements.plist \
        main.py
fi

if [ $? -ne 0 ]; then
    print_error "打包失败！请检查错误信息"
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
