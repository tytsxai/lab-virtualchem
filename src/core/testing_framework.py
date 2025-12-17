import logging
import queue
import threading
import time
import traceback
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from functools import wraps
from typing import Any

try:
    import pytest

    PYTEST_AVAILABLE = True
except ImportError:
    PYTEST_AVAILABLE = False
    pytest = None

try:
    from hypothesis import given
    from hypothesis import strategies as st

    HYPOTHESIS_AVAILABLE = True
except ImportError:
    HYPOTHESIS_AVAILABLE = False
    given = None
    st = None

"""测试框架"""

logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    """测试结果"""

    test_name: str
    status: str  # passed, failed, skipped, error
    duration: float
    error_message: str | None = None
    error_traceback: str | None = None
    assertions: int = 0
    coverage: float | None = None


@dataclass
class TestSuite:
    """测试套件"""

    name: str
    tests: list[Callable]
    setup: Callable | None = None
    teardown: Callable | None = None
    parallel: bool = False


class TestRunner:
    """测试运行器"""

    def __init__(self, parallel: bool = False, max_workers: int = 4):
        """初始化测试运行器

        Args:
            parallel: 是否并行执行
            max_workers: 最大工作线程数
        """
        self.parallel = parallel
        self.max_workers = max_workers
        self.results: list[TestResult] = []
        self._lock = threading.Lock()

        logger.info(f"测试运行器已初始化 (并行: {parallel}, 工作线程: {max_workers})")

    def run_test(self, test_func: Callable, test_name: str | None = None) -> TestResult:
        """运行单个测试

        Args:
            test_func: 测试函数
            test_name: 测试名称

        Returns:
            测试结果
        """
        name = test_name or test_func.__name__
        start_time = time.time()

        try:
            # 执行测试
            test_func()
            duration = time.time() - start_time

            result = TestResult(test_name=name, status="passed", duration=duration)

            logger.info(f"测试通过: {name} ({duration:.3f}s)")

        except AssertionError as e:
            duration = time.time() - start_time

            result = TestResult(
                test_name=name,
                status="failed",
                duration=duration,
                error_message=str(e),
                error_traceback=traceback.format_exc(),
            )

            logger.error(f"测试失败: {name} - {e}")

        except Exception as e:
            duration = time.time() - start_time

            result = TestResult(
                test_name=name,
                status="error",
                duration=duration,
                error_message=str(e),
                error_traceback=traceback.format_exc(),
            )

            logger.error(f"测试错误: {name} - {e}")

        with self._lock:
            self.results.append(result)

        return result

    def run_suite(self, suite: TestSuite) -> list[TestResult]:
        """运行测试套件

        Args:
            suite: 测试套件

        Returns:
            测试结果列表
        """
        logger.info(f"开始运行测试套件: {suite.name}")

        # 执行设置
        if suite.setup:
            try:
                suite.setup()
                logger.info("测试套件设置完成")
            except Exception as e:
                logger.error(f"测试套件设置失败: {e}")
                return []

        results = []

        try:
            if suite.parallel and self.parallel:
                # 并行执行
                results = self._run_parallel(suite.tests)
            else:
                # 串行执行
                for test_func in suite.tests:
                    result = self.run_test(test_func)
                    results.append(result)

            logger.info(f"测试套件完成: {suite.name}")

        finally:
            # 执行清理
            if suite.teardown:
                try:
                    suite.teardown()
                    logger.info("测试套件清理完成")
                except Exception as e:
                    logger.error(f"测试套件清理失败: {e}")

        return results

    def _run_parallel(self, tests: list[Callable]) -> list[TestResult]:
        """并行运行测试

        Args:
            tests: 测试函数列表

        Returns:
            测试结果列表
        """
        results = []
        result_queue = queue.Queue()

        def worker():
            while True:
                try:
                    test_func = test_queue.get(timeout=1)
                    result = self.run_test(test_func)
                    result_queue.put(result)
                    test_queue.task_done()
                except queue.Empty:
                    break

        test_queue = queue.Queue()
        for test_func in tests:
            test_queue.put(test_func)

        # 启动工作线程
        threads = []
        for _ in range(min(self.max_workers, len(tests))):
            thread = threading.Thread(target=worker)
            thread.start()
            threads.append(thread)

        # 等待所有测试完成
        test_queue.join()

        # 收集结果
        while not result_queue.empty():
            results.append(result_queue.get())

        # 等待线程结束
        for thread in threads:
            thread.join()

        return results

    def get_statistics(self) -> dict[str, Any]:
        """获取测试统计信息

        Returns:
            统计信息
        """
        if not self.results:
            return {
                "total_tests": 0,
                "passed": 0,
                "failed": 0,
                "errors": 0,
                "total_duration": 0,
                "average_duration": 0,
            }

        total_tests = len(self.results)
        passed = sum(1 for r in self.results if r.status == "passed")
        failed = sum(1 for r in self.results if r.status == "failed")
        errors = sum(1 for r in self.results if r.status == "error")
        total_duration = sum(r.duration for r in self.results)
        average_duration = total_duration / total_tests

        return {
            "total_tests": total_tests,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "success_rate": passed / total_tests,
            "total_duration": total_duration,
            "average_duration": average_duration,
        }

    def generate_report(self) -> str:
        """生成测试报告

        Returns:
            测试报告
        """
        stats = self.get_statistics()

        report = f"""
测试报告
{"=" * 50}
总测试数: {stats["total_tests"]}
通过: {stats["passed"]}
失败: {stats["failed"]}
错误: {stats["errors"]}
成功率: {stats["success_rate"]:.2%}
总耗时: {stats["total_duration"]:.3f}s
平均耗时: {stats["average_duration"]:.3f}s

详细结果:
"""

        for result in self.results:
            status_icon = "✅" if result.status == "passed" else "❌"
            report += f"{status_icon} {result.test_name} ({result.duration:.3f}s)\n"

            if result.error_message:
                report += f"   错误: {result.error_message}\n"

        return report


