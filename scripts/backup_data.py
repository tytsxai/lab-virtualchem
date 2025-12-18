#!/usr/bin/env python3
"""Create daily/weekly backups for VirtualChemLab data.

Design goals:
- Safe by default (never deletes source data).
- Portable (zip format; no external deps).
- Rotates old backups (daily/weekly keep policy).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.build_info import get_build_info  # noqa: E402


@dataclass(frozen=True)
class BackupSpec:
    mode: str
    output_dir: Path
    keep: int
    include_data: bool
    include_user_data: bool
    include_config: bool


def _iter_files(base: Path) -> list[Path]:
    if not base.exists():
        return []
    if base.is_file():
        return [base]
    return [p for p in base.rglob("*") if p.is_file()]


def _add_files(zf: zipfile.ZipFile, root: Path, paths: list[Path]) -> list[str]:
    added: list[str] = []
    for path in paths:
        try:
            rel = path.relative_to(root)
        except Exception:
            rel = path.name
        arcname = str(rel).replace("\\", "/")
        zf.write(path, arcname=arcname)
        added.append(arcname)
    return added


def _rotate_backups(output_dir: Path, keep: int) -> None:
    backups = sorted(
        [p for p in output_dir.glob("*.zip") if p.is_file()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for old in backups[keep:]:
        try:
            old.unlink()
        except Exception:
            pass


def create_backup(spec: BackupSpec) -> Path:
    output_dir = spec.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    build = get_build_info()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"vcl_{spec.mode}_{ts}_v{build.version}.zip"
    out_path = output_dir / filename

    included_roots: list[str] = []
    files_added: list[str] = []

    # Collect targets
    targets: list[Path] = []
    if spec.include_data:
        included_roots.append("data/")
        targets.extend(_iter_files(PROJECT_ROOT / "data"))
        # SQLite WAL/shm (if exists)
        for suffix in ("", "-wal", "-shm"):
            candidate = PROJECT_ROOT / "data" / f"virtualchemlab.db{suffix}"
            if candidate.exists():
                targets.append(candidate)

    if spec.include_user_data:
        included_roots.append("user_data/")
        targets.extend(_iter_files(PROJECT_ROOT / "user_data"))

    if spec.include_config:
        config_json = PROJECT_ROOT / "config.json"
        if config_json.exists():
            included_roots.append("config.json")
            targets.append(config_json)

    # De-dup
    targets = sorted({p.resolve() for p in targets if p.exists()})

    manifest = {
        "created_at": datetime.now().isoformat(),
        "mode": spec.mode,
        "project_root": str(PROJECT_ROOT),
        "included_roots": included_roots,
        "build": build.as_dict(),
        "python": sys.version,
        "platform": os.name,
    }

    tmp_path = out_path.with_suffix(".zip.tmp")
    try:
        with zipfile.ZipFile(tmp_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            files_added.extend(_add_files(zf, PROJECT_ROOT, targets))
            zf.writestr(
                "manifest.json",
                json.dumps(
                    {**manifest, "files": files_added},
                    ensure_ascii=False,
                    indent=2,
                ),
            )
        os.replace(tmp_path, out_path)
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass

    _rotate_backups(output_dir, spec.keep)
    return out_path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backup VirtualChemLab runtime data.")
    parser.add_argument(
        "--mode",
        choices=["daily", "weekly"],
        default="daily",
        help="Backup mode (affects default retention).",
    )
    parser.add_argument(
        "--output-dir",
        default="backups",
        help="Where to write backup files (default: backups/).",
    )
    parser.add_argument(
        "--keep",
        type=int,
        default=0,
        help="Retention count; 0 means use mode default (daily=14, weekly=8).",
    )
    parser.add_argument("--no-data", action="store_true", help="Exclude data/ directory.")
    parser.add_argument(
        "--no-user-data", action="store_true", help="Exclude user_data/ directory."
    )
    parser.add_argument("--no-config", action="store_true", help="Exclude config.json.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    keep = args.keep or (14 if args.mode == "daily" else 8)
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = PROJECT_ROOT / output_dir / args.mode
    else:
        output_dir = output_dir / args.mode

    spec = BackupSpec(
        mode=args.mode,
        output_dir=output_dir,
        keep=keep,
        include_data=not args.no_data,
        include_user_data=not args.no_user_data,
        include_config=not args.no_config,
    )
    start = time.time()
    out = create_backup(spec)
    duration = (time.time() - start) * 1000
    print(json.dumps({"backup": str(out), "ms": round(duration, 2), **asdict(spec)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

