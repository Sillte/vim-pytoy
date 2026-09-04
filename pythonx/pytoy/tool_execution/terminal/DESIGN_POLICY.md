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

### Package Boundaries

Internal implementation modules must not be imported directly from
outside their package.

A package may expose multiple explicit external boundaries:

- `__init__.py`: API for ordinary package users.
- `contract.py` or `contract/`: API required by extension authors.

`contract` is not merely an implementation detail. It explicitly marks
the concepts that extension authors are allowed and expected to depend on.

Therefore, an external module may import from a `contract` package even
when that package is not part of the ordinary user-facing API.

Other internal modules remain implementation details unless explicitly
designated as public.

In Clean Architecture terminology, some contracts may correspond to ports, while others may simply be shared data types or protocols required to implement an infrastructure extension.

We use the contract package to make the extension boundary explicit, rather than relying solely on the architectural notion of a port.

## Rules

- Main-thread operations that create or modify terminal executions must be
  performed from the main thread.
- Terminal/process interaction is delegated to the `terminal_runner` package.
- `TerminalJobProtocol.dispose()` must be safe to call before start, after exit,
  or more than once. Each backend must release its backend-specific resources
  and dispose its shared `TerminalJobCore`.

## Notes

- A terminal execution represents a persistent interactive terminal rather
  than a single command attempt.

## Discussions

- The representation of failures that occur while starting or running a
  terminal, particularly cases where no exit code can be obtained, has not
  yet been finalized.
