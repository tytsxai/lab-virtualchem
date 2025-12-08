"""Lightweight stubs to keep UI smoke tests fast and offscreen-friendly."""

from __future__ import annotations

import contextlib
from pathlib import Path
from typing import Any

from src import __version__ as APP_VERSION


class StubI18n:
    """Minimal translation stub."""

    def __init__(self) -> None:
        self.current_language = "zh_CN"
        self.i18n_dir = Path(".")
        self._translations = {
            "app.title": "VirtualChemLab",
            "app.version": APP_VERSION,
            "ui.experiment_list": "Experiments",
            "ui.welcome": "Welcome",
            "ui.select_experiment_hint": "Pick an experiment to begin",
            "ui.refresh": "Refresh",
            "status.ready": "Ready",
        }

    def t(self, key: str, **kwargs: Any) -> str:
        value = self._translations.get(key, key)
        if kwargs:
            with contextlib.suppress(KeyError, ValueError):
                return str(value).format(**kwargs)
        return str(value)


class StubTemplateEngine:
    """TemplateEngine stub that avoids disk access."""

    def __init__(self) -> None:
        self.templates_dir = Path("tests/templates")

    def list_available_experiments(self) -> list[dict[str, str]]:
        return []

    def load_experiment_by_id(self, template_id: str):
        return {"id": template_id, "title": f"Experiment {template_id}"}


class StubStore:
    """In-memory JSONStore replacement."""

    def __init__(self) -> None:
        self._data: dict[str, Any] = {"app_first_run": False}

    def get(self, key: str, default: Any | None = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def save_record(self, record: Any) -> bool:
        self._data["last_record"] = record
        return True

    def list_user_records(self, user_id: str) -> list[dict[str, Any]]:
        return []


class StubDeveloperAuth:
    """DeveloperAuth stub that always authenticates."""

    def authenticate_by_secret_sequence(self, sequence: str) -> bool:
        return False

    def authenticate(self, key: str) -> bool:
        return True

    def is_locked_out(self) -> bool:
        return False

    def is_authenticated(self) -> bool:
        return True


class StubContainer:
    """Tiny DI container that resolves by token name."""

    def __init__(self, overrides: dict[str, Any] | None = None) -> None:
        self._services = overrides or {}

    def resolve(self, token: Any) -> Any:
        key = token if isinstance(token, str) else getattr(token, "__name__", token)
        if key in self._services:
            return self._services[key]
        raise KeyError(f"Stub service for {key} is not registered")


def build_stub_container() -> StubContainer:
    """Factory to assemble the default stub container."""
    return StubContainer(
        {
            "TemplateEngine": StubTemplateEngine(),
            "I18n": StubI18n(),
            "JSONStore": StubStore(),
            "DeveloperAuth": StubDeveloperAuth(),
        }
    )
