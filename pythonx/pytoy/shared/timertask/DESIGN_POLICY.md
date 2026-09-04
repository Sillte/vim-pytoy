# Design Policy

## Purpose

Provide timer-based execution shared by Vim, Neovim, and non-editor environments.

## Design

- `TimerTaskManager` owns the timer API and delegates scheduling to a backend implementation.
- Backend implementations own the registered task state and backend-specific timer handles.
- `TimerStopException` is a control signal for cooperative task termination, not an error.
- A task that raises `TimerStopException` finishes with the `"stopped"` reason.
- Other task exceptions are delivered through `on_error` and do not finish through `on_finish`.
- A task that reaches its repeat limit finishes with the `"finished"` reason.

## Rules

- Users must not raise exceptions from `on_finish` or `on_error` callbacks.
- `on_finish` and `on_error` callbacks are notification hooks, not part of task control flow.


## Discussions 

- The Dummy backend should defensively prevent exceptions from notification
	callbacks (`on_finish` / `on_error`) from terminating its scheduler thread.
    - Other backends execute callbacks on the main thread, so callback exceptions
	    remain observable by the caller and are a lower-priority defensive concern.
