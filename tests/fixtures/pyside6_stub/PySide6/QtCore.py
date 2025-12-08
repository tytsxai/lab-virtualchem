"""Lightweight QtCore stubs used in tests."""

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
    def __init__(self) -> None:
        self.timeout = _Signal()
        self._single_shot = False

    def setSingleShot(self, value: bool) -> None:
        self._single_shot = bool(value)

    def start(self, _timeout: int | None = None) -> None:
        # No-op timing stub; callers rely on timeout signal manually.
        pass

    def stop(self) -> None:
        pass
