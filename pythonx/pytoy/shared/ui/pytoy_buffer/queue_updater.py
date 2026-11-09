import logging
from queue import Empty, Queue

from pytoy.shared.pytoy_configuration import PytoyConfiguration
from pytoy.shared.timertask import TimerTask
from pytoy.shared.ui.contract.buffer import BufferProtocol as PytoyBufferProtocol


class QueueUpdater:
    """Update buffer from `threading.Queue` and `TimerTask`."""

    def __init__(
        self,
        buffer: PytoyBufferProtocol,
        queue: Queue,
        taskname: str | None = None,
        interval: int = 100,
    ):
        self._buffer = buffer
        self._taskname = taskname
        self._queue = queue
        self._interval = interval
        self._logger: logging.Logger | None = None

    @property
    def taskname(self) -> str | None:
        return self._taskname

    def _updater(self):
        while True:
            try:
                lines: list[str] = self._queue.get_nowait()
            except Empty:
                break
            content = "\n".join(lines)
            try:
                self._buffer.append(content)
            except Exception:
                if self._logger is None:
                    self._logger = PytoyConfiguration().get_logger(location="global", level=logging.INFO)
                self._logger.exception("QueueUpdater failed to append queued content")
                raise

    def register(self) -> str:
        self._taskname = TimerTask.register(self._updater, name=self._taskname)
        return self._taskname

    def deregister(self):
        if not self.taskname:
            raise ValueError("`QueueUpdater`: TimerTask is not yet registered.`")
        # In order to acquire the info as much as possible.
        self._updater()
        TimerTask.deregister(self.taskname)
