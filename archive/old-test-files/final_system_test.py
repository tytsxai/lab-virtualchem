"""
最终系统测试
验证整个VirtualChemLab系统的完整性和功能性
"""

import sys
import time
import traceback
sys.path.insert(0, '.')
sys.path.insert(0, 'src')

def test_system_completeness():
    """测试系统完整性"""
    print("🔬 VirtualChemLab 系统完整性测试")
    print("=" * 50)

    # 测试核心模块
    core_modules = [
        'src.core.config_manager',
        'src.utils.logger',
        'src.core.error_handler',
        'src.core.user_workflow_manager',
        'src.core.service_registration',
        'src.core.di_container',
        'src.core.event_bus',
        'src.performance.integrated_optimizer',
    ]

    print("📦 测试核心模块...")
    for module in core_modules:
        try:
            __import__(module)
            print(f"  ✅ {module}")
        except Exception as e:
            print(f"  ❌ {module}: {e}")
            return False

    # 测试UI模块
    ui_modules = [
        'src.ui.main_window',
        'src.ui.enhanced_feedback',
        'src.ui.settings_dialog',
        'src.ui.context_help',
        'src.ui.user_preferences',
        'src.ui.splash_screen',
        'src.ui.startup_checklist',
        'src.ui.achievement_dialog',
        'src.ui.customization.theme_manager',
        'src.ui.dev_console',
        'src.ui.gamification.gamification_panel',
        'src.ui.gamification.level_up_dialog',
    ]

    print("🎨 测试UI模块...")
    for module in ui_modules:
        try:
            __import__(module)
            print(f"  ✅ {module}")
        except Exception as e:
            print(f"  ❌ {module}: {e}")
            return False

    # 测试工具模块
    utility_modules = [
        'src.utils.lazy_import',
        'src.utils.startup_optimizer',
        'src.utils.safe_io',
        'src.utils.safe_network',
        'src.core.crypto_payment',
        'src.core.event_setup',
    ]

    print("🛠️ 测试工具模块...")
    for module in utility_modules:
        try:
            __import__(module)
            print(f"  ✅ {module}")
        except Exception as e:
            print(f"  ❌ {module}: {e}")
            return False

    return True

def test_functionality():
    """测试基本功能"""
    print("⚡ 测试基本功能...")
    try:
        # 测试配置管理器
        from src.core.config_manager import ConfigManager
        config_manager = ConfigManager()
        test_config = config_manager.get("app.name", "VirtualChemLab")
        assert test_config == "VirtualChemLab"
        print("  ✅ 配置管理器正常工作")

        # 测试日志系统
        from src.utils.logger import get_logger, get_log_stats
        logger = get_logger("test")
        logger.info("测试日志消息")
        stats = get_log_stats()
        assert "total" in stats
        print("  ✅ 日志系统正常工作")

        # 测试错误处理器
        from src.core.error_handler import ErrorHandler, ErrorContext
        error_handler = ErrorHandler()
        context = ErrorContext(component="test")
        result = error_handler.handle_error(ValueError("测试错误"), context)
        assert result is True
        print("  ✅ 错误处理器正常工作")

        # 测试性能优化器
        from src.performance.integrated_optimizer import IntegratedPerformanceOptimizer
        optimizer = IntegratedPerformanceOptimizer()
        summary = optimizer.get_performance_summary()
        assert "status" in summary
        print("  ✅ 性能优化器正常工作")

        return True

    except Exception as e:
        print(f"  ❌ 功能测试失败: {e}")
        traceback.print_exc()
        return False

def test_ui_components():
    """测试UI组件"""
    print("🖼️ 测试UI组件...")
    try:
        # 测试反馈管理器
        from src.ui.enhanced_feedback import FeedbackManager
        feedback_mgr = FeedbackManager.instance()
        assert feedback_mgr is not None
        print("  ✅ 反馈管理器正常工作")

        # 测试主题管理器
        from src.ui.customization.theme_manager import ThemeManager
        theme_mgr = ThemeManager()
        current_theme = theme_mgr.get_current_theme()
        assert current_theme is not None
        print("  ✅ 主题管理器正常工作")

        # 测试成就对话框
        from src.ui.achievement_dialog import Achievement
        achievement = Achievement("test", "测试成就", "这是一个测试成就")
        assert achievement.name == "测试成就"
        print("  ✅ 成就系统正常工作")

        # 测试游戏化面板
        from src.ui.gamification.gamification_panel import GamificationPanel
        panel = GamificationPanel()
        assert panel.level_card is not None
        print("  ✅ 游戏化面板正常工作")

        return True

    except Exception as e:
        print(f"  ❌ UI组件测试失败: {e}")
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    start_time = time.time()

    print("🚀 开始VirtualChemLab系统完整性测试")
    print(f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # 测试系统完整性
    completeness_ok = test_system_completeness()
    if not completeness_ok:
        print("\n❌ 系统完整性测试失败！")
        return False

    print()

    # 测试基本功能
    functionality_ok = test_functionality()
    if not functionality_ok:
        print("\n❌ 功能测试失败！")
        return False

    print()

    # 测试UI组件
    ui_ok = test_ui_components()
    if not ui_ok:
        print("\n❌ UI组件测试失败！")
        return False

    # 计算测试耗时
    elapsed_time = time.time() - start_time

    print()
    print("=" * 50)
    print("🎉 VirtualChemLab 系统测试完成！")
    print(f"测试耗时: {elapsed_time:.2f}秒")
    print()
    print("✅ 系统完整性: 通过")
    print("✅ 基本功能: 通过")
    print("✅ UI组件: 通过")
    print()
    print("🎊 VirtualChemLab 系统已准备就绪！")
    print("=" * 50)

    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n测试过程中发生异常: {e}")
        traceback.print_exc()
        sys.exit(1)
