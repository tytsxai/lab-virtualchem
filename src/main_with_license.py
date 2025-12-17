"""
VirtualChemLab 应用入口 (含许可证验证)

集成了加密货币支付许可证系统的版本
"""

import os
import sys
from pathlib import Path

# 设置Python环境编码为UTF-8（Windows系统）
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    os.environ["PYTHONIOENCODING"] = "utf-8"

# 添加项目根目录到Python路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import asyncio  # noqa: E402
import logging  # noqa: E402

from src.core.license_manager import LicenseManager  # noqa: E402
from src.core.license_middleware import (  # noqa: E402
    LicenseException,
    LicenseMiddleware,
)
from src.core.startup_preflight import ensure_secure_startup  # noqa: E402
from src.utils.config import Config  # noqa: E402
from src.utils.logger import setup_logger  # noqa: E402

from . import __version__ as APP_VERSION  # noqa: E402

logger = setup_logger("virtualchemlab", logging.INFO)
DISPLAY_VERSION = f"v{APP_VERSION}"


def check_license() -> bool:
    """检查许可证

    Returns:
        是否通过验证
    """
    try:
        # 从配置文件读取密钥
        config_file = PROJECT_ROOT / "config" / "crypto_payment_config.json"

        if config_file.exists():
            import json

            with open(config_file, encoding="utf-8") as f:
                config = json.load(f)
                secret_key = config.get("license", {}).get(
                    "secret_key", "default_secret_key"
                )
                strict_mode = config.get("license", {}).get("strict_mode", False)
                trial_days = config.get("license", {}).get("trial_days", 7)
        else:
            logger.warning("未找到许可证配置文件,使用默认配置")
            secret_key = "default_secret_key"
            strict_mode = False
            trial_days = 7

        # 创建许可证管理器
        license_file = PROJECT_ROOT / "data" / "license.json"
        license_manager = LicenseManager(secret_key, license_file)

        # 创建中间件
        middleware = LicenseMiddleware(
            license_manager=license_manager,
            strict_mode=strict_mode,
            trial_days=trial_days,
        )

        # 执行验证
        async def verify():
            await middleware.process(None, lambda: None)

        asyncio.run(verify())

        # 获取许可证信息
        current_license = middleware.get_current_license()

        if current_license:
            logger.info("=" * 60)
            logger.info("许可证验证通过")

            info = license_manager.get_license_info(current_license)
            logger.info(f"许可证类型: {info['license_type']}")
            logger.info(f"用户: {info['email']}")
            logger.info(f"剩余天数: {info['days_remaining']} 天")

            if info["days_remaining"] < 30:
                logger.warning("⚠️  许可证即将过期,请及时续费")

            logger.info("=" * 60)
        else:
            if not strict_mode:
                logger.warning("=" * 60)
                logger.warning("⚠️  试用模式")
                logger.warning(f"试用期: {trial_days} 天")
                logger.warning("部分功能可能受限")
                logger.warning("=" * 60)
                logger.info("")
                logger.info("💡 购买完整版许可证:")
                logger.info(
                    "   1. 获取机器ID: python tools/license_generator.py machine-id"
                )
                logger.info("   2. 访问: https://virtualchemlab.com")
                logger.info("   3. 支持: BTC, ETH, USDT, TRX 等加密货币支付")
                logger.info("=" * 60)

        return True

    except LicenseException as e:
        logger.error("=" * 60)
        logger.error("❌ 许可证验证失败")
        logger.error(str(e))
        logger.error("=" * 60)
        logger.info("")
        logger.info("💡 获取许可证:")
        logger.info("   1. 获取机器ID:")
        logger.info("      python tools/license_generator.py machine-id")
        logger.info("")
        logger.info("   2. 购买许可证 (支持加密货币):")
        logger.info("      - 个人版: $99 (BTC: 0.0025)")
        logger.info("      - 教育版: $299 (BTC: 0.0075)")
        logger.info("      - 商业版: $999 (BTC: 0.025)")
        logger.info("")
        logger.info("   3. 联系购买:")
        logger.info("      Email: sales@virtualchemlab.com")
        logger.info("      Telegram: @VirtualChemLabSupport")
        logger.info("")
        logger.info("   4. 激活许可证:")
        logger.info(
            "      python tools/license_generator.py activate data/license.json"
        )
        logger.info("=" * 60)

        return False

    except Exception as e:
        logger.error(f"许可证检查出错: {e}")
        logger.warning("跳过许可证检查,继续启动")
        return True


def main() -> int:
    """应用主入口

    Returns:
        退出代码
    """
    logger.info("=" * 60)
    logger.info("VirtualChemLab - 虚拟化学实验室")
    logger.info("版本: %s (加密货币授权版)", DISPLAY_VERSION)
    logger.info("=" * 60)
    logger.info("")

    try:
        # 检查许可证
        if not check_license():
            logger.error("应用启动失败: 许可证验证未通过")
            return 1

        logger.info("")
        logger.info("=" * 60)
        logger.info("应用启动中...")
        logger.info("=" * 60)

        # 加载配置
        config = Config()
        logger.info(f"配置加载完成, 语言: {config.get('app.language')}")

        # 启动前安全校验（密钥长度/存在性）
        ensure_secure_startup(config=config)

        # 检查依赖
        try:
            from PySide6.QtWidgets import QApplication  # noqa: F401
        except ImportError:
            logger.error("PySide6 未安装, 请运行: pip install -r requirements.txt")
            return 1

        # 配置DI容器
        logger.info("⚙️ 配置依赖注入容器...")
        from src.core.service_registration import get_configured_container

        container = get_configured_container()
        logger.info("✅ 服务容器配置完成")

        # 启用高DPI支持
        from PySide6.QtCore import Qt

        try:
            from src.ui.responsive import DPIHelper

            DPIHelper.enable_high_dpi_scaling()
        except Exception as e:
            logger.warning(f"高DPI设置警告: {e}")
            if hasattr(Qt, "AA_EnableHighDpiScaling"):
                QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
            if hasattr(Qt, "AA_UseHighDpiPixmaps"):
                QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

        # 启动Qt应用
        logger.info("🚀 启动GUI应用...")
        app = QApplication(sys.argv)
        app.setApplicationName("VirtualChemLab")
        app.setApplicationDisplayName("虚拟化学实验室 (授权版)")
        app.setOrganizationName("VirtualChemLab")

        # Windows任务栏图标设置
        if sys.platform == "win32":
            try:
                import ctypes

                app_user_model_id = f"VirtualChemLab.Licensed.{APP_VERSION}"
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                    app_user_model_id
                )
            except Exception:
                pass

        # 创建主窗口
        from src.ui.main_window import MainWindow

        window = MainWindow(container=container)
        window.show()

        logger.info("✅ 应用启动成功")
        logger.info("=" * 60)

        # 运行事件循环
        return app.exec()

    except KeyboardInterrupt:
        logger.info("\n用户中断")
        return 0
    except Exception as e:
        logger.exception(f"应用启动失败: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
