from __future__ import annotations

import asyncio
import logging
import re
import sys
import threading
import time
import traceback
from contextlib import contextmanager
from pathlib import Path
from typing import Self, Sequence


class DebugLogger:
    """Thread-safe logger for local diagnostics."""

    def __init__(
        self,
        logfile: Path | str | None = None,
        *,
        min_level: str | None = None,
        logger: logging.Logger | None = None,
    ):
        logfile = Path(logfile or "./debuglog.txt")
        logfile.parent.mkdir(parents=True, exist_ok=True)

        self._lock = threading.RLock()
        self._depth = threading.local()
        self._logger = logger or logging.getLogger(f"pytoy.debug.{id(self)}")
        self._min_level = self._level_value(min_level or "DEBUG")
        self._handler: logging.Handler | None = None
        self._logfile = logfile
        if logger is None:
            self._logger.setLevel(self._min_level)
            self._add_file_handler(logfile)
        elif min_level is not None:
            self._logger.setLevel(self._min_level)

    @property
    def enabled(self) -> bool:
        return self._logger.isEnabledFor(logging.DEBUG)

    @property
    def debug_enabled(self) -> bool:
        return self._logger.isEnabledFor(logging.DEBUG)

    @property
    def min_level(self) -> str:
        return logging.getLevelName(self._logger.level)

    def set_level(self, level: str) -> None:
        level_value = self._level_value(level)
        if self._logger is not None:
            self._logger.setLevel(level_value)
        else:
            self._min_level = level_value

    @classmethod
    def _level_value(cls, level: str) -> int:
        normalized = level.upper()
        level_value = logging.getLevelNamesMapping().get(normalized)
        if level_value is None:
            raise ValueError(f"Unknown log level: {level}")
        return level_value

    def enable(self):
        if self._handler is None:
            self._open_logfile(self._logfile)

    def disable(self):
        self.close()

    def close(self):
        with self._lock:
            if self._handler is not None:
                self._logger.removeHandler(self._handler)
                self._handler.close()
                self._handler = None

    def clear(self):
        if self._handler is None:
            return
        self.close()
        self._logfile.write_text("")
        self._open_logfile(self._logfile)

    def _open_logfile(self, logfile: Path | str):
        logfile = Path(logfile)

        with self._lock:
            logfile.parent.mkdir(parents=True, exist_ok=True)
            self._logfile = logfile
            self._add_file_handler(logfile)

    def _add_file_handler(self, logfile: Path):
        handler = logging.FileHandler(
            logfile,
            encoding="utf-8",
        )
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] [P:%(process)d] [%(threadName)s:%(thread)d] %(message)s"
        )
        handler.setFormatter(formatter)
        self._logger.addHandler(handler)
        self._handler = handler

    def log(self, *message: object, level: str = "INFO", category: str | None = None, **fields: object):
        self._safe_log_record(message, level=level, category=category, fields=fields)

    def _safe_log_record(
        self,
        message: tuple[object, ...],
        *,
        level: str,
        category: str | None,
        fields: dict[str, object],
    ) -> None:
        try:
            self._log_record(message, level=level, category=category, fields=fields)
        except Exception:
            return

    def _log_record(
        self,
        message: tuple[object, ...],
        *,
        level: str,
        category: str | None,
        fields: dict[str, object],
    ) -> None:
        level = level.upper()
        level_value = self._level_value(level)
        if not self._logger.isEnabledFor(level_value):
            return

        line = " ".join(map(str, message))
        if category is not None:
            line = f"category={category} {line}"
        if fields:
            line += " " + " ".join(f"{key}={value!s}" for key, value in fields.items())

        self._logger.log(
            level_value,
            line,
            extra={"pytoy_category": category, "pytoy_fields": fields},
        )

    def event(
        self,
        event_name: str,
        *,
        level: str = "INFO",
        category: str | None = None,
        **fields: object,
    ) -> None:
        self.log(f"[EVENT] {event_name}", level=level, category=category, **fields)

    def exception(
        self,
        *message: object,
        level: str = "ERROR",
        category: str | None = None,
        **fields: object,
    ) -> None:
        self.log(*message, level=level, category=category, **fields)
        self.log(traceback.format_exc().rstrip(), level=level, category=category)

    @contextmanager
    def trace(
        self,
        *message: object,
        stack: bool = False,
        warn_ms: float | None = None,
        category: str | None = None,
        **fields: object,
    ):
        line = " ".join(map(str, message))

        depth = self._get_depth()
        self._set_depth(depth + 1)

        prefix = "  " * depth
        status = "ok"

        self._safe_log_record((f"{prefix}>>> {line}",), level="INFO", category=category, fields=fields)

        if stack:
            self.stack()

        start = time.perf_counter()

        try:
            yield
        except Exception as e:
            status = "error"
            self._safe_log_record(
                (f"{prefix}!!! {type(e).__name__}: {e}",),
                level="ERROR",
                category=category,
                fields={**fields, "status": "error"},
            )
            self._safe_log_record(
                (traceback.format_exc().rstrip(),),
                level="ERROR",
                category=category,
                fields={},
            )
            raise

        finally:
            elapsed = (time.perf_counter() - start) * 1000

            self._set_depth(depth)

            self._safe_log_record(
                (f"{prefix}<<< {line} ({elapsed:.3f} ms)",),
                level="INFO",
                category=category,
                fields={**fields, "elapsed_ms": f"{elapsed:.3f}", "status": status},
            )

            if warn_ms is not None and elapsed >= warn_ms:
                self.log(f"WARNING: '{line}' took {elapsed:.3f} ms")
                self.dump_threads()

    def stack(self):
        if not self.enabled:
            return
        if not self._logger.isEnabledFor(logging.DEBUG):
            return
        for s in traceback.format_stack()[:-1]:
            self.log(s.rstrip(), level="DEBUG")

    def dump_threads(self, *, with_asyncio: bool = True):
        if not self.enabled:
            return
        threads = {t.ident: t.name for t in threading.enumerate()}
        lines = ["========== THREAD DUMP =========="]
        for tid, frame in sys._current_frames().items():
            name = threads.get(tid, "<unknown>")
            lines.append(f"Thread {name} ({tid})")
            lines.extend(s.rstrip() for s in traceback.format_stack(frame))
        lines.append("=================================")
        self._safe_log_record(
            ("\n".join(lines),),
            level="DEBUG",
            category="thread_dump",
            fields={},
        )
        if with_asyncio:
            self.dump_asyncio()

    def dump_asyncio(
        self,
        loop: asyncio.AbstractEventLoop | None = None,
        *,
        with_stacks: bool = False,
    ) -> None:
        if not self.debug_enabled:
            return
        if loop is None:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                return

        tasks = asyncio.all_tasks(loop)
        lines = [
            "========== ASYNCIO TASK DUMP ==========",
            f"Loop: {loop!r}",
            f"Running: {loop.is_running()}",
            f"Closed: {loop.is_closed()}",
            f"Task count: {len(tasks)}",
        ]
        for task in tasks:
            state = "cancelled" if task.cancelled() else "done" if task.done() else "pending"
            coroutine = task.get_coro()
            coroutine_name = getattr(coroutine, "__qualname__", repr(coroutine))
            lines.append(f"Task {task.get_name()} state={state} coroutine={coroutine_name} repr={task!r}")
            if with_stacks:
                for frame in task.get_stack():
                    lines.append(f"  File {frame.f_code.co_filename}, line {frame.f_lineno}, in {frame.f_code.co_name}")
        lines.append("========================================")
        self._safe_log_record(
            ("\n".join(lines),),
            level="DEBUG",
            category="asyncio.task_dump",
            fields={"task_count": len(tasks)},
        )

    def _get_depth(self):
        return getattr(self._depth, "value", 0)

    def _set_depth(self, value):
        self._depth.value = value


