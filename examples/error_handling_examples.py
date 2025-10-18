"""错误处理示例

演示如何使用VirtualChemLab的错误处理功能
"""

import logging
import sys
from pathlib import Path

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.enhanced_error_handler import (
    ErrorSeverity,
    error_handler,
    handle_errors,
)
from src.utils.safe_io import SafeFileIO, safe_read_json, safe_write_json
from src.utils.safe_network import SafeNetworkClient, check_network

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============ 示例1: 基本错误处理装饰器 ============


@handle_errors(
    context="示例：基本操作",
    user_message="操作失败",
    hint="这是一个演示错误处理的示例",
    severity=ErrorSeverity.ERROR,
    show_dialog=False,  # 命令行示例不显示对话框
)
def example_basic_error_handling():
    """示例：基本的错误处理"""
    print("\n=== 示例1: 基本错误处理 ===")

    # 模拟一个错误
    raise ValueError("这是一个演示错误")


# ============ 示例2: 文件操作错误处理 ============


def example_file_operations():
    """示例：文件操作的错误处理"""
    print("\n=== 示例2: 文件操作错误处理 ===")

    # 2.1 读取不存在的文件（使用默认值）
    print("\n2.1 读取不存在的文件:")
    data = safe_read_json("nonexistent.json", default={"status": "default"})
    print(f"  结果: {data}")

    # 2.2 安全写入文件
    print("\n2.2 写入文件:")
    test_data = {"name": "测试", "value": 123}
    success = safe_write_json("temp_test.json", test_data, create_dirs=True)
    print(f"  写入成功: {success}")

    # 2.3 带备份的写入
    print("\n2.3 带备份的写入:")
    SafeFileIO.write_json("temp_test.json", {"updated": True}, backup=True)
    print("  已创建备份文件")

    # 2.4 检查磁盘空间
    print("\n2.4 检查磁盘空间:")
    has_space = SafeFileIO.check_disk_space(".", required_mb=100)
    print(f"  有足够空间(100MB): {has_space}")

    # 2.5 复制文件
    print("\n2.5 复制文件:")
    SafeFileIO.copy_file("temp_test.json", "temp_test_copy.json")
    print("  文件已复制")

    # 清理
    SafeFileIO.delete_file("temp_test.json", missing_ok=True)
    SafeFileIO.delete_file("temp_test.json.backup", missing_ok=True)
    SafeFileIO.delete_file("temp_test_copy.json", missing_ok=True)
    print("\n  临时文件已清理")


# ============ 示例3: 网络操作错误处理 ============


def example_network_operations():
    """示例：网络操作的错误处理"""
    print("\n=== 示例3: 网络操作错误处理 ===")

    # 3.1 检查网络连接
    print("\n3.1 检查网络连接:")
    is_online = check_network()
    print(f"  网络状态: {'在线' if is_online else '离线'}")

    # 3.2 带重试的网络请求
    print("\n3.2 带重试的网络请求:")
    client = SafeNetworkClient(timeout=5)

    try:
        # 尝试请求一个不存在的服务器（会触发重试）
        response = client.get("http://localhost:9999/test")
        print(f"  响应: {response}")
    except Exception as e:
        print(f"  捕获到错误: {type(e).__name__}: {e}")
        print("  ✓ 自动重试机制已执行")


# ============ 示例4: 自定义错误处理 ============


class CustomOperationError(Exception):
    """自定义业务错误"""

    pass


@handle_errors(
    context="自定义操作",
    user_message="自定义操作失败",
    severity=ErrorSeverity.WARNING,
    show_dialog=False,
)
def example_custom_error():
    """示例：处理自定义错误"""
    print("\n=== 示例4: 自定义错误处理 ===")

    raise CustomOperationError("这是一个自定义业务错误")


# ============ 示例5: 不同严重程度的错误 ============


def example_error_severities():
    """示例：不同严重程度的错误"""
    print("\n=== 示例5: 不同严重程度的错误 ===")

    # 5.1 信息级别
    @handle_errors(severity=ErrorSeverity.INFO, show_dialog=False)
    def info_level():
        print("\n5.1 信息级别:")
        raise Exception("这是一个信息级别的提示")

    # 5.2 警告级别
    @handle_errors(severity=ErrorSeverity.WARNING, show_dialog=False)
    def warning_level():
        print("\n5.2 警告级别:")
        raise Exception("这是一个警告级别的提示")

    # 5.3 错误级别
    @handle_errors(severity=ErrorSeverity.ERROR, show_dialog=False)
    def error_level():
        print("\n5.3 错误级别:")
        raise Exception("这是一个错误级别的提示")

    # 5.4 严重错误级别
    @handle_errors(severity=ErrorSeverity.CRITICAL, show_dialog=False)
    def critical_level():
        print("\n5.4 严重错误级别:")
        raise Exception("这是一个严重错误级别的提示")

    info_level()
    warning_level()
    error_level()
    critical_level()


# ============ 示例6: 错误恢复 ============


