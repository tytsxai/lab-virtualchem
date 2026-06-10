"""VirtualChemLab 应用入口（包内入口）。

说明：
- 仓库根目录的 `main.py` 是“薄转发”入口，用于兼容 `python main.py` 并统一启动链路。
- 本包是实际的应用启动实现：配置加载 -> 启动前安全闸 -> DI 容器 -> Qt 应用。

CLI 兼容：
文档与部分脚本会使用 `--env development` 选择环境；底层配置系统以环境变量
`ENVIRONMENT` 为准，因此这里会把 `--env` 映射到 `ENVIRONMENT`，并从 `sys.argv`
移除该参数，避免 Qt 将其当作未知选项。
"""

from __future__ import annotations

import atexit
import logging
import os
import sys
import threading
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from src.core.config_loader import get_config
from src.core.service_registration import configure_container
from src.core.startup_preflight import ensure_secure_startup
from src.utils.logger import get_logger, setup_logger

from .. import __version__ as APP_VERSION

# 设置Python环境编码为UTF-8（Windows系统）
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    os.environ["PYTHONIOENCODING"] = "utf-8"

# 添加项目根目录到Python路径（安全校验）
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if PROJECT_ROOT.is_dir() and (PROJECT_ROOT / "src").is_dir():
    project_root_str = str(PROJECT_ROOT)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)

# 设置日志
setup_logger("virtualchemlab", logging.INFO)
logger = get_logger(__name__)
std_logger = logging.getLogger(__name__)
DISPLAY_VERSION = f"v{APP_VERSION}"


def _resolve_log_file_path(config: object, *, project_root: Path) -> Path:
    logs_subdir = getattr(getattr(config, "paths", object()), "logs", "logs")
    logs_dir = (project_root / str(logs_subdir)).resolve()
    logs_dir.mkdir(parents=True, exist_ok=True)

    requested = Path(str(getattr(getattr(config, "log", object()), "file", "app.log")))
    if requested.is_absolute():
        requested = Path(requested.name)

    if requested.parts and requested.parts[0] == logs_dir.name:
        requested = Path(*requested.parts[1:])

    candidate = (logs_dir / requested).resolve()
    if not candidate.is_relative_to(logs_dir):
        return (logs_dir / "app.log").resolve()

    candidate.parent.mkdir(parents=True, exist_ok=True)
    return candidate


def _redact_startup_error(exc: BaseException) -> str:
    errno = getattr(exc, "errno", None)
    if errno is not None:
        return f"{exc.__class__.__name__}(errno={errno})"
    return exc.__class__.__name__


def _install_exit_cleanup_hook(cleanup: Callable[[], object]) -> None:
    atexit.register(cleanup)


def _install_global_exception_hooks() -> None:
    """Ensure unexpected exceptions are visible in logs (incl. background threads)."""

    root_logger = logging.getLogger("virtualchemlab")

    def _handle_unhandled(exc_type, exc, tb):  # noqa: ANN001
        root_logger.critical("Unhandled exception", exc_info=(exc_type, exc, tb))

    sys.excepthook = _handle_unhandled

    if hasattr(threading, "excepthook"):

        def _handle_thread(args):  # noqa: ANN001
            root_logger.critical(
                "Unhandled thread exception",
                exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
            )

        threading.excepthook = _handle_thread  # type: ignore[assignment]


def _apply_cli_environment_overrides(argv: list[str]) -> list[str]:
    """Parse `--env`/`--env=...` from argv and map it to `ENVIRONMENT`."""
    if len(argv) <= 1:
        return argv

    cleaned: list[str] = [argv[0]]
    idx = 1
    while idx < len(argv):
        token = argv[idx]
        if token == "--env":
            value = argv[idx + 1] if idx + 1 < len(argv) else ""
            if value:
                os.environ["ENVIRONMENT"] = _normalize_environment_name(value)
            idx += 2
            continue
        if token.startswith("--env="):
            value = token.split("=", 1)[1].strip()
            if value:
                os.environ["ENVIRONMENT"] = _normalize_environment_name(value)
            idx += 1
            continue
        cleaned.append(token)
        idx += 1
    return cleaned


def _normalize_environment_name(value: str) -> str:
    """Normalize common CLI aliases to config-supported environment names."""
    normalized = value.strip().lower()
    aliases = {
        "dev": "development",
        "prod": "production",
        "stage": "staging",
    }
    return aliases.get(normalized, normalized)


