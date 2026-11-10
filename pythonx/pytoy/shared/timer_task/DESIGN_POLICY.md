# Design Policy

## Purpose

Provide timer-based execution shared by Vim, Neovim, and non-editor environments.

## Public API

- `TimerTaskScheduler` and the supported dispatch/thread-affinity helpers are
  exported from the package root in `__init__.py`.
- `TimerTaskManager` and backend implementations are internal infrastructure.

## Design

- `TimerTaskScheduler` is the public operation facade; it delegates to a
  `TimerTaskManager`.
- `GlobalCoreContext` owns the shared `TimerTaskManager`.
- A scheduler may receive a manager explicitly for isolated tests and composition.
- `TimerTaskScheduler()` uses the manager from `GlobalCoreContext` by default.
- Global dispatch and thread-affinity helpers use the manager from
  `GlobalCoreContext`, ensuring they share the dispatch thread used by the product
  `TimerTaskScheduler`.
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
- TimerTaskScheduler notification hooks and Event notifications must execute on the
	thread guaranteed by TimerTaskScheduler.
- This includes `on_finish`, `on_error`, and the `TimerTaskScheduler` implementation's
	registration, deregistration, and exit Event notifications.
- Each TimerTaskScheduler implementation is responsible for defining and maintaining
	the thread on which its callbacks and Event notifications are executed. It
	exposes that thread through the `backend_thread` property.
- Consumers may rely on the TimerTaskScheduler guarantee and must not need to know which
	concrete thread a TimerTaskScheduler implementation uses.
- `TimerTaskScheduler.is_dispatch_thread()` reports whether the caller is on a
  thread used by the scheduler to execute callbacks.
- `assert_backend_or_main_thread()` and `backend_or_main_thread_only` provide
	the shared policy for APIs that may run on the main or TimerTaskScheduler dispatch
	thread.
- `backend_thread_dispatch` schedules a no-argument backend operation on the
	TimerTaskScheduler execution thread and may receive an `on_error` callback.
- Backend operations in the Dummy backend must use
	`backend_thread_dispatch`, so the Dummy backend follows the same dispatch
	boundary as editor backends.

## Discussion

- Whether exceptions raised by `on_finish` and `on_error` should be exposed is unresolved.