class VimEventTracer:
    DEFAULT_EVENTS = [
        "BufAdd",
        "BufRead",
        "BufReadPost",
        "BufEnter",
        "BufWinEnter",
        "WinEnter",
        "WinNew",
    ]

    instances: dict[str, Self] = dict()
    instances_by_id: dict[int, Self] = dict()
    _event_name_pattern = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")

    @classmethod
    def get(cls, name: str) -> Self | None:
        return cls.instances.get(name)

    def __new__(cls, name: str = "default", events: Sequence[str] | None = None, *args, **kwargs):
        if name in cls.instances:
            instance = cls.instances[name]
            return instance
        return super().__new__(cls)

    def __init__(
        self,
        name: str = "default",
        events: Sequence[str] | None = None,
        logger: DebugLogger | None = None,
    ) -> None:
        if getattr(self, "_initialized", False):
            return

        self._initialized = True
        events = self.DEFAULT_EVENTS if events is None else events
        self._logger = logger if logger is not None else DebugLogger()
        self._events = tuple(events)
        self._id = id(self)
        self._enabled = False
        self._name = name
        self.instances[self._name] = self
        self.instances_by_id[self._id] = self

    @property
    def logger(self) -> DebugLogger:
        return self._logger

    @property
    def id(self) -> int:
        return self._id

    @property
    def name(self):
        return self._name

    def start(self) -> None:
        import vim

        if self._enabled:
            return

        invalid_events = [event for event in self._events if not self._event_name_pattern.fullmatch(event)]
        if invalid_events:
            raise ValueError(f"Invalid Vim event name(s): {invalid_events}")

        vim.command(f"augroup PytoyTrace{self._id}")
        vim.command("autocmd!")

        for event in self._events:
            vim.command(
                rf"autocmd {event} * python3 from pytoy.devtools.debug_logger import log_nvim_event; log_nvim_event({self._id}, '{event}')"
            )
        vim.command("augroup END")
        self._enabled = True

    def stop(self) -> None:
        if not self._enabled:
            return
        import vim

        vim.command(f"augroup PytoyTrace{self._id}")
        vim.command("autocmd!")
        vim.command("augroup END")
        self._enabled = False


def log_nvim_event(tracer_id: int, event: str):
    import vim

    tracer = VimEventTracer.instances_by_id.get(tracer_id)
    if not tracer:
        raise ValueError("Tracer cannot be retrieved.")
    logger = tracer.logger

    bufnr = vim.current.buffer.number
    winid = vim.eval("win_getid()")
    buffer_name = vim.current.buffer.name

    logger.event("vim." + event, category="vim.event", buf=bufnr, win=winid, name=buffer_name)


if __name__ == "__main__":
    ...
