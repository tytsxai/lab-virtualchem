"""Lightweight QtGui stubs."""

from __future__ import annotations

from dataclasses import dataclass


class QGuiApplication:
    _instance = None

    def __init__(self, _args=None) -> None:
        type(self)._instance = self

    @classmethod
    def instance(cls):
        return cls._instance


@dataclass
class QImage:
    width: int = 0
    height: int = 0


@dataclass
class QPixmap:
    width: int = 0
    height: int = 0


@dataclass(frozen=True)
class QColor:
    r: int = 0
    g: int = 0
    b: int = 0


class QPainter:
    class RenderHint:
        Antialiasing = 1
        SmoothPixmapTransform = 2

    def __init__(self, *_args, **_kwargs) -> None:
        return

    def setRenderHint(self, *_args, **_kwargs) -> None:  # noqa: N802
        return


def __getattr__(name: str):  # noqa: ANN001
    return type(name, (), {})
