"""Startup preflight checks for production safety.

This module centralizes critical runtime validations so that all entrypoints
(GUI/CLI) consistently enforce security-sensitive requirements before the
application proceeds to heavy initialization (Qt, DI, DB, etc.).
"""

from __future__ import annotations

import logging
import os
from collections.abc import Iterable
from typing import Any

from src import __version__ as APP_VERSION
from src.core.build_info import get_build_info

logger = logging.getLogger(__name__)


REQUIRED_SECRETS: tuple[tuple[str, str], ...] = (
    ("JWT_SECRET_KEY", "JWT 密钥"),
    ("SESSION_SECRET_KEY", "会话密钥"),
)

# Security baseline: we treat secrets shorter than this as weak and refuse to
# start in strict production. Keep consistent with `config_loader` and API probes.
MIN_SECRET_LENGTH = 32


def _get_environment(config: Any | None) -> str:
    """提取运行环境，默认 development"""
    try:
        env = getattr(getattr(config, "app", None), "environment", None)
    except Exception:
        env = None
    return (env or os.getenv("ENVIRONMENT") or "development").lower()


def _resolve_secret(env_name: str, config_value: str | None = None) -> str:
    """优先读取环境变量，否则退回配置值"""
    return os.getenv(env_name, "") or (config_value or "")


def ensure_secure_startup(
    config: Any | None = None, extra_required: Iterable[tuple[str, str]] | None = None
) -> None:
    """统一启动前安全校验，避免弱密钥在生产环境运行。

    Args:
        config: 应用配置对象（可选，用于读取环境与密钥值）
        extra_required: optional additional (env, label) pairs to validate.
    Raises:
        SystemExit: 严格生产环境（`ENVIRONMENT=production`）下缺失/弱密钥时 fail-fast。
        ValueError: 非严格生产环境下缺失/弱密钥时抛出（用于调用方选择是否继续运行）。
    """

    env_name = _get_environment(config)
    strict_mode = env_name == "production"
    build = get_build_info()

    # 统一记录启动元信息，便于排查环境漂移/构建不一致
    logger.info(
        "startup_preflight: version=%s env=%s build_time=%s build_id=%s build_sha=%s",
        APP_VERSION,
        env_name,
        build.build_time,
        build.build_id,
        build.build_sha,
    )

    # 构造校验列表（包含配置中的环境变量名称和实际值）
    if config and hasattr(config, "security"):
        security_cfg = config.security
        base_required: list[tuple[str, str, str | None]] = [
            (
                getattr(security_cfg, "jwt_secret_env", "JWT_SECRET_KEY"),
                "JWT 密钥",
                getattr(security_cfg, "jwt_secret_key", None),
            ),
            (
                getattr(security_cfg, "session_secret_env", "SESSION_SECRET_KEY"),
                "会话密钥",
                getattr(security_cfg, "session_secret_key", None),
            ),
        ]
    else:
        base_required = [(env, label, None) for env, label in REQUIRED_SECRETS]

    if extra_required:
        base_required.extend((env, label, None) for env, label in extra_required)

    # 生产环境要求的额外密钥（来自 config_loader 的约定字段）
    developer_enabled = False
    if config is not None:
        try:
            developer_cfg = getattr(config, "developer", None)
            if developer_cfg is not None:
                developer_enabled = bool(getattr(developer_cfg, "enabled", False))
        except Exception:  # noqa: BLE001
            developer_enabled = False

        try:
            if hasattr(config, "security") and developer_enabled:
                security_cfg = config.security
                dev_secret_env = getattr(security_cfg, "developer_secret_env", None)
                if dev_secret_env:
                    base_required.append((dev_secret_env, "开发者密钥", None))
        except Exception:  # noqa: BLE001
            pass

    errors: list[str] = []
    warnings: list[str] = []

    for secret_env, label, config_value in base_required:
        value = _resolve_secret(secret_env, config_value)
        if len(value) >= MIN_SECRET_LENGTH:
            continue

        message = f"{label} 未设置或长度不足(>={MIN_SECRET_LENGTH}): {secret_env}"
        if strict_mode:
            errors.append(message)
        else:
            warnings.append(message)

    for warning in warnings:
        logger.warning("启动前安全提醒（%s环境）: %s", env_name, warning)

    if errors:
        joined = "; ".join(errors)
        # 生产环境 fail-fast：直接退出，避免弱密钥运行
        logger.critical(
            "startup_preflight failed (env=%s version=%s build_id=%s): %s",
            env_name,
            APP_VERSION,
            build.build_id,
            joined,
        )
        if strict_mode:
            raise SystemExit(1)
        raise ValueError(f"安全检查失败: {joined}")


def assert_version_alignment(config_version: str | None) -> None:
    """Logically ensure config/app versions do not drift.

    We do not raise here to avoid blocking development scenarios; callers can
    decide whether to treat mismatches as fatal. For P0 we simply align via
    config_loader; this helper is kept for future strictness.
    """

    if not config_version:
        return
    if config_version != APP_VERSION:
        raise ValueError(
            f"配置版本({config_version}) 与应用版本({APP_VERSION}) 不一致，请同步后再启动"
        )


__all__ = ["ensure_secure_startup", "assert_version_alignment"]
