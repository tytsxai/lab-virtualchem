"""测试运行器"""

import sys
import time
from pathlib import Path

# 添加项目根目录到Python路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.testing_framework import TestRunner, TestSuite  # noqa: E402


def run_security_tests() -> None:
    """运行安全性测试"""
    print("🔒 运行安全性测试...")

    # 导入安全性测试
    from tests.test_security import (  # noqa: E402
        TestDataEncryption,
        TestDataSanitizer,
        TestInputValidator,
        TestPasswordManager,
        TestRBACManager,
        TestSecureToken,
    )

    # 创建测试套件
    security_tests = [
        TestInputValidator,
        TestRBACManager,
        TestDataEncryption,
        TestPasswordManager,
        TestSecureToken,
        TestDataSanitizer,
    ]

    # 运行测试
    runner = TestRunner(parallel=False)
    suite = TestSuite(name="安全性测试", tests=list(security_tests), parallel=False)

    results = runner.run_suite(suite)

    # 打印结果
    print(f"✅ 安全性测试完成: {len(results)} 个测试")
    for result in results:
        status_icon = "✅" if result.status == "passed" else "❌"
        print(f"  {status_icon} {result.test_name} ({result.duration:.3f}s)")
        if result.error_message:
            print(f"    错误: {result.error_message}")

    # return results


def run_performance_tests() -> None:
    """运行性能测试"""
    print("⚡ 运行性能测试...")

    # 导入性能测试
    from tests.test_performance import (
        TestAsyncCache,
        TestAsyncRateLimiter,
        TestAsyncServiceManager,
        TestCacheManager,
        TestDatabasePool,
        TestPerformanceBenchmarks,
    )

    # 创建测试套件
    performance_tests = [
        TestAsyncServiceManager,
        TestAsyncCache,
        TestAsyncRateLimiter,
        TestCacheManager,
        TestDatabasePool,
        TestPerformanceBenchmarks,
    ]

    # 运行测试
    runner = TestRunner(parallel=True)
    suite = TestSuite(name="性能测试", tests=list(performance_tests), parallel=True)

    results = runner.run_suite(suite)

    # 打印结果
    print(f"✅ 性能测试完成: {len(results)} 个测试")
    for result in results:
        status_icon = "✅" if result.status == "passed" else "❌"
        print(f"  {status_icon} {result.test_name} ({result.duration:.3f}s)")
        if result.error_message:
            print(f"    错误: {result.error_message}")

    # return results


def run_integration_tests() -> None:
    """运行集成测试"""
    print("🔗 运行集成测试...")

    # 导入集成测试
    from tests.test_integration import (
        TestAsyncIntegration,
        TestCacheIntegration,
        TestDatabaseIntegration,
        TestExperimentIntegration,
        TestFullSystemIntegration,
        TestSecurityIntegration,
    )

    # 创建测试套件
    integration_tests = [
        TestExperimentIntegration,
        TestSecurityIntegration,
        TestCacheIntegration,
        TestAsyncIntegration,
        TestDatabaseIntegration,
        TestFullSystemIntegration,
    ]

    # 运行测试
    runner = TestRunner(parallel=False)  # 集成测试串行执行
    suite = TestSuite(name="集成测试", tests=list(integration_tests), parallel=False)

    results = runner.run_suite(suite)

    # 打印结果
    print(f"✅ 集成测试完成: {len(results)} 个测试")
    for result in results:
        status_icon = "✅" if result.status == "passed" else "❌"
        print(f"  {status_icon} {result.test_name} ({result.duration:.3f}s)")
        if result.error_message:
            print(f"    错误: {result.error_message}")

    # return results


def run_all_tests() -> None:
    """运行所有测试"""
    print("🚀 开始运行所有测试...")
    print("=" * 60)

    start_time = time.time()

    try:
        # 运行安全性测试
        run_security_tests()
        print()

        # 运行性能测试
        run_performance_tests()
        print()

        # 运行集成测试
        run_integration_tests()
        print()

    except Exception as e:
        print(f"❌ 测试运行失败: {e}")
        return

    # 计算总耗时
    total_time = time.time() - start_time

    # 生成测试报告
    print("=" * 60)
    print("📊 测试报告")
    print("=" * 60)

    # 统计信息
    print(f"⏱️  总耗时: {total_time:.2f} 秒")
    print("✅ 所有测试已完成")


def run_specific_test(test_name: str) -> None:
    """运行特定测试"""
    print(f"🎯 运行特定测试: {test_name}")

    # 根据测试名称运行对应测试
    if test_name == "security":
        run_security_tests()
    elif test_name == "performance":
        run_performance_tests()
    elif test_name == "integration":
        run_integration_tests()
    else:
        print(f"❌ 未知的测试类型: {test_name}")
        # return []


def main() -> None:
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="VirtualChemLab 测试运行器")
    parser.add_argument(
        "--test",
        choices=["security", "performance", "integration", "all"],
        default="all",
        help="要运行的测试类型",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")

    args = parser.parse_args()

    # 设置日志级别
    if args.verbose:
        import logging

        logging.basicConfig(level=logging.DEBUG)

    # 运行测试
    if args.test == "all":
        run_all_tests()
        sys.exit(0)
    else:
        run_specific_test(args.test)
        sys.exit(0)


if __name__ == "__main__":
    main()
