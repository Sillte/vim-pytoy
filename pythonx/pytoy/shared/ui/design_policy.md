# Design Policy

## Purpose

`shared/ui` is the boundary between the application and editor-specific UI
backends such as Vim, Neovim, VSCode, and Dummy.

## Package Boundaries

The UI package has separate boundaries for separate audiences:

- `__init__.py`: API for ordinary users of the UI package.
- `contract/`: API that backend and extension authors must understand.
- `pytoy_buffer/`, `pytoy_window/`, and other feature packages: user-facing
  facades and feature-specific implementation boundaries.
- `impls/`: backend-specific implementation details within a feature package.

`contract/` is an explicit extension boundary. It may contain protocols and
shared data types required to implement or extend a UI backend. It is not merely
an alternative name for an internal module named `protocol.py`.

## Dependency Direction

Facades and backend implementations depend on the contract. The contract must
not depend on a concrete facade or backend implementation.

```text
facade          -> contract
backend         -> contract
contract       -X-> facade
contract       -X-> backend
```

Buffer and Window are peer UI concepts. A Window displays a Buffer, and a
Buffer may be displayed by one or more Windows. Their contracts may refer to
one another, but ownership and lifecycle management belong to the respective
providers rather than to the peer objects themselves.

## Rules

- Ordinary users should import from the UI package or feature package public
  APIs, not from backend implementation modules.
- Backend and extension authors may depend on the explicitly designated
  `contract/` boundary.
- Backend-specific kernels, registries, editor adapters, and conversion
  helpers remain outside the contract.
- Do not move UI integration concepts into a generic domain package solely to
  fit Clean Architecture terminology.
- Keep the distinction between ordinary public API and extension contract
  explicit when changing package structure.
