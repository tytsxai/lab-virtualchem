@echo off
chcp 936 >nul
echo.
echo ========================================
echo   ChemLab 数据导入工具
echo ========================================
echo.

cd /d "%~dp0"

REM 检查 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 错误: 未找到 Python
    echo 请先安装 Python 3.10+
    pause
    exit /b 1
)

echo ✅ Python 已安装
echo.

REM 检查依赖
echo 检查依赖包...
python -c "import yaml, git, pydantic" >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠️  缺少依赖包,正在安装...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo ❌ 依赖安装失败
        pause
        exit /b 1
    )
)

echo ✅ 依赖包完整
echo.

REM 提示用户选择
echo 请选择导入类型:
echo   1. 导入所有数据 (实验 + 知识库)
echo   2. 仅导入实验模板
echo   3. 仅导入知识库
echo   4. 验证已导入数据
echo.
set /p choice="请输入选择 (1-4): "

if "%choice%"=="1" (
    echo.
    echo 开始导入所有数据...
    python scripts\import_all.py --verbose
) else if "%choice%"=="2" (
    echo.
    echo 开始导入实验模板...
    python scripts\import_experiments.py --verbose
) else if "%choice%"=="3" (
    echo.
    echo 开始导入知识库...
    python scripts\import_knowledge.py --verbose
) else if "%choice%"=="4" (
    echo.
    echo 验证实验模板...
    python scripts\validate_output.py ..\..\data\templates
    echo.
    echo 验证知识库...
    python scripts\validate_output.py ..\..\data\knowledge
) else (
    echo ❌ 无效选择
    pause
    exit /b 1
)

echo.
echo ========================================
echo   操作完成!
echo ========================================
echo.
echo 下一步:
echo   1. 检查 data\templates\ 目录查看新实验
echo   2. 检查 data\knowledge\ 目录查看新知识卡片
echo   3. 启动 VirtualChemLab 使用新数据
echo.
pause
