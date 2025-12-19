#!/usr/bin/env python3
"""
VirtualChemLab readiness check script

Provides a single entry point to validate dependencies, configuration, security
settings, assets, monitoring toggles, and filesystem prerequisites before a
release or deployment.
"""

from __future__ import annotations

import importlib
import json
import os
import sys
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

try:
    from src.core.config_loader import Config, get_config
except Exception as exc:  # pragma: no cover - defensive import
    print("[ERROR] 无法导入配置系统，请确认依赖已安装:", exc)
    sys.exit(1)


@dataclass
class CheckResult:
    """Aggregated result for a readiness check."""

    name: str
    passed: bool
    detail: str


def check_python_version() -> CheckResult:
    """Ensure interpreter meets minimum requirements."""
    version_info = sys.version_info
    if version_info >= (3, 10):
        return CheckResult("Python 版本", True, f"当前版本 {sys.version}")
    return CheckResult("Python 版本", False, f"需要 >= 3.10，当前: {sys.version}")


def check_dependencies() -> CheckResult:
    """Verify critical runtime dependencies are importable."""
    required_modules = ("PySide6", "numpy", "pydantic", "yaml")
    missing: List[str] = []
    for module in required_modules:
        try:
            importlib.import_module(module)
        except Exception:
            missing.append(module)
    if not missing:
        return CheckResult("关键依赖", True, "所有核心依赖均可导入")
    return CheckResult("关键依赖", False, f"缺少依赖: {', '.join(missing)}")


def _resolve_path(raw: str | Path) -> Path:
    path = Path(raw).expanduser()
    return path if path.is_absolute() else (PROJECT_ROOT / path)


def check_environment_alignment(config: Config) -> CheckResult:
    """Ensure ENVIRONMENT aligns with intended deployment mode."""
    env_var = (os.getenv("ENVIRONMENT") or "").strip().lower()
    config_env = str(getattr(config.app, "environment", "development")).lower()
    detected_env = env_var or (
        "production" if bool(getattr(sys, "frozen", False)) else "development"
    )

    if detected_env != config_env:
        hint = (
            "请设置 ENVIRONMENT 以加载对应的 config/<env>.json"
            if not env_var
            else "请对齐 ENVIRONMENT 与配置环境"
        )
        return CheckResult(
            "环境变量一致性",
            False,
            f"ENVIRONMENT={env_var or '未设置'} -> 加载环境={detected_env}, 配置环境={config_env}; {hint}",
        )
    detail = f"ENVIRONMENT={env_var or config_env}"
    return CheckResult("环境变量一致性", True, detail)


def check_config_security(config: Config) -> List[CheckResult]:
    """Run security oriented validations."""
    results: List[CheckResult] = []
    env = str(getattr(config.app, "environment", "development")).lower()
    raw_security = _read_config_json().get("security", {})
    jwt_env = (
        os.getenv("JWT_SECRET_ENV")
        or raw_security.get("jwt_secret_env")
        or "JWT_SECRET_KEY"
    ).strip()
    jwt_secret = (os.getenv(jwt_env) or "").strip()
    if env == "production":
        if jwt_secret and len(jwt_secret) >= 32 and "change-in-production" not in jwt_secret:
            results.append(CheckResult("JWT 密钥", True, f"{jwt_env} 已设置"))
        else:
            results.append(
                CheckResult(
                    "JWT 密钥",
                    False,
                    f"缺少安全的 {jwt_env}，生产环境必须提供 >=32 位密钥",
                )
            )
    else:
        secret = getattr(config.security, "jwt_secret_key", "")
        if secret and len(secret) >= 32 and "change-in-production" not in secret:
            results.append(CheckResult("JWT 密钥", True, "密钥长度与内容安全"))
        else:
            results.append(
                CheckResult(
                    "JWT 密钥",
                    False,
                    "缺少安全的 JWT_SECRET_KEY，请在环境变量中配置",
                )
            )
    dev_section = _read_config_json().get("developer", {})
    dev_enabled = dev_section.get("enabled", False)
    if env == "production" and dev_enabled:
        results.append(
            CheckResult("开发者模式", False, "生产环境禁止默认开启开发者工具，请在 config.json 中关闭")
        )
    else:
        detail = "开发者模式仅在非生产环境启用" if dev_enabled else "开发者模式默认关闭"
        results.append(CheckResult("开发者模式", True, detail))
    session_env = (
        os.getenv("SESSION_SECRET_ENV")
        or raw_security.get("session_secret_env")
        or "SESSION_SECRET_KEY"
    ).strip()
    session_secret = (os.getenv(session_env) or "").strip()
    if env == "production":
        if session_secret and len(session_secret) >= 32:
            results.append(CheckResult("会话密钥", True, f"{session_env} 已设置"))
        else:
            results.append(
                CheckResult(
                    "会话密钥",
                    False,
                    f"缺少安全的 {session_env}，生产环境必须提供 >=32 位密钥",
                )
            )
    else:
        results.append(CheckResult("会话密钥", True, "非生产环境跳过强校验"))
    return results


