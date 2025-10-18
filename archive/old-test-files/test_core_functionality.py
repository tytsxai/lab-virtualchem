"""
测试核心功能
"""

import sys
sys.path.insert(0, '.')
sys.path.insert(0, 'src')

def test_core_functionality():
    """测试核心功能"""
    print('Testing core functionality...')

    try:
        # 测试配置管理器
        from src.core.config_manager import ConfigManager
        config_manager = ConfigManager()
        app_name = config_manager.get('app.name', 'VirtualChemLab')
        print(f'  ConfigManager: OK (app.name = {app_name})')

        # 测试日志系统
        from src.utils.logger import get_logger, get_log_stats
        logger = get_logger('test')
        logger.info('Testing logger system')
        stats = get_log_stats()
        print(f'  Logger: OK (total entries: {stats["total"]})')

        # 测试错误处理器
        from src.core.error_handler import ErrorHandler, ErrorContext
        error_handler = ErrorHandler()
        context = ErrorContext(component='test')
        result = error_handler.handle_error(ValueError('Test error'), context)
        print(f'  ErrorHandler: OK (handled: {result})')

        # 测试性能优化器
        from src.performance.integrated_optimizer import IntegratedPerformanceOptimizer
        optimizer = IntegratedPerformanceOptimizer()
        summary = optimizer.get_performance_summary()
        print(f'  PerformanceOptimizer: OK (status: {summary["status"]})')

        # 测试UI组件
        from src.ui.enhanced_feedback import FeedbackManager
        feedback_mgr = FeedbackManager.instance()
        print(f'  FeedbackManager: OK (instance: {feedback_mgr is not None})')

        print('\nAll core functionality tests passed!')
        return True

    except Exception as e:
        print(f'ERROR: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_core_functionality()
    sys.exit(0 if success else 1)
