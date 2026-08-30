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

Operations may depend on the current terminal snapshot.

### Backend Independence

The job model is independent of the terminal mechanism used by a backend.

## Rules

- Construction does not start execution.
- Execution is started explicitly.
- Disposal ends the job lifecycle.

## Discussions
