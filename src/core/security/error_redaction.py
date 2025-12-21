"""
对外错误信息脱敏/去敏：避免泄露内部文件路径等实现细节。
"""

from __future__ import annotations

import os
import re
from typing import Final


_WIN_ABS_PATH: Final[re.Pattern[str]] = re.compile(
    r"(?i)(?:[a-z]:\\\\(?:[^\\s:'\\\"]+\\\\)*[^\\s:'\\\"]+)"
)
_UNIX_ABS_PATH: Final[re.Pattern[str]] = re.compile(r"(?:/[^\\s:'\\\"]+)+")


def redact_paths(text: str) -> str:
    if not text:
        return ""

    cwd = os.getcwd()
    safe = text.replace(cwd, "<redacted-path>")

    safe = _WIN_ABS_PATH.sub("<redacted-path>", safe)
    safe = _UNIX_ABS_PATH.sub("<redacted-path>", safe)
    return safe


def safe_error_message(exc: BaseException) -> str:
    return redact_paths(str(exc))

