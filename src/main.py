"""VirtualChemLab 应用入口"""

import os
import sys
from pathlib import Path

# 设置Python环境编码为UTF-8（Windows系统）
if sys.platform == "win32":
    # 设置控制台代码页为UTF-8
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    # 设置环境变量
    os.environ["PYTHONIOENCODING"] = "utf-8"

# 添加项目根目录到Python路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import logging  # noqa: E402

from src.core.config_loader import get_config  # noqa: E402
from src.core.service_registration import configure_container  # noqa: E402
from src.core.startup_preflight import ensure_secure_startup  # noqa: E402
from src.utils.logger import get_logger, setup_logger  # noqa: E402

from . import __version__ as APP_VERSION  # noqa: E402

# 设置日志
setup_logger("virtualchemlab", logging.INFO)
logger = get_logger(__name__)
DISPLAY_VERSION = f"v{APP_VERSION}"


def main() -> int:
    """应用主入口

    Returns:
        退出代码
    """
    logger.info("=" * 60)
    logger.info("VirtualChemLab - 虚拟化学实验室")
    logger.info("版本: %s", DISPLAY_VERSION)
    logger.info("=" * 60)

    try:
        # 1. 加载配置
        config = get_config()
        logger.info("✅ 配置加载完成")
        logger.info(f"   环境: {config.app.environment}")
        logger.info(f"   调试模式: {config.app.debug}")

        # 1.1 统一的启动前安全校验（密钥长度/存在性）
        ensure_secure_startup(config=config)

        # 2. 检查依赖
        try:
            from PySide6.QtCore import Qt  # type: ignore
            from PySide6.QtWidgets import QApplication  # type: ignore
        except ImportError:
            logger.error("❌ PySide6 未安装，请运行: pip install -r requirements.txt")
            return 1

        # 3. 配置DI容器
        logger.info("⚙️ 配置依赖注入容器...")
        container = configure_container(config=config)
        logger.info(f"✅ 已注册 {len(container.get_all_services())} 个服务")

        # 4. 启用高DPI支持
        try:
            from src.ui.responsive import DPIHelper

            DPIHelper.enable_high_dpi_scaling()
        except Exception as e:
            logger.warning(f"高DPI设置警告: {e}")
            if hasattr(Qt, "AA_EnableHighDpiScaling"):
                QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
            if hasattr(Qt, "AA_UseHighDpiPixmaps"):
                QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

        # 5. 启动Qt应用
        logger.info("🚀 启动GUI应用...")
        app = QApplication(sys.argv)
        app.setApplicationName("VirtualChemLab")
        app.setApplicationDisplayName("虚拟化学实验室")
        app.setApplicationVersion(APP_VERSION)
        app.setOrganizationName("VirtualChemLab")

        # Windows任务栏图标设置
        if sys.platform == "win32":
            try:
                import ctypes

                app_id = f"VirtualChemLab.Desktop.{APP_VERSION}"
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
            except Exception:
                pass

        # 6. 创建主窗口（使用DI容器）
        from src.ui.main_window import MainWindow

        window = MainWindow(container=container)
        window.show()

        logger.info("✅ 应用启动成功")
        logger.info("=" * 60)

        # 7. 运行事件循环
        return app.exec()

    except KeyboardInterrupt:
        logger.info("\n⚠️ 用户中断")
        return 0
    except Exception as e:
        logger.error(f"❌ 应用启动失败: {e}")
        return 1


def test_core_only() -> int:
    """仅测试核心功能（不启动GUI）

    Returns:
        退出代码
    """
    logger.info("=" * 60)
    logger.info("核心引擎测试模式")
    logger.info("=" * 60)

    try:
        # 加载配置
        config = get_config()
        logger.info(f"✅ 配置加载完成: {config.app.name} v{config.app.version}")

        # 配置容器
        container = configure_container(config=config)
        logger.info(f"✅ DI容器已配置: {len(container.get_all_services())} 个服务")

        # 测试核心服务
        from src.core.curve_generator import CurveGenerator
        from src.core.template_engine import TemplateEngine

        # 测试模板引擎
        template_engine = container.resolve(TemplateEngine)
        logger.info("\n📋 可用实验:")
        experiments = template_engine.list_available_experiments()

        if not experiments:
            logger.warning("  未找到实验模板，请确保 assets/templates/ 目录存在")
        else:
            for exp in experiments:
                logger.info(f"  - {exp['id']}: {exp['title']} ({exp['level']})")

        # 测试曲线生成
        curve_gen = container.resolve(CurveGenerator)
        logger.info("\n📊 测试滴定曲线生成...")
        curve_data = curve_gen.generate_titration_curve(acid_type="strong", acid_M=0.1, acid_V_ml=25.0, base_M=0.1)
        V = curve_data[0]
        logger.info("  ✅ 成功生成 %d 个数据点", len(V))

        logger.info("\n" + "=" * 60)
        logger.info("✅ 核心引擎测试完成!")
        logger.info("=" * 60)

        return 0

    except Exception as e:
        logger.exception(f"❌ 测试失败: {e}")
        return 1


if __name__ == "__main__":
    # 检查命令行参数
    if len(sys.argv) > 1 and sys.argv[1] == "--test-core":
        # 仅测试核心功能
        sys.exit(test_core_only())
    else:
        # 启动完整应用
        sys.exit(main())
