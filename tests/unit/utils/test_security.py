from __future__ import annotations

from pathlib import Path

import pytest
from pytest import MonkeyPatch

from src.utils.security import (
    is_safe_filename,
    mask_sensitive_string,
    safe_path_join,
    sanitize_for_log,
    sanitize_identifier,
    secure_random_string,
    validate_path_in_directory,
    validate_string_length,
)


def test_safe_path_join_allows_normal_relative_paths(tmp_path: Path) -> None:
    base = tmp_path / "base"
    base.mkdir()

    joined = safe_path_join(base, "subdir", "file.txt")
    assert joined == base / "subdir" / "file.txt"
    assert validate_path_in_directory(joined, base) is True


def test_safe_path_join_rejects_non_path_base_dir(tmp_path: Path) -> None:
    with pytest.raises(TypeError):
        safe_path_join("not-a-path", "file.txt")  # type: ignore[arg-type]


def test_safe_path_join_rejects_non_str_part(tmp_path: Path) -> None:
    base = tmp_path / "base"
    base.mkdir()

    with pytest.raises(TypeError):
        safe_path_join(base, 123)  # type: ignore[arg-type]


def test_safe_path_join_skips_empty_segments(tmp_path: Path) -> None:
    base = tmp_path / "base"
    base.mkdir()

    joined = safe_path_join(base, "", "subdir", "", "file.txt")
    assert joined == base / "subdir" / "file.txt"


@pytest.mark.parametrize("part", ["C:\\Windows\\System32", "D:/data/file.txt"])
def test_safe_path_join_blocks_windows_drive_absolute(tmp_path: Path, part: str) -> None:
    base = tmp_path / "base"
    base.mkdir()

    with pytest.raises(ValueError):
        safe_path_join(base, part)


@pytest.mark.parametrize(
    "parts",
    [
        ("..", "evil.txt"),
        ("subdir", "..", "evil.txt"),
        ("/etc", "passwd"),
        ("subdir/../evil.txt",),
        ("../evil.txt",),
        ("..\\evil.txt",),
    ],
)
def test_safe_path_join_blocks_traversal(tmp_path: Path, parts: tuple[str, ...]) -> None:
    base = tmp_path / "base"
    base.mkdir()

    with pytest.raises(ValueError):
        safe_path_join(base, *parts)


def test_validate_path_in_directory_detects_symlink_escape(tmp_path: Path) -> None:
    base = tmp_path / "base"
    outside = tmp_path / "outside"
    base.mkdir()
    outside.mkdir()

    target = outside / "secret.txt"
    target.write_text("secret", encoding="utf-8")

    link = base / "link.txt"
    link.symlink_to(target)

    assert validate_path_in_directory(link, base) is False


def test_validate_path_in_directory_rejects_non_path_inputs() -> None:
    with pytest.raises(TypeError):
        validate_path_in_directory("not-a-path", Path("."))  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        validate_path_in_directory(Path("."), "not-a-path")  # type: ignore[arg-type]


def test_validate_path_in_directory_allows_same_path(tmp_path: Path) -> None:
    base = tmp_path / "base"
    base.mkdir()
    assert validate_path_in_directory(base, base) is True


def test_validate_path_in_directory_handles_oserror(monkeypatch: MonkeyPatch) -> None:
    def _raise_oserror(self: Path, strict: bool = False) -> Path:  # noqa: ARG001
        raise OSError("boom")

    monkeypatch.setattr(Path, "resolve", _raise_oserror)
    assert validate_path_in_directory(Path("a"), Path("b")) is False


def test_is_safe_filename_accepts_simple_names() -> None:
    assert is_safe_filename("a.txt") is True
    assert is_safe_filename("ABC_123-xyz.log") is True


def test_is_safe_filename_rejects_non_str() -> None:
    with pytest.raises(TypeError):
        is_safe_filename(123)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "filename",
    ["", ".", "..", "../a.txt", "a/b.txt", "a\\b.txt", "a\x00b.txt"],
)
def test_is_safe_filename_rejects_unsafe(filename: str) -> None:
    assert is_safe_filename(filename) is False


def test_sanitize_identifier_default_pattern_ok() -> None:
    assert sanitize_identifier("ABC_123-xyz") == "ABC_123-xyz"


