"""安全工具函数

提供路径安全、输入验证、日志脱敏与安全随机字符串等常用能力。
"""

from __future__ import annotations

import os
import re
import secrets
import string
from pathlib import Path
from typing import Any, Iterable


def validate_path_in_directory(path: Path, allowed_dir: Path) -> bool:
    """验证路径在允许目录内"""

    if not isinstance(path, Path) or not isinstance(allowed_dir, Path):
        raise TypeError("path 和 allowed_dir 必须是 pathlib.Path")

    try:
        resolved_allowed = allowed_dir.resolve(strict=False)
        resolved_path = path.resolve(strict=False)
    except OSError:
        return False

    if resolved_allowed == resolved_path:
        return True

    try:
        resolved_path.relative_to(resolved_allowed)
        return True
    except ValueError:
        return False


def safe_path_join(base_dir: Path, *parts: str) -> Path:
    """安全路径拼接，防止路径遍历"""

    if not isinstance(base_dir, Path):
        raise TypeError("base_dir 必须是 pathlib.Path")

    current: Path = base_dir
    for part in parts:
        if not isinstance(part, str):
            raise TypeError("parts 必须是 str")
        if part == "":
            continue

        # 显式阻止路径遍历与绝对路径（包含 Windows 风格分隔符/盘符）
        raw_segments = [seg for seg in re.split(r"[\\\\/]+", part) if seg]
        if any(seg == ".." for seg in raw_segments):
            raise ValueError("检测到路径遍历片段 '..'")
        if part.startswith(("/", "\\\\")) or re.match(r"^[A-Za-z]:[\\\\/]", part):
            raise ValueError("不允许使用绝对路径")

        current = current / part

    if not validate_path_in_directory(current, base_dir):
        raise ValueError("检测到路径遍历或不允许的绝对路径")

    return current


def is_safe_filename(filename: str) -> bool:
    """验证文件名安全（无路径分隔符）"""

    if not isinstance(filename, str):
        raise TypeError("filename 必须是 str")

    if filename in {"", ".", ".."}:
        return False

    if "\x00" in filename:
        return False

    separators = {"/", "\\"}
    if os.sep:
        separators.add(os.sep)
    if os.altsep:
        separators.add(os.altsep)

    if any(sep in filename for sep in separators):
        return False

    # 避免像 "a/../b" 这类被绕过；确保它就是一个纯文件名
    return Path(filename).name == filename


def sanitize_identifier(value: str, pattern: str = r"^[A-Za-z0-9_-]+$") -> str:
    """验证标识符格式"""

    if not isinstance(value, str):
        raise TypeError("value 必须是 str")
    if not isinstance(pattern, str):
        raise TypeError("pattern 必须是 str")
    if value == "":
        raise ValueError("标识符不能为空")

    if re.fullmatch(pattern, value) is None:
        raise ValueError("标识符格式不合法")

    return value


def validate_string_length(value: str, max_length: int) -> str:
    """验证字符串长度"""

    if not isinstance(value, str):
        raise TypeError("value 必须是 str")
    if not isinstance(max_length, int):
        raise TypeError("max_length 必须是 int")
    if max_length < 0:
        raise ValueError("max_length 必须 >= 0")

    if len(value) > max_length:
        raise ValueError("字符串长度超出限制")
    return value


def mask_sensitive_string(value: str, visible_chars: int = 4) -> str:
    """敏感字符串掩码"""

    if not isinstance(visible_chars, int):
        raise TypeError("visible_chars 必须是 int")
    if visible_chars < 0:
        raise ValueError("visible_chars 必须 >= 0")

    text = value if isinstance(value, str) else str(value)
    if text == "":
        return ""

    if visible_chars == 0:
        return "*" * len(text)

    if len(text) <= visible_chars:
        return "*" * len(text)

    masked_len = len(text) - visible_chars
    return ("*" * masked_len) + text[-visible_chars:]


def _normalize_sensitive_keys(sensitive_keys: Iterable[str]) -> set[str]:
    normalized: set[str] = set()
    for key in sensitive_keys:
        if isinstance(key, str) and key:
            normalized.add(key)
            normalized.add(key.lower())
    return normalized


def _sanitize_value_for_log(value: Any, sensitive_key_set: set[str]) -> Any:
    if isinstance(value, dict):
        return sanitize_for_log(value, list(sensitive_key_set))
    if isinstance(value, list):
        return [
            _sanitize_value_for_log(item, sensitive_key_set)
            if isinstance(item, (dict, list))
            else item
            for item in value
        ]
    return value


def sanitize_for_log(data: dict, sensitive_keys: list) -> dict:
    """日志脱敏"""

    if not isinstance(data, dict):
        raise TypeError("data 必须是 dict")
    if not isinstance(sensitive_keys, list):
        raise TypeError("sensitive_keys 必须是 list")

    sensitive_key_set = _normalize_sensitive_keys(sensitive_keys)
    sanitized: dict[str, Any] = {}

    for key, value in data.items():
        key_str = str(key)
        if key_str in sensitive_key_set or key_str.lower() in sensitive_key_set:
            if value is None:
                sanitized[key_str] = None
            elif isinstance(value, str):
                sanitized[key_str] = mask_sensitive_string(value)
            else:
                sanitized[key_str] = "***"
            continue

        sanitized[key_str] = _sanitize_value_for_log(value, sensitive_key_set)

    return sanitized


def secure_random_string(length: int) -> str:
    """安全随机字符串"""

    if not isinstance(length, int):
        raise TypeError("length 必须是 int")
    if length <= 0:
        raise ValueError("length 必须 > 0")

    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))
