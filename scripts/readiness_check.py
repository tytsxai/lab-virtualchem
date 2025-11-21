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


def check_config_security(config: Config) -> List[CheckResult]:
    """Run security oriented validations."""
    results: List[CheckResult] = []
    secret = getattr(config.security, "jwt_secret_key", "")
    if secret and len(secret) >= 32 and "change-in-production" not in secret:
        results.append(CheckResult("JWT 密钥", True, "密钥长度与内容安全"))
    else:
        results.append(
            CheckResult("JWT 密钥", False, "缺少安全的 JWT_SECRET_KEY，请在环境变量中配置")
        )

    env = config.app.environment
    dev_section = _read_config_json().get("developer", {})
    dev_enabled = dev_section.get("enabled", False)
    if env == "production" and dev_enabled:
        results.append(
            CheckResult("开发者模式", False, "生产环境禁止默认开启开发者工具，请在 config.json 中关闭")
        )
    else:
        detail = "开发者模式仅在非生产环境启用" if dev_enabled else "开发者模式默认关闭"
        results.append(CheckResult("开发者模式", True, detail))
    return results


def check_filesystem() -> List[CheckResult]:
    """Ensure required directories and files exist."""
    required_paths = {
        PROJECT_ROOT / "assets" / "templates": "实验模板目录",
        PROJECT_ROOT / "assets" / "knowledge": "知识库目录",
        PROJECT_ROOT / "assets" / "i18n": "国际化目录",
        PROJECT_ROOT / "logs": "日志目录",
        PROJECT_ROOT / "reports": "报告目录",
        PROJECT_ROOT / "data": "数据目录",
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
    log_path = PROJECT_ROOT / log_cfg.file
    log_dir = log_path.parent
    if log_dir.exists():
        results.append(CheckResult("日志目录", True, f"{log_dir} 已存在"))
    else:
        results.append(CheckResult("日志目录", False, f"{log_dir} 不存在，请创建"))
    return results


def _read_config_json() -> dict:
    """Load the raw config.json for checks that bypass env merge."""
    config_path = PROJECT_ROOT / "config.json"
    if not config_path.exists():
        return {}
    with open(config_path, encoding="utf-8") as handle:
        return json.load(handle)


def run_all_checks() -> List[CheckResult]:
    """Execute every readiness check."""
    config = get_config()
    results: List[CheckResult] = [check_python_version(), check_dependencies()]
    results.extend(check_config_security(config))
    results.extend(check_filesystem())
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
