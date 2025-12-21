"""Lightweight QtTest stubs."""


class QTest:
    @staticmethod
    def qWait(_ms: int) -> None:
        return None


def __getattr__(name: str):  # noqa: ANN001
    return type(name, (), {})
