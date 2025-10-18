@echo off
REM 运行测试脚本(Windows)

echo =========================================
echo VirtualChemLab 测试套件
echo =========================================
echo.

REM 激活虚拟环境(如果存在)
if exist venv\Scripts\activate.bat (
    echo 激活虚拟环境...
    call venv\Scripts\activate.bat
)

REM 运行代码检查
echo 1. 运行代码检查(ruff)...
ruff check src/ tests/
echo.

REM 运行类型检查
echo 2. 运行类型检查(mypy)...
mypy src/
echo.

REM 运行单元测试
echo 3. 运行单元测试(pytest)...
pytest tests/ -v --cov=src --cov-report=html --cov-report=term
echo.

REM 生成测试报告
echo =========================================
echo 测试完成!
echo HTML覆盖率报告: htmlcov\index.html
echo =========================================

pause




