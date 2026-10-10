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
- Completion is transferred from the worker thread to the TimerTask dispatch
  thread before it is observed by the execution layer.
- A completed execution produces either a result or an exception.
  These are delivered to the caller through separate callbacks.
- The execution layer does not block the caller waiting for completion.

## Rules

- Execution creation and discarding an unstarted execution are restricted to
  the main thread or the TimerTask dispatch thread.
- Starting an execution is serialized by the manager lock and may be requested
  from any thread.
- A cancellation request may be issued from any thread.
- A running function must cooperate with cancellation for cancellation
  to take effect.
- An execution that has not started may be discarded; started executions are
  cancelled cooperatively and must not be discarded.
- Callers must not subscribe to an execution's `on_exit` event or dispose its
  subscriptions concurrently with discarding that unstarted execution.
- If starting an execution fails before its worker thread starts, its status
  remains `created` and the manager keeps it registered for retry. The failure
  propagates synchronously and does not emit `ThreadExecutionExit` because no
  worker started.

## Notes

## Discussions
