#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

LINK_PATTERN = re.compile(r"\]\(([^)]+)\)")
INLINE_CODE_PATTERN = re.compile(r"`[^`]*`")


DEFAULT_ENTRY_DOCS = (
    "README.md",
    "QUICK_START.md",
    "QUICK_START_GUIDE.md",
    "QUICK_START_COMPLETION.md",
    "INSTALL.md",
    "DEPLOY.md",
    "CONTRIBUTING.md",
    "项目文档索引.md",
    "docs/README.md",
    "docs/DEVELOPER_DOCS_INDEX.md",
    "docs/PROTOCOL_INDEX.md",
)


IGNORED_DIR_NAMES = {
    ".git",
    ".venv",
    ".venv39",
    ".venv311",
    ".venv312",
    "venv311",
    "__pycache__",
    "build",
    "dist",
    "htmlcov",
}


@dataclass(frozen=True)
class MissingLink:
    md_path: Path
    line_no: int
    target: str


def _is_ignored_path(path: Path, ignored_dir_names: set[str] | None = None) -> bool:
    effective_ignored = ignored_dir_names or IGNORED_DIR_NAMES
    return any(part in effective_ignored for part in path.parts)


def _iter_markdown_files(root: Path, ignored_dir_names: set[str] | None = None) -> list[Path]:
    return sorted(
        p
        for p in root.rglob("*.md")
        if p.is_file() and not _is_ignored_path(p, ignored_dir_names=ignored_dir_names)
    )


def _resolve_target(md_path: Path, raw_target: str) -> Path | None:
    target = raw_target.strip()
    if not target:
        return None
    if target.startswith(("http://", "https://", "mailto:", "#")):
        return None
    if target.startswith("file:"):
        return None
    if "*" in target or "<" in target or ">" in target:
        return None

    # Strip fragment and query string.
    target = target.split("#", 1)[0].split("?", 1)[0].strip()
    if not target:
        return None

    return (md_path.parent / target).resolve()


def check_links(markdown_files: list[Path]) -> list[MissingLink]:
    missing: list[MissingLink] = []

    for md_path in markdown_files:
        in_fenced_code_block = False
        try:
            lines = md_path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            lines = md_path.read_text(encoding="utf-8", errors="replace").splitlines()

        for idx, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("```") or stripped.startswith("~~~"):
                in_fenced_code_block = not in_fenced_code_block
                continue
            if in_fenced_code_block:
                continue

            scan_line = INLINE_CODE_PATTERN.sub("", line)
            for raw_target in LINK_PATTERN.findall(scan_line):
                resolved = _resolve_target(md_path, raw_target)
                if resolved is None:
                    continue
                if not resolved.exists():
                    missing.append(MissingLink(md_path=md_path, line_no=idx, target=raw_target))

    return missing


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check local Markdown links for missing targets.")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Scan all Markdown files under the repo (excluding venv/build/dist/etc).",
    )
    parser.add_argument(
        "--include-archive",
        action="store_true",
        help="Include archive/ historical docs when using --all (default: excluded).",
    )
    args = parser.parse_args(argv)

    root = Path(__file__).resolve().parent.parent

    if args.all:
        ignored = set(IGNORED_DIR_NAMES)
        if not args.include_archive:
            ignored.add("archive")
        markdown_files = _iter_markdown_files(root, ignored_dir_names=ignored)
    else:
        markdown_files = []
        for rel in DEFAULT_ENTRY_DOCS:
            path = (root / rel).resolve()
            if not path.exists():
                print(f"[WARN] entry doc missing: {rel}", file=sys.stderr)
                continue
            markdown_files.append(path)

    missing = check_links(markdown_files)
    if not missing:
        print(f"OK: checked {len(markdown_files)} markdown file(s), no missing local links.")
        return 0

    for item in missing:
        rel = item.md_path.relative_to(root)
        print(f"{rel}:{item.line_no}: missing link target: {item.target}")

    print(f"FAIL: {len(missing)} missing link(s) in {len(markdown_files)} markdown file(s).")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
