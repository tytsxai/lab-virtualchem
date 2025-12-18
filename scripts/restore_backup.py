#!/usr/bin/env python3
"""Restore helper for backups created by scripts/backup_data.py.

Safety rules:
- Default is extract-only into a separate directory (no overwrites).
- Optional `--apply` can copy extracted files into the project root.
- Never trusts zip paths: prevents zip-slip / path traversal.
- `--apply` is allowlisted to runtime data only (data/, user_data/, config.json).
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import zipfile
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ALLOWED_APPLY_PREFIXES: tuple[str, ...] = ("data/", "user_data/", "config.json")


class UnsafeBackupError(RuntimeError):
    pass


def _is_safe_member(name: str) -> bool:
    # Zip format uses POSIX separators; normalize to reduce edge cases.
    normalized = name.replace("\\", "/").lstrip("/")
    if not normalized or normalized.endswith("/"):
        return True  # directories / empty are safe (ignored)
    parts = [p for p in normalized.split("/") if p]
    if any(part in {".", ".."} for part in parts):
        return False
    # Windows drive-letter paths like C:\
    if ":" in parts[0]:
        return False
    return True


def _member_target_path(extract_dir: Path, member_name: str) -> Path:
    normalized = member_name.replace("\\", "/").lstrip("/")
    target = (extract_dir / normalized).resolve()
    extract_root = extract_dir.resolve()
    try:
        target.relative_to(extract_root)
    except ValueError as exc:
        raise UnsafeBackupError(f"zip-slip detected: {member_name}") from exc
    return target


def _safe_extract(zf: zipfile.ZipFile, dest: Path) -> None:
    for info in zf.infolist():
        name = info.filename
        if not _is_safe_member(name):
            raise UnsafeBackupError(f"unsafe zip member path: {name}")
        normalized = name.replace("\\", "/").lstrip("/")
        if not normalized or normalized.endswith("/"):
            continue

        target_path = _member_target_path(dest, normalized)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with zf.open(info, "r") as src, open(target_path, "wb") as dst:
            shutil.copyfileobj(src, dst)


def _load_manifest(extracted_dir: Path) -> dict:
    manifest = extracted_dir / "manifest.json"
    if not manifest.exists():
        return {}
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


def _is_allowed_apply_path(rel_posix: str) -> bool:
    rel_posix = rel_posix.replace("\\", "/").lstrip("/")
    if rel_posix == "config.json":
        return True
    return any(rel_posix.startswith(prefix) for prefix in ALLOWED_APPLY_PREFIXES if prefix.endswith("/"))


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
        try:
            _safe_extract(zf, target_dir)
        except UnsafeBackupError as exc:
            print(f"unsafe backup zip: {exc}", file=sys.stderr)
            return 3

    print(f"extracted_to: {target_dir}")
    manifest = _load_manifest(target_dir)
    if manifest:
        build = manifest.get("build") if isinstance(manifest.get("build"), dict) else {}
        print(
            f"manifest: mode={manifest.get('mode')} version={build.get('version')} build_id={build.get('build_id')}"
        )

    if not args.apply:
        print("not applied (extract-only).")
        print("To apply: run again with --apply after verifying extracted contents.")
        return 0

    # Apply: copy back into project root, overwriting.
    # Safety: only allow runtime mutable data. Never overwrite code.
    for path in target_dir.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(target_dir)
        rel_posix = str(rel).replace("\\", "/")
        if rel_posix == "manifest.json":
            continue
        if not _is_allowed_apply_path(rel_posix):
            print(f"skip (not allowlisted): {rel_posix}")
            continue
        dest = PROJECT_ROOT / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
    print(f"applied_to: {PROJECT_ROOT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
