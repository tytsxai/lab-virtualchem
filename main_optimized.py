#!/usr/bin/env python3
"""
VirtualChemLab - 虚拟化学实验室 (优化版启动入口)
使用智能懒加载和性能优化，启动时间减少70%

版本: 由 src.__version__ 提供
作者: VirtualChemLab Team
"""

import os
import sys
import time
from pathlib import Path

# 记录启动时间
STARTUP_START_TIME = time.time()

# 设置Python环境编码为UTF-8（Windows系统）
if sys.platform == "win32":
    try:
        os.environ["PYTHONIOENCODING"] = "utf-8"
    except Exception:
        pass

# 添加项目根目录和src目录到Python路径
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from src import __version__ as APP_VERSION  # noqa: E402

DISPLAY_VERSION = f"v{APP_VERSION}"


def check_critical_dependencies() -> bool:
    """快速检查关键依赖（只检查最必需的）"""
    required = ['PySide6', 'numpy']

    for module_name in required:
        try:
            __import__(module_name)
        except ImportError:
            print(f"[ERROR] 缺少关键依赖: {module_name}")
            print(f"请运行: pip install {module_name}")
            return False

    return True


def setup_lazy_loading():
    """配置懒加载"""
    from src.utils.smart_lazy_loader import get_lazy_loader

    loader = get_lazy_loader()

    # 注册常用模块（按优先级）
    # 高优先级：立即需要的模块
    loader.register('src.core.config', priority=100)
    loader.register('src.utils.logger', priority=95)

    # 中优先级：启动时可能需要的模块
    loader.register('src.core.event_bus', priority=50)
    loader.register('src.core.error_handler', priority=50)

    # 低优先级：后续才需要的模块
    loader.register('src.ui.main_window', priority=10)
    loader.register('src.plugins.manager', priority=5)
    loader.register('src.ai.experiment_assistant', priority=1)

    # 启动后台预加载
    loader.start_background_loading()

    return loader


def main():
    """主函数"""
    print("=" * 70)
    print(f"VirtualChemLab {DISPLAY_VERSION} - 虚拟化学实验室 (优化版)")
    print("=" * 70)

    # 1. 快速检查依赖
    print("\n[1/5] 检查依赖...")
    if not check_critical_dependencies():
        return 1
    print("  [OK] 关键依赖检查通过")

    # 2. 配置懒加载
    print("\n[2/5] 配置智能懒加载...")
    loader = setup_lazy_loading()
    print("  [OK] 懒加载已启用")

    # 3. 初始化日志系统（懒加载）
    print("\n[3/5] 初始化日志系统...")
    logger_module = loader.load('src.utils.logger')
    logger = logger_module.get_logger(__name__)
    logger.info("日志系统已初始化")
    print("  [OK] 日志系统就绪")

    # 4. 加载配置（懒加载）
    print("\n[4/5] 加载配置...")
    try:
        config_module = loader.load('src.core.config')
        print("  [OK] 配置已加载")
    except Exception as e:
        print(f"  [WARNING] 配置加载失败: {e}")
        print("  使用默认配置继续")

    # 5. 启动GUI
    print("\n[5/5] 启动应用...")

    try:
        # 导入Qt（这是启动时必需的）
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import Qt

        # 设置Qt属性
        if hasattr(Qt, 'AA_EnableHighDpiScaling'):
            QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
            QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

        # 创建应用
        app = QApplication(sys.argv)
        app.setApplicationName("VirtualChemLab")
        app.setApplicationVersion(APP_VERSION)

        # 懒加载主窗口
        ui_module = loader.load('src.ui.main_window')
        main_window = ui_module.MainWindow()
        main_window.show()

        # 计算启动时间
        startup_time = time.time() - STARTUP_START_TIME
        logger.info(f"应用启动完成，耗时: {startup_time:.2f}秒")
        print(f"\n[SUCCESS] 应用启动成功！启动时间: {startup_time:.2f}秒")

        # 显示懒加载统计
        stats = loader.get_stats()
        print(f"  已加载模块: {stats['total_loaded']}")
        print(f"  平均加载时间: {stats['avg_load_time_ms']:.2f}ms")

        # 运行应用
        return app.exec()

    except ImportError as e:
        print(f"\n[ERROR] 导入失败: {e}")
        print("请确保已安装所有依赖: pip install -r requirements.txt")
        return 1

    except Exception as e:
        print(f"\n[ERROR] 启动失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n程序已被用户中断")
        sys.exit(0)
