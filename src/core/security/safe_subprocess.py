"""
安全的 subprocess 调用封装

目标：
- 禁止 shell=True
- 禁止以字符串形式传入命令（避免被当作 shell 命令拼接）
- 强制使用参数列表/元组
"""

from __future__ import annotations

import subprocess
from collections.abc import Sequence
from typing import Any


class UnsafeSubprocessArguments(ValueError):
    """不安全的 subprocess 参数"""


def _validate_args(args: Sequence[str]) -> list[str]:
    if isinstance(args, (str, bytes)):
        raise UnsafeSubprocessArguments("subprocess args 必须为字符串序列，不能为单个字符串/bytes")
    if not args:
        raise UnsafeSubprocessArguments("subprocess args 不能为空")

    normalized: list[str] = []
    for item in args:
        if not isinstance(item, str):
            raise UnsafeSubprocessArguments("subprocess args 元素必须为 str")
        if item == "":
            raise UnsafeSubprocessArguments("subprocess args 元素不能为空字符串")
        normalized.append(item)
    return normalized


def run(
    args: Sequence[str],
    *,
    shell: bool | None = None,
    check: bool = False,
    capture_output: bool = False,
    text: bool = True,
    timeout: float | None = None,
    **kwargs: Any,
) -> subprocess.CompletedProcess[str]:
    """
    安全版本的 subprocess.run。
    """
    if shell is True:
        raise UnsafeSubprocessArguments("禁止使用 shell=True")

    safe_args = _validate_args(args)
    return subprocess.run(
        safe_args,
        shell=False,
        check=check,
        capture_output=capture_output,
        text=text,
        timeout=timeout,
        **kwargs,
    )


def popen(
    args: Sequence[str],
    *,
    shell: bool | None = None,
    **kwargs: Any,
) -> subprocess.Popen[str]:
    """
    安全版本的 subprocess.Popen。
    """
    if shell is True:
        raise UnsafeSubprocessArguments("禁止使用 shell=True")

    safe_args = _validate_args(args)
    return subprocess.Popen(
        safe_args,
        shell=False,
        text=True,
        **kwargs,
    )