def example_error_recovery():
    """示例：错误恢复机制"""
    print("\n=== 示例6: 错误恢复机制 ===")

    max_retries = 3
    attempt = 0

    while attempt < max_retries:
        try:
            print(f"\n尝试 {attempt + 1}/{max_retries}")

            # 模拟可能失败的操作
            if attempt < 2:
                raise ConnectionError("模拟连接失败")

            print("  ✓ 操作成功!")
            break

        except ConnectionError as e:
            attempt += 1
            if attempt < max_retries:
                print(f"  ✗ 失败: {e}, 将重试...")
            else:
                print("  ✗ 所有重试都失败")
                raise


# ============ 示例7: 链式错误处理 ============


@handle_errors(context="步骤3", show_dialog=False)
def step_3():
    """第三步：可能失败"""
    print("  执行步骤3...")
    raise ValueError("步骤3失败")


@handle_errors(context="步骤2", show_dialog=False)
def step_2():
    """第二步：调用步骤3"""
    print("  执行步骤2...")
    step_3()


@handle_errors(context="步骤1", show_dialog=False)
def step_1():
    """第一步：调用步骤2"""
    print("  执行步骤1...")
    step_2()


def example_chained_errors():
    """示例：链式错误处理"""
    print("\n=== 示例7: 链式错误处理 ===")
    print("\n执行多步骤操作:")
    step_1()


# ============ 示例8: 错误历史记录 ============


def example_error_history():
    """示例：查看错误历史"""
    print("\n=== 示例8: 错误历史记录 ===")

    # 触发几个错误
    for i in range(3):
        try:
            raise ValueError(f"测试错误 {i + 1}")
        except ValueError as e:
            error_handler.handle_exception(
                e,
                context=f"测试{i + 1}",
                show_dialog=False,
            )

    # 查看错误历史
    print(f"\n错误历史记录数量: {len(error_handler.error_history)}")
    for i, err in enumerate(error_handler.error_history[-3:], 1):
        print(f"\n错误 {i}:")
        print(f"  消息: {err.message}")
        print(f"  严重程度: {err.severity.value}")
        print(f"  错误码: {err.error_code}")


# ============ 示例9: 上下文管理器错误处理 ============


class SafeOperation:
    """安全操作上下文管理器"""

    def __init__(self, operation_name: str):
        self.operation_name = operation_name

    def __enter__(self):
        print(f"\n开始操作: {self.operation_name}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            print(f"  ✗ 操作失败: {exc_val}")
            # 记录错误但不抛出
            error_handler.handle_exception(
                exc_val,
                context=self.operation_name,
                show_dialog=False,
            )
            return True  # 抑制异常
        else:
            print("  ✓ 操作成功")
            return False


def example_context_manager():
    """示例：使用上下文管理器处理错误"""
    print("\n=== 示例9: 上下文管理器错误处理 ===")

    with SafeOperation("数据处理"):
        # 可能失败的操作
        result = 10 / 2
        print(f"  计算结果: {result}")

    with SafeOperation("除零操作"):
        # 会失败的操作
        result = 10 / 0


# ============ 示例10: 组合使用多种错误处理工具 ============


def example_combined_usage():
    """示例：组合使用多种错误处理工具"""
    print("\n=== 示例10: 组合使用 ===")

    @handle_errors(
        context="复合操作",
        user_message="复合操作失败",
        show_dialog=False,
    )
    def complex_operation():
        # 1. 文件操作
        print("\n1. 读取配置文件:")
        config = safe_read_json("config.json", default={"mode": "default"})
        print(f"  配置: {config}")

        # 2. 检查网络
        print("\n2. 检查网络:")
        is_online = check_network()
        print(f"  网络状态: {'在线' if is_online else '离线'}")

        # 3. 处理数据
        print("\n3. 处理数据:")
        if config.get("mode") == "strict":
            raise ValueError("严格模式下检测到错误")

        print("  数据处理完成")

        # 4. 保存结果
        print("\n4. 保存结果:")
        result = {"status": "success", "timestamp": "2025-10-07"}
        SafeFileIO.write_json("result.json", result)
        print("  结果已保存")

    complex_operation()

    # 清理
    SafeFileIO.delete_file("result.json", missing_ok=True)


# ============ 主函数 ============


def main():
    """运行所有示例"""
    print("=" * 60)
    print("VirtualChemLab 错误处理示例")
    print("=" * 60)

    examples = [
        ("基本错误处理", example_basic_error_handling),
        ("文件操作", example_file_operations),
        ("网络操作", example_network_operations),
        ("自定义错误", example_custom_error),
        ("错误严重程度", example_error_severities),
        ("错误恢复", example_error_recovery),
        ("链式错误", example_chained_errors),
        ("错误历史", example_error_history),
        ("上下文管理器", example_context_manager),
        ("组合使用", example_combined_usage),
    ]

    for name, func in examples:
        try:
            func()
        except Exception as e:
            logger.error(f"示例'{name}'执行出错: {e}", exc_info=True)

    print("\n" + "=" * 60)
    print("所有示例执行完成!")
    print("=" * 60)

    # 显示统计
    print("\n错误统计:")
    print(f"  总错误数: {len(error_handler.error_history)}")

    # 按严重程度统计
    from collections import Counter

    severity_counts = Counter(err.severity for err in error_handler.error_history)
    for severity, count in severity_counts.items():
        print(f"  {severity.value}: {count}")


if __name__ == "__main__":
    main()

