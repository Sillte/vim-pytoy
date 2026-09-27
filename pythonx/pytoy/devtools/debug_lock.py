from __future__ import annotations

import threading
import time
from contextlib import contextmanager

from pytoy.devtools.debug_logger import DebugLogger


class DebugLock:
    def __init__(
        self,
        lock: threading.Lock | threading.RLock,
        *,
        name: str,
        logger: DebugLogger | None = None,
        dump_after_ms: float | None = 1000,
        capture_stack: bool = False,
    ) -> None:
        self._lock = lock
        self._name = name
        self._logger = logger if logger is not None else DebugLogger()
        self._dump_after_ms = dump_after_ms
        self._capture_stack = capture_stack
        self._state_lock = threading.Lock()

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

        if self._capture_stack:
            self._logger.stack()
        with self._state_lock:
            owner = self._owner
            owner_name = self._owner_name
        self._logger.log(
            f"WAIT {self._name} depth={depth} current={current.name}({current.ident}) owner={owner_name}({owner})",
            category="lock",
        )

        acquired = self._lock.acquire()
        if acquired:
            with self._state_lock:
                self._owner = threading.get_ident()
                self._owner_name = threading.current_thread().name

        elapsed = (time.perf_counter() - start) * 1000

        self._set_depth(depth + 1)

        with self._state_lock:
            owner = self._owner
            owner_name = self._owner_name
        self._logger.log(
            f"ACQUIRE {self._name} depth={depth + 1}",
            category="lock",
            elapsed_ms=f"{elapsed:.3f}",
            owner=owner_name,
            owner_id=owner,
        )

        if self._dump_after_ms is not None and elapsed >= self._dump_after_ms:
            self._logger.log(f"LOCK WAIT WARNING: {self._name}", category="lock", elapsed_ms=f"{elapsed:.3f}")
            if self._logger.debug_enabled:
                self._logger.stack()
                self._logger.dump_threads()

        return acquired

    def release(self) -> None:
        depth = self._get_depth()
        current_id = threading.get_ident()
        with self._state_lock:
            owner = self._owner
            owner_name = self._owner_name
        self._logger.log(
            f"RELEASE {self._name} depth={depth}",
            category="lock",
            owner=owner_name,
            owner_id=owner,
        )
        if owner != current_id:
            self._logger.log(
                f"RELEASE OWNER MISMATCH {self._name}",
                level="WARNING",
                category="lock",
                expected_owner=owner,
                actual_owner=current_id,
            )

        self._set_depth(max(0, depth - 1))
        if self._get_depth() == 0:
            with self._state_lock:
                self._owner = None
                self._owner_name = None

        self._lock.release()

    @contextmanager
    def scope(self):
        self.acquire()
        try:
            yield
        except Exception as error:
            self._logger.exception(
                f"LOCK SCOPE ERROR {self._name}: {type(error).__name__}: {error}",
                category="lock",
            )
            raise
        finally:
            self.release()

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.release()
