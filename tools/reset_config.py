"""
VirtualChemLab 配置重置工具（安全版）。

背景：
- `config.json` 是“本地覆盖配置”，会叠加到 `config/base.json` 之上；
- 当 `config.json` 被误改为无效 JSON 或者写入了不兼容字段时，会导致启动失败或行为异常；
- 直接删除文件容易丢失排障线索，因此本工具默认会先备份。

默认行为：
- 备份并重置仓库根目录 `config.json`
- 重置内容为 `config/base.json`（作为“可运行的最小基线”）

注意：
- 该工具不会重置用户目录下的运行时数据（`~/.virtualchemlab/`），除非显式指定 `--user`。
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="VirtualChemLab 配置重置工具")
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="不备份直接覆盖（不推荐）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只打印将要执行的动作，不实际修改文件",
    )
    parser.add_argument(
        "--user",
        action="store_true",
        help="同时重置用户目录下的运行时 config（~/.virtualchemlab/config.json）",
    )
    return parser.parse_args()


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _backup_file(path: Path, backup_dir: Path) -> Path:
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / f"{path.name}.{_timestamp()}.bak"
    shutil.copy2(path, backup_path)
    return backup_path


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _reset_project_config(*, dry_run: bool, backup: bool) -> None:
    target = PROJECT_ROOT / "config.json"
    base = PROJECT_ROOT / "config" / "base.json"
    backup_dir = PROJECT_ROOT / "backups" / "config"

    if not base.exists():
        raise FileNotFoundError(f"缺少基线配置文件: {base}")

    action = f"重置 {target} -> 使用 {base}"
    print(f"🧹 {action}")

    if dry_run:
        return

    if target.exists() and backup:
        backup_path = _backup_file(target, backup_dir)
        print(f"📦 已备份: {backup_path.relative_to(PROJECT_ROOT)}")

    shutil.copy2(base, target)
    print("✅ 已重置 config.json")


def _reset_user_config(*, dry_run: bool, backup: bool) -> None:
    from src.core.config_loader import DEFAULT_RUNTIME_HOME  # noqa: E402
    from src.core.config_loader import _user_config_path  # noqa: E402

    target = _user_config_path(DEFAULT_RUNTIME_HOME)
    backup_dir = DEFAULT_RUNTIME_HOME / "backups" / "config"

    if not target.exists():
        print(f"➖ 用户配置不存在，无需重置: {target}")
        return

    print(f"🧹 重置用户配置: {target}")
    if dry_run:
        return

    if backup:
        backup_path = _backup_file(target, backup_dir)
        print(f"📦 已备份: {backup_path}")

    # 用户配置主要用于存储运行时生成/持久化的 secrets；重置为最小空结构。
    _write_json(target, {})
    print("✅ 已重置用户配置")


def main() -> int:
    args = _parse_args()
    backup = not args.no_backup

    try:
        _reset_project_config(dry_run=args.dry_run, backup=backup)
        if args.user:
            _reset_user_config(dry_run=args.dry_run, backup=backup)
    except Exception as exc:  # noqa: BLE001
        print(f"❌ 重置失败: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

