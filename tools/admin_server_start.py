"""
管理后台服务器启动脚本
"""

import argparse
import json
import os
import secrets
import sys
from pathlib import Path
from typing import Any

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.api.admin_api import create_admin_api  # noqa: E402
from src.utils.logger import get_logger  # noqa: E402

logger = get_logger("admin_server")

_DEFAULT_LICENSE_SECRET_ENV = "LICENSE_SECRET_KEY"


def resolve_license_secret(config: dict[Any, Any], environment: str) -> str:
    """Resolve license signing secret from env/config placeholder.

    `config/crypto_payment_config.json` stores `license.secret_key` as a `${VAR}`
    placeholder; production must provide that env var.
    """

    raw = config.get("license", {}).get("secret_key", "")
    raw_str = str(raw).strip()

    env_name = _DEFAULT_LICENSE_SECRET_ENV
    if raw_str.startswith("${") and raw_str.endswith("}") and len(raw_str) > 3:
        env_name = raw_str[2:-1].strip() or env_name

    secret = (os.getenv(env_name) or "").strip()
    if not secret:
        message = f"未设置 {env_name}（用于许可证签名/校验）"
        if environment == "production":
            raise ValueError(f"{message}，生产环境禁止使用默认/占位值")
        logger.warning("%s，将使用配置中的占位值，许可证校验可能失败。", message)
        return raw_str

    if secret.startswith("YOUR_") or "change" in secret.lower() or len(secret) < 32:
        message = f"{env_name} 长度不足或仍为占位值，请提供>=32位的生产密钥"
        if environment == "production":
            raise ValueError(message)
        logger.warning("%s（当前为非生产环境，将继续运行）", message)

    return secret


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
    parser.add_argument("--admin-secret", type=str, default=None, help="管理后台密钥（默认从环境变量读取）")

    args = parser.parse_args()

    # 加载配置
    config = load_config()

    # 参数优先级: 命令行 > 配置文件 > 默认值
    host = args.host or config.get("admin_api", {}).get("host", "127.0.0.1")
    port = args.port or config.get("admin_api", {}).get("port", 5000)
    environment = os.getenv("ENVIRONMENT", "development").strip() or "development"
    secret_key = resolve_license_secret(config, environment=environment)

    admin_secret_env = config.get("developer", {}).get("admin_secret_env", "VCL_ADMIN_SECRET_KEY")
    admin_secret = (
        args.admin_secret
        or os.getenv(admin_secret_env)
        or os.getenv("VCL_ADMIN_SECRET_KEY")
    )
    if not admin_secret:
        if environment == "production":
            raise ValueError(f"生产环境必须设置管理后台密钥 ({admin_secret_env})")
        admin_secret = secrets.token_urlsafe(48)
        os.environ.setdefault(admin_secret_env, admin_secret)

        # 与 API Key 行为保持一致：不在日志中打印密钥本体，仅写入用户目录供本机调试
        secret_dir = Path.home() / ".virtualchemlab"
        secret_path = secret_dir / "admin_secret.txt"
        try:
            secret_dir.mkdir(parents=True, exist_ok=True)
            secret_path.write_text(admin_secret + "\n", encoding="utf-8")
            try:
                os.chmod(secret_path, 0o600)
            except Exception:
                pass

            logger.warning(
                "未提供管理后台密钥，在%s环境生成临时密钥并写入 %s（仅当前会话有效）；"
                "请在管理面板右上角输入该值。",
                environment,
                str(secret_path),
            )
        except Exception:
            logger.warning(
                "未提供管理后台密钥，在%s环境生成临时密钥（仅当前会话有效）；"
                "请通过 --admin-secret 或环境变量 %s 提供。",
                environment,
                admin_secret_env,
            )

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
        api = create_admin_api(
            license_file=license_file,
            secret_key=secret_key,
            host=host,
            port=port,
            admin_secret=admin_secret,
        )

        logger.info("\n✅ 服务器已启动！")
        logger.info(f"📊 管理面板: http://{host}:{port}/dashboard")
        logger.info(f"🔌 API地址: http://{host}:{port}/api")
        logger.info("\n按 Ctrl+C 停止服务器\n")

        # 启动服务器
        api.run(debug=args.debug)

    except KeyboardInterrupt:
        logger.info("\n服务器已停止")
    except Exception as e:
        logger.error(f"服务器启动失败: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
