@echo off
REM ============================================================================
REM VirtualChemLab Windows 自动化打包脚本
REM 版本: 自动读取 src\__init__.py
REM ============================================================================

chcp 65001 > nul
setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
set "PYTHONPATH=%SCRIPT_DIR%;%SCRIPT_DIR%\src;%PYTHONPATH%"

echo.
echo ========================================
echo   VirtualChemLab Windows 打包工具
echo ========================================
echo.

REM 初始化应用名称
set APP_NAME=VirtualChemLab
set ENTRY_SCRIPT=main.py
set PYINSTALLER_VERSION=6.3.0

REM ============================================================================
REM 步骤 1/8: 环境检查
REM ============================================================================
echo [1/8] 检查Python环境...

python --version > nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python！请先安装Python 3.10+
    pause
    exit /b 1
)

python --version

for /f "delims=" %%i in ('python -c "from src import __version__; print(__version__)"') do set "VERSION=%%i"

if not defined VERSION (
    echo [错误] 无法读取版本号，请检查 src\__init__.py
    pause
    exit /b 1
)

echo 当前版本: %VERSION%

pushd "%SCRIPT_DIR%"

REM ============================================================================
REM 步骤 2/8: 依赖安装（锁文件）
REM ============================================================================
echo.
echo [2/8] 安装依赖（requirements.lock）...

if not exist "%SCRIPT_DIR%\requirements.lock" (
    echo [错误] 未找到 requirements.lock，无法安装依赖
    pause
    exit /b 1
)

python -m pip install --upgrade pip
python -m pip install --require-hashes -r "%SCRIPT_DIR%\requirements.lock"
if errorlevel 1 (
    echo [错误] 锁文件安装失败
    pause
    exit /b 1
)

python -m pip install "pyinstaller==%PYINSTALLER_VERSION%"
if errorlevel 1 (
    echo [错误] 安装 PyInstaller 失败
    pause
    exit /b 1
)

python -c "import PySide6, pymunk, numba, sqlalchemy" >nul 2>&1
if errorlevel 1 (
    echo [错误] 依赖校验失败，请检查 requirements.lock
    pause
    exit /b 1
)

echo [✓] 依赖安装完成

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

echo [✓] 清理完成

REM ============================================================================
REM 步骤 4/8: 创建图标（如果不存在）
REM ============================================================================
echo.
echo [4/8] 检查应用图标...

set "ICON_FLAG="

if not exist "assets\icons" (
    mkdir assets\icons
)

if exist "assets\icons\app.ico" (
    set "ICON_FLAG=--icon=%SCRIPT_DIR%\assets\icons\app.ico"
    echo [✓] 找到应用图标: assets\icons\app.ico
) else (
    echo [警告] 未找到app.ico，将使用默认图标
)

REM ============================================================================
REM 步骤 5/8: 运行PyInstaller
REM ============================================================================
echo.
echo [5/8] 开始打包应用（这可能需要几分钟）...
echo.

echo 使用 VirtualChemLab.spec 打包...
pyinstaller --clean --noconfirm VirtualChemLab.spec

if errorlevel 1 (
    echo [错误] 打包失败！
    echo 请检查错误信息并重试
    pause
    exit /b 1
)

if not exist "dist\%APP_NAME%\%APP_NAME%.exe" (
    echo [错误] 未找到生成的可执行文件: dist\%APP_NAME%\%APP_NAME%.exe
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

set "INNO_SETUP=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist "%INNO_SETUP%" set "INNO_SETUP=%ProgramFiles%\Inno Setup 6\ISCC.exe"

if exist "%INNO_SETUP%" (
    if exist "installer_windows.iss" (
        echo 运行Inno Setup编译安装程序...
        "%INNO_SETUP%" /DMyAppVersion=%VERSION% installer_windows.iss

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
REM 步骤 8/8: 生成构建报告
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

popd
endlocal
