# Design Policy

## Purpose

Manage command execution lifecycle from user request through handler-based completion monitoring.

## Terminology

- `Command`: A user-requested operation to be executed in a terminal, represented by `CommandExecutionRequest`.
- `Execution`: A single concrete attempt to run a command, tracked with a unique ID and status.
- `Runner`: A separate lower-level job_execution package handling actual process spawning and I/O.


## Design

- `CommandExecutor` is the entry point for command execution setup and initiation; it accepts a `CommandExecutionRequest` and returns a `CommandExecutionHandler`.
- `CommandExecutionHandler` manages the lifecycle and state queries of a single execution after it has started.
- Terminal/process concerns are delegated to the `command_runner` package; this package focuses on execution setup, lifecycle management, and buffer I/O coordination.
- External code can query execution state through `CommandExecutionHandler` but cannot access internal `Execution` objects directly.

## Rules
<!-- Constraints that must be preserved when modifying/designing this package,
which is not inferred from the best development practice -->

- Main-thread operations (command creation, handler creation, starting execution) must be called from the main thread.
- Execution state queries can be performed from any thread.

## Notes

<!--
Important implementation/contextual information that cannot be inferred
from the code or best development practice and does not belong to Design or Rules.
-->


## Discussions

<!-- Unresolved design questions.
Record alternatives, trade-offs, and decisions that are not finalized yet.
-->


