"""Lightweight JSON config helper (legacy/compat).

This class provides a small, dependency-free config reader/writer used by some
utility code and the REST API stack. It intentionally does *not* enforce the
security baseline (secrets, production fail-fast) — that logic lives in
`src/core/config_loader.py` and `src/core/startup_preflight.py`.

If you need typed/validated app config for startup and DI, use
`src/core/config_loader.get_config()` instead of this module.
"""

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

from src import __version__ as APP_VERSION

logger = logging.getLogger(__name__)


class Config:
    """配置管理器"""

    def __init__(self, config_path: Path | None = None) -> None:
        """初始化配置

        Args:
            config_path: 配置文件路径
        """
        env_path = (os.getenv("VCL_CONFIG_PATH") or "").strip()
        resolved_env_path = Path(env_path).expanduser() if env_path else None

        default_root = Path.home() / ".virtualchemlab"
        if os.name == "nt":
            base = os.getenv("APPDATA") or os.getenv("LOCALAPPDATA")
            if base:
                default_root = Path(base) / ".virtualchemlab"

        self.config_path = config_path or resolved_env_path or (default_root / "config.json")
        self._data: dict[str, Any] = self._load_default_config()

        # 运行时数据目录重定向（生产/打包环境常见需求）
        runtime_env = (os.getenv("VCL_DATA_DIR") or "").strip()
        if runtime_env:
            self._apply_runtime_root(Path(runtime_env).expanduser())

        # 如果存在用户配置,加载并合并
        if self.config_path.exists():
            self.load()

    def _load_default_config(self) -> dict[str, Any]:
        """加载默认配置"""
        return {
            "app": {
                "name": "VirtualChemLab",
                "version": APP_VERSION,
                "language": "zh_CN",
            },
            "paths": {
                "templates": "assets/templates",
                "templates_dir": "assets/templates",  # 兼容旧代码
                "knowledge": "assets/knowledge",
                "knowledge_dir": "assets/knowledge",  # 兼容旧代码
                "i18n": "assets/i18n",
                "logs": "logs",
                "reports": "reports",
                "data_dir": "data/records",
                "user_data_dir": "user_data",
            },
            "ui": {
                "theme": "light",
                "font_size": 12,
                "window_width": 1200,
                "window_height": 800,
            },
            "experiment": {
                "auto_save": True,
                "save_interval": 60,
                "max_undo_steps": 50,
                "enable_hints": True,
                "allow_skip_steps": False,
            },
            "reporting": {
                "format": "html",
                "include_charts": True,
                "include_data": True,
            },
        }

    def _apply_runtime_root(self, root: Path) -> None:
        paths = self._data.setdefault("paths", {})
        paths["logs"] = str(root / "logs")
        paths["reports"] = str(root / "reports")
        paths["data_dir"] = str(root / "data" / "records")
        paths["user_data_dir"] = str(root / "user_data")

    def load(self) -> None:
        """从文件加载配置"""
        try:
            with open(self.config_path, encoding="utf-8") as f:
                user_config = json.load(f)

            # 深度合并配置
            self._deep_merge(self._data, user_config)
            self._normalize_language_codes()

        except Exception as exc:  # noqa: BLE001
            # 生产环境中静默回退到默认配置会造成“看似正常、实际漂移”的风险。
            # 这里保持兼容行为（不抛异常），但至少把失败原因写入日志。
            logger.warning("加载配置失败，已回退到默认配置: %s (%s)", self.config_path, exc)

    def save(self) -> None:
        """保存配置到文件"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        tmp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=str(self.config_path.parent),
                delete=False,
                suffix=".tmp",
            ) as f:
                tmp_path = Path(f.name)
                json.dump(self._data, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(str(tmp_path), str(self.config_path))
            # Best-effort tighten permissions for secrets on POSIX.
            if os.name == "posix":
                try:
                    os.chmod(str(self.config_path), 0o600)
                except Exception:  # noqa: BLE001
                    pass
        finally:
            if tmp_path is not None and tmp_path.exists():
                try:
                    tmp_path.unlink()
                except Exception:  # noqa: BLE001
                    pass

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值

        Args:
            key: 配置键(支持点号分隔,如 "app.language")
            default: 默认值

        Returns:
            配置值
        """
        keys = key.split(".")
        value = self._data

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: Any) -> None:
        """设置配置值

        Args:
            key: 配置键(支持点号分隔)
            value: 配置值
        """
        keys = key.split(".")
        data = self._data

        for k in keys[:-1]:
            if k not in data or not isinstance(data[k], dict):
                data[k] = {}
            data = data[k]

        data[keys[-1]] = value
        if key in ("app.language", "ui.language") or key.endswith(".language"):
            self._normalize_language_codes()

    def _normalize_language_codes(self) -> None:
        """规范语言代码（例如 zh-CN -> zh_CN），避免 i18n 文件名匹配失败。"""

        def _norm(value: Any) -> Any:
            if not isinstance(value, str) or not value:
                return value
            normalized = value.replace("-", "_")
            parts = normalized.split("_")
            if len(parts) == 2:
                return f"{parts[0].lower()}_{parts[1].upper()}"
            return normalized

        app = self._data.get("app")
        if isinstance(app, dict) and "language" in app:
            app["language"] = _norm(app.get("language"))

        ui = self._data.get("ui")
        if isinstance(ui, dict) and "language" in ui:
            ui["language"] = _norm(ui.get("language"))

    def _deep_merge(self, base: dict, update: dict) -> None:
        """深度合并字典

        Args:
            base: 基础字典
            update: 更新字典
        """
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    @property
    def config(self) -> dict[str, Any]:
        """兼容属性：返回当前配置字典。"""
        return self._data

    @property
    def config_file(self) -> Path:
        """兼容属性：返回配置文件路径。"""
        return self.config_path

    def reload(self) -> None:
        """重新加载配置（重置为默认后再合并用户配置）。"""
        self._data = self._load_default_config()
        if self.config_path.exists():
            self.load()
