@echo off
chcp 936 >nul
title 虚拟化学实验室 开发者启动面板 - 增强版

echo ════════════════════════════════════════════════════════════════
echo.
echo      🧪 虚拟化学实验室 开发者启动面板 - 增强版
echo.
echo      版本: v2.1.0
echo.
echo ════════════════════════════════════════════════════════════════
echo.

REM 切换到脚本所在目录
cd /d "%~dp0"

REM 检查Python是否安装
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到Python
    echo.
    echo 请先安装 Python 3.10 或更高版本
    echo 下载地址: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

echo [信息] 正在启动开发者面板（增强版）...
echo.

REM 检查依赖
python -c "import tkinter" >nul 2>&1
if %errorlevel% neq 0 (
    echo [警告] 未找到tkinter模块
    echo 如果面板启动失败，请安装完整版Python（包含tkinter）
    echo.
    pause
)

REM 启动增强版图形界面
python tools\developer_panel_enhanced.py

if %errorlevel% neq 0 (
    echo.
    echo [错误] 面板启动失败 (错误码: %errorlevel%)
    echo.
    echo 可能的原因:
    echo  1. 缺少依赖库 - 运行: pip install -r requirements.txt
    echo  2. Python版本不兼容 - 需要 Python 3.10+
    echo  3. tkinter未安装 - 重新安装完整版Python
    echo.
    pause
    exit /b 1
)

exit /b 0
