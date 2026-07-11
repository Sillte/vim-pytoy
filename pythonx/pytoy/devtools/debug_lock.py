from pytoy.devtools.debug_logger import DebugLogger


import threading
import time
from contextlib import contextmanager


class DebugLock:
    def __init__(
        self,
        lock: threading.Lock | threading.RLock,
        *,
        name: str,
        logger: DebugLogger | None = None,
        dump_after_ms: float | None = 1000,
    ) -> None:
        self._lock = lock
        self._name = name
        self._logger = logger or DebugLogger()
        self._dump_after_ms = dump_after_ms

        self._owner: int | None = None
        self._owner_name: str | None = None
        self._depth = threading.local()

    def _get_depth(self) -> int:
        return getattr(self._depth, "value", 0)

    def _set_depth(self, value) -> None:
        self._depth.value = value

    def acquire(self) -> bool:
        depth = self._get_depth()
        start = time.perf_counter()
        current = threading.current_thread()

        self._logger.stack()
        self._logger.log(
            f"WAIT {self._name} "
            f"depth={depth} "
            f"current={current.name}({current.ident}) "
            f"owner={self._owner_name}({self._owner})"
        )

        acquired = self._lock.acquire()
        if acquired:
            self._owner = threading.get_ident()
            self._owner_name = threading.current_thread().name

        elapsed = (time.perf_counter() - start) * 1000

        self._set_depth(depth + 1)

        self._logger.log(
            f"ACQUIRE {self._name} depth={depth + 1} ({elapsed:.3f} ms)owner={self._owner_name}({self._owner})"
        )

        if self._dump_after_ms is not None and elapsed >= self._dump_after_ms:
            self._logger.log(f"LOCK WAIT WARNING: {self._name}")
            self._logger.dump_threads()

        return acquired

    def release(self) -> None:
        depth = self._get_depth()
        self._logger.log(f"RELEASE {self._name} depth={depth} owner={self._owner_name}({self._owner})")

        self._set_depth(max(0, depth - 1))
        if self._get_depth() == 0:
            self._owner = None
            self._owner_name = None

        self._lock.release()

    @contextmanager
    def scope(self):
        self.acquire()
        try:
            yield
        finally:
            self.release()

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.release()
