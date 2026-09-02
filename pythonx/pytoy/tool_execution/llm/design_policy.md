# Design Policy

## Purpose

Manage asynchronous LLM operations through a handler-based execution model.

## Terminology

- `Execution`: A managed instance of an LLM operation.
- `Exit`: The terminal lifecycle event of an execution.
- `Result`: The value produced by a successful execution.
- `Outcome`: The distinction between successful completion and exceptional
  termination.
- `Runner`: A lower-level component responsible for performing the operation.

## Design

- An execution communicates completion through an `Exit` event carrying an
  `Outcome`.
- Successful completion carries an execution-specific `Result`; exceptional
  termination carries an exception.
- External callers interact with executions through handlers.
- The execution layer delegates actual asynchronous execution to the lower-level
  runner.

## Rules

- The execution layer must preserve the distinction between successful
  completion and exceptional termination.
- An exception that prevents normal completion must not be represented as a
  successful `Result`.
- Lifecycle events must identify the execution that produced them.
- Public execution entry points are currently restricted to the main thread.

## Discussions

- The precise lifecycle and thread-affinity contract between the execution
  layer and the lower-level runner should remain defined by the runner until
  a package-wide contract is established.

- The appropriate scope of retained execution context may evolve as
  subsequent LLM interactions are introduced.
