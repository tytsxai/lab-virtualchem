"""Lightweight QtWidgets stubs."""

from __future__ import annotations

from dataclasses import dataclass

from .QtCore import _Signal


class QApplication:
    _instance = None

    def __init__(self, _args=None) -> None:
        type(self)._instance = self
        self.aboutToQuit = _Signal()

    @classmethod
    def instance(cls):
        return cls._instance

    def processEvents(self) -> None:
        pass

    def exec(self) -> int:
        return 0

    def setApplicationName(self, _name: str) -> None:
        return None

    def setApplicationDisplayName(self, _name: str) -> None:
        return None

    def setApplicationVersion(self, _version: str) -> None:
        return None

    def setOrganizationName(self, _name: str) -> None:
        return None


class QWidget:
    def __init__(self, *args, **kwargs) -> None:  # noqa: ANN001
        self._object_name = ""

    def setObjectName(self, name: str) -> None:
        self._object_name = name

    def objectName(self) -> str:
        return self._object_name

    def findChild(self, _cls, _name: str):  # noqa: ANN001
        return None


class QLabel(QWidget):
    def __init__(self, *args, **kwargs) -> None:  # noqa: ANN001
        super().__init__()
        self._text = ""

    def setText(self, text: str) -> None:
        self._text = text

    def text(self) -> str:
        return self._text


class QPushButton(QWidget):
    clicked = _Signal()


class QMessageBox:
    Ok = 0
    Cancel = 1


@dataclass
class QVBoxLayout:
    _parent: QWidget | None = None

    def addWidget(self, _widget: QWidget) -> None:
        return None


@dataclass
class QHBoxLayout(QVBoxLayout):
    pass


class QMainWindow(QWidget):
    def __init__(self, *args, **kwargs) -> None:  # noqa: ANN001
        super().__init__()


class QDialog(QWidget):
    def exec(self) -> int:
        return 0


class QFileDialog:
    @staticmethod
    def getOpenFileName(*_args, **_kwargs):  # noqa: ANN001
        return "", ""


class QInputDialog:
    @staticmethod
    def getText(*_args, **_kwargs):  # noqa: ANN001
        return "", False


class QLineEdit(QWidget):
    def __init__(self, *args, **kwargs) -> None:  # noqa: ANN001
        super().__init__()
        self._text = ""

    def setText(self, text: str) -> None:
        self._text = text

    def text(self) -> str:
        return self._text


class QTextEdit(QLineEdit):
    pass


class QCheckBox(QWidget):
    def __init__(self, *args, **kwargs) -> None:  # noqa: ANN001
        super().__init__()
        self._checked = False

    def setChecked(self, value: bool) -> None:
        self._checked = bool(value)

    def isChecked(self) -> bool:
        return self._checked


class QComboBox(QWidget):
    def __init__(self, *args, **kwargs) -> None:  # noqa: ANN001
        super().__init__()
        self._items: list[str] = []
        self._current = 0

    def addItem(self, text: str) -> None:
        self._items.append(text)

    def currentText(self) -> str:
        if not self._items:
            return ""
        return self._items[self._current]


class QListWidgetItem:
    def __init__(self, text: str = "") -> None:
        self._text = text

    def text(self) -> str:
        return self._text


class QListWidget(QWidget):
    def __init__(self, *args, **kwargs) -> None:  # noqa: ANN001
        super().__init__()
        self._items: list[QListWidgetItem] = []

    def addItem(self, item):  # noqa: ANN001
        if isinstance(item, str):
            self._items.append(QListWidgetItem(item))
        else:
            self._items.append(item)


class QSplitter(QWidget):
    def __init__(self, *args, **kwargs) -> None:  # noqa: ANN001
        super().__init__()


class QStackedWidget(QWidget):
    def __init__(self, *args, **kwargs) -> None:  # noqa: ANN001
        super().__init__()


class QStatusBar(QWidget):
    pass


class QTabWidget(QWidget):
    pass


def __getattr__(name: str):  # noqa: ANN001
    """
    Fallback for unimplemented QtWidgets symbols.

    Used to satisfy imports during test collection when the real Qt bindings are
    unavailable or unsafe to import.
    """
    return type(name, (), {})
