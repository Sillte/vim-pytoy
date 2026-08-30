# Design Policy

## Design

### Job Lifecycle

A terminal job represents a single execution.

Its lifecycle consists of three phases:

- construction
- execution
- disposal

A disposed job is not restarted.

### Input

Terminal input is represented as operations rather than being limited to
direct string writes.

A driver converts input strings into `InputOperation` sequences, and the
terminal job executes those operations.

Operations may depend on the current terminal snapshot.

### Backend Independence

The job model is independent of the terminal mechanism used by a backend.

### Event Thread Boundary

Public events requested by `TerminalJobRequest` are executed on the main
thread.

## Rules

- Construction does not start execution.
- `start()` begins execution and may be called only once.
- `send()` and `interrupt()` require execution to have started.
- Calling `send()` or `interrupt()` before `start()` is an error.
- `terminate()` may be called before `start()`, but subsequent behavior is
  unspecified.
- `events` may be subscribed to after construction and before `start()`.
- Disposal ends the job lifecycle.
- A disposed job cannot be restarted.

## Discussions

### Runner Execution Boundary

`TerminalJobRunner.run()` currently combines job construction and execution.

Separating these operations would make the lifecycle more explicit, but the
current calling pattern can work around this limitation. The practical need
for changing `run()` is currently low.

### Pre-start `terminate()`

`terminate()` currently accepts a call before `start()`, but subsequent
behavior is unspecified.

Requiring `start()` before `terminate()` may provide a clearer lifecycle
contract. One possible approach is to make `start()` fail if the job has
already been terminated.