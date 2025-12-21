"""Lightweight QtCore stubs used in tests."""

from __future__ import annotations

from dataclasses import dataclass


class _Signal:
    def __init__(self) -> None:
        self._slots: list = []

    def connect(self, func) -> None:
        self._slots.append(func)

    def disconnect(self, func) -> None:
        try:
            self._slots.remove(func)
        except ValueError:
            pass

    def emit(self, *args, **kwargs) -> None:
        for func in list(self._slots):
            func(*args, **kwargs)


class QEventLoop:
    def __init__(self) -> None:
        self._running = False

    def exec(self) -> None:
        self._running = True

    def quit(self) -> None:
        self._running = False


class QTimer:
    def __init__(self, _parent=None) -> None:  # noqa: ANN001
        self.timeout = _Signal()
        self._single_shot = False
        self._active = False

    def setSingleShot(self, value: bool) -> None:
        self._single_shot = bool(value)

    def start(self, _timeout: int | None = None) -> None:
        # No-op timing stub; callers rely on timeout signal manually.
        self._active = True

    def stop(self) -> None:
        self._active = False

    def isActive(self) -> bool:
        return bool(self._active)


class Qt:
    AlignLeft = 0
    AlignRight = 1
    AlignHCenter = 2
    AlignVCenter = 3
    Horizontal = 4
    Vertical = 5


@dataclass(frozen=True)
class QPointF:
    x: float = 0.0
    y: float = 0.0


@dataclass(frozen=True)
class QSize:
    width: int = 0
    height: int = 0


class QEvent:
    def __init__(self, _type: int | None = None) -> None:
        self.type = _type


class QObject:
    def __init__(self, _parent=None) -> None:  # noqa: ANN001
        self._parent = _parent


class QThread:
    def __init__(self) -> None:
        self._running = False

    def start(self) -> None:
        self._running = True

    def quit(self) -> None:
        self._running = False

    def wait(self, _msecs: int | None = None) -> bool:
        return True


def Signal(*_args, **_kwargs):  # noqa: ANN001
    return _Signal()


def __getattr__(name: str):  # noqa: ANN001
    """
    Fallback for unimplemented QtCore symbols.

    Many tests import a broad set of Qt classes at module import time; in unit-test
    environments we only need imports to succeed (tests may be deselected).
    """
    if name in {"Signal"}:
        return Signal
    return type(name, (), {})
