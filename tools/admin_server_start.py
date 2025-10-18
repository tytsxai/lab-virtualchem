"""
管理后台服务器启动脚本
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.api.admin_api import create_admin_api  # noqa: E402
from src.utils.logger import get_logger  # noqa: E402

logger = get_logger("admin_server")


def load_config() -> dict[Any, Any]:
    """加载配置"""
    config_file = PROJECT_ROOT / "config" / "crypto_payment_config.json"

    if config_file.exists():
        with open(config_file, encoding="utf-8") as f:
            return json.load(f)
    else:
        logger.warning("未找到配置文件，使用默认配置")
        return {
            "license": {"secret_key": "default_secret_key"},
            "admin_api": {"host": "127.0.0.1", "port": 5000},
        }


def main() -> None:
    """主函数"""
    parser = argparse.ArgumentParser(description="VirtualChemLab 管理后台服务器")
    parser.add_argument("--host", type=str, default=None, help="主机地址（默认: 127.0.0.1）")
    parser.add_argument("--port", type=int, default=None, help="端口（默认: 5000）")
    parser.add_argument("--debug", action="store_true", help="启用调试模式")
    parser.add_argument(
        "--license-file",
        type=str,
        default=None,
        help="许可证文件路径（默认: data/license.json）",
    )

    args = parser.parse_args()

    # 加载配置
    config = load_config()

    # 参数优先级: 命令行 > 配置文件 > 默认值
    host = args.host or config.get("admin_api", {}).get("host", "127.0.0.1")
    port = args.port or config.get("admin_api", {}).get("port", 5000)
    secret_key = config.get("license", {}).get("secret_key", "default_secret_key")

    license_file = Path(args.license_file) if args.license_file else PROJECT_ROOT / "data" / "license.json"

    # 创建API实例
    logger.info("=" * 60)
    logger.info("VirtualChemLab 管理后台服务器")
    logger.info("=" * 60)
    logger.info(f"主机地址: {host}")
    logger.info(f"端口: {port}")
    logger.info(f"许可证文件: {license_file}")
    logger.info(f"调试模式: {'开启' if args.debug else '关闭'}")
    logger.info("=" * 60)

    try:
        api = create_admin_api(license_file=license_file, secret_key=secret_key, host=host, port=port)

        logger.info("\n✅ 服务器已启动！")
        logger.info(f"📊 管理面板: http://{host}:{port}/dashboard")
        logger.info(f"🔌 API地址: http://{host}:{port}/api")
        logger.info("\n按 Ctrl+C 停止服务器\n")

        # 添加静态文件路由（管理面板）
        @api.app.route("/dashboard")
        def dashboard() -> tuple[str, int] | str:
            """管理面板"""
            dashboard_file = PROJECT_ROOT / "src" / "api" / "admin_dashboard.html"
            if dashboard_file.exists():
                with open(dashboard_file, encoding="utf-8") as f:
                    return f.read()
            return "管理面板未找到", 404

        # 启动服务器
        api.run(debug=args.debug)

    except KeyboardInterrupt:
        logger.info("\n服务器已停止")
    except Exception as e:
        logger.error(f"服务器启动失败: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
