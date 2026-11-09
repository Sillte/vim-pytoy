import logging
from queue import Queue
from unittest.mock import Mock

import pytest

from pytoy.shared.ui.pytoy_buffer import queue_updater
from pytoy.shared.ui.pytoy_buffer.queue_updater import QueueUpdater


class BufferStub:
    def __init__(self) -> None:
        self.contents: list[str] = []

    def append(self, content: str) -> None:
        self.contents.append(content)


def test_queue_updater_drains_all_available_items() -> None:
    queue: Queue[list[str]] = Queue()
    queue.put(["first", "line"])
    queue.put(["second"])
    buffer = BufferStub()
    updater = QueueUpdater(buffer, queue)  # pyright: ignore[reportArgumentType]  # ty: ignore[invalid-argument-type]

    updater._updater()

    assert buffer.contents == ["first\nline", "second"]
    assert queue.empty()
    assert updater._logger is None


def test_queue_updater_logs_and_surfaces_append_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    class FailingBuffer:
        def append(self, content: str) -> None:
            raise RuntimeError("append failed")

    logger = Mock(spec=logging.Logger)

    class ConfigurationStub:
        def get_logger(self, *, location: str, level: int) -> logging.Logger:
            assert location == "global"
            assert level == logging.INFO
            return logger

    monkeypatch.setattr(queue_updater, "PytoyConfiguration", ConfigurationStub)
    queue: Queue[list[str]] = Queue()
    queue.put(["queued"])
    updater = QueueUpdater(FailingBuffer(), queue)  # pyright: ignore[reportArgumentType]  # ty: ignore[invalid-argument-type]

    assert updater._logger is None
    with pytest.raises(RuntimeError, match="append failed"):
        updater._updater()

    logger.exception.assert_called_once_with("QueueUpdater failed to append queued content")
    assert updater._logger is logger
