#!/usr/bin/env python3
"""Backup VirtualChemLab runtime data directory.

Design goals:
- Small, dependency-free, and safe by default
- Works for desktop/packaged environments where install dir is not writable
- Produces a single tar.gz archive with timestamp + version
"""

from __future__ import annotations

import argparse
import os
import tarfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class BackupResult:
    archive_path: Path
    included_paths: list[Path]
    skipped_paths: list[Path]


def _default_runtime_root() -> Path:
    env = (os.getenv("VCL_DATA_DIR") or "").strip()
    if env:
        return Path(env).expanduser()
    return Path.home() / ".virtualchemlab"


def _project_version() -> str:
    try:
        # Avoid importing the whole app; just read src.__version__
        project_root = Path(__file__).resolve().parents[1]
        import sys

        sys.path[:0] = [str(project_root), str(project_root / "src")]
        from src import __version__  # noqa: E402

        return str(__version__)
    except Exception:
        return "unknown"


def _candidate_paths(root: Path) -> list[Path]:
    return [
        root / "config.json",
        root / "api_key.txt",
        root / "logs",
        root / "reports",
        root / "user_data",
        root / "data",
        root / "storage",
        root / "backups",
    ]


def create_backup(
    runtime_root: Path, output_dir: Path, keep: int = 7, dry_run: bool = False
) -> BackupResult:
    runtime_root = runtime_root.expanduser().resolve()
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    version = _project_version()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    archive_name = f"virtualchemlab_backup_{version}_{timestamp}.tar.gz"
    archive_path = output_dir / archive_name

    included: list[Path] = []
    skipped: list[Path] = []

    candidates = _candidate_paths(runtime_root)
    for path in candidates:
        if path.exists():
            included.append(path)
        else:
            skipped.append(path)

    if dry_run:
        return BackupResult(archive_path=archive_path, included_paths=included, skipped_paths=skipped)

    with tarfile.open(archive_path, "w:gz") as tf:
        for path in included:
            arcname = path.relative_to(runtime_root)
            tf.add(path, arcname=str(arcname))

    # Retention: keep newest N archives
    if keep >= 0:
        archives = sorted(
            output_dir.glob("virtualchemlab_backup_*.tar.gz"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for old in archives[keep:]:
            try:
                old.unlink()
            except Exception:
                pass

    return BackupResult(archive_path=archive_path, included_paths=included, skipped_paths=skipped)


def main() -> int:
    parser = argparse.ArgumentParser(description="Backup VirtualChemLab runtime data directory")
    parser.add_argument(
        "--runtime-root",
        type=Path,
        default=_default_runtime_root(),
        help="Runtime data directory (default: $VCL_DATA_DIR or ~/.virtualchemlab)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=_default_runtime_root() / "backups",
        help="Where to write backups (default: <runtime-root>/backups)",
    )
    parser.add_argument(
        "--keep",
        type=int,
        default=int((os.getenv("VCL_BACKUP_KEEP") or "7").strip() or "7"),
        help="How many archives to keep (default: 7, or $VCL_BACKUP_KEEP). Use 0 to keep none, -1 to disable pruning.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print what would be included")

    args = parser.parse_args()
    result = create_backup(
        runtime_root=args.runtime_root,
        output_dir=args.output_dir,
        keep=args.keep,
        dry_run=args.dry_run,
    )

    print(f"Runtime root: {args.runtime_root}")
    print(f"Output dir:   {args.output_dir}")
    print(f"Archive:      {result.archive_path}")
    print("")
    print("Included:")
    for p in result.included_paths:
        print(f"  - {p}")
    if result.skipped_paths:
        print("")
        print("Skipped (not found):")
        for p in result.skipped_paths:
            print(f"  - {p}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

