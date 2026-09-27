import threading
from pathlib import Path

from pytoy.devtools.debug_lock import DebugLock
from pytoy.devtools.debug_logger import DebugLogger


def test_debug_lock_logs_structured_lock_records(tmp_path: Path):
    logger = DebugLogger(tmp_path / "debug.log")
    lock = DebugLock(threading.Lock(), name="test", logger=logger)
    try:
        with lock:
            pass
    finally:
        logger.close()

    content = (tmp_path / "debug.log").read_text()
    assert "category=lock" in content
    assert "elapsed_ms=" in content
    assert ")owner=" not in content


def test_debug_lock_does_not_collect_expensive_diagnostics_at_warning_level(tmp_path: Path, monkeypatch):
    logger = DebugLogger(tmp_path / "debug.log", min_level="WARNING")
    lock = DebugLock(threading.Lock(), name="test", logger=logger, dump_after_ms=0)
    stack_calls = []
    dump_calls = []
    monkeypatch.setattr(logger, "stack", lambda: stack_calls.append(True))
    monkeypatch.setattr(logger, "dump_threads", lambda: dump_calls.append(True))
    try:
        lock.acquire()
        lock.release()
    finally:
        logger.close()

    assert not stack_calls
    assert not dump_calls


def test_debug_lock_captures_stack_when_explicitly_enabled(tmp_path: Path, monkeypatch):
    logger = DebugLogger(tmp_path / "debug.log")
    lock = DebugLock(threading.Lock(), name="test", logger=logger, capture_stack=True)
    stack_calls = []
    monkeypatch.setattr(logger, "stack", lambda: stack_calls.append(True))
    try:
        lock.acquire()
        lock.release()
    finally:
        logger.close()

    assert stack_calls


def test_debug_lock_scope_logs_and_reraises_exception(tmp_path: Path):
    logger = DebugLogger(tmp_path / "debug.log")
    lock = DebugLock(threading.Lock(), name="test", logger=logger)
    error = ValueError("scope failed")

    try:
        try:
            with lock.scope():
                raise error
        except ValueError as caught:
            assert caught is error
    finally:
        logger.close()

    content = (tmp_path / "debug.log").read_text()
    assert "LOCK SCOPE ERROR test: ValueError: scope failed" in content
    assert "Traceback (most recent call last)" in content
    assert "category=lock" in content

    assert lock._lock.acquire(blocking=False)
    lock._lock.release()
