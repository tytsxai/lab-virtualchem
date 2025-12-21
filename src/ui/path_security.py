"""UI 文件路径安全策略。

用于处理 QFileDialog 返回的路径，防止：
- 路径穿越（../）
- 指向非预期目录（例如用户选择系统敏感目录）
"""

from __future__ import annotations

from pathlib import Path


def project_root() -> Path:
    # src/ui/xxx.py -> repo root
    return Path(__file__).resolve().parents[2]


def default_allowed_dirs() -> list[Path]:
    root = project_root()
    candidates = [
        root / "user_data",
        root / "reports",
        root / "logs",
        root / "outputs",
        root / "data",
        root / "assets",
        root / "backups",
        root / "temp",
    ]
    return [p.resolve() for p in candidates]


def validate_dialog_path(path_str: str, allowed_dirs: list[Path] | None = None) -> Path:
    """校验 QFileDialog 返回的路径，限制在允许目录内。"""
    if not path_str:
        raise ValueError("empty path")

    resolved = Path(path_str).expanduser().resolve()
    allowed = allowed_dirs or default_allowed_dirs()

    for base in allowed:
        try:
            if resolved.is_relative_to(base):
                return resolved
        except AttributeError:
            # Python<3.9 fallback
            try:
                resolved.relative_to(base)
                return resolved
            except ValueError:
                pass

    raise ValueError(f"path not allowed: {resolved}")

