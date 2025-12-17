"""
测试转换器兼容层

为了兼容工具包 `tools/chemlab_integration` 中的转换器单元测试，
这里提供一个简单的转发模块，使得 `tests.test_converters` 路径可用。
"""

from tools.chemlab_integration.tests.test_converters import *  # noqa: F401,F403
