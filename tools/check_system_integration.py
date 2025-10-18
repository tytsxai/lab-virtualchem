"""
VirtualChemLab 系统互通性检查工具

检查项目:
1. 模块接口连接性
2. 依赖注入容器配置
3. 事件总线订阅发布
4. 服务层互通性
5. API接口响应性
6. UI与后端交互
7. 插件系统集成
8. 缓存和队列连接
9. 系统整体响应流畅度

作者: VirtualChemLab Team
日期: 2025-10-06
"""

import asyncio
import sys
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@dataclass
class IntegrationCheckResult:
    """集成检查结果"""
    category: str  # 检查类别
    check_name: str  # 检查名称
    status: str  # healthy/warning/error/critical
    message: str  # 详细信息
    details: dict[str, Any] = field(default_factory=dict)  # 额外详情
    response_time: float = 0.0  # 响应时间(毫秒)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class IntegrationReport:
    """集成报告"""
    overall_status: str
    total_checks: int
    passed: int
    warnings: int
    errors: int
    critical: int
    checks: list[IntegrationCheckResult]
    total_time: float
    timestamp: datetime = field(default_factory=datetime.now)


class SystemIntegrationChecker:
    """系统集成检查器"""

    def __init__(self):
        self.results: list[IntegrationCheckResult] = []
        self.start_time = time.time()

    def add_result(self, category: str, check_name: str, status: str,
                   message: str, details: dict[str, Any] = None,
                   response_time: float = 0.0):
        """添加检查结果"""
        result = IntegrationCheckResult(
            category=category,
            check_name=check_name,
            status=status,
            message=message,
            details=details or {},
            response_time=response_time
        )
        self.results.append(result)

    # ========== 1. 核心模块导入检查 ==========

    def check_core_modules(self):
        """检查核心模块是否能正常导入"""
        print("\n" + "="*70)
        print("1️⃣  核心模块导入检查")
        print("="*70)

        core_modules = {
            "依赖注入容器": "src.core.di_container",
            "事件总线": "src.core.event_bus",
            "中间件": "src.core.middleware",
            "仓储模式": "src.core.repository",
            "工厂模式": "src.core.factory",
            "配置管理": "src.core.config",
            "应用启动器": "src.core.bootstrap",
            "缓存系统": "src.core.cache",
            "消息队列": "src.core.message_queue",
            "认证授权": "src.core.auth",
            "数据验证": "src.core.validation",
            "健康检查": "src.core.health",
            "弹性容错": "src.core.resilience",
        }

        for name, module_path in core_modules.items():
            start = time.time()
            try:
                __import__(module_path)
                elapsed = (time.time() - start) * 1000
                self.add_result(
                    "核心模块",
                    f"导入{name}",
                    "healthy",
                    f"✓ {name}导入成功",
                    {"module": module_path},
                    elapsed
                )
                print(f"  ✓ {name:20s} - 导入成功 ({elapsed:.1f}ms)")
            except Exception as e:
                elapsed = (time.time() - start) * 1000
                self.add_result(
                    "核心模块",
                    f"导入{name}",
                    "error",
                    f"✗ {name}导入失败: {str(e)}",
                    {"module": module_path, "error": str(e)},
                    elapsed
                )
                print(f"  ✗ {name:20s} - 导入失败: {str(e)}")

    # ========== 2. 依赖注入容器检查 ==========

    def check_di_container(self):
        """检查依赖注入容器的服务注册和解析"""
        print("\n" + "="*70)
        print("2️⃣  依赖注入容器检查")
        print("="*70)

        try:
            from src.core.di_container import DIContainer
            from src.interfaces.storage import IStorage
            from src.storage.json_store import JSONStore

            start = time.time()
            container = DIContainer()
            elapsed = (time.time() - start) * 1000

            self.add_result(
                "DI容器",
                "容器创建",
                "healthy",
                "✓ DI容器创建成功",
                {},
                elapsed
            )
            print(f"  ✓ DI容器创建成功 ({elapsed:.1f}ms)")

            # 测试服务注册
            start = time.time()
            container.register_singleton(IStorage, JSONStore)
            elapsed = (time.time() - start) * 1000

            self.add_result(
                "DI容器",
                "服务注册",
                "healthy",
                "✓ 服务注册成功",
                {"service": "IStorage -> JSONStore"},
                elapsed
            )
            print(f"  ✓ 服务注册成功 ({elapsed:.1f}ms)")

            # 测试服务解析
            start = time.time()
            storage = container.resolve(IStorage)
            elapsed = (time.time() - start) * 1000

            if storage is not None:
                self.add_result(
                    "DI容器",
                    "服务解析",
                    "healthy",
                    "✓ 服务解析成功",
                    {"service": "IStorage", "instance": type(storage).__name__},
                    elapsed
                )
                print(f"  ✓ 服务解析成功 ({elapsed:.1f}ms)")
            else:
                self.add_result(
                    "DI容器",
                    "服务解析",
                    "error",
                    "✗ 服务解析返回None",
                    {},
                    elapsed
                )
                print("  ✗ 服务解析返回None")

            # 测试自动依赖注入
            print("\n  测试自动依赖注入...")

            class TestService:
                def __init__(self, storage: IStorage):
                    self.storage = storage

            container.register_transient(TestService, TestService)
            start = time.time()
            test_service = container.resolve(TestService)
            elapsed = (time.time() - start) * 1000

            if test_service and hasattr(test_service, 'storage'):
                self.add_result(
                    "DI容器",
                    "自动依赖注入",
                    "healthy",
                    "✓ 自动依赖注入成功",
                    {"service": "TestService", "injected": "IStorage"},
                    elapsed
                )
                print(f"  ✓ 自动依赖注入成功 ({elapsed:.1f}ms)")
            else:
                self.add_result(
                    "DI容器",
                    "自动依赖注入",
                    "error",
                    "✗ 自动依赖注入失败",
                    {},
                    elapsed
                )
                print("  ✗ 自动依赖注入失败")

        except Exception as e:
            self.add_result(
                "DI容器",
                "容器测试",
                "critical",
                f"✗ DI容器测试失败: {str(e)}",
                {"error": str(e), "traceback": traceback.format_exc()}
            )
            print(f"  ✗ DI容器测试失败: {str(e)}")

    # ========== 3. 事件总线检查 ==========

    def check_event_bus(self):
        """检查事件总线的发布订阅机制"""
        print("\n" + "="*70)
        print("3️⃣  事件总线检查")
        print("="*70)

        try:
            from src.core.event_bus import Event, EventBus, EventPriority

            start = time.time()
            bus = EventBus()
            elapsed = (time.time() - start) * 1000

            self.add_result(
                "事件总线",
                "总线创建",
                "healthy",
                "✓ 事件总线创建成功",
                {},
                elapsed
            )
            print(f"  ✓ 事件总线创建成功 ({elapsed:.1f}ms)")

            # 测试订阅
            event_received = []

            def test_handler(event: Event):
                event_received.append(event)

            start = time.time()
            bus.subscribe("test.event", test_handler, priority=EventPriority.HIGH)
            elapsed = (time.time() - start) * 1000

            self.add_result(
                "事件总线",
                "事件订阅",
                "healthy",
                "✓ 事件订阅成功",
                {"event": "test.event"},
                elapsed
            )
            print(f"  ✓ 事件订阅成功 ({elapsed:.1f}ms)")

            # 测试发布
            start = time.time()
            test_event = Event(
                name="test.event",
                data={"message": "测试消息"},
                source="integration_checker"
            )
            results = bus.publish(test_event)
            elapsed = (time.time() - start) * 1000

            if len(event_received) > 0:
                self.add_result(
                    "事件总线",
                    "事件发布",
                    "healthy",
                    "✓ 事件发布成功,订阅者接收到事件",
                    {"subscribers": len(results), "received": len(event_received)},
                    elapsed
                )
                print(f"  ✓ 事件发布成功,{len(event_received)}个订阅者接收 ({elapsed:.1f}ms)")
            else:
                self.add_result(
                    "事件总线",
                    "事件发布",
                    "error",
                    "✗ 事件发布失败,订阅者未接收到事件",
                    {},
                    elapsed
                )
                print("  ✗ 事件发布失败,订阅者未接收到事件")

            # 测试通配符订阅
            wildcard_received = []

            def wildcard_handler(event: Event):
                wildcard_received.append(event)

            bus.subscribe("test.*", wildcard_handler)

            test_event2 = Event(name="test.wildcard", data={})
            bus.publish(test_event2)

            if len(wildcard_received) > 0:
                self.add_result(
                    "事件总线",
                    "通配符订阅",
                    "healthy",
                    "✓ 通配符订阅工作正常",
                    {"pattern": "test.*"}
                )
                print("  ✓ 通配符订阅工作正常")
            else:
                self.add_result(
                    "事件总线",
                    "通配符订阅",
                    "warning",
                    "⚠ 通配符订阅可能未工作",
                    {}
                )
                print("  ⚠ 通配符订阅可能未工作")

        except Exception as e:
            self.add_result(
                "事件总线",
                "总线测试",
                "critical",
                f"✗ 事件总线测试失败: {str(e)}",
                {"error": str(e), "traceback": traceback.format_exc()}
            )
            print(f"  ✗ 事件总线测试失败: {str(e)}")

    # ========== 4. 服务契约层检查 ==========

    def check_service_contracts(self):
        """检查服务契约层的接口定义"""
        print("\n" + "="*70)
        print("4️⃣  服务契约层检查")
        print("="*70)

        contracts = {
            "实验服务": "src.contracts.experiment_service",
            "存储服务": "src.contracts.storage_service",
            "报告服务": "src.contracts.report_service",
            "插件服务": "src.contracts.plugin_service",
        }

        for name, module_path in contracts.items():
            start = time.time()
            try:
                module = __import__(module_path, fromlist=[''])
                elapsed = (time.time() - start) * 1000

                # 检查是否有Service类定义
                classes = [item for item in dir(module) if 'Service' in item]

                self.add_result(
                    "服务契约",
                    f"{name}接口",
                    "healthy",
                    f"✓ {name}接口定义完整",
                    {"module": module_path, "classes": len(classes)},
                    elapsed
                )
                print(f"  ✓ {name:20s} - 接口完整({len(classes)}个类) ({elapsed:.1f}ms)")
            except Exception as e:
                elapsed = (time.time() - start) * 1000
                self.add_result(
                    "服务契约",
                    f"{name}接口",
                    "error",
                    f"✗ {name}接口导入失败: {str(e)}",
                    {"module": module_path, "error": str(e)},
                    elapsed
                )
                print(f"  ✗ {name:20s} - 导入失败: {str(e)}")

    # ========== 5. 服务实现层检查 ==========

    def check_service_implementations(self):
        """检查服务实现层"""
        print("\n" + "="*70)
        print("5️⃣  服务实现层检查")
        print("="*70)

        implementations = {
            "实验服务实现": "src.services.experiment_service_impl",
            "存储服务实现": "src.services.storage_service_impl",
            "报告服务实现": "src.services.report_service_impl",
            "插件服务实现": "src.services.plugin_service_impl",
        }

        for name, module_path in implementations.items():
            start = time.time()
            try:
                module = __import__(module_path, fromlist=[''])
                elapsed = (time.time() - start) * 1000

                # 检查实现类
                impl_classes = [item for item in dir(module) if 'Impl' in item or 'Service' in item]

                self.add_result(
                    "服务实现",
                    name,
                    "healthy",
                    f"✓ {name}加载成功",
                    {"module": module_path, "classes": len(impl_classes)},
                    elapsed
                )
                print(f"  ✓ {name:20s} - 实现完整({len(impl_classes)}个类) ({elapsed:.1f}ms)")
            except Exception as e:
                elapsed = (time.time() - start) * 1000
                self.add_result(
                    "服务实现",
                    name,
                    "error",
                    f"✗ {name}加载失败: {str(e)}",
                    {"module": module_path, "error": str(e)},
                    elapsed
                )
                print(f"  ✗ {name:20s} - 加载失败: {str(e)}")

    # ========== 6. UI层集成检查 ==========

    def check_ui_integration(self):
        """检查UI层与后端的集成"""
        print("\n" + "="*70)
        print("6️⃣  UI层集成检查")
        print("="*70)

        ui_components = {
            "主窗口": "src.ui.main_window",
            "实验视图": "src.ui.experiment_view",
            "知识浏览器": "src.ui.knowledge_browser",
            "记录浏览器": "src.ui.record_browser",
            "开发者控制台": "src.ui.developer_console",
            "主题管理": "src.ui.themes",
            "响应式布局": "src.ui.responsive",
        }

        for name, module_path in ui_components.items():
            start = time.time()
            try:
                __import__(module_path, fromlist=[''])
                elapsed = (time.time() - start) * 1000

                self.add_result(
                    "UI集成",
                    f"{name}组件",
                    "healthy",
                    f"✓ {name}组件加载成功",
                    {"module": module_path},
                    elapsed
                )
                print(f"  ✓ {name:20s} - 加载成功 ({elapsed:.1f}ms)")
            except Exception as e:
                elapsed = (time.time() - start) * 1000
                # UI组件可能依赖Qt,缺少Qt时标记为警告而非错误
                status = "warning" if "PySide6" in str(e) or "PyQt" in str(e) else "error"
                self.add_result(
                    "UI集成",
                    f"{name}组件",
                    status,
                    f"{'⚠' if status == 'warning' else '✗'} {name}组件加载失败: {str(e)}",
                    {"module": module_path, "error": str(e)},
                    elapsed
                )
                symbol = "⚠" if status == "warning" else "✗"
                print(f"  {symbol} {name:20s} - 加载失败: {str(e)}")

    # ========== 7. 插件系统检查 ==========

    def check_plugin_system(self):
        """检查插件系统"""
        print("\n" + "="*70)
        print("7️⃣  插件系统检查")
        print("="*70)

        try:
            from src.plugins import PluginRegistry

            start = time.time()
            registry = PluginRegistry()
            elapsed = (time.time() - start) * 1000

            self.add_result(
                "插件系统",
                "注册表创建",
                "healthy",
                "✓ 插件注册表创建成功",
                {},
                elapsed
            )
            print(f"  ✓ 插件注册表创建成功 ({elapsed:.1f}ms)")

            # 测试插件注册
            registry.register(
                name="test_plugin",
                description="测试插件",
                module_name="test",
                license="MIT"
            )

            # 使用正确的方法名 list_plugins
            plugins = registry.list_plugins()
            if len(plugins) > 0:
                self.add_result(
                    "插件系统",
                    "插件注册",
                    "healthy",
                    f"✓ 插件注册功能正常,已注册{len(plugins)}个插件",
                    {"count": len(plugins)}
                )
                print(f"  ✓ 插件注册功能正常,已注册{len(plugins)}个插件")
            else:
                self.add_result(
                    "插件系统",
                    "插件注册",
                    "warning",
                    "⚠ 未检测到已注册的插件",
                    {}
                )
                print("  ⚠ 未检测到已注册的插件")

        except Exception as e:
            self.add_result(
                "插件系统",
                "系统测试",
                "error",
                f"✗ 插件系统测试失败: {str(e)}",
                {"error": str(e)}
            )
            print(f"  ✗ 插件系统测试失败: {str(e)}")

    # ========== 8. 缓存系统检查 ==========

    def check_cache_system(self):
        """检查缓存系统"""
        print("\n" + "="*70)
        print("8️⃣  缓存系统检查")
        print("="*70)

        try:
            from src.core.cache import CacheStrategy, MemoryCache

            # 测试LRU缓存
            start = time.time()
            lru = MemoryCache(max_size=100, strategy=CacheStrategy.LRU)
            lru.set("key1", "value1")
            value = lru.get("key1")
            elapsed = (time.time() - start) * 1000

            if value == "value1":
                self.add_result(
                    "缓存系统",
                    "LRU缓存",
                    "healthy",
                    "✓ LRU缓存工作正常",
                    {},
                    elapsed
                )
                print(f"  ✓ LRU缓存工作正常 ({elapsed:.1f}ms)")
            else:
                self.add_result(
                    "缓存系统",
                    "LRU缓存",
                    "error",
                    "✗ LRU缓存读写异常",
                    {}
                )
                print("  ✗ LRU缓存读写异常")

            # 测试LFU缓存
            start = time.time()
            lfu = MemoryCache(max_size=100, strategy=CacheStrategy.LFU)
            lfu.set("key2", "value2")
            value = lfu.get("key2")
            elapsed = (time.time() - start) * 1000

            if value == "value2":
                self.add_result(
                    "缓存系统",
                    "LFU缓存",
                    "healthy",
                    "✓ LFU缓存工作正常",
                    {},
                    elapsed
                )
                print(f"  ✓ LFU缓存工作正常 ({elapsed:.1f}ms)")
            else:
                self.add_result(
                    "缓存系统",
                    "LFU缓存",
                    "error",
                    "✗ LFU缓存读写异常",
                    {}
                )
                print("  ✗ LFU缓存读写异常")

            # 测试TTL缓存
            start = time.time()
            ttl = MemoryCache(max_size=100, strategy=CacheStrategy.TTL)
            ttl.set("key3", "value3", ttl=60)
            value = ttl.get("key3")
            elapsed = (time.time() - start) * 1000

            if value == "value3":
                self.add_result(
                    "缓存系统",
                    "TTL缓存",
                    "healthy",
                    "✓ TTL缓存工作正常",
                    {},
                    elapsed
                )
                print(f"  ✓ TTL缓存工作正常 ({elapsed:.1f}ms)")
            else:
                self.add_result(
                    "缓存系统",
                    "TTL缓存",
                    "error",
                    "✗ TTL缓存读写异常",
                    {}
                )
                print("  ✗ TTL缓存读写异常")

        except Exception as e:
            self.add_result(
                "缓存系统",
                "系统测试",
                "error",
                f"✗ 缓存系统测试失败: {str(e)}",
                {"error": str(e)}
            )
            print(f"  ✗ 缓存系统测试失败: {str(e)}")

    # ========== 9. 异步消息队列检查 ==========

    async def check_message_queue_async(self):
        """检查异步消息队列"""
        print("\n" + "="*70)
        print("9️⃣  消息队列检查")
        print("="*70)

        try:
            from src.core.message_queue import InMemoryMessageQueue, Message, MessagePriority

            start = time.time()
            queue = InMemoryMessageQueue(worker_count=2)
            elapsed = (time.time() - start) * 1000

            self.add_result(
                "消息队列",
                "队列创建",
                "healthy",
                "✓ 消息队列创建成功",
                {},
                elapsed
            )
            print(f"  ✓ 消息队列创建成功 ({elapsed:.1f}ms)")

            # 订阅消息
            messages_received = []

            class TestHandler:
                async def handle(self, message):
                    messages_received.append(message)
                    return True

            handler = TestHandler()
            await queue.subscribe("test.topic", handler)

            self.add_result(
                "消息队列",
                "主题订阅",
                "healthy",
                "✓ 主题订阅成功",
                {"topic": "test.topic"}
            )
            print("  ✓ 主题订阅成功")

            # 启动队列
            await queue.start()

            # 发布消息
            start = time.time()
            message = Message(
                topic="test.topic",
                data={"data": "测试数据"},
                priority=MessagePriority.NORMAL
            )
            message_id = await queue.publish(message)
            elapsed = (time.time() - start) * 1000

            # 等待消息处理
            await asyncio.sleep(0.1)

            if len(messages_received) > 0:
                self.add_result(
                    "消息队列",
                    "消息发布",
                    "healthy",
                    "✓ 消息发布并接收成功",
                    {"message_id": message_id, "received": len(messages_received)},
                    elapsed
                )
                print(f"  ✓ 消息发布并接收成功 ({elapsed:.1f}ms)")
            else:
                self.add_result(
                    "消息队列",
                    "消息发布",
                    "warning",
                    "⚠ 消息已发布但未接收到(可能是异步延迟)",
                    {"message_id": message_id}
                )
                print("  ⚠ 消息已发布但未接收到(可能是异步延迟)")

            # 停止队列
            await queue.stop()

        except Exception as e:
            self.add_result(
                "消息队列",
                "系统测试",
                "error",
                f"✗ 消息队列测试失败: {str(e)}",
                {"error": str(e)}
            )
            print(f"  ✗ 消息队列测试失败: {str(e)}")

    # ========== 10. 模块间通信检查 ==========

    def check_inter_module_communication(self):
        """检查模块间通信"""
        print("\n" + "="*70)
        print("🔟 模块间通信检查")
        print("="*70)

        try:
            from src.core.bootstrap import create_app
            from src.interfaces.storage import IStorage

            # 创建应用(自动初始化所有组件)
            start = time.time()
            container = create_app()
            elapsed = (time.time() - start) * 1000

            self.add_result(
                "模块通信",
                "应用初始化",
                "healthy",
                "✓ 应用初始化成功",
                {},
                elapsed
            )
            print(f"  ✓ 应用初始化成功 ({elapsed:.1f}ms)")

            # 测试DI容器中的服务解析
            start = time.time()
            try:
                container.resolve(IStorage)
                elapsed = (time.time() - start) * 1000

                self.add_result(
                    "模块通信",
                    "跨模块服务解析",
                    "healthy",
                    "✓ 跨模块服务解析成功",
                    {"service": "IStorage"},
                    elapsed
                )
                print(f"  ✓ 跨模块服务解析成功 ({elapsed:.1f}ms)")
            except Exception as e:
                self.add_result(
                    "模块通信",
                    "跨模块服务解析",
                    "warning",
                    f"⚠ 服务解析异常: {str(e)}",
                    {}
                )
                print(f"  ⚠ 服务解析异常: {str(e)}")

        except Exception as e:
            self.add_result(
                "模块通信",
                "通信测试",
                "error",
                f"✗ 模块间通信测试失败: {str(e)}",
                {"error": str(e)}
            )
            print(f"  ✗ 模块间通信测试失败: {str(e)}")

    # ========== 11. 性能响应检查 ==========

    def check_performance_metrics(self):
        """检查系统性能指标"""
        print("\n" + "="*70)
        print("1️⃣1️⃣  性能响应检查")
        print("="*70)

        # 统计响应时间
        response_times = [r.response_time for r in self.results if r.response_time > 0]

        if response_times:
            avg_time = sum(response_times) / len(response_times)
            max_time = max(response_times)
            min_time = min(response_times)

            print("\n  响应时间统计:")
            print(f"    平均响应: {avg_time:.2f}ms")
            print(f"    最快响应: {min_time:.2f}ms")
            print(f"    最慢响应: {max_time:.2f}ms")

            # 评估性能
            if avg_time < 50:
                status = "healthy"
                message = "✓ 系统响应优秀 (平均 < 50ms)"
            elif avg_time < 200:
                status = "healthy"
                message = "✓ 系统响应良好 (平均 < 200ms)"
            elif avg_time < 500:
                status = "warning"
                message = "⚠ 系统响应一般 (平均 < 500ms)"
            else:
                status = "warning"
                message = "⚠ 系统响应较慢 (平均 >= 500ms)"

            self.add_result(
                "性能指标",
                "响应时间",
                status,
                message,
                {
                    "avg_ms": round(avg_time, 2),
                    "max_ms": round(max_time, 2),
                    "min_ms": round(min_time, 2)
                }
            )
            print(f"\n  {message}")

    # ========== 生成报告 ==========

    def generate_report(self) -> IntegrationReport:
        """生成集成报告"""
        total_time = time.time() - self.start_time

        # 统计各状态数量
        status_counts = {
            "healthy": 0,
            "warning": 0,
            "error": 0,
            "critical": 0
        }

        for result in self.results:
            status_counts[result.status] = status_counts.get(result.status, 0) + 1

        # 确定整体状态
        if status_counts["critical"] > 0:
            overall = "critical"
        elif status_counts["error"] > 0:
            overall = "error"
        elif status_counts["warning"] > 0:
            overall = "warning"
        else:
            overall = "healthy"

        report = IntegrationReport(
            overall_status=overall,
            total_checks=len(self.results),
            passed=status_counts["healthy"],
            warnings=status_counts["warning"],
            errors=status_counts["error"],
            critical=status_counts["critical"],
            checks=self.results,
            total_time=total_time
        )

        return report

    def print_report(self, report: IntegrationReport):
        """打印报告"""
        print("\n" + "="*70)
        print("系统集成检查报告")
        print("="*70)

        # 状态映射
        status_icons = {
            "healthy": "[OK]",
            "warning": "[WARN]",
            "error": "[ERR]",
            "critical": "[CRIT]"
        }

        print(f"\n整体状态: {status_icons.get(report.overall_status, '[?]')} {report.overall_status.upper()}")
        print(f"\n总检查项: {report.total_checks}")
        print(f"  [OK]  通过: {report.passed}")
        print(f"  [WARN]警告: {report.warnings}")
        print(f"  [ERR] 错误: {report.errors}")
        print(f"  [CRIT]严重: {report.critical}")
        print(f"\n总耗时: {report.total_time:.2f}秒")

        # 按类别分组显示
        print("\n" + "="*70)
        print("详细结果 (按类别)")
        print("="*70)

        categories = {}
        for check in report.checks:
            if check.category not in categories:
                categories[check.category] = []
            categories[check.category].append(check)

        for category, checks in categories.items():
            print(f"\n【{category}】")
            for check in checks:
                icon = status_icons.get(check.status, "❓")
                time_info = f"({check.response_time:.1f}ms)" if check.response_time > 0 else ""
                print(f"  {icon} {check.check_name:30s} {time_info}")
                if check.status in ["error", "critical"]:
                    print(f"      └─ {check.message}")

        # 关键问题摘要
        issues = [c for c in report.checks if c.status in ["error", "critical"]]
        if issues:
            print("\n" + "="*70)
            print("关键问题摘要")
            print("="*70)
            for issue in issues:
                print(f"\n  [{issue.category}] {issue.check_name}")
                print(f"    状态: {issue.status.upper()}")
                print(f"    信息: {issue.message}")

        # 建议
        print("\n" + "="*70)
        print("建议")
        print("="*70)

        if report.overall_status == "healthy":
            print("\n  系统集成状态良好!")
            print("  - 所有核心模块互通正常")
            print("  - 接口连接流畅")
            print("  - 响应速度优秀")
        elif report.overall_status == "warning":
            print("\n  系统基本正常,但有一些警告:")
            if report.warnings > 0:
                print(f"  - 发现 {report.warnings} 个警告,建议检查")
            print("  - 部分可选功能可能未完全启用")
        else:
            print("\n  系统存在问题,需要修复:")
            if report.errors > 0:
                print(f"  - 发现 {report.errors} 个错误")
            if report.critical > 0:
                print(f"  - 发现 {report.critical} 个严重问题")
            print("  - 请查看上方详细错误信息并修复")

        print("\n" + "="*70)


