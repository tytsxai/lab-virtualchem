"""
src.config 配置模块安全修复测试（TASK-013）
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest



@pytest.fixture(autouse=True)
def _isolate_singletons(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setenv("VCL_USER_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("VCL_MAX_CONFIG_BYTES", "4096")

    from src.config.config_manager import ConfigManager

    ConfigManager._instance = None
    import src.config.config_manager as config_manager_module

    config_manager_module._config_manager = None


def test_config_path_must_be_under_user_data(tmp_path: Path):
    from src.config.config_manager import ConfigError, ConfigManager

    manager = ConfigManager()
    with pytest.raises(ConfigError):
        manager.load("../evil.json")

    with pytest.raises(ConfigError):
        manager.load(tmp_path.parent / "evil.json")


def test_load_ignores_unknown_keys_and_nested_injection(tmp_path: Path):
    from src.config.config_manager import ConfigManager

    config_file = tmp_path / "config.json"
    config_file.write_text(
        json.dumps(
            {
                "app": {"theme": "dark", "__class__": "Injected"},
                "ui": {"window_width": 1280, "unknown": 123},
                "totally_new_section": {"x": 1},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    manager = ConfigManager()
    manager.load("config.json")

    assert manager.get("app.theme") == "dark"
    assert manager.get("app.__class__") is None
    assert manager.get("ui.unknown") is None
    assert manager.get("totally_new_section.x") is None


def test_set_rejects_unknown_key_injection(tmp_path: Path):
    from src.config.config_manager import ConfigError, ConfigManager

    manager = ConfigManager()
    manager.load("config.json")  # 不存在时会创建

    with pytest.raises(ConfigError):
        manager.set("danger.new_key", "x", save=False)


def test_load_rejects_oversized_config_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from src.config.config_manager import ConfigError, ConfigManager

    monkeypatch.setenv("VCL_MAX_CONFIG_BYTES", "64")

    config_file = tmp_path / "config.json"
    config_file.write_text(" " * 100, encoding="utf-8")

    manager = ConfigManager()
    with pytest.raises(ConfigError):
        manager.load("config.json")


def test_save_is_atomic_and_uses_os_replace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from src.config.config_manager import ConfigManager

    manager = ConfigManager()
    manager.load("config.json")  # 创建默认配置
    manager.set("app.theme", "dark", save=False)

    calls: list[tuple[Path, Path]] = []
    original_replace = os.replace

    def _spy_replace(src: str | os.PathLike, dst: str | os.PathLike):
        calls.append((Path(src), Path(dst)))
        return original_replace(src, dst)

    monkeypatch.setattr(os, "replace", _spy_replace)
    manager.save()

    assert calls
    assert calls[-1][1].name == "config.json"
    assert (tmp_path / "config.json").exists()


def test_defaults_are_not_mutated_and_export_is_deepcopied(tmp_path: Path):
    from src.config.config_manager import ConfigManager

    manager = ConfigManager()
    manager.load("config.json")

    manager.set("ui.window_width", 900, save=False)
    exported = manager.export()
    exported["ui"]["window_width"] = 1000

    assert manager.get("ui.window_width") == 900

    manager.reset()
    assert manager.get("ui.window_width") == 1280


def test_get_settings_proxy_reads_from_config(tmp_path: Path):
    from src.config import get_settings
    from src.config.config_manager import ConfigManager

    manager = ConfigManager()
    manager.load("config.json")
    manager.set("app.theme", "light", save=False)

    assert get_settings().get("app.theme") == "light"


def test_load_rejects_invalid_json(tmp_path: Path):
    from src.config.config_manager import ConfigError, ConfigManager

    (tmp_path / "config.json").write_text("{invalid", encoding="utf-8")
    manager = ConfigManager()
    with pytest.raises(ConfigError):
        manager.load("config.json")


def test_load_rejects_invalid_config_by_validation(tmp_path: Path):
    from src.config.config_manager import ConfigError, ConfigManager

    (tmp_path / "config.json").write_text(
        json.dumps({"app": {"theme": "not-a-theme"}}, ensure_ascii=False),
        encoding="utf-8",
    )
    manager = ConfigManager()
    with pytest.raises(ConfigError):
        manager.load("config.json")


def test_load_rejects_non_object_json(tmp_path: Path):
    from src.config.config_manager import ConfigError, ConfigManager

    (tmp_path / "config.json").write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    manager = ConfigManager()
    with pytest.raises(ConfigError):
        manager.load("config.json")


def test_load_missing_file_tolerates_save_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from src.config.config_manager import ConfigManager

    monkeypatch.setenv("VCL_MAX_CONFIG_BYTES", "32")
    ConfigManager._instance = None

    manager = ConfigManager()
    # 文件不存在时会尝试保存默认配置；保存失败应被吞掉并继续使用内存默认配置
    manager.load("config.json")
    assert manager.get("app.name") == "VirtualChemLab"


def test_set_invalid_value_rolls_back(tmp_path: Path):
    from src.config.config_manager import ConfigError, ConfigManager

    manager = ConfigManager()
    manager.load("config.json")
    before = manager.get("ui.window_width")

    with pytest.raises(ConfigError):
        manager.set("ui.window_width", 1, save=False)

    assert manager.get("ui.window_width") == before


def test_set_invalid_path_rejected(tmp_path: Path):
    from src.config.config_manager import ConfigError, ConfigManager

    manager = ConfigManager()
    manager.load("config.json")
    manager._config["ui"] = "not-a-dict"
    with pytest.raises(ConfigError):
        manager.set("ui.window_width", 900, save=False)


def test_save_rejects_invalid_internal_config(tmp_path: Path):
    from src.config.config_manager import ConfigError, ConfigManager

    manager = ConfigManager()
    manager.load("config.json")
    manager._config["ui"]["window_width"] = 1
    with pytest.raises(ConfigError):
        manager.save()


def test_save_cleanup_ignores_unlink_errors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from src.config.config_manager import ConfigManager

    manager = ConfigManager()
    manager.load("config.json")

    tmp_file = tmp_path / "config.json.unlink-error.tmp"
    tmp_file.write_text("stale", encoding="utf-8")

    def _fake_mkstemp(*args, **kwargs):
        fd = os.open(tmp_file, os.O_RDWR | os.O_CREAT | os.O_TRUNC, 0o600)
        return fd, str(tmp_file)

    def _boom_replace(*args, **kwargs):
        raise OSError("replace failed")

    def _boom_unlink(self: Path, *args, **kwargs):
        raise OSError("unlink failed")

    monkeypatch.setattr("tempfile.mkstemp", _fake_mkstemp)
    monkeypatch.setattr(os, "replace", _boom_replace)
    monkeypatch.setattr(Path, "unlink", _boom_unlink)

    # unlink 失败应被吞掉，但整体保存仍会因 replace 失败而抛 ConfigError
    from src.config.config_manager import ConfigError

    with pytest.raises(ConfigError):
        manager.save()


def test_import_config_merge_rejects_invalid_and_rolls_back(tmp_path: Path):
    from src.config.config_manager import ConfigError, ConfigManager

    manager = ConfigManager()
    manager.load("config.json")
    before = manager.get("ui.window_width")
    with pytest.raises(ConfigError):
        manager.import_config({"ui": {"window_width": 1}}, merge=True)
    assert manager.get("ui.window_width") == before


def test_user_data_dir_default_resolution(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    from src.config.config_manager import ConfigManager

    monkeypatch.delenv("VCL_USER_DATA_DIR", raising=False)
    ConfigManager._instance = None
    manager = ConfigManager()
    path = manager._get_user_data_dir()
    assert path.name == "user_data"


def test_enforce_file_size_limit_handles_stat_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from src.config.config_manager import ConfigError, ConfigManager

    manager = ConfigManager()
    manager.load("config.json")

    def _raise(*args, **kwargs):
        raise OSError("stat failed")

    monkeypatch.setattr(Path, "stat", _raise)
    with pytest.raises(ConfigError):
        manager._enforce_file_size_limit(tmp_path / "config.json")

def test_save_without_config_file_is_noop(tmp_path: Path):
    from src.config.config_manager import ConfigManager

    manager = ConfigManager()
    manager._config_file = None
    manager.save()  # 不应抛异常


def test_save_rejects_oversized_content(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from src.config.config_manager import ConfigError, ConfigManager

    manager = ConfigManager()
    manager.load("config.json")

    manager._max_config_bytes = 32
    # 生成足够大的内容
    manager.set("developer.log_level", "X" * 100, save=False)
    with pytest.raises(ConfigError):
        manager.save()


def test_import_config_rejects_non_dict(tmp_path: Path):
    from src.config.config_manager import ConfigError, ConfigManager

    manager = ConfigManager()
    manager.load("config.json")
    with pytest.raises(ConfigError):
        manager.import_config(["not", "a", "dict"])  # type: ignore[arg-type]


def test_import_config_replace_mode_and_whitelist(tmp_path: Path):
    from src.config.config_manager import ConfigManager

    manager = ConfigManager()
    manager.load("config.json")
    manager.import_config(
        {"app": {"theme": "dark"}, "evil": {"x": 1}},
        merge=False,
    )
    assert manager.get("app.theme") == "dark"
    assert manager.get("evil.x") is None


def test_reset_unknown_key_does_not_crash(tmp_path: Path):
    from src.config.config_manager import ConfigManager

    manager = ConfigManager()
    manager.load("config.json")
    manager.reset("not.exists.anywhere")


def test_reset_known_key_restores_default(tmp_path: Path):
    from src.config.config_manager import ConfigManager

    manager = ConfigManager()
    manager.load("config.json")
    manager.set("app.theme", "dark", save=False)
    manager.reset("app.theme")
    assert manager.get("app.theme") == "auto"


def test_set_with_save_triggers_save_path(tmp_path: Path):
    from src.config.config_manager import ConfigManager

    manager = ConfigManager()
    manager.load("config.json")
    manager.set("app.theme", "light", save=True)
    assert (tmp_path / "config.json").exists()


def test_import_config_merge_success(tmp_path: Path):
    from src.config.config_manager import ConfigManager

    manager = ConfigManager()
    manager.load("config.json")
    manager.import_config({"app": {"theme": "dark"}}, merge=True)
    assert manager.get("app.theme") == "dark"


def test_set_rejects_non_leaf_path_key(tmp_path: Path):
    from src.config.config_manager import ConfigError, ConfigManager

    manager = ConfigManager()
    manager.load("config.json")
    with pytest.raises(ConfigError):
        manager.set("app.name.extra", "x", save=False)


def test_validate_reports_multiple_error_cases(tmp_path: Path):
    from src.config.config_manager import ConfigManager

    manager = ConfigManager()
    manager.load("config.json")

    manager._config["ui"]["window_height"] = 1
    manager._config["app"]["language"] = ""
    manager._config["performance"]["memory_threshold_mb"] = -1
    manager._config["performance"]["debounce_delay"] = -1

    errors = manager.validate()
    assert any("ui.window_height" in e for e in errors)
    assert any("app.language" in e for e in errors)
    assert any("performance.memory_threshold_mb" in e for e in errors)
    assert any("performance.debounce_delay" in e for e in errors)


def test_save_cleans_up_temp_file_when_replace_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    from src.config.config_manager import ConfigError, ConfigManager

    manager = ConfigManager()
    manager.load("config.json")
    manager.set("app.theme", "dark", save=False)

    tmp_file = tmp_path / "config.json.tmp"
    tmp_file.write_text("stale", encoding="utf-8")

    def _fake_mkstemp(*args, **kwargs):
        # 返回一个可写 fd，路径固定，便于断言清理逻辑
        fd = os.open(tmp_file, os.O_RDWR | os.O_CREAT | os.O_TRUNC, 0o600)
        return fd, str(tmp_file)

    def _boom_replace(*args, **kwargs):
        raise OSError("replace failed")

    monkeypatch.setattr("tempfile.mkstemp", _fake_mkstemp)
    monkeypatch.setattr(os, "replace", _boom_replace)

    with pytest.raises(ConfigError):
        manager.save()

    assert not tmp_file.exists()


def test_convenience_wrappers_load_config_and_set_setting(tmp_path: Path):
    from src.config.config_manager import get_setting, load_config, set_setting

    load_config("config.json")
    set_setting("app.theme", "light", save=False)
    assert get_setting("app.theme") == "light"
