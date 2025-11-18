"""
Pytest 全局配置

这里可以集中放置测试收集相关的定制逻辑。
"""

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
