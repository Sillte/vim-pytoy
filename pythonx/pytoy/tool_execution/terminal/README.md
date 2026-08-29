# Design Policy

## Purpose

Manage persistent terminal interactions through handler-based access to
terminal executions.

## Terminology

- `Terminal`: A persistent interactive execution associated with a terminal
  driver and buffer.
- `Execution`: A concrete terminal instance managed by this package.
- `Runner`: A lower-level component responsible for the actual terminal/process
  interaction.

## Design

- A terminal is identified by its driver kind and buffer; when an existing
  execution matches the requested terminal, its handler is reused rather than
  creating another execution.
- The execution context retained by the manager represents the information
  required to create the same terminal again after the previous execution has
  ended.
- Internal `TerminalExecution` objects are not exposed to external callers;
  interaction with an execution is performed through its handler.
- Terminal execution completion is represented as an exit event, which is the
  central lifecycle boundary for completion-related notifications.

## Rules

- Main-thread operations that create or modify terminal executions must be
  performed from the main thread.
- Terminal/process interaction is delegated to the `terminal_runner` package.

## Notes

- A terminal execution represents a persistent interactive terminal rather
  than a single command attempt.

## Discussions

- The representation of failures that occur while starting or running a
  terminal, particularly cases where no exit code can be obtained, has not
  yet been finalized.