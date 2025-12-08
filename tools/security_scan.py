#!/usr/bin/env python3
"""
Lightweight security scan helper for local runs.

Runs Bandit (code security) and Safety (dependency vulnerability) if available,
captures their output into the logs/ directory, and prints a short summary so
results can be archived in documentation.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Tuple


ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "logs"


def now_ts() -> str:
    return datetime.now().isoformat(timespec="seconds")


def fmt_cmd(cmd: Iterable[str]) -> str:
    return " ".join(cmd)


def run_command(cmd: List[str]) -> Tuple[int, str, str]:
    """Run a command and capture output without raising."""
    result = subprocess.run(
        cmd,
        cwd=ROOT,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.returncode, result.stdout or "", result.stderr or ""


def write_report(
    name: str, cmd: List[str], version: str, exit_code: int, stdout: str, stderr: str, path: Path
) -> None:
    """Persist a human-readable report for traceability."""
    lines = [
        f"{name} report",
        f"Timestamp: {now_ts()}",
        f"Version: {version}",
        f"Command: {fmt_cmd(cmd)}",
        f"Exit code: {exit_code}",
        "",
        "STDOUT:",
        stdout.strip() or "<empty>",
        "",
        "STDERR:",
        stderr.strip() or "<empty>",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def get_tool_version(tool: str) -> str:
    code, out, err = run_command([tool, "--version"])
    if code == 0 and out:
        return out.splitlines()[0].strip()
    if err:
        return err.splitlines()[0].strip()
    return "unknown"


def run_bandit(report_path: Path) -> bool:
    if not shutil.which("bandit"):
        print("Bandit not found; skip Bandit scan.")
        return False

    cmd = ["bandit", "-r", "src", "-ll"]
    exit_code, stdout, stderr = run_command(cmd)
    version = get_tool_version("bandit")
    write_report("Bandit", cmd, version, exit_code, stdout, stderr, report_path)

    status = "passed" if exit_code == 0 else "completed with findings/failures"
    print(f"[Bandit] {status}; report -> {report_path}")
    return True


def run_safety(report_path: Path) -> bool:
    if not shutil.which("safety"):
        print("Safety not found; skip Safety scan.")
        return False

    cmd = ["safety", "check", "--full-report"]
    exit_code, stdout, stderr = run_command(cmd)
    version = get_tool_version("safety")
    write_report("Safety", cmd, version, exit_code, stdout, stderr, report_path)

    status = "passed" if exit_code == 0 else "completed with findings/failures"
    print(f"[Safety] {status}; report -> {report_path}")
    return True


def run_pip_audit(report_path: Path) -> bool:
    if not shutil.which("pip-audit"):
        print("pip-audit not found; skip pip-audit scan.")
        return False

    cmd = ["pip-audit", "-r", "requirements.txt"]
    exit_code, stdout, stderr = run_command(cmd)
    version = get_tool_version("pip-audit")
    write_report("pip-audit", cmd, version, exit_code, stdout, stderr, report_path)

    status = "passed" if exit_code == 0 else "completed with findings/failures"
    print(f"[pip-audit] {status}; report -> {report_path}")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run security scans and capture reports.")
    parser.add_argument("--skip-bandit", action="store_true", help="Skip Bandit scan.")
    parser.add_argument("--skip-safety", action="store_true", help="Skip Safety scan.")
    parser.add_argument(
        "--with-pip-audit",
        action="store_true",
        help="Also run pip-audit (written to logs/safety-report.txt when Safety is absent).",
    )
    args = parser.parse_args(argv)

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    ran_any = False

    if not args.skip_bandit:
        ran_any |= run_bandit(LOG_DIR / "bandit-report.txt")

    safety_done = False
    if not args.skip_safety:
        safety_done = run_safety(LOG_DIR / "safety-report.txt")
        ran_any |= safety_done

    if args.with_pip_audit or not safety_done:
        pip_audit_target = LOG_DIR / ("pip-audit-report.txt" if safety_done else "safety-report.txt")
        ran_any |= run_pip_audit(pip_audit_target)

    if not ran_any:
        print("No security tools were run. Install bandit/safety or enable pip-audit.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
