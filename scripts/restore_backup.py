#!/usr/bin/env python3
"""Restore helper for backups created by scripts/backup_data.py.

Safety rules:
- Default is extract-only into a separate directory (no overwrites).
- Optional `--apply` can copy extracted files into the project root.
"""

from __future__ import annotations

import argparse
import shutil
import sys
import zipfile
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Restore a VirtualChemLab backup zip.")
    parser.add_argument("backup_zip", help="Path to backup zip created by backup_data.py")
    parser.add_argument(
        "--extract-dir",
        default="restores",
        help="Directory to extract into (default: restores/ under project root).",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Copy extracted files into project root (overwrites existing files).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List files in the backup and exit.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    backup_zip = Path(args.backup_zip).expanduser().resolve()
    if not backup_zip.exists():
        print(f"backup not found: {backup_zip}", file=sys.stderr)
        return 2

    with zipfile.ZipFile(backup_zip, "r") as zf:
        members = zf.namelist()
        if args.dry_run:
            for name in members:
                print(name)
            return 0

        extract_root = Path(args.extract_dir)
        if not extract_root.is_absolute():
            extract_root = PROJECT_ROOT / extract_root
        extract_root.mkdir(parents=True, exist_ok=True)

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target_dir = extract_root / f"{backup_zip.stem}_{stamp}"
        target_dir.mkdir(parents=True, exist_ok=True)
        zf.extractall(target_dir)

    print(f"extracted_to: {target_dir}")

    if not args.apply:
        print("not applied (extract-only).")
        print("To apply: run again with --apply after verifying extracted contents.")
        return 0

    # Apply: copy back into project root, overwriting.
    for path in target_dir.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(target_dir)
        dest = PROJECT_ROOT / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
    print(f"applied_to: {PROJECT_ROOT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

