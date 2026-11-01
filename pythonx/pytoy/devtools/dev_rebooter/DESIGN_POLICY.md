# Design Policy

## Purpose

Provide opt-in diagnostics for the Vim integration and its Python support
code, especially when behavior crosses threads, callbacks, or process
boundaries.

## Design

- `DebugLogger` is an independently configurable diagnostic adapter. Code that
  needs shared routing should inject the same standard `logging.Logger`; the
  adapter itself is not a singleton.
- Log lines remain human-readable and include a timestamp, severity, process,
  and thread identity. Structured context is represented as `key=value` pairs
  on the same line.
- `event()` is used for named lifecycle or callback events. `exception()` is
  used when a traceback is relevant to the failure.
- Categories such as `lock`, `vim.event`, `asyncio`, and `vscode.neovim` are
  supplied as the `category` field so an investigation can filter related
  records without changing the message text.
- `DebugLock` and `VimEventTracer` provide diagnostics for their own concerns;
  they must not become general-purpose synchronization or event abstractions.
- `VimEventTracer` owns Vim autocmd registration and event-context collection.
  It receives a `DebugLogger`; `DebugLogger` does not create or return Vim
  tracers.
- `DebugLogger` is not a singleton. `VimEventTracer` currently reuses one
  tracer for each name because Vimscript callbacks need to resolve a live
  tracer after Python returns to Vim. This is an operational convenience for
  a debugging tool, not a requirement that all tracers share one instance.

## Rules

- Diagnostics must not change the behavior being observed. Logging failures
  must not be allowed to replace the original application failure.
- Existing log calls should remain valid. New call sites should use a severity
  level and named fields when those make the record easier to filter.
- `DebugLock` must not capture a stack on every acquire. Set
  `capture_stack=True` only for a focused investigation; slow waits capture a
  stack when the wait threshold is exceeded.
- Stack and thread-dump collection is diagnostic and potentially expensive; it
  is only performed when `DebugLogger.debug_enabled` is true. Stack traces and
  thread dumps are DEBUG data, even when a lock wait is reported at WARNING.
- `DebugLogger.dump_threads()` can also record asyncio tasks through its
  `with_asyncio` option. `DebugLogger.dump_asyncio()` accepts an explicit event
  loop and records task name, state, and coroutine; task frames are included
  only with `with_stacks=True`. Calls without an active loop are a no-op.
- Diagnostic output is best effort. Logging or handler failures must not
  replace an exception or change the behavior of the operation being observed.
- The logger may be used from worker threads, but callers remain responsible
  for any main-thread requirements of the operation they describe.
- Do not put secrets or full user content into diagnostic fields unless the
  value is necessary to investigate the behavior.
- Use `shared.loggers.setup_logger()` for components that already use the
  standard `logging.Logger` API. Its rotating file handler is the preferred
  file sink for long-running investigations.
- A configured standard logger can be injected with
  `DebugLogger(logger=external_logger)`. In this mode `DebugLogger` delegates
  records to the external logger and does not open or own a logfile.
- In the injected mode, level names, numeric values, filtering, and handler
  policy belong to `logging.Logger`. `DebugLogger` only translates its small
  convenience API into standard logging calls.
- The tracer registry is the essential callback mechanism: a callback carries
  a tracer ID and resolves it in Python. The name-based reuse may be replaced
  later by explicit lifecycle management without changing the callback
  contract.
- Tracer event configuration is copied to an immutable tuple. `events=None`
  selects the default event set, while an empty sequence intentionally means
  that no events are registered.

## Notes

- This logger is for local debugging, not durable application telemetry.
- The logfile format is intentionally line-oriented so it can be inspected
  with ordinary text tools while still carrying stable severity and fields.
- When an external logger is injected, its handlers own filtering, formatting,
  rotation, and closing. `DebugLogger.close()`, `clear()`, and
  logfile selection must not be used to manage that external logger.
- `VimEventTracer.stop()` removes autocmds but currently retains the tracer in
  its registry so a callback already queued by Vim can still resolve it. If
  tracer creation becomes long-lived or dynamic, add an explicit `dispose()`
  operation that stops the tracer and removes both registry entries.

## External Logger Example

```python
import logging

from pytoy.devtools.debug_logger import DebugLogger
from pytoy.shared.loggers import setup_logger


external_logger = setup_logger(
    "vim_pytoy.vscode_neovim",
    log_file="debuglog.txt",
    enable_console=False,
    level=logging.DEBUG,
)
debug_logger = DebugLogger(logger=external_logger)

debug_logger.event(
    "rpc-send",
    category="vscode.neovim",
    trace_id="abc123",
    method="nvim_buf_set_lines",
    request_id=4,
)
```

The caller configures and owns `external_logger`. This makes the same
diagnostic API usable with application-level handlers, pytest `caplog`, or a
rotating workspace log without coupling `DebugLogger` to one file policy.

## Vim Event Example

Create the logging route first, then inject it into the Vim event tracer:

```python
import logging

from pytoy.devtools.debug_logger import DebugLogger, VimEventTracer
from pytoy.shared.loggers import setup_logger


external_logger = setup_logger(
    "vim_pytoy.events",
    log_file="debuglog.txt",
    enable_console=False,
    level=logging.INFO,
)
debug_logger = DebugLogger(logger=external_logger)
event_tracer = VimEventTracer(
    name="workspace-events",
    logger=debug_logger,
    events=("BufEnter", "BufLeave", "WinEnter"),
)
event_tracer.start()
```

When a registered Vim event fires, the tracer records an event with the
`vim.event` category, the event name, buffer number, window id, and buffer
name. Call `event_tracer.stop()` when the investigation ends. The tracer is
the Vim integration boundary; the logger only records the observation.

## Async Communication Example

When investigating communication between Python and the vscode-neovim
extension, log the lifecycle and metadata around each send/receive operation.
Do not log the complete buffer, conversation, or authentication data. A
correlation id connects records from different asyncio tasks.

```python
import asyncio
import logging
from uuid import uuid4

from pytoy.shared.loggers import setup_logger


logger = setup_logger(
    "vim_pytoy.vscode_neovim",
    log_file="debuglog.txt",
    enable_console=False,
    level=logging.DEBUG,
)


def _message_summary(message: dict[str, object]) -> dict[str, object]:
    return {
        "method": message.get("method"),
        "request_id": message.get("id"),
        "field_count": len(message),
    }


async def capture_rpc(send, receive, message: dict[str, object]) -> dict[str, object]:
    trace_id = uuid4().hex[:12]
    summary = _message_summary(message)
    logger.debug(
        "vscode-neovim send",
        extra={"category": "vscode.neovim", "trace_id": trace_id, **summary},
    )

    started = asyncio.get_running_loop().time()
    try:
        await send(message)
        response = await receive()
    except Exception:
        logger.exception(
            "vscode-neovim communication failed",
            extra={"category": "vscode.neovim", "trace_id": trace_id, **summary},
        )
        raise
    else:
        elapsed_ms = (asyncio.get_running_loop().time() - started) * 1000
        logger.debug(
            "vscode-neovim receive",
            extra={
                "category": "vscode.neovim",
                "trace_id": trace_id,
                "elapsed_ms": round(elapsed_ms, 3),
                **_message_summary(response),
            },
        )
        return response
```

`extra` fields are consumed by the configured formatter or handler. If a
component needs category-based filtering, attach a `logging.Filter` to its
handler and accept only records whose `category` matches the investigation.
The transport implementation remains responsible for framing, timeouts, and
main-thread dispatch; logging observes those operations but does not perform
them.