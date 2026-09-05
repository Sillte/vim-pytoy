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
- `TimerTaskManager` owns public task names. It maps each public name to a
	unique implementation name before calling a backend implementation.
- As a Manager-to-implementation contract, every `TaskName` passed from
	`TimerTaskManager` to a backend implementation is unique among active tasks.
- Backend implementations publish registration and deregistration events.
	`TimerTaskManager` subscribes to these events and protects its public-name
	mapping with an `RLock`, because backend registration may complete on a
	different thread.

## Rules

- Users must not raise exceptions from `on_finish` or `on_error` callbacks.
- `on_finish` and `on_error` callbacks are notification hooks, not part of task control flow.
- TimerTask notification hooks and Event notifications must execute on the
	thread guaranteed by TimerTask.
- This includes `on_finish`, `on_error`, and the `TimerTask` implementation's
	registration, deregistration, and exit Event notifications.
- Each TimerTask implementation is responsible for defining and maintaining
	the thread on which its callbacks and Event notifications are executed.
- Consumers may rely on the TimerTask guarantee and must not need to know which
	concrete thread a TimerTask implementation uses.

## Discussion

- Whether exceptions raised by `on_finish` and `on_error` should be exposed is unresolved.
