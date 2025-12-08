import contextlib
import json
import logging
from io import StringIO
from pathlib import Path

import pytest

from src.utils.logger import MASK_TEXT, SensitiveDataFilter, StructuredFormatter, setup_logger


def _build_stream_logger(name: str, stream: StringIO, formatter: logging.Formatter) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.handlers.clear()
    logger.propagate = False
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(stream)
    handler.addFilter(SensitiveDataFilter())
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


def test_sensitive_filter_masks_common_patterns():
    stream = StringIO()
    logger = _build_stream_logger("privacy-test-message", stream, logging.Formatter("%(message)s"))

    logger.info("email=john.doe@example.com token=abcd1234efgh phone 138-1234-5678")
    output = stream.getvalue()

    assert "john.doe@example.com" not in output
    assert "***@example.com" in output
    assert "abcd1234efgh" not in output
    assert "token=ab***gh" in output
    assert "138-1234-5678" not in output
    assert "***5678" in output


def test_extra_fields_masked_and_non_sensitive_preserved():
    stream = StringIO()
    logger = _build_stream_logger("privacy-test-extra", stream, StructuredFormatter())

    logger.info(
        "user login",
        extra={
            "extra_data": {
                "password": "supersecret",
                "note": "safe-value",
                "email": "user@example.com",
            }
        },
    )

    payload = json.loads(stream.getvalue())
    assert payload["extra"]["password"] == MASK_TEXT
    assert payload["extra"]["email"] == MASK_TEXT
    assert payload["extra"]["note"] == "safe-value"
    assert payload["message"] == "user login"


def test_setup_logger_enforces_filters_and_levels_in_production(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("ENVIRONMENT", "production")
    log_path = tmp_path / "privacy.log"
    logger = setup_logger("privacy-setup", logging.DEBUG, log_file=log_path, enable_console=False)

    try:
        assert logger.level >= logging.INFO
        assert all(handler.level >= logging.INFO for handler in logger.handlers)
        assert any(isinstance(f, SensitiveDataFilter) for h in logger.handlers for f in h.filters)

        logger.info("secret=shhh-this-should-not-leak")
        for handler in logger.handlers:
            with contextlib.suppress(Exception):
                handler.flush()

        content = log_path.read_text(encoding="utf-8")
        assert "secret=shhh-this-should-not-leak" not in content
        assert "sh***ak" in content or MASK_TEXT in content
    finally:
        for handler in list(logger.handlers):
            with contextlib.suppress(Exception):
                handler.close()
        logger.handlers.clear()
