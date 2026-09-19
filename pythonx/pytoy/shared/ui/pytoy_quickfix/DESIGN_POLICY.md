# Design Policy

## Goal

`pytoy_quickfix` provides a backend-independent Quickfix object and editor
views for presenting it.

## Public Concepts

- `Quickfix` is the public facade for a QuickfixEntity.
- `QuickfixEntity` owns records, normalized selection state, and lifecycle.
- `QuickfixViewer` projects a Quickfix onto an editor Window, Buffer, and
  Position. A dedicated quickfix Buffer is an implementation detail of a
  viewer.
- `QuickfixManager` owns the identity and lifecycle of multiple Quickfix
  objects.
- `QuickfixRecord` and `QuickfixState` are shared data concepts.

The public API uses facade objects. It must not expose backend implementations,
service objects, resolver objects, or implementation escape hatches.

## Responsibilities

`Quickfix` supports:

- replacing and clearing records;
- inspecting records, state, and the current record;
- selecting and navigating records.

`QuickfixViewer` supports:

- presenting Quickfix state in the editor;
- creating and updating a dedicated Pytoy Buffer;
- resolving the current record to editor location and focus behavior.

`QuickfixManager` supports:

- creating, registering, finding, explicitly updating, and removing
  QuickfixEntity objects;
- resolving the default/current Quickfix;
- defining the lifecycle of viewers when a Quickfix is removed.

The manager does not own records, selection state, editor windows, buffers, or
positions. A removed Quickfix must not leave dangling viewers.

## Invariants

- Quickfix navigation is backend-independent and uses zero-based normalized
  state.
- Editor-specific indexing and effects are confined to adapters or viewers.
- A viewer is a projection of a Quickfix, not its source of truth.
- State clearing and closing an editor view are separate operations.
- Manager lifecycle is explicit and injectable for tests; module-level mutable
  caches are not the lifecycle mechanism.
- `create` rejects duplicate names. `update` is the explicit replacement
  operation, and `remove` also disposes the removed entity.
- Quickfix creation may later accept an owner buffer or lifecycle event source.
  Any subscription must be owned and detached according to the owner lifecycle.

## Refactoring Order

1. Fix the minimal `Quickfix` facade and behavior tests.
2. Define `QuickfixManager` identity and lifecycle.
3. Define `QuickfixViewer` and its owner/event subscription behavior.
4. Move editor effects behind the viewer and backend boundaries.

The handler pattern may later wrap these facades for integrations that need a
manager-backed handle, but it is not the primary Quickfix API.
