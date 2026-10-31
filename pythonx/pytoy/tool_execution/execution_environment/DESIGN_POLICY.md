# Design Policy

## Purpose

Provide a public, implementation-independent interface for discovering and
selecting Python execution environments.

## Design

- `EnvironmentManager` is the public entry point for environment-related
  operations. Public operations must be exported from this package's
  `__init__.py`.
- Concrete environment solvers, including `UVEnvironmentSolver`, are
  implementation details. Callers outside this package should not depend on
  them directly.
- If another use case needs to discover a virtual environment, expose the
  required behavior through `EnvironmentManager` rather than making a solver
  public or adding another direct dependency on a concrete solver.
- The public operation should express environment discovery without requiring
  callers to depend on a particular environment implementation.

## Current Exception

`devtools` currently uses `UVEnvironmentSolver` directly to pass a detected
virtual environment to a restarted editor. Keep that integration as-is for
now. Do not treat it as a precedent for additional callers; when another use
case needs virtual environment discovery, move the public-facing operation to
`EnvironmentManager`.
