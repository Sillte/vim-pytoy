# Specification

The public API is exported from `__init__.py`. The main user-facing types are
`RoutineSessionHandler` and `RoutineUnitHandler`.

## Session lifecycle

- A session owns routine units whose names are unique within that session.
- A session handler uses the global core-context manager unless a manager is
  explicitly supplied.
- `terminate()` is idempotent. It terminates the session's units before firing
  `on_exit` with the session ID.
- If an `on_exit` listener raises, Event dispatch stops at that listener. The
  exit emitter is still disposed before the exception propagates.
- Once terminated, session operations that require the session object fail;
  `id` remains available and further calls to `terminate()` do nothing.

## Routine unit lifecycle

- `start()` requests the first execution without applying the inter-iteration
  delay. Preparation may run after `start()` returns. Calling `start()` again
  while the unit is starting or active has no effect. Starting a terminated
  unit raises an error.
- `alive` is false before the first execution starts and after termination; it
  is true while an execution is running or the unit is waiting for its next
  iteration.
- Each worker invocation runs through `ThreadExecutionHandler`. After an
  execution exits, the unit increments its iteration count and either schedules
  the next execution after the requested delay or terminates.
- `max_iteration` is the total number of executions. `None` means no limit.
- `on_execution_preparing` fires before each execution is started and provides
  its `ThreadExecutionHandler`. Listeners must not start or discard that handler.
- If `on_execution_preparing` raises before the first execution starts, the
  execution is discarded and the unit returns to an unstarted, retryable state.
  Since preparation is dispatched asynchronously, the error is handled by the
  TimerTask dispatch and is not raised synchronously by `start()`. If preparing
  a later iteration raises, the unit is terminated before the error is handed
  back to TimerTask dispatch.
- For each iteration, the `RoutineUnitHooks.on_exit` callback runs before the
  `on_iteration_exit` event. Callback errors do not prevent iteration-count
  updates, scheduling, or unit termination. A single error propagates after
  that processing; multiple errors are raised as an `ExceptionGroup`.
- Event listener exceptions follow the [`Event` contract](../../lib/events/SPECIFICATION.md):
  dispatch stops at the first failing listener, and the exception propagates
  after routine processing.


## Recommendations
Callbacks registered with events or hooks should generally not raise exceptions.
Exceptions raised by callbacks follow the contract of the event or hook that invokes them.