# Design Policy

## Purpose

Manage command execution from a user request through a handler-based
execution lifecycle and completion notification.

## Terminology

- `Command`: A user-requested operation represented by
  `CommandExecutionRequest`.
- `Execution`: A single concrete attempt to execute a command.
- `Backend execution context`: The execution context in which the backend
  invokes `TimerTask` callbacks. The `TimerTask` implementation determines
  this context for each backend.

## Design

- `CommandExecutionHandler` is the public handle for an execution;
  `CommandExecution` remains an internal entity.
- Information required to repeat an execution is preserved independently of
  the concrete execution entity.
- Execution completion is transferred through the package's exit/event flow
  rather than exposing the internal execution entity to external consumers.
- Process I/O and backend event callbacks are separate responsibilities.
  Process I/O may be performed asynchronously, while output updates, hooks,
  and execution completion are dispatched through the backend execution
  context.

## Rules

- Command creation, handler creation, execution start, and termination must be
  performed from the main thread.
- Backend implementations must emit command events and invoke event callbacks
  from the backend execution context defined by `TimerTask`.
- External code must not depend on `CommandExecution` as part of the command
  execution interface.
