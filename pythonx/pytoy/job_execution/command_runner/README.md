# Design Policy

## Purpose

`CommandRunner` provides a backend-independent interface for executing
external commands and receiving their output.

## Rules

- An OutputJob must not emit execution events before its consumer can
  subscribe to them.
- `alive` must be `False` before `on_job_exit` is emitted.
- `on_job_exit` must be emitted from the main thread.

## Discussions