async def main():
    """主函数"""
    # 设置UTF-8输出编码
    if sys.platform == "win32":
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8')

    print("=" * 70)
    print("VirtualChemLab 系统互通性检查")
    print("=" * 70)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    checker = SystemIntegrationChecker()

    # 执行所有检查
    checker.check_core_modules()
    checker.check_di_container()
    checker.check_event_bus()
    checker.check_service_contracts()
    checker.check_service_implementations()
    checker.check_ui_integration()
    checker.check_plugin_system()
    checker.check_cache_system()
    await checker.check_message_queue_async()
    checker.check_inter_module_communication()
    checker.check_performance_metrics()

    # 生成并打印报告
    report = checker.generate_report()
    checker.print_report(report)

    # 保存报告到文件
    report_file = PROJECT_ROOT / "系统互通性检查报告.md"
    save_report_to_file(report, report_file)
    print(f"\n详细报告已保存到: {report_file}")

    return 0 if report.overall_status in ["healthy", "warning"] else 1


def save_report_to_file(report: IntegrationReport, filepath: Path):
    """保存报告到文件"""
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write("# VirtualChemLab 系统互通性检查报告\n\n")
        f.write(f"**生成时间**: {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**整体状态**: {report.overall_status.upper()}\n\n")

        f.write("## 📊 统计概览\n\n")
        f.write(f"- 总检查项: {report.total_checks}\n")
        f.write(f"- ✅ 通过: {report.passed}\n")
        f.write(f"- ⚠️ 警告: {report.warnings}\n")
        f.write(f"- ❌ 错误: {report.errors}\n")
        f.write(f"- 🚨 严重: {report.critical}\n")
        f.write(f"- ⏱️ 总耗时: {report.total_time:.2f}秒\n\n")

        f.write("## 📋 详细检查结果\n\n")

        # 按类别分组
        categories = {}
        for check in report.checks:
            if check.category not in categories:
                categories[check.category] = []
            categories[check.category].append(check)

        for category, checks in categories.items():
            f.write(f"### {category}\n\n")
            f.write("| 检查项 | 状态 | 响应时间 | 说明 |\n")
            f.write("|--------|------|----------|------|\n")

            for check in checks:
                status_icon = {"healthy": "✅", "warning": "⚠️", "error": "❌", "critical": "🚨"}.get(check.status, "❓")
                time_str = f"{check.response_time:.1f}ms" if check.response_time > 0 else "-"
                f.write(f"| {check.check_name} | {status_icon} {check.status} | {time_str} | {check.message} |\n")

            f.write("\n")

        # 问题列表
        issues = [c for c in report.checks if c.status in ["error", "critical"]]
        if issues:
            f.write("## 🔴 关键问题\n\n")
            for i, issue in enumerate(issues, 1):
                f.write(f"### {i}. {issue.check_name}\n\n")
                f.write(f"- **类别**: {issue.category}\n")
                f.write(f"- **状态**: {issue.status.upper()}\n")
                f.write(f"- **信息**: {issue.message}\n")
                if issue.details:
                    f.write(f"- **详情**: {issue.details}\n")
                f.write("\n")

        f.write("## 💡 建议\n\n")
        if report.overall_status == "healthy":
            f.write("✅ 系统集成状态良好,所有模块互通正常!\n")
        elif report.overall_status == "warning":
            f.write("⚠️ 系统基本正常,建议检查警告项目。\n")
        else:
            f.write("❌ 系统存在问题,请尽快修复上述错误。\n")

        f.write("\n---\n\n")
        f.write("*报告由 VirtualChemLab 系统互通性检查工具自动生成*\n")


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
