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
- Public execution entry points may run on the main thread or TimerTask dispatch thread.
- Manager state and retained execution contexts are protected by an `RLock`.
- Standard LLM execution lifecycle events are logged through the global LLM
  logger by default.
- Feature-specific diagnostics may use a feature logger, but must not replace
  the standard lifecycle log.
- Lifecycle records include the execution kind and, when available, the
  execution id and exception.

## Discussions

- The precise lifecycle and thread-affinity contract between the execution
  layer and the lower-level runner should remain defined by the runner until
  a package-wide contract is established.

- The appropriate scope of retained execution context may evolve as
  subsequent LLM interactions are introduced.
- Cancellation is delegated to `pytoy_llm`. Canceling a `created` execution
  discards it without an exit; canceling a `running` execution requests
  cooperative cancellation and leaves it managed until its exit is delivered.
- A running cancellation exits with `TaskCanceledException`. It produces the
  normal `LLMExecutionExit` and invokes `on_exit`, but not `on_exception`.
- If startup fails before the task execution leaves `created`, the execution
  layer removes the attempt's subscriptions and propagates the exception
  without canceling the task. The registered execution remains `created` and
  may be started again.
