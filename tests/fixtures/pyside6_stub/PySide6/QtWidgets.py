"""Lightweight QtWidgets stubs."""


class QApplication:
    _instance = None

    def __init__(self, _args=None) -> None:
        type(self)._instance = self

    @classmethod
    def instance(cls):
        return cls._instance

    def processEvents(self) -> None:
        pass
