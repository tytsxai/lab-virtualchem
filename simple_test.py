"""
简单系统测试
"""

import sys
import time
sys.path.insert(0, '.')
sys.path.insert(0, 'src')

def main():
    """主测试函数"""
    print("VirtualChemLab System Test")
    print("=" * 40)

    # 测试核心模块
    core_modules = [
        'src.core.config_manager',
        'src.utils.logger',
        'src.core.error_handler',
        'src.core.user_workflow_manager',
        'src.performance.integrated_optimizer',
    ]

    print("Testing core modules...")
    for module in core_modules:
        try:
            __import__(module)
            print(f"  OK: {module}")
        except Exception as e:
            print(f"  ERROR: {module}: {e}")
            return False

    # 测试UI模块
    ui_modules = [
        'src.ui.main_window',
        'src.ui.enhanced_feedback',
        'src.ui.settings_dialog',
        'src.ui.context_help',
    ]

    print("Testing UI modules...")
    for module in ui_modules:
        try:
            __import__(module)
            print(f"  OK: {module}")
        except Exception as e:
            print(f"  ERROR: {module}: {e}")
            return False

    print("=" * 40)
    print("All critical modules imported successfully!")
    print("VirtualChemLab system is ready!")

    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Test failed: {e}")
        sys.exit(1)
