# Design Policy

## Purpose

Manage command execution from a user request through a handler-based
execution lifecycle and completion notification.

## Terminology

- `Command`: A user-requested operation represented by
  `CommandExecutionRequest`.
- `Execution`: A single concrete attempt to execute a command.
- `Resolved Parameters`: Concrete parameters and resources resolved for an
  execution before it starts.

## Design

- `CommandExecutionHandler` is the public handle for an execution;
  `CommandExecution` remains an internal entity.
- Information required to repeat an execution is preserved independently of
  the concrete execution entity.
- Execution completion is transferred through the package's exit/event flow
  rather than exposing the internal execution entity to external consumers.

## Rules

- Command creation, handler creation, and execution start must be performed
  from the backend's required thread. 
- Execution state queries may be performed from any thread.
- External code must not depend on `CommandExecution` as part of the command
  execution interface.
- Hook callbacks must not raise exceptions. A hook that raises is considered an implementation error in the caller's integration.

## Discussions

- Query results are best-effort observations rather than stable snapshots.
