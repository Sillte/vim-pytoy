# Design Policy

## Purpose

Provide named, lifecycle-managed recurring routines by composing shared timer and thread-execution services.

## Design

- `RoutineSessionHandler` is the package's user-facing facade. A session owns its routine units; its manager retains active sessions and removes them when the session exits.
- A routine unit's runner owns iteration counting and schedules each next iteration through `TimerTask`. Each worker invocation is executed through `ThreadExecution`; routine sessions must not implement their own thread or timer backends.
- A unit's `on_exit` reports an individual iteration. A session's `on_exit` reports termination of the whole session. Keep these event scopes distinct.
- The session manager is an internal registry. Handlers use the core context's manager by default; explicit manager injection is for isolated composition and tests.

## Rules

- Unit names are unique within a session.
- Terminating a session terminates its units before notifying session-exit subscribers.
- A finite `max_iteration` is the total number of worker invocations; `None` means the unit repeats without a limit.
