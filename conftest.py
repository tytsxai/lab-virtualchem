"""
Pytest 全局配置

这里可以集中放置测试收集相关的定制逻辑。
"""

import asyncio
import inspect
from pathlib import Path

# 一些子项目自带的测试文件会与主项目的测试入口重名，
# 比如 `tools/chemlab_integration/tests/test_converters.py`，
# 会和顶层 `tests/test_converters.py` 产生模块名冲突。
#
# 主项目已经在 `tests/test_converters.py` 中对转换器逻辑进行了覆盖，
# 因此可以安全地忽略工具子目录中的这份重复测试。

collect_ignore = [
    # 子项目中与主项目重复的测试
    "tools/chemlab_integration/tests/test_converters.py",
    # 归档的旧版系统测试，包含 GUI/线程等重型场景，默认跳过
    "archive/old-test-files/final_system_test.py",
    "archive/old-test-files/test_core_functionality.py",
    "archive/old-test-files/test_imports.py",
]


def pytest_configure(config):
    """注册额外的markers，避免第三方插件缺失导致的警告"""
    config.addinivalue_line("markers", "asyncio: 标记异步测试")

    # 覆盖率数据文件使用 `temp/.coverage`（见 `.coveragerc`）。
    # 当上一次 pytest 进程异常退出（例如 segfault/bus error）时，该文件可能损坏，
    # 导致后续运行直接报错 "no such table: tracer" 并把总覆盖率记为 0。
    #
    # 维护安全策略：每次测试运行都从干净的 coverage 文件开始。
    coverage_path = Path("temp") / ".coverage"
    if coverage_path.exists():
        try:
            coverage_path.unlink()
        except OSError:
            # 不因清理失败阻断测试；pytest-cov 仍可能覆盖该文件
            pass


def pytest_pyfunc_call(pyfuncitem):
    """
    让pytest原生支持async def测试函数，避免依赖pytest-asyncio。

    这里简单地在新的事件循环中执行协程函数，其余测试保持默认行为。
    """
    if inspect.iscoroutinefunction(pyfuncitem.obj):
        testargs = {arg: pyfuncitem.funcargs[arg] for arg in pyfuncitem._fixtureinfo.argnames}
        asyncio.run(pyfuncitem.obj(**testargs))
        return True
    return None
