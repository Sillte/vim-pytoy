# Design Policy

## Purpose

`pytoy_quickfix` provides a backend-independent Quickfix domain object and
adapters that connect it to editor UIs. The domain state must remain usable
without Vim, Nvim, VS Code, or a specific editor buffer implementation.

## Terminology

### Entity identity and kind

`QuickfixEntity` is a stateful domain entity. Its `id` is its identity and is
generated independently for each entity. Its `kind` describes the purpose or
category of the Quickfix and is not an identity or uniqueness constraint.

Entities with the same `kind` may coexist. `QuickfixEntityQuery` is used when
the manager needs to search by kind.

### Facade and entity

`QuickfixEntity` owns the records, normalized selection state, working
directory, and lifecycle events. `Quickfix` is the public facade over one
entity and is the normal entry point for application code.

### Viewer

A Viewer connects one entity to an external UI. The current concrete viewers
are `PytoyQuickfixViewer` for the pytoy buffer/window UI and
`BackendQuickfixViewer` for the selected backend UI. They are obtained through
`Quickfix.provide_ui("pytoy")` or `Quickfix.provide_ui("backend")`.

The viewer is a projection and adapter, not the source of truth. It may be
created on demand and must not become the owner of Quickfix records or
selection state.

## Public API

The public Quickfix package exposes:

- `Quickfix`;
- `PytoyQuickfixViewer` and `BackendQuickfixViewer`;
- `QuickfixRecord` and `QuickfixState`;
- `QuickfixRecordsCreator`, its Protocol, and related creator types.

`QuickfixEntity`, `QuickfixEntityManager`, backend-specific implementations,
and internal viewer helpers are implementation details unless explicitly
exported by the package.

`PytoyQuickfix` remains as an alias.

## Responsibilities

### QuickfixEntity

- owns records and the current zero-based selection;
- exposes `select`, `next`, and `prev` for domain navigation;
- validates lifecycle access after disposal;
- emits its end event exactly once.

### Quickfix

- creates or reuses entities through `QuickfixEntityManager`;
- exposes domain operations without leaking entity implementation details;
- selects the current entity through `Quickfix.current()`;
- provides UI adapters through `provide_ui()`.

### QuickfixRecordsCreator

- converts command output text and a working directory into Quickfix records;
- accepts a regex or a callable implementation;
- normalizes a single `QuickfixRecord` result into a sequence;
- does not own an entity or interact with an editor backend.

### QuickfixEntityManager

- creates and registers entities;
- stores entities by `QuickfixEntity.id`;
- queries entities by `QuickfixEntityQuery`, including `kind`;
- tracks the current entity;
- removes entities and responds to entity end events.

The manager does not own records, selection logic, editor windows, buffers, or
positions. There is no manager-level replacement operation: a new entity has
a new identity, and an existing entity is updated through its domain facade.

### Viewers

All Viewer implementations follow `QuickfixViewerProtocol`:

- `show()` and `close()` manage the UI lifecycle;
- `sync_to_ui()` applies entity state to the external UI;
- `sync_from_ui()` imports externally changed records or selection state;
- `jump(with_focus=...)` opens the selected record in the editor.

`sync_to_ui` and `sync_from_ui` have opposite directions. Backend-specific
indexing and editor commands belong inside the corresponding Viewer
implementation. `with_focus` controls whether `jump()` focuses the opened
editor window; it does not change entity selection.

## Invariants

- Entity identity is `id`; `kind` is descriptive and may be shared.
- Quickfix navigation is backend-independent and uses zero-based normalized
  state.
- A UI may change independently of the library, so backend viewers must
  support explicit synchronization in both directions.
- A viewer is not a second state store for records or selection.
- Clearing entity state and closing a UI are separate operations.
- Entity disposal is idempotent and removes it from its manager.
- Manager lifecycle is injectable for tests; module-level mutable caches are
  not a lifecycle mechanism.
- Owner subscriptions are retained and disposed with the entity.
- UI-specific effects remain behind Viewer implementations and are not added
  to the domain entity.

## Extension guidance

When adding a backend or UI:

1. Implement `QuickfixViewerProtocol`.
2. Keep backend records and index conversions inside that implementation.
3. Register backend selection in the Viewer factory.
4. Do not add backend dependencies to `QuickfixEntity` or its domain methods.
5. Add focused tests for synchronization, empty state, selection, and disposal.
