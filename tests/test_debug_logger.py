import asyncio
import logging
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest

from pytoy.devtools.debug_logger import DebugLogger, VimEventTracer


@pytest.fixture
def logger(tmp_path: Path):
    instance = DebugLogger(tmp_path / "debug.log")
    try:
        yield instance
    finally:
        instance.close()


def test_log_includes_level_and_fields(logger: DebugLogger, tmp_path: Path):
    logger.event("buffer-enter", category="vim.event", buf=3, name="test.py")

    content = (tmp_path / "debug.log").read_text()

    assert "[INFO]" in content
    assert "category=vim.event" in content
    assert "[EVENT] buffer-enter" in content
    assert "buf=3 name=test.py" in content


def test_min_level_filters_debug_messages(logger: DebugLogger, tmp_path: Path):
    logger.set_level("WARNING")
    other_logger = DebugLogger(tmp_path / "other.log")
    try:
        assert other_logger.min_level == "DEBUG"
    finally:
        other_logger.close()
    logger.log("hidden", level="INFO")
    logger.log("visible", level="WARNING")

    content = (tmp_path / "debug.log").read_text()

    assert "hidden" not in content
    assert "visible" in content


def test_trace_logs_exception_with_traceback(logger: DebugLogger, tmp_path: Path):
    with pytest.raises(ValueError):
        with logger.trace("operation"):
            raise ValueError("bad value")

    content = (tmp_path / "debug.log").read_text()

    assert "[ERROR]" in content
    assert "ValueError: bad value" in content
    assert "status=error" in content


def test_external_logging_logger_is_used(tmp_path: Path, caplog: pytest.LogCaptureFixture):
    external_logger = logging.getLogger("test.debug_logger.external")
    external_logger.setLevel(logging.DEBUG)
    instance = DebugLogger(tmp_path / "unused.log", logger=external_logger)
    try:
        with caplog.at_level(logging.DEBUG, logger=external_logger.name):
            instance.event("rpc-send", category="vscode.neovim", request_id=4)
    finally:
        instance.close()

    assert "[EVENT] rpc-send" in caplog.text
    assert "category=vscode.neovim" in caplog.text
    assert not (tmp_path / "unused.log").exists()


def test_external_logger_owns_level_configuration(tmp_path: Path):
    external_logger = logging.getLogger("test.debug_logger.level")
    external_logger.setLevel(logging.ERROR)
    instance = DebugLogger(tmp_path / "unused.log", logger=external_logger)
    try:
        assert instance.min_level == "ERROR"
        instance.set_level("DEBUG")
        assert external_logger.level == logging.DEBUG
        assert instance.min_level == "DEBUG"
    finally:
        instance.close()


def test_instances_are_independent(tmp_path: Path):
    first = DebugLogger(tmp_path / "first.log", min_level="WARNING")
    second = DebugLogger(tmp_path / "second.log")
    try:
        assert first is not second
        assert first.min_level == "WARNING"
        assert second.min_level == "DEBUG"
    finally:
        first.close()
        second.close()


def test_vim_event_tracer_uses_injected_logger(logger: DebugLogger):
    tracer = VimEventTracer(name="test-injected-logger", logger=logger)

    assert tracer.logger is logger


def test_vim_event_tracer_start_uses_tracer_id(monkeypatch: pytest.MonkeyPatch, logger: DebugLogger):
    commands: list[str] = []
    monkeypatch.setitem(sys.modules, "vim", SimpleNamespace(command=commands.append))
    tracer = VimEventTracer(name="test-start-id", events=("BufEnter",), logger=logger)

    tracer.start()

    assert tracer._enabled
    assert any(f"log_nvim_event({tracer.id}, 'BufEnter')" in command for command in commands)
    assert all('"test-start-id"' not in command for command in commands)


def test_vim_event_tracer_rejects_invalid_event(monkeypatch: pytest.MonkeyPatch, logger: DebugLogger):
    monkeypatch.setitem(sys.modules, "vim", SimpleNamespace(command=lambda command: None))
    tracer = VimEventTracer(name="test-invalid-event", events=("BufEnter; echo bad",), logger=logger)

    with pytest.raises(ValueError, match="Invalid Vim event"):
        tracer.start()


def test_vim_event_tracer_copies_events_and_allows_empty_configuration(logger: DebugLogger):
    events = ["BufEnter"]
    tracer = VimEventTracer(name="test-event-copy", events=events, logger=logger)
    events.append("BufLeave")
    empty_tracer = VimEventTracer(name="test-empty-events", events=(), logger=logger)

    assert tracer._events == ("BufEnter",)
    assert empty_tracer._events == ()


def test_external_logger_keeps_thread_dump(caplog: pytest.LogCaptureFixture):
    external_logger = logging.getLogger("test.debug_logger.thread_dump")
    external_logger.setLevel(logging.DEBUG)
    instance = DebugLogger(logger=external_logger)

    with caplog.at_level(logging.DEBUG, logger=external_logger.name):
        instance.dump_threads()

    assert "THREAD DUMP" in caplog.text
    assert "Thread " in caplog.text


def test_dump_asyncio_logs_running_tasks(caplog: pytest.LogCaptureFixture):
    external_logger = logging.getLogger("test.debug_logger.tasks")
    external_logger.setLevel(logging.DEBUG)
    instance = DebugLogger(logger=external_logger)

    async def task_body():
        await asyncio.sleep(1)

    async def exercise():
        task = asyncio.create_task(task_body(), name="test-task")
        try:
            instance.dump_asyncio()
            instance.dump_asyncio(with_stacks=True)
        finally:
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task

    with caplog.at_level(logging.DEBUG, logger=external_logger.name):
        asyncio.run(exercise())

    assert "category=asyncio.task_dump" in caplog.text
    assert "Running: True" in caplog.text
    assert "Closed: False" in caplog.text
    assert "Task count: 2" in caplog.text
    assert "Task test-task state=pending" in caplog.text
    assert "test_dump_asyncio_logs_running_tasks.<locals>.task_body" in caplog.text
    assert "in task_body" in caplog.text


def test_logging_failure_does_not_replace_application_exception(tmp_path: Path):
    class FailingLogger:
        def isEnabledFor(self, level: int) -> bool:
            return True

        def log(self, *args: object, **kwargs: object) -> None:
            raise RuntimeError("logging failed")

    instance = DebugLogger(tmp_path / "unused.log", logger=cast(logging.Logger, FailingLogger()))

    with pytest.raises(ValueError, match="application failed"):
        with instance.trace("operation"):
            raise ValueError("application failed")
