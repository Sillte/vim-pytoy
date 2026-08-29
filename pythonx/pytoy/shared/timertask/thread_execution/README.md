# Design Policy

## Purpose

Execute user-provided functions in separate threads while keeping
thread execution and result delivery separate.

## Terminology

- `CancelToken`: The mechanism for cooperative cancellation.
- `Exit`: A completion message transferred from the worker thread to
  the main thread.

## Design

- Cancellation is cooperative. A cancellation request does not forcibly
  terminate the executing function.
- Completion is transferred from the worker thread to the main thread
  before it is observed by the execution layer.
- A completed execution produces either a result or an exception.
  These are delivered to the caller through separate callbacks.
- The execution layer does not block the caller waiting for completion.

## Rules

- Execution state must be observed and modified from the main thread,
  except for cancellation requests.
- A cancellation request may be issued from any thread.
- A running function must cooperate with cancellation for cancellation
  to take effect.

## Notes

## Discussions
