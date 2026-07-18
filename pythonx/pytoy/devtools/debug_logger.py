from __future__ import annotations

from pathlib import Path
from datetime import datetime
from contextlib import contextmanager
from typing import TextIO, Sequence, Self
import os
import sys
import threading
import time
import traceback


class DebugLogger:
    """Thread-safe singleton logger for debugging."""

    _instance: "DebugLogger | None" = None
    _instance_lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(
        self,
        logfile: Path | str | None = None,
    ):
        if self._initialized:
            if logfile and logfile != Path(self._logfile):
                self.change_logfile(logfile)
            return
        self._initialized = True

        logfile = Path(logfile or "./debuglog.txt")
        logfile.parent.mkdir(parents=True, exist_ok=True)

        self._lock = threading.RLock()
        self._depth = threading.local()

        self._logfile = logfile
        self._fp: TextIO | None = None

        self.change_logfile(logfile)

    @property
    def enabled(self) -> bool:
        return self._fp is not None

    def enable(self):
        if self._fp is None:
            self.change_logfile(self._logfile)

    def disable(self):
        self.close()

    def close(self):
        with self._lock:
            if self._fp is not None:
                self._fp.close()
                self._fp = None

    def clear(self):
        self.close()
        self._logfile.write_text("")
        self.change_logfile(self._logfile)

    def change_logfile(self, logfile: Path | str):
        logfile = Path(logfile)

        with self._lock:
            if self._fp is not None:
                self._fp.close()

            logfile.parent.mkdir(parents=True, exist_ok=True)
            self._logfile = logfile

            self._fp = logfile.open(
                "a",
                encoding="utf-8",
                buffering=1,
            )

    def log(self, *message: object):
        now = datetime.now().strftime("%H:%M:%S.%f")[:-3]

        pid = os.getpid()
        tid = threading.get_ident()
        tname = threading.current_thread().name

        line = " ".join(map(str, message))

        with self._lock:
            fp = self._fp
            if fp is None:
                return
            fp.write(f"{now} [P:{pid}] [{tname}:{tid}] {line}\n")
            fp.flush()

    @contextmanager
    def trace(
        self,
        *message: object,
        stack: bool = False,
        warn_ms: float | None = None,
    ):
        line = " ".join(map(str, message))

        depth = self._get_depth()
        self._set_depth(depth + 1)

        prefix = "  " * depth

        self.log(f"{prefix}>>> {line}")

        if stack:
            self.stack()

        start = time.perf_counter()

        try:
            yield
        except Exception as e:
            self.log(f"{prefix}!!! {type(e).__name__}: {e}")
            self.log(traceback.format_exc())
            raise

        finally:
            elapsed = (time.perf_counter() - start) * 1000

            self._set_depth(depth)

            self.log(f"{prefix}<<< {line} ({elapsed:.3f} ms)")

            if warn_ms is not None and elapsed >= warn_ms:
                self.log(f"WARNING: '{line}' took {elapsed:.3f} ms")
                self.dump_threads()

    def stack(self):
        for s in traceback.format_stack()[:-1]:
            self.log(s.rstrip())

    def _write_with_no_lock(self, line):
        if self._fp:
            self._fp.write(line)
            self._fp.flush()

    def dump_threads(self):
        self.log("========== THREAD DUMP ==========")
        threads = {t.ident: t.name for t in threading.enumerate()}
        with self._lock:
            for tid, frame in sys._current_frames().items():
                name = threads.get(tid, "<unknown>")
                self._write_with_no_lock(f"\nThread {name} ({tid}) \n")
                for s in traceback.format_stack(frame):
                    self._write_with_no_lock(s.rstrip())
                self._write_with_no_lock("\n")
        self.log("=================================")

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
    
    @classmethod
    def get(cls, name: str) -> Self | None:
        return cls.instances.get(name)

    def __new__(cls, name:str = "default", events: Sequence[str] | None = None, *args, **kwargs):
        if name in cls.instances:
            instance = cls.instances[name]
            if events and set(events) != instance._events:
                raise ValueError(f"Failed to initiate `VimEventTracer`, {events}")
            return instance
        return super().__new__(cls, *args, **kwargs)


    def __init__(self, name:str = "default", events: Sequence[str] | None = None) -> None:
        if getattr(self, "_initialized", False):
            return

        self._initialized = True
        events = events or self.DEFAULT_EVENTS
        self._initialized = True
        self._logger = DebugLogger()
        self._events = events
        self._id = id(self)
        self._enabled = False
        self._name = name
        self.instances[self._name] = self
        
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
        self._enabled = True

        vim.command(f"augroup PytoyTrace{self._id}")
        vim.command("autocmd!")

        for event in self._events:
            vim.command(
                rf'autocmd {event} * python3 from pytoy.devtools.debug_logger import log_nvim_event; log_nvim_event("{self._name}", "{event}")'
            )
        vim.command("augroup END")
        
    def stop(self) -> None:
        if not self._enabled:
            return 
        import vim
        vim.command(f"augroup PytoyTrace{self._id}")
        vim.command("autocmd!")
        vim.command("augroup END")
        self._enabled = False
        

def log_nvim_event(name: str, event: str):
    import vim

    tracer = VimEventTracer.get(name)
    if not tracer:
        raise ValueError("Tracer cannot be retrieved.")
    logger = tracer.logger

    bufnr = vim.current.buffer.number
    winid = vim.eval("win_getid()")
    buffer_name = vim.current.buffer.name


    logger.log(
        f"[EVENT] {event} "
        f"buf={bufnr} "
        f"win={winid} "
        f"name={buffer_name}"
    )
    

if __name__ == "__main__":
    ...