def test_sanitize_identifier_type_errors_and_empty_value() -> None:
    with pytest.raises(TypeError):
        sanitize_identifier(123)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        sanitize_identifier("ok", pattern=123)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        sanitize_identifier("")


def test_sanitize_identifier_default_pattern_rejects() -> None:
    with pytest.raises(ValueError):
        sanitize_identifier("not ok")


def test_sanitize_identifier_custom_pattern() -> None:
    assert sanitize_identifier("aaaa", pattern=r"^a+$") == "aaaa"
    with pytest.raises(ValueError):
        sanitize_identifier("aaab", pattern=r"^a+$")


def test_validate_string_length_ok_and_rejects() -> None:
    assert validate_string_length("abc", 3) == "abc"
    assert validate_string_length("", 0) == ""
    with pytest.raises(ValueError):
        validate_string_length("abcd", 3)


def test_validate_string_length_type_errors_and_negative_max_length() -> None:
    with pytest.raises(TypeError):
        validate_string_length(123, 3)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        validate_string_length("abc", "3")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        validate_string_length("abc", -1)


def test_mask_sensitive_string_basic() -> None:
    assert mask_sensitive_string("12345678", visible_chars=4) == "****5678"
    assert mask_sensitive_string("1234", visible_chars=4) == "****"
    assert mask_sensitive_string("", visible_chars=4) == ""


def test_mask_sensitive_string_converts_non_str_and_handles_visible_chars_type() -> None:
    assert mask_sensitive_string(123456, visible_chars=2) == "****56"
    with pytest.raises(TypeError):
        mask_sensitive_string("abc", visible_chars="2")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        mask_sensitive_string("abc", visible_chars=-1)


def test_mask_sensitive_string_masks_when_text_shorter_than_visible() -> None:
    assert mask_sensitive_string("ab", visible_chars=10) == "**"


def test_mask_sensitive_string_visible_chars_zero() -> None:
    assert mask_sensitive_string("abcd", visible_chars=0) == "****"


def test_sanitize_for_log_masks_sensitive_keys_and_is_pure() -> None:
    data = {
        "username": "alice",
        "password": "supersecret",
        "Token": "abcd1234",
        "nested": {"api_key": "k123456789"},
        "list": [{"password": "p1"}, {"ok": "x"}],
    }

    out = sanitize_for_log(data, sensitive_keys=["password", "token", "api_key"])
    assert out["username"] == "alice"
    assert out["password"] != data["password"]
    assert out["Token"] != data["Token"]
    assert out["nested"]["api_key"] != data["nested"]["api_key"]
    assert out["list"][0]["password"] != "p1"
    assert out["list"][1]["ok"] == "x"

    assert data["password"] == "supersecret"
    assert data["nested"]["api_key"] == "k123456789"


def test_sanitize_for_log_type_errors() -> None:
    with pytest.raises(TypeError):
        sanitize_for_log([], sensitive_keys=["password"])  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        sanitize_for_log({}, sensitive_keys="password")  # type: ignore[arg-type]


def test_sanitize_for_log_masks_none_and_non_str_sensitive_values() -> None:
    out = sanitize_for_log(
        data={"token": None, "password": 12345, "ok": "x"},
        sensitive_keys=["token", "password"],
    )
    assert out["token"] is None
    assert out["password"] == "***"
    assert out["ok"] == "x"


def test_sanitize_for_log_normalizes_keys_and_sanitizes_nested_lists() -> None:
    data = {
        123: "value",
        "PASSWORD": "secret",
        "nested": [{"password": "p1"}, ["ok", {"password": "p2"}]],
    }
    out = sanitize_for_log(data, sensitive_keys=["password", "", None])  # type: ignore[list-item]

    assert out["123"] == "value"
    assert out["PASSWORD"] != "secret"
    assert out["nested"][0]["password"] != "p1"
    assert out["nested"][1][0] == "ok"
    assert out["nested"][1][1]["password"] != "p2"


def test_secure_random_string_length_and_charset() -> None:
    value = secure_random_string(32)
    assert len(value) == 32
    assert all(ch.isalnum() for ch in value)


def test_secure_random_string_invalid_length() -> None:
    with pytest.raises(ValueError):
        secure_random_string(0)


def test_secure_random_string_type_error() -> None:
    with pytest.raises(TypeError):
        secure_random_string("32")  # type: ignore[arg-type]
