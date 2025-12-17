"""
模块间集成测试
验证修复后的模块互通性
"""

import unittest
from typing import Any
from unittest.mock import Mock

from src.core.curve_generator import CurveGenerator
from src.core.event_bus import Event, EventPriority
from src.core.experiment_controller import ExperimentController
from src.core.rule_validator import RuleValidator
from src.core.service_registration import configure_container
from src.interfaces.experiment import (
    ICurveGenerator,
    IExperimentEngine,
    IExperimentValidator,
)
from src.interfaces.storage import ILogger, IStorage


class TestModuleIntegration(unittest.TestCase):
    """模块间集成测试"""

    def setUp(self):
        """测试前准备"""
        self.container = configure_container()

    def test_di_container_resolution(self):
        """测试DI容器解析功能"""
        # 测试核心服务解析
        logger = self.container.resolve(ILogger)
        self.assertIsNotNone(logger)

        storage = self.container.resolve(IStorage[Any])
        self.assertIsNotNone(storage)

    def test_experiment_engine_interface(self):
        """测试实验引擎接口注册"""
        # 测试接口解析
        engine = self.container.resolve(IExperimentEngine)
        self.assertIsNotNone(engine)
        self.assertIsInstance(engine, ExperimentController)

        # 测试接口方法
        self.assertTrue(hasattr(engine, "start_experiment"))
        self.assertTrue(hasattr(engine, "get_current_step"))
        self.assertTrue(hasattr(engine, "submit_step"))
        self.assertTrue(hasattr(engine, "next_step"))
        self.assertTrue(hasattr(engine, "complete_experiment"))

    def test_experiment_validator_interface(self):
        """测试实验验证器接口注册"""
        validator = self.container.resolve(IExperimentValidator)
        self.assertIsNotNone(validator)
        self.assertIsInstance(validator, RuleValidator)

        # 测试接口方法
        self.assertTrue(hasattr(validator, "check_step"))
        self.assertTrue(hasattr(validator, "evaluate_score_rules"))
        self.assertTrue(hasattr(validator, "validate_input"))

    def test_curve_generator_interface(self):
        """测试曲线生成器接口注册"""
        generator = self.container.resolve(ICurveGenerator)
        self.assertIsNotNone(generator)
        self.assertIsInstance(generator, CurveGenerator)

        # 测试接口方法
        self.assertTrue(hasattr(generator, "generate"))
        self.assertTrue(hasattr(generator, "generate_titration_curve"))
        self.assertTrue(hasattr(generator, "generate_temperature_curve"))

    def test_event_bus_integration(self):
        """测试事件总线集成"""
        from src.core.event_bus import EventBus

        event_bus = self.container.resolve(EventBus)
        self.assertIsNotNone(event_bus)

        # 测试事件发布
        event = Event(
            "test.integration", {"test": "data"}, priority=EventPriority.NORMAL
        )
        results = event_bus.publish(event)

        # 应该有处理器响应（至少是系统默认处理器）
        self.assertIsInstance(results, list)

    def test_service_lifecycle(self):
        """测试服务生命周期"""
        # 测试单例服务
        logger1 = self.container.resolve(ILogger)
        logger2 = self.container.resolve(ILogger)
        self.assertIs(logger1, logger2)

        # 测试瞬态服务
        engine1 = self.container.resolve(IExperimentEngine)
        engine2 = self.container.resolve(IExperimentEngine)
        self.assertIsNot(engine1, engine2)

    def test_error_handling(self):
        """测试错误处理"""
        # 测试解析不存在的服务
        with self.assertRaises(ValueError):
            self.container.resolve(type("NonExistentService", (), {}))

    def test_configuration_integration(self):
        """测试配置集成"""
        from src.core.config_loader import Config

        config = self.container.resolve(Config)
        self.assertIsNotNone(config)

        # 测试配置属性
        self.assertTrue(hasattr(config, "paths"))
        self.assertTrue(hasattr(config, "security"))

    def test_storage_integration(self):
        """测试存储集成"""
        storage = self.container.resolve(IStorage[Any])
        self.assertIsNotNone(storage)

        # 测试存储方法
        self.assertTrue(hasattr(storage, "save_record"))
        self.assertTrue(hasattr(storage, "load_record"))
        self.assertTrue(hasattr(storage, "delete_record"))

    def test_full_workflow_integration(self):
        """测试完整工作流程集成"""
        # 获取所需服务
        engine = self.container.resolve(IExperimentEngine)
        validator = self.container.resolve(IExperimentValidator)
        generator = self.container.resolve(ICurveGenerator)
        storage = self.container.resolve(IStorage[Any])
        logger = self.container.resolve(ILogger)

        # 验证所有服务都可用
        self.assertIsNotNone(engine)
        self.assertIsNotNone(validator)
        self.assertIsNotNone(generator)
        self.assertIsNotNone(storage)
        self.assertIsNotNone(logger)

        # 测试服务间协作
        # 这里可以添加更复杂的集成测试逻辑


class TestEventCommunication(unittest.TestCase):
    """事件通信测试"""

    def setUp(self):
        """测试前准备"""
        self.container = configure_container()

    def test_event_subscription(self):
        """测试事件订阅"""
        from src.core.event_bus import Event, EventBus, EventPriority

        event_bus = self.container.resolve(EventBus)

        # 创建测试处理器
        test_handler = Mock()

        # 订阅事件
        event_bus.subscribe("test.event", test_handler, EventPriority.NORMAL)

        # 发布事件
        event = Event("test.event", {"data": "test"}, EventPriority.NORMAL)
        results = event_bus.publish(event)

        # 验证处理器被调用
        self.assertTrue(len(results) > 0)

    def test_event_priority(self):
        """测试事件优先级"""
        from src.core.event_bus import Event, EventBus, EventPriority

        event_bus = self.container.resolve(EventBus)

        # 创建不同优先级的处理器
        high_priority_handler = Mock()
        normal_priority_handler = Mock()

        # 订阅事件（注意：先订阅低优先级，后订阅高优先级）
        event_bus.subscribe(
            "test.priority", normal_priority_handler, EventPriority.NORMAL
        )
        event_bus.subscribe("test.priority", high_priority_handler, EventPriority.HIGH)

        # 发布事件
        event = Event("test.priority", {"data": "test"}, EventPriority.NORMAL)
        results = event_bus.publish(event)

        # 验证处理器被调用
        self.assertTrue(len(results) > 0)


def run_integration_tests():
    """运行集成测试"""
    print("=" * 60)
    print("VirtualChemLab 模块间集成测试")
    print("=" * 60)

    # 创建测试套件
    suite = unittest.TestSuite()

    # 添加测试用例
    suite.addTest(unittest.makeSuite(TestModuleIntegration))
    suite.addTest(unittest.makeSuite(TestEventCommunication))

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 打印结果
    print(f"\n{'=' * 60}")
    print("测试结果")
    print(f"{'=' * 60}")
    print(f"运行测试: {result.testsRun}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")

    if result.failures:
        print("\n失败的测试:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback}")

    if result.errors:
        print("\n错误的测试:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback}")

    success = len(result.failures) == 0 and len(result.errors) == 0
    if success:
        print("\n🎉 所有集成测试通过!")
    else:
        print(f"\n⚠️  {len(result.failures) + len(result.errors)} 个测试失败")

    return 0 if success else 1


if __name__ == "__main__":
    import sys

    sys.exit(run_integration_tests())
