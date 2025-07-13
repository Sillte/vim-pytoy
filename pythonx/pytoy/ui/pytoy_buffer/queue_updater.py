from queue import Queue, Empty
from pytoy.infra.timertask import TimerTask
from pytoy.ui.pytoy_buffer.protocol import PytoyBufferProtocol


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

    @property
    def taskname(self) -> str | None:
        return self._taskname

    def _updater(self):
        while self._queue.qsize():
            try:
                lines: list[str] = self._queue.get_nowait()
                content = "".join(lines)
                self._buffer.append(content)  # type: ignore
            except Empty:
                break
            except Exception as e:
                print("_QueueUpdater", e)

    def register(self) -> str:
        self._taskname = TimerTask.register(self._updater, name=self._taskname)
        return self._taskname

    def deregister(self):
        if not self.taskname:
            raise ValueError("`QueueUpdater`: TimerTask is not yet registered.`")
        # In order to acquire the info as much as possible.
        self._updater()
        TimerTask.deregister(self.taskname)
