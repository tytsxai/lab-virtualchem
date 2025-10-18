"""配置管理"""

import json
from pathlib import Path
from typing import Any


class Config:
    """配置管理器"""

    def __init__(self, config_path: Path | None = None) -> None:
        """初始化配置

        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path or Path.home() / ".virtualchemlab" / "config.json"
        self._data: dict[str, Any] = self._load_default_config()

        # 如果存在用户配置,加载并合并
        if self.config_path.exists():
            self.load()

    def _load_default_config(self) -> dict[str, Any]:
        """加载默认配置"""
        return {
            "app": {
                "name": "VirtualChemLab",
                "version": "1.0.0",
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

    def load(self) -> None:
        """从文件加载配置"""
        try:
            with open(self.config_path, encoding="utf-8") as f:
                user_config = json.load(f)

            # 深度合并配置
            self._deep_merge(self._data, user_config)

        except Exception:
            pass  # 加载失败则使用默认配置

    def save(self) -> None:
        """保存配置到文件"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

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
