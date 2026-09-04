# Design Policy

## Purpose

`shared/ui` is the boundary between the application and editor-specific UI
backends such as Vim, Neovim, VSCode, and Dummy.

## Boundaries

The UI package has two intentional external boundaries:

- the ordinary user-facing API;
- the `contract/` API for backend and extension authors.

`contract/` is explicit because the concepts required to implement a backend
are not necessarily part of the ordinary user-facing API. It may contain
protocols and the shared data needed to implement them. It is not merely an
alternative name for an internal module named `protocol.py`.

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

- Ordinary users depend on the public facade, not on backend implementation
  modules.
- Backend and extension authors depend on the explicitly designated `contract/`
  boundary.
- Backend-specific kernels, registries, editor adapters, and conversion
  helpers are not part of the contract.
- Do not move UI integration concepts into a generic domain package solely to
  fit Clean Architecture terminology.

Facades return facade objects to ordinary callers. Backend implementations
return contract objects to their facades; wrapping occurs at the public
boundary.

The `contexts` packages are intentionally outside the current import cleanup.
They construct backend kernel registries and therefore have a separate
initialization responsibility. Their dependency boundary must be decided
before changing their imports.
