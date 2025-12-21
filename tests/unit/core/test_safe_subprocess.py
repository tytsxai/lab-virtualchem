from __future__ import annotations

from pathlib import Path

import pytest

from src.core.auto_updater import AutoUpdater
from src.core.device_fingerprint import DeviceFingerprintCollector
from src.core.security.safe_subprocess import UnsafeSubprocessArguments
from src.core.security.safe_subprocess import popen as safe_popen
from src.core.security.safe_subprocess import run as safe_run


def test_safe_subprocess_run_rejects_string_args():
    with pytest.raises(UnsafeSubprocessArguments):
        safe_run("echo hi")  # type: ignore[arg-type]


def test_safe_subprocess_run_rejects_shell_true():
    with pytest.raises(UnsafeSubprocessArguments):
        safe_run(["echo", "hi"], shell=True)


def test_safe_subprocess_popen_rejects_shell_true():
    with pytest.raises(UnsafeSubprocessArguments):
        safe_popen(["echo", "hi"], shell=True)


def test_device_fingerprint_uses_safe_run_for_macos_cpu_info(monkeypatch: pytest.MonkeyPatch):
    collector = DeviceFingerprintCollector()

    calls: list[tuple[list[str], dict]] = []

    def fake_safe_run(args, **kwargs):
        calls.append((list(args), dict(kwargs)))

        class Result:
            stdout = "Apple M3\n"

        return Result()

    monkeypatch.setattr("src.core.device_fingerprint.safe_run", fake_safe_run)
    assert collector._get_cpu_info_macos() == "Apple M3"

    assert calls, "期望调用 safe_run"
    assert calls[0][0] == ["sysctl", "-n", "machdep.cpu.brand_string"]


def test_auto_updater_install_update_uses_safe_run_on_windows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    updater = AutoUpdater(update_url="https://example.invalid", check_interval=10)
    updater.platform = "windows"

    installer = tmp_path / "installer.exe"
    installer.write_bytes(b"fake")

    called = {"args": None, "shell": None, "check": None}

    def fake_safe_run(args, **kwargs):
        called["args"] = list(args)
        called["shell"] = kwargs.get("shell")
        called["check"] = kwargs.get("check")

        class Result:
            returncode = 0

        return Result()

    monkeypatch.setattr("src.core.auto_updater.safe_run", fake_safe_run)
    assert updater.install_update(installer) is True
    assert called["args"] == [str(installer.resolve())]
    assert called["shell"] is False
    assert called["check"] is True

