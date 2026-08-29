# Design Policy

## Purpose

`CommandRunner` provides a backend-independent interface for executing
external commands and receiving their output.

## Rules

- An `OutputJob` must not start execution until its consumer has subscribed to its events.
- `alive` must be `False` before `on_job_exit` is emitted.
- `on_job_exit` must be emitted from the main thread.