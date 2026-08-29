# Design Policy

## Purpose

Provide a common execution model for tool-level operations while keeping
the lifecycle and responsibilities of individual execution types explicit.

## Terminology

- `Tool`: A calculator handled in this package. A tool may be regarded as a function or may be regarded as a session or a sequence of interactions.
- `Execution`: A managed instance of a tool operation.
- `Exit`: The terminal lifecycle event of an execution.
- `Result`: The domain-specific value produced by a successful execution.
- `Outcome`: The distinction between successful completion and exceptional
  termination.
- `Runner`: A lower-level component responsible for performing the actual
  operation.

## Design

- An execution communicates completion through an `Exit` event.
- An `Exit` represents the completion of one execution instance and carries
  an `Outcome`.
- A successful `Outcome` carries the execution-specific `Result`.
- An error `Outcome` carries the exception that prevented normal completion.
- `Result` types are execution-specific and should not be unified merely
  because different executions share the same lifecycle model.
- External callers interact with executions through handlers rather than
  through internal execution objects.
- Lower-level runners are responsible for translating execution-level
  failures into the execution's `Outcome`.

## Rules

- The execution layer must not invent a successful result when the lower-level
  runner cannot establish successful completion.
- Execution-specific conditions derived from a successful `Result` belong to
  the corresponding execution's hooks or event handling rather than to the
  common `Outcome` abstraction.
- Exceptions that prevent normal execution completion are represented as
  errors rather than as ordinary execution results.
- The execution layer should preserve the distinction between successful
  completion and exceptional termination.
- Lifecycle events must provide enough information to identify the execution
  that produced them.

## Notes

- `Outcome` is the common semantic boundary between successful execution and
  exceptional termination.
- `Result` describes what a particular execution produced; it is not itself
  the lifecycle event.
- An execution may expose additional events during its lifetime. These events
  are distinct from the final `Exit` event.
- Terminal executions may derive conditions such as zero and non-zero exit
  codes from their successful result. Failure to obtain a meaningful exit
  result is not treated as an ordinary non-zero result.

## Discussions

- The precise contract between each execution and its runner, including how
  failures before or during `run` are represented, should be defined by the
  corresponding runner.
- The relationship between execution-specific `Result` types and lower-level
  result types should remain explicit until there is evidence that a shared
  abstraction is necessary.
- The event model may evolve as execution types expose more lifecycle events.

- Execution managers currently rely on main-thread access for their internal
  state. Whether manager state should become thread-safe independently from
  main-thread hook dispatch remains under consideration.
- Main-thread restrictions currently cover both execution management and
  hook invocation, but these represent different concerns and may need to be
  separated.