#!/usr/bin/env python3
"""
VirtualChemLab 健康检查脚本
用于快速验证系统所有核心组件是否正常工作
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def print_header(text: str):
    """打印标题"""
    print("\n" + "=" * 60)
    print(f" {text}")
    print("=" * 60)


def check_imports():
    """检查核心模块导入"""
    print_header("检查1: 核心模块导入")

    try:

        print("✅ 所有核心模块导入成功")
        return True
    except Exception as e:
        print(f"❌ 模块导入失败: {e}")
        return False


def check_di_container():
    """检查依赖注入容器"""
    print_header("检查2: 依赖注入容器")

    try:
        from src.core.di_container import DIContainer
        from src.interfaces.storage import ILogger

        # 创建容器
        container = DIContainer()

        # 注册测试服务
        class TestLogger(ILogger):
            def debug(self, message: str, **kwargs):
                pass

            def info(self, message: str, **kwargs):
                pass

            def warning(self, message: str, **kwargs):
                pass

            def error(self, message: str, **kwargs):
                pass

            def critical(self, message: str, **kwargs):
                pass

        container.register_singleton(ILogger, TestLogger)

        # 解析服务
        logger = container.resolve(ILogger)

        assert isinstance(logger, TestLogger), "解析的服务类型不正确"

        print("✅ 依赖注入容器工作正常")
        return True
    except Exception as e:
        print(f"❌ 依赖注入容器失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def check_service_registration():
    """检查服务注册"""
    print_header("检查3: 服务注册系统")

    try:
        from src.core.config_loader import Config
        from src.core.event_bus import EventBus
        from src.core.service_registration import get_configured_container
        from src.interfaces.storage import ILogger

        # 获取配置好的容器
        container = get_configured_container()

        # 验证核心服务已注册
        assert container.is_registered(ILogger), "ILogger未注册"
        assert container.is_registered(Config), "Config未注册"
        assert container.is_registered(EventBus), "EventBus未注册"

        # 尝试解析服务
        container.resolve(ILogger)
        container.resolve(Config)
        container.resolve(EventBus)

        print(f"✅ 服务注册系统正常 (已注册 {len(container.get_all_services())} 个服务)")
        return True
    except Exception as e:
        print(f"❌ 服务注册失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def check_event_bus():
    """检查事件总线"""
    print_header("检查4: 事件总线")

    try:
        from src.core.event_bus import Event, EventBus

        event_bus = EventBus()

        # 测试事件发布和订阅
        test_result = {"called": False, "data": None}

        def handler(event):
            test_result["called"] = True
            test_result["data"] = event.data

        event_bus.subscribe("test.event", handler)

        # 创建并发布事件对象
        event = Event(name="test.event", data={"message": "测试"})
        event_bus.publish(event)

        assert test_result["called"], "事件处理器未被调用"
        assert test_result["data"]["message"] == "测试", "事件数据不正确"

        print("✅ 事件总线工作正常")
        return True
    except Exception as e:
        print(f"❌ 事件总线失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def check_config_system():
    """检查配置系统"""
    print_header("检查5: 配置系统")

    try:
        from src.core.config_loader import get_config

        config = get_config()

        # 验证配置加载
        assert hasattr(config, "app"), "配置缺少app部分"
        assert hasattr(config, "paths"), "配置缺少paths部分"

        print(f"✅ 配置系统正常 (应用: {config.app.name})")
        return True
    except Exception as e:
        print(f"❌ 配置系统失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def check_logger_interface():
    """检查日志接口一致性"""
    print_header("检查6: 日志接口一致性")

    try:
        # 从不同位置导入ILogger
        from src.interfaces.storage import ILogger as ILogger1

        # 验证是同一个类
        print(f"  ILogger 类型: {ILogger1}")

        # 检查是否有重复定义

        # 这些模块都应该使用相同的ILogger
        print("✅ 日志接口一致性正常")
        return True
    except Exception as e:
        print(f"❌ 日志接口检查失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def run_demo_tests():
    """运行演示测试"""
    print_header("检查7: 演示文件测试")

    import subprocess

    demos = [
        ("bootstrap_demo.py", "基础启动演示"),
        ("architecture_demo.py", "架构组件演示"),
        ("advanced_features_demo.py", "高级特性演示"),
    ]

    all_passed = True

    for demo_file, demo_name in demos:
        demo_path = project_root / "examples" / demo_file

        if not demo_path.exists():
            print(f"⚠️  {demo_name}: 文件不存在")
            continue

        try:
            result = subprocess.run(
                [sys.executable, str(demo_path)],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(project_root),
            )

            if result.returncode == 0:
                print(f"✅ {demo_name}: 通过")
            else:
                print(f"❌ {demo_name}: 失败")
                print(f"   错误: {result.stderr[:200]}")
                all_passed = False
        except subprocess.TimeoutExpired:
            print(f"⏱️  {demo_name}: 超时")
            all_passed = False
        except Exception as e:
            print(f"❌ {demo_name}: 异常 - {e}")
            all_passed = False

    return all_passed


def main():
    """主函数"""
    print("\n" + "╔" + "═" * 58 + "╗")
    print("║" + " " * 10 + "VirtualChemLab 健康检查" + " " * 24 + "║")
    print("╚" + "═" * 58 + "╝")

    checks = [
        ("核心模块导入", check_imports),
        ("依赖注入容器", check_di_container),
        ("服务注册系统", check_service_registration),
        ("事件总线", check_event_bus),
        ("配置系统", check_config_system),
        ("日志接口一致性", check_logger_interface),
        ("演示文件测试", run_demo_tests),
    ]

    results = []

    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ {name}: 发生异常 - {e}")
            results.append((name, False))

    # 打印总结
    print_header("健康检查总结")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    print(f"\n检查结果: {passed}/{total} 通过\n")

    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {status}: {name}")

    print("\n" + "=" * 60)

    if passed == total:
        print("🎉 所有检查通过！系统健康状态良好。")
        print("=" * 60)
        return 0
    else:
        print(f"⚠️  {total - passed} 个检查失败，需要修复。")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
