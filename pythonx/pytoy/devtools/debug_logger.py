from __future__ import annotations

from pathlib import Path
from datetime import datetime
from contextlib import contextmanager
from typing import TextIO
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
        

def log_nvim_event(event: str):
    import vim

    logger = DebugLogger()

    bufnr = vim.current.buffer.number
    winid = vim.eval("win_getid()")
    name = vim.current.buffer.name

    logger.log(
        f"[EVENT] {event} "
        f"buf={bufnr} "
        f"win={winid} "
        f"name={name}"
    )
    
__ON: bool = False
    
def start_event_log():
    global __ON 
    if __ON:
        return 
    __ON = True
    import vim 
    events = [
        "BufAdd",
        "BufRead",
        "BufReadPost",
        "BufEnter",
        "BufWinEnter",
        "WinEnter",
        "WinNew",
    ]

    vim.command("augroup PytoyTrace")
    vim.command("autocmd!")

    for event in events:
        vim.command(
            rf'autocmd {event} * python3 from pytoy.devtools.debug_logger import log_nvim_event; log_nvim_event("{event}")'
        )

    vim.command("augroup END")


if __name__ == "__main__":
    ...
