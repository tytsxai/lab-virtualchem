"""
导入测试脚本
"""

import sys
import traceback
sys.path.insert(0, '.')
sys.path.insert(0, 'src')

def test_imports():
    """测试所有关键模块的导入"""
    modules_to_test = [
        'src.core.error_handler',
        'src.core.config_manager',
        'src.utils.logger',
        'src.performance.integrated_optimizer',
        'src.core.user_workflow_manager',
        'src.ui.main_window',
        'src.ui.enhanced_feedback',
        'src.ui.settings_dialog',
        'src.ui.context_help',
        'src.ui.user_preferences',
        'src.ui.splash_screen',
        'src.ui.startup_checklist',
        'src.core.service_registration',
        'src.core.di_container',
        'src.core.event_bus',
        'src.core.event_setup',
        'src.core.crypto_payment',
        'src.ui.achievement_dialog',
        'src.ui.customization.theme_manager',
        'src.ui.dev_console',
        'src.ui.gamification.gamification_panel',
        'src.ui.gamification.level_up_dialog',
    ]

    failed = []
    passed = []

    for module in modules_to_test:
        try:
            __import__(module)
            passed.append(module)
            print(f'OK: {module}')
        except Exception as e:
            failed.append((module, str(e)))
            print(f'ERROR: {module}: {e}')

    print(f'\nSUMMARY:')
    print(f'PASSED: {len(passed)}/{len(modules_to_test)}')
    print(f'FAILED: {len(failed)}/{len(modules_to_test)}')

    if failed:
        print('\nFAILED MODULES:')
        for module, error in failed:
            print(f'  {module}: {error}')

    return len(failed) == 0

if __name__ == '__main__':
    success = test_imports()
    if success:
        print('\nALL CRITICAL MODULES IMPORT SUCCESSFULLY!')
    else:
        print('\nSOME MODULES FAILED TO IMPORT.')
    sys.exit(0 if success else 1)