class TestAssertions:
    """测试断言类"""

    @staticmethod
    def assert_equal(actual: Any, expected: Any, message: str = "") -> None:
        """断言相等"""
        if actual != expected:
            raise AssertionError(f"{message} - 期望: {expected}, 实际: {actual}")

    @staticmethod
    def assert_not_equal(actual: Any, expected: Any, message: str = "") -> None:
        """断言不相等"""
        if actual == expected:
            raise AssertionError(f"{message} - 值不应相等: {actual}")

    @staticmethod
    def assert_true(condition: bool, message: str = "") -> None:
        """断言为真"""
        if not condition:
            raise AssertionError(f"{message} - 条件应为真")

    @staticmethod
    def assert_false(condition: bool, message: str = "") -> None:
        """断言为假"""
        if condition:
            raise AssertionError(f"{message} - 条件应为假")

    @staticmethod
    def assert_is_none(value: Any, message: str = "") -> None:
        """断言为None"""
        if value is not None:
            raise AssertionError(f"{message} - 值应为None，实际: {value}")

    @staticmethod
    def assert_is_not_none(value: Any, message: str = "") -> None:
        """断言不为None"""
        if value is None:
            raise AssertionError(f"{message} - 值不应为None")

    @staticmethod
    def assert_in(item: Any, container: Any, message: str = "") -> None:
        """断言包含"""
        if item not in container:
            raise AssertionError(f"{message} - {item} 不在 {container} 中")

    @staticmethod
    def assert_not_in(item: Any, container: Any, message: str = "") -> None:
        """断言不包含"""
        if item in container:
            raise AssertionError(f"{message} - {item} 在 {container} 中")

    @staticmethod
    def assert_raises(
        expected_exception: type[Exception], func: Callable, *args, **kwargs
    ) -> None:
        """断言抛出异常"""
        try:
            func(*args, **kwargs)
            raise AssertionError(
                f"期望抛出 {expected_exception.__name__}，但未抛出异常"
            )
        except expected_exception:
            pass
        except Exception as e:
            raise AssertionError(
                f"期望抛出 {expected_exception.__name__}，但抛出 {type(e).__name__}: {e}"
            ) from e


# 全局测试运行器
test_runner = TestRunner()


def test_case(name: str | None = None):
    """测试用例装饰器

    Args:
        name: 测试名称
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*_args, **_kwargs):
            return test_runner.run_test(func, name)

        return wrapper

    return decorator


def test_suite(name: str, parallel: bool = False):
    """测试套件装饰器

    Args:
        name: 套件名称
        parallel: 是否并行执行
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*_args, **_kwargs):
            suite = TestSuite(name=name, tests=[func], parallel=parallel)
            return test_runner.run_suite(suite)

        return wrapper

    return decorator


