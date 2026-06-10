#!/usr/bin/env python3
"""VirtualChemLab 仓库根启动入口（薄转发）。

生产就绪要求：所有启动路径（开发运行、PyInstaller 打包、脚本调用）必须走同一套
启动流程（配置加载、启动前安全校验、日志初始化、DI 容器等），避免不同入口绕过
安全闸或产生不一致行为。

本文件仅负责：
- 兼容历史入口 `python main.py`
- 兼容 `--test-core`
- 转发到 `src.main`
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _bootstrap_sys_path() -> None:
    project_root = Path(__file__).parent
    sys.path.insert(0, str(project_root))
    sys.path.insert(0, str(project_root / "src"))


def _apply_cli_environment_overrides(argv: list[str]) -> list[str]:
    """Parse `--env`/`--env=...` from argv and map it to `ENVIRONMENT`.

    Why this exists:
    - Documentation and historical scripts often call `python main.py --env development`.
    - The actual configuration system keys off the environment variable `ENVIRONMENT`.
    - Qt receives `sys.argv`; removing `--env` avoids Qt treating it as an unknown option.

    Args:
        argv: full argv list (including argv[0])
    Returns:
        A new argv list with the `--env` flag stripped (if present).
    """
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
    if sys.platform == "win32":
        os.environ.setdefault("PYTHONIOENCODING", "utf-8")

    _bootstrap_sys_path()
    sys.argv = _apply_cli_environment_overrides(sys.argv)

    from src.main import main as app_main  # noqa: E402
    from src.main import test_core_only  # noqa: E402

    if len(sys.argv) > 1 and sys.argv[1] == "--test-core":
        return int(test_core_only())
    return int(app_main())


if __name__ == "__main__":
    raise SystemExit(main())
