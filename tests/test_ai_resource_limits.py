from __future__ import annotations

import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor

import pytest

from src.ai.chemistry_assistant import ChemistryAI


@pytest.fixture
def fake_ai():
    ai = ChemistryAI.__new__(ChemistryAI)
    ai.qa_chain = None
    ai._request_timestamps = deque()
    ai._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="test_chem_ai")
    ai.MAX_INPUT_CHARS = 10
    ai.MAX_REQUESTS_PER_MINUTE = 2
    ai.REQUEST_TIMEOUT_SECONDS = 0.05
    yield ai
    ai._executor.shutdown(wait=False, cancel_futures=True)


def test_ask_rejects_too_long_input(fake_ai):
    fake_ai.llm = lambda _prompt: "ok"
    result = fake_ai.ask("x" * 11)
    assert "输入过长" in result


def test_ask_rate_limited(fake_ai, monkeypatch):
    fake_ai.llm = lambda _prompt: "ok"

    t = 1000.0

    def _mono():
        return t

    monkeypatch.setattr("src.ai.chemistry_assistant.time.monotonic", _mono)

    assert fake_ai.ask("hi") == "ok"
    assert fake_ai.ask("hi2") == "ok"

    # 第三次在同一分钟内应被限流
    denied = fake_ai.ask("hi3")
    assert "请求过于频繁" in denied


def test_ask_timeout(fake_ai):
    def slow_llm(_prompt: str) -> str:
        time.sleep(0.2)
        return "late"

    fake_ai.llm = slow_llm
    result = fake_ai.ask("hi")
    assert "超时" in result


def test_logs_do_not_include_raw_input(fake_ai, caplog):
    secret = "SECRET_INPUT_DO_NOT_LOG"
    fake_ai.llm = lambda _prompt: "ok"
    with caplog.at_level("INFO"):
        _ = fake_ai.ask(secret)
    combined = "\n".join(r.message for r in caplog.records)
    assert secret not in combined
    assert "input_len=" in combined
    assert "sha256_16=" in combined

