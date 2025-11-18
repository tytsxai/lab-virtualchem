@echo off
REM ============================================================================
REM VirtualChemLab Windows 自动化打包脚本
REM 版本: 2.0.0
REM ============================================================================

chcp 65001 > nul
setlocal enabledelayedexpansion

echo.
echo ========================================
echo   VirtualChemLab Windows 打包工具
echo   Version 2.0.0
echo ========================================
echo.

REM 设置版本号
set VERSION=2.0.0
set APP_NAME=VirtualChemLab

REM ============================================================================
REM 步骤 1/8: 环境检查
REM ============================================================================
echo [1/8] 检查Python环境...

python --version > nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python！请先安装Python 3.8+
    pause
    exit /b 1
)

python --version

REM ============================================================================
REM 步骤 2/8: 依赖检查
REM ============================================================================
echo.
echo [2/8] 检查必要依赖...

python -c "import PySide6" 2>nul
if errorlevel 1 (
    echo [错误] 缺少PySide6！
    echo 请运行: pip install -r requirements.txt
    pause
    exit /b 1
)

python -c "import pymunk" 2>nul
if errorlevel 1 (
    echo [警告] 缺少pymunk，安装中...
    pip install pymunk==6.6.0
)

python -c "import numba" 2>nul
if errorlevel 1 (
    echo [警告] 缺少numba，安装中...
    pip install numba==0.58.1
)

python -c "import sqlalchemy" 2>nul
if errorlevel 1 (
    echo [警告] 缺少sqlalchemy，安装中...
    pip install sqlalchemy==2.0.23
)

python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo [警告] 缺少PyInstaller，安装中...
    pip install pyinstaller==6.3.0
)

echo [✓] 依赖检查完成

REM ============================================================================
REM 步骤 3/8: 清理旧构建
REM ============================================================================
echo.
echo [3/8] 清理旧构建文件...

if exist "build" (
    echo 删除 build 目录...
    rmdir /s /q build
)

if exist "dist" (
    echo 删除 dist 目录...
    rmdir /s /q dist
)

if exist "%APP_NAME%.spec" (
    echo 删除旧的spec文件...
    del /q %APP_NAME%.spec
)

echo [✓] 清理完成

REM ============================================================================
REM 步骤 4/8: 创建图标（如果不存在）
REM ============================================================================
echo.
echo [4/8] 检查应用图标...

if not exist "assets\icons" (
    mkdir assets\icons
)

if not exist "assets\icons\app.ico" (
    echo [警告] 未找到app.ico，将使用默认图标
)

REM ============================================================================
REM 步骤 5/8: 运行PyInstaller
REM ============================================================================
echo.
echo [5/8] 开始打包应用（这可能需要几分钟）...
echo.

if exist "VirtualChemLab-optimized.spec" (
    echo 使用优化的spec配置文件...
    pyinstaller VirtualChemLab-optimized.spec --clean --noconfirm
) else (
    echo 使用默认配置打包...
    pyinstaller ^
        --name=%APP_NAME% ^
        --windowed ^
        --onedir ^
        --clean ^
        --noconfirm ^
        --icon=assets\icons\app.ico ^
        --add-data "assets;assets" ^
        --add-data "config;config" ^
        --add-data "data\templates;data\templates" ^
        --hidden-import=PySide6.QtCore ^
        --hidden-import=PySide6.QtGui ^
        --hidden-import=PySide6.QtWidgets ^
        --hidden-import=pymunk ^
        --hidden-import=numba ^
        --hidden-import=sqlalchemy ^
        --exclude-module=matplotlib ^
        --exclude-module=pandas ^
        --exclude-module=pytest ^
        main.py
)

if errorlevel 1 (
    echo [错误] 打包失败！
    echo 请检查错误信息并重试
    pause
    exit /b 1
)

echo [✓] 打包完成

REM ============================================================================
REM 步骤 6/8: 优化打包文件
REM ============================================================================
echo.
echo [6/8] 优化打包文件...

cd dist\%APP_NAME%

REM 删除不需要的文件
echo 删除调试文件...
if exist "*.pdb" del /q *.pdb
if exist "*.pyc" del /q *.pyc
if exist "*.pyo" del /q *.pyo

REM 删除__pycache__目录
echo 删除缓存目录...
for /d /r %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d"

REM 删除测试文件
echo 删除测试文件...
for /d /r %%d in (tests) do @if exist "%%d" rmdir /s /q "%%d"

cd ..\..

echo [✓] 优化完成

REM ============================================================================
REM 步骤 7/8: 创建安装程序（需要Inno Setup）
REM ============================================================================
echo.
echo [7/8] 创建Windows安装程序...

set INNO_SETUP="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"

if exist %INNO_SETUP% (
    if exist "installer_windows.iss" (
        echo 运行Inno Setup编译安装程序...
        %INNO_SETUP% installer_windows.iss

        if errorlevel 1 (
            echo [警告] 安装程序创建失败
        ) else (
            echo [✓] 安装程序创建完成
        )
    ) else (
        echo [警告] 未找到installer_windows.iss配置文件
        echo 跳过安装程序创建
    )
) else (
    echo [提示] 未安装Inno Setup，跳过安装程序创建
    echo 下载地址: https://jrsoftware.org/isdl.php
)

REM ============================================================================
REM 步骤 8/8: 生成报告
REM ============================================================================
echo.
echo [8/8] 生成构建报告...
echo.

echo ========================================
echo   构建完成！
echo ========================================
echo.
echo 应用程序位置:
echo   dist\%APP_NAME%\%APP_NAME%.exe
echo.

if exist "dist\%APP_NAME%-Setup-%VERSION%.exe" (
    echo 安装程序位置:
    echo   dist\%APP_NAME%-Setup-%VERSION%.exe
    echo.
)

REM 计算文件大小
echo 文件信息:
dir "dist\%APP_NAME%" | find "个文件"
echo.

if exist "dist\%APP_NAME%-Setup-%VERSION%.exe" (
    for %%A in ("dist\%APP_NAME%-Setup-%VERSION%.exe") do (
        set size=%%~zA
        set /a size_mb=!size! / 1048576
        echo 安装程序大小: !size_mb! MB
    )
)

echo.
echo ========================================
echo   测试说明
echo ========================================
echo.
echo 1. 直接运行测试:
echo    双击: dist\%APP_NAME%\%APP_NAME%.exe
echo.
echo 2. 安装程序测试:
echo    双击: dist\%APP_NAME%-Setup-%VERSION%.exe
echo.
echo 3. 如果运行出错，请检查:
echo    - 是否缺少必要的依赖文件
echo    - 是否有杀毒软件拦截
echo    - 查看日志文件获取详细信息
echo.

REM ============================================================================
REM 生成运行脚本
REM ============================================================================
echo @echo off > "dist\运行%APP_NAME%.bat"
echo cd %APP_NAME% >> "dist\运行%APP_NAME%.bat"
echo start %APP_NAME%.exe >> "dist\运行%APP_NAME%.bat"

echo [✓] 已生成快捷启动脚本

echo.
echo 按任意键退出...
pause > nul

endlocal
