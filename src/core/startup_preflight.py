"""Startup preflight checks for production safety.

This module centralizes critical runtime validations so that all entrypoints
(GUI/CLI) consistently enforce security-sensitive requirements before the
application proceeds to heavy initialization (Qt, DI, DB, etc.).
"""

from __future__ import annotations

import os
import logging
from typing import Any, Iterable, Tuple

from src import __version__ as APP_VERSION

logger = logging.getLogger(__name__)


REQUIRED_SECRETS: tuple[Tuple[str, str], ...] = (
    ("JWT_SECRET_KEY", "JWT 密钥"),
    ("SESSION_SECRET_KEY", "会话密钥"),
)


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


def ensure_secure_startup(config: Any | None = None, extra_required: Iterable[Tuple[str, str]] | None = None) -> None:
    """统一启动前安全校验，避免弱密钥在生产环境运行。

    Args:
        config: 应用配置对象（可选，用于读取环境与密钥值）
        extra_required: optional additional (env, label) pairs to validate.
    Raises:
        ValueError: 当生产环境缺失或弱密钥时抛出。
    """

    env_name = _get_environment(config)
    strict_mode = env_name == "production"

    # 构造校验列表（包含配置中的环境变量名称和实际值）
    if config and hasattr(config, "security"):
        security_cfg = getattr(config, "security")
        base_required: list[tuple[str, str, str | None]] = [
            (getattr(security_cfg, "jwt_secret_env", "JWT_SECRET_KEY"), "JWT 密钥", getattr(security_cfg, "jwt_secret_key", None)),
            (getattr(security_cfg, "session_secret_env", "SESSION_SECRET_KEY"), "会话密钥", getattr(security_cfg, "session_secret_key", None)),
        ]
    else:
        base_required = [(env, label, None) for env, label in REQUIRED_SECRETS]

    if extra_required:
        base_required.extend((env, label, None) for env, label in extra_required)

    errors: list[str] = []
    warnings: list[str] = []

    for secret_env, label, config_value in base_required:
        value = _resolve_secret(secret_env, config_value)
        if len(value) >= 32:
            continue

        message = f"{label} 未设置或长度不足(>=32): {secret_env}"
        if strict_mode:
            errors.append(message)
        else:
            warnings.append(message)

    for warning in warnings:
        logger.warning("启动前安全提醒（%s环境）: %s", env_name, warning)

    if errors:
        joined = "; ".join(errors)
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
