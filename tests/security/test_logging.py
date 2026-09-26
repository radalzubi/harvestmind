"""Logs never carry tokens or tenant rows (SEC-015)."""
from __future__ import annotations

import io
import logging


def test_intake_logger_prints_no_local_variables():
    import api.routers.intake  # noqa: F401  configures the loguru sink
    from loguru import logger
    sink = io.StringIO()
    handle = logger.add(sink, level="INFO", diagnose=False, backtrace=False)
    try:
        def inner():
            tenant_rows = {"supplier": "SECRET-SUPPLIER-VALUE", "price": 12.5}   # noqa: F841  a local the traceback must not print
            raise RuntimeError("boom")
        try:
            inner()
        except RuntimeError:
            logger.exception("confirm insert failed for session {}", "ext-000000000000")
    finally:
        logger.remove(handle)
    text = sink.getvalue()
    assert "confirm insert failed" in text and "SECRET-SUPPLIER-VALUE" not in text


def test_request_logs_carry_the_request_id_not_the_token():
    from api.main import _log
    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    _log.addHandler(handler)
    try:
        _log.exception("unhandled error request_id=%s path=%s", "req-abc", "/me")
    finally:
        _log.removeHandler(handler)
    assert "req-abc" in buf.getvalue() and "Bearer" not in buf.getvalue()
