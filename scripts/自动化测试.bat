@echo off
chcp 936 >nul
echo =====================================
echo VirtualChemLab 自动化测试系统
echo =====================================
echo.

:menu
echo 请选择测试类型:
echo.
echo [1] 🚀 完整测试套件 (推荐)
echo [2] 🧪 单元测试
echo [3] 🔗 集成测试
echo [4] 🖥️  UI测试
echo [5] ⚡ 性能测试
echo [6] 🔍 代码质量检查
echo [7] 🔒 安全检查
echo [8] 📊 生成测试报告
echo [9] ⚙️  配置 pre-commit 钩子
echo [0] 退出
echo.

set /p choice="请输入选项 (0-9): "

if "%choice%"=="1" goto full_test
if "%choice%"=="2" goto unit_test
if "%choice%"=="3" goto integration_test
if "%choice%"=="4" goto ui_test
if "%choice%"=="5" goto performance_test
if "%choice%"=="6" goto quality_check
if "%choice%"=="7" goto security_check
if "%choice%"=="8" goto generate_report
if "%choice%"=="9" goto setup_precommit
if "%choice%"=="0" goto exit

echo 无效选项,请重新选择
goto menu

:full_test
echo.
echo 🚀 运行完整测试套件...
echo.
python scripts\run_all_tests.py --type all --report
pause
goto menu

:unit_test
echo.
echo 🧪 运行单元测试...
echo.
python scripts\run_all_tests.py --type unit
pause
goto menu

:integration_test
echo.
echo 🔗 运行集成测试...
echo.
python scripts\run_all_tests.py --type integration
pause
goto menu

:ui_test
echo.
echo 🖥️  运行UI测试...
echo.
python scripts\run_all_tests.py --type ui
pause
goto menu

:performance_test
echo.
echo ⚡ 运行性能测试...
echo.
python scripts\run_all_tests.py --type performance
pause
goto menu

:quality_check
echo.
echo 🔍 运行代码质量检查...
echo.
python scripts\run_all_tests.py --type quality
pause
goto menu

:security_check
echo.
echo 🔒 运行安全检查...
echo.
python scripts\run_all_tests.py --type security
pause
goto menu

:generate_report
echo.
echo 📊 生成测试报告...
echo.
echo 运行测试并生成报告...
python scripts\run_all_tests.py --type all --report
echo.
echo ✅ 报告生成完成!
echo.
echo 查看报告:
echo   - HTML覆盖率: htmlcov\index.html
echo   - JSON报告: test_reports\test_report_*.json
echo   - 文本报告: test_reports\test_report_*.txt
echo.
pause
goto menu

:setup_precommit
echo.
echo ⚙️  配置 pre-commit 钩子...
echo.
echo 安装 pre-commit...
pip install pre-commit
echo.
echo 安装 Git 钩子...
pre-commit install
echo.
echo ✅ pre-commit 已配置!
echo.
echo 现在每次提交前都会自动运行代码检查和测试。
echo 使用 'git commit --no-verify' 可以跳过钩子。
echo.
pause
goto menu

:exit
echo.
echo 👋 再见!
exit /b 0
