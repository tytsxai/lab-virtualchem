"""Tests for SensitiveDataFilter and logging setup."""

from __future__ import annotations

import logging

from src.utils.logger import SensitiveDataFilter, setup_logger


def test_sensitive_data_filter_masks_known_fields(caplog):
    logger = logging.getLogger("vcl.test.mask")
    handler = logging.StreamHandler()
    handler.addFilter(SensitiveDataFilter())
    formatter = logging.Formatter("%(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    with caplog.at_level(logging.INFO, logger="vcl.test.mask"):
        logger.info("token=abc123 password=secret email=user@example.com")

    masked = [rec.message for rec in caplog.records]
    assert all("***" in rec for rec in masked)


def test_setup_logger_attaches_filter(monkeypatch):
    logger = setup_logger("vcl.test.setup", logging.INFO)
    assert any(isinstance(f, SensitiveDataFilter) for h in logger.handlers for f in h.filters)