def main() -> int:
    """应用主入口

    Returns:
        退出代码
    """
    _install_global_exception_hooks()
    sys.argv = _apply_cli_environment_overrides(sys.argv)
    logger.info("=" * 60)
    logger.info("VirtualChemLab - 虚拟化学实验室")
    logger.info("版本: %s", DISPLAY_VERSION)
    logger.info("=" * 60)

    try:
        try:
            config = get_config()
        except OSError as exc:
            std_logger.error("配置加载失败（已脱敏输出）", exc_info=True)
            sys.stderr.write(
                "\n[ERROR] 配置/数据目录不可写或不可访问，应用无法启动。\n"
                "建议：\n"
                "  1) 关闭程序后重试（避免文件被占用）\n"
                "  2) 确保磁盘空间充足\n"
                "  3) 设置环境变量 VCL_DATA_DIR 指向可写目录\n"
                "  4) 或设置 VCL_CONFIG_PATH 指向可写的 config.json 路径\n"
                f"错误类型: {_redact_startup_error(exc)}\n"
                "详细堆栈已写入日志。\n\n"
            )
            return 1

        resolved_log_file = _resolve_log_file_path(config, project_root=PROJECT_ROOT)
        setup_logger(
            "virtualchemlab",
            level=getattr(config.log, "level", "INFO"),
            log_file=resolved_log_file,
            max_bytes=int(getattr(config.log, "max_size", 10 * 1024 * 1024)),
            backup_count=int(getattr(config.log, "backup_count", 5)),
            enable_console=True,
            replace_handlers=True,
        )
        logger.info(
            "logging initialized: file=%s utc=%s",
            str(resolved_log_file),
            datetime.now(timezone.utc).isoformat(),
        )
        logger.info("✅ 配置加载完成")
        logger.info(
            "   环境: %s", getattr(getattr(config, "app", object()), "environment", "")
        )
        logger.info(
            "   调试模式: %s", getattr(getattr(config, "app", object()), "debug", "")
        )

        ensure_secure_startup(config=config)

        from src.ui.qt_sanity import ensure_single_qt_binding

        ensure_single_qt_binding(abort=True)

        try:
            from PySide6.QtCore import Qt  # type: ignore
            from PySide6.QtWidgets import QApplication  # type: ignore
        except ImportError:
            logger.error("❌ PySide6 未安装，请运行: pip install -r requirements.lock")
            return 1

        logger.info("⚙️ 配置依赖注入容器...")
        container = configure_container(config=config)
        logger.info("✅ 已注册 %d 个服务", len(container.get_all_services()))

        try:
            from src.ui.responsive import DPIHelper

            DPIHelper.enable_high_dpi_scaling()
        except Exception as exc:  # noqa: BLE001
            logger.warning("高DPI设置警告: %s", exc)
            if hasattr(Qt, "AA_EnableHighDpiScaling"):
                QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
            if hasattr(Qt, "AA_UseHighDpiPixmaps"):
                QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

        logger.info("🚀 启动GUI应用...")
        app = QApplication(sys.argv)
        app.setApplicationName("VirtualChemLab")
        app.setApplicationDisplayName("虚拟化学实验室")
        app.setApplicationVersion(APP_VERSION)
        app.setOrganizationName("VirtualChemLab")

        if sys.platform == "win32":
            try:
                import ctypes

                app_id = f"VirtualChemLab.Desktop.{APP_VERSION}"
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
            except Exception:
                pass

        from src.ui.main_window import MainWindow

        window = MainWindow(container=container)
        window.show()

        logger.info("✅ 应用启动成功")
        logger.info("=" * 60)

        def _cleanup() -> None:
            try:
                logging.shutdown()
            except Exception:
                pass

        _install_exit_cleanup_hook(_cleanup)
        try:
            app.aboutToQuit.connect(_cleanup)  # type: ignore[attr-defined]
        except Exception:
            pass

        return app.exec()

    except KeyboardInterrupt:
        logger.info("\n⚠️ 用户中断")
        return 0
    except Exception:
        std_logger.critical("❌ 应用启动失败", exc_info=True)
        return 1


def test_core_only() -> int:
    """仅测试核心功能（不启动GUI）"""
    logger.info("=" * 60)
    logger.info("核心引擎测试模式")
    logger.info("=" * 60)

    try:
        config = get_config()
        logger.info("✅ 配置加载完成: %s v%s", config.app.name, config.app.version)

        container = configure_container(config=config)
        logger.info("✅ DI容器已配置: %d 个服务", len(container.get_all_services()))

        from src.core.curve_generator import CurveGenerator
        from src.core.template_engine import TemplateEngine

        template_engine = container.resolve(TemplateEngine)
        logger.info("\n📋 可用实验:")
        experiments = template_engine.list_available_experiments()

        if not experiments:
            logger.warning("  未找到实验模板，请确保 assets/templates/ 目录存在")
        else:
            for exp in experiments:
                logger.info("  - %s: %s (%s)", exp["id"], exp["title"], exp["level"])

        curve_gen = container.resolve(CurveGenerator)
        logger.info("\n📊 测试滴定曲线生成...")
        curve_data = curve_gen.generate_titration_curve(
            acid_type="strong", acid_M=0.1, acid_V_ml=25.0, base_M=0.1
        )
        V = curve_data[0]
        logger.info("  ✅ 成功生成 %d 个数据点", len(V))

        logger.info("\n" + "=" * 60)
        logger.info("✅ 核心引擎测试完成!")
        logger.info("=" * 60)

        return 0

    except Exception as exc:  # noqa: BLE001
        logger.exception("❌ 测试失败: %s", exc)
        return 1
