#!/usr/bin/env python3
"""Utility to keep project version in sync from src/__init__.py."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Iterable, Tuple

ROOT = Path(__file__).resolve().parent.parent
INIT_FILE = ROOT / "src" / "__init__.py"
PYPROJECT_FILE = ROOT / "pyproject.toml"
CONFIG_FILE = ROOT / "config.json"
VERSION_INFO_FILE = ROOT / "version_info.txt"
INSTALLER_FILE = ROOT / "installer_windows.iss"


def parse_version(version: str) -> Tuple[int, int, int]:
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", version)
    if not match:
        raise ValueError(f"Invalid version '{version}'. Use semantic versioning like 2.0.1")
    return tuple(int(part) for part in match.groups())


def read_init_version() -> str:
    text = INIT_FILE.read_text(encoding="utf-8")
    match = re.search(r'__version__\s*=\s*"([^"]+)"', text)
    if not match:
        raise RuntimeError("Could not find __version__ in src/__init__.py")
    return match.group(1)


def update_init_version(version: str, dry_run: bool) -> bool:
    text = INIT_FILE.read_text(encoding="utf-8")
    new_text, count = re.subn(r'(__version__\s*=\s*")[^"]+(")', rf"\g<1>{version}\g<2>", text, count=1)
    if count == 0 or new_text == text:
        return False
    if not dry_run:
        INIT_FILE.write_text(new_text, encoding="utf-8")
    return True


def update_pyproject(version: str, dry_run: bool) -> bool:
    """Keep pyproject aligned. If it still has a literal version, update it."""
    text = PYPROJECT_FILE.read_text(encoding="utf-8")
    changed = False

    literal_pattern = re.compile(r'^(version\s*=\s*)"([^"]+)"', re.MULTILINE)
    if literal_pattern.search(text):
        text, count = literal_pattern.subn(rf'\1"{version}"', text, count=1)
        changed = changed or count > 0

    if 'version = {attr = "src.__version__"}' in text:
        pass
    elif "[tool.setuptools.dynamic]" in text:
        # keep user-provided dynamic block intact
        pass

    if changed and not dry_run:
        PYPROJECT_FILE.write_text(text, encoding="utf-8")
    return changed


def update_config_json(version: str, dry_run: bool) -> bool:
    if not CONFIG_FILE.exists():
        return False
    data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    app_info = data.setdefault("app", {})
    if app_info.get("version") == version:
        return False
    app_info["version"] = version
    if not dry_run:
        CONFIG_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=4), encoding="utf-8")
    return True


def update_version_info(version: str, dry_run: bool) -> bool:
    major, minor, patch = parse_version(version)
    file_version_tuple = f"({major}, {minor}, {patch}, 0)"
    file_version_str = f"{version}.0"

    text = VERSION_INFO_FILE.read_text(encoding="utf-8")
    replacements = {
        r"filevers=\(\d+, \d+, \d+, \d+\)": f"filevers={file_version_tuple}",
        r"prodvers=\(\d+, \d+, \d+, \d+\)": f"prodvers={file_version_tuple}",
        r"StringStruct\(u'FileVersion', u'[^']+'\)": f"StringStruct(u'FileVersion', u'{file_version_str}')",
        r"StringStruct\(u'ProductVersion', u'[^']+'\)": f"StringStruct(u'ProductVersion', u'{version}')",
    }

    new_text = text
    changed = False
    for pattern, replacement in replacements.items():
        new_text, count = re.subn(pattern, replacement, new_text)
        changed = changed or count > 0

    if changed and not dry_run:
        VERSION_INFO_FILE.write_text(new_text, encoding="utf-8")
    return changed


def update_installer(version: str, dry_run: bool) -> bool:
    text = INSTALLER_FILE.read_text(encoding="utf-8")
    new_text, count = re.subn(r'(#define MyAppVersion\s+")([^"]+)(")', rf"\g<1>{version}\g<3>", text, count=1)
    if count == 0 or new_text == text:
        return False
    if not dry_run:
        INSTALLER_FILE.write_text(new_text, encoding="utf-8")
    return True


def summarize(results: Iterable[Tuple[str, bool]]) -> None:
    for name, changed in results:
        status = "updated" if changed else "already ok"
        print(f"{name}: {status}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sync project version across build/config files.")
    parser.add_argument(
        "version",
        nargs="?",
        help="Target version (e.g. 2.0.1). If omitted, use the current src/__version__.",
    )
    parser.add_argument(
        "--set",
        dest="set_version",
        help="Explicitly set __version__ to the given value before syncing (alias of positional argument).",
    )
    parser.add_argument("--dry-run", action="store_true", help="Show planned changes without writing files.")
    args = parser.parse_args(argv)

    current_version = read_init_version()
    target_version = args.set_version or args.version or current_version
    wants_update = args.set_version is not None or args.version is not None
    parse_version(target_version)  # validate early

    if wants_update:
        updated = update_init_version(target_version, args.dry_run)
        if updated:
            print(f"src/__init__.py: set __version__ to {target_version}")
        elif current_version != target_version:
            print("src/__init__.py did not change; verify __version__ location")
    else:
        print(f"Syncing using existing src/__version__: {current_version}")

    results = [
        ("pyproject.toml", update_pyproject(target_version, args.dry_run)),
        ("config.json", update_config_json(target_version, args.dry_run)),
        ("version_info.txt", update_version_info(target_version, args.dry_run)),
        ("installer_windows.iss", update_installer(target_version, args.dry_run)),
    ]
    summarize(results)

    if args.dry_run:
        print("Dry run complete; no files were modified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