def check_filesystem(config: Config) -> List[CheckResult]:
    """Ensure required directories and files exist."""
    required_paths = {
        _resolve_path(getattr(config.paths, "templates", "assets/templates")): "实验模板目录",
        _resolve_path(getattr(config.paths, "knowledge", "assets/knowledge")): "知识库目录",
        _resolve_path(getattr(config.paths, "i18n", "assets/i18n")): "国际化目录",
        _resolve_path(getattr(config.paths, "logs", "logs")): "日志目录",
        _resolve_path(getattr(config.paths, "reports", "reports")): "报告目录",
        _resolve_path(getattr(config.paths, "user_data", "user_data")): "用户数据目录",
    }
    results: List[CheckResult] = []
    for path, description in required_paths.items():
        if path.exists():
            results.append(CheckResult(description, True, f"{path}"))
        else:
            results.append(
                CheckResult(description, False, f"{path} 不存在，请创建或检查路径配置")
            )
    return results


def check_monitoring(config: Config) -> List[CheckResult]:
    """Validate monitoring/logging settings."""
    results: List[CheckResult] = []
    monitoring = config.monitoring
    if monitoring.enabled and monitoring.health_check_interval > 0:
        results.append(
            CheckResult(
                "监控配置", True, f"已启用 (间隔 {monitoring.health_check_interval}s)"
            )
        )
    else:
        results.append(CheckResult("监控配置", False, "监控已关闭或配置不完整"))

    log_cfg = config.log
    log_path = _resolve_path(log_cfg.file)
    log_dir = log_path.parent
    if log_dir.exists():
        results.append(CheckResult("日志目录", True, f"{log_dir} 已存在"))
    else:
        results.append(CheckResult("日志目录", False, f"{log_dir} 不存在，请创建"))

    # 日志目录可写性探测（与 /healthz 保持一致的核心条件）
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        probe = log_dir / ".readiness_write_probe"
        with open(probe, "wb") as f:
            f.write(b"ok\n")
            f.flush()
            os.fsync(f.fileno())
        probe.unlink(missing_ok=True)
        results.append(CheckResult("日志目录可写", True, f"{log_dir}"))
    except Exception as exc:  # noqa: BLE001
        results.append(CheckResult("日志目录可写", False, str(exc)))
    return results


def _read_config_json() -> dict:
    """Load the raw config.json for checks that bypass env merge."""
    config_path = PROJECT_ROOT / "config.json"
    if not config_path.exists():
        return {}
    try:
        with open(config_path, encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return {}


def check_config_json_integrity() -> CheckResult:
    """Validate config.json syntax without stopping the whole check."""
    config_path = PROJECT_ROOT / "config.json"
    if not config_path.exists():
        return CheckResult("config.json", True, "未找到（可选）")
    try:
        with open(config_path, encoding="utf-8") as handle:
            json.load(handle)
        return CheckResult("config.json", True, "JSON 格式有效")
    except Exception as exc:  # noqa: BLE001
        return CheckResult("config.json", False, f"JSON 解析失败: {exc}")


def run_all_checks() -> List[CheckResult]:
    """Execute every readiness check."""
    results: List[CheckResult] = [
        check_python_version(),
        check_dependencies(),
        check_config_json_integrity(),
    ]
    try:
        config = get_config()
    except Exception as exc:  # noqa: BLE001
        results.append(CheckResult("配置加载", False, f"加载失败: {exc}"))
        return results

    results.append(check_environment_alignment(config))
    results.extend(check_config_security(config))
    results.extend(check_filesystem(config))
    results.extend(check_monitoring(config))
    return results


def _print_summary(results: Iterable[CheckResult]) -> int:
    """Pretty-print the summary table."""
    failures: List[CheckResult] = []
    print("=" * 72)
    print("VirtualChemLab - 系统就绪度检查")
    print("=" * 72)
    for result in results:
        status = "✅" if result.passed else "❌"
        print(f"{status} {result.name}: {result.detail}")
        if not result.passed:
            failures.append(result)
    print("=" * 72)
    if failures:
        print("未通过检查: ")
        for fail in failures:
            print(f" - {fail.name}: {fail.detail}")
        print(
            textwrap.dedent(
                """
                请根据上方提示修复问题后重试。
                如果在生产环境部署，请务必确认所有检查通过。
                """
            ).strip()
        )
    else:
        print("所有检查均已通过，系统就绪 ✅")
    print("=" * 72)
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(_print_summary(run_all_checks()))