class MockObject:
    """模拟对象"""

    def __init__(self, **kwargs):
        self._attributes = kwargs
        self._calls = []

    def __getattr__(self, name):
        if name in self._attributes:
            return self._attributes[name]
        return MockObject()

    def __call__(self, *args, **kwargs):
        self._calls.append((args, kwargs))
        return MockObject()

    def assert_called_with(self, *args, **kwargs):
        """断言调用参数"""
        if (args, kwargs) not in self._calls:
            raise AssertionError(f"期望调用参数: {args}, {kwargs}")

    def assert_called(self):
        """断言被调用"""
        if not self._calls:
            raise AssertionError("期望被调用，但未被调用")

    def assert_not_called(self):
        """断言未被调用"""
        if self._calls:
            raise AssertionError("期望未被调用，但被调用了")

    def reset(self):
        """重置调用记录"""
        self._calls.clear()


class TestDataFactory:
    """测试数据工厂"""

    @staticmethod
    def create_experiment_data(**kwargs) -> dict[str, Any]:
        """创建实验测试数据"""
        default_data = {
            "id": "test_exp_001",
            "title": "测试实验",
            "description": "这是一个测试实验",
            "level": "basic",
            "duration_min": 30,
            "steps": [
                {"id": "step_1", "text": "第一步：准备试剂", "check": None},
                {"id": "step_2", "text": "第二步：开始实验", "check": None},
            ],
            "curves": [],
            "score_rules": [],
        }

        default_data.update(kwargs)
        return default_data

    @staticmethod
    def create_user_data(**kwargs) -> dict[str, Any]:
        """创建用户测试数据"""
        default_data = {
            "user_id": "test_user_001",
            "username": "testuser",
            "role": "student",
            "email": "test@example.com",
            "created_at": datetime.now().isoformat(),
        }

        default_data.update(kwargs)
        return default_data

    @staticmethod
    def create_step_data(**kwargs) -> dict[str, Any]:
        """创建步骤测试数据"""
        default_data = {
            "id": "test_step_001",
            "text": "测试步骤",
            "check": None,
            "hints": [],
            "safety_level": "info",
        }

        default_data.update(kwargs)
        return default_data


class PerformanceTest:
    """性能测试"""

    def __init__(self, name: str):
        self.name = name
        self.results = []

    def measure(self, func: Callable, *args, **kwargs) -> float:
        """测量函数执行时间

        Args:
            func: 要测量的函数
            *args: 函数参数
            **kwargs: 函数关键字参数

        Returns:
            执行时间（秒）
        """
        start_time = time.time()
        func(*args, **kwargs)
        duration = time.time() - start_time

        self.results.append(
            {
                "function": func.__name__,
                "duration": duration,
                "timestamp": datetime.now(),
            }
        )

        return duration

    def benchmark(
        self, func: Callable, iterations: int = 100, *args, **kwargs
    ) -> dict[str, float]:
        """基准测试

        Args:
            func: 要测试的函数
            iterations: 迭代次数
            *args: 函数参数
            **kwargs: 函数关键字参数

        Returns:
            基准测试结果
        """
        durations = []

        for _ in range(iterations):
            duration = self.measure(func, *args, **kwargs)
            durations.append(duration)

        return {
            "min": min(durations),
            "max": max(durations),
            "mean": sum(durations) / len(durations),
            "median": sorted(durations)[len(durations) // 2],
            "std": (
                sum((d - sum(durations) / len(durations)) ** 2 for d in durations)
                / len(durations)
            )
            ** 0.5,
        }

    def get_report(self) -> str:
        """获取性能测试报告

        Returns:
            性能测试报告
        """
        if not self.results:
            return f"性能测试 '{self.name}' 没有结果"

        durations = [r["duration"] for r in self.results]

        report = f"""
性能测试报告: {self.name}
{"=" * 50}
测试次数: {len(self.results)}
最小耗时: {min(durations):.6f}s
最大耗时: {max(durations):.6f}s
平均耗时: {sum(durations) / len(durations):.6f}s
总耗时: {sum(durations):.6f}s
"""

        return report


# 全局测试断言
assertions = TestAssertions()

# 全局测试数据工厂
test_data_factory = TestDataFactory()
