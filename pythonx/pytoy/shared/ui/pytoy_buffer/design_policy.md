# Design Policy

## Purpose

`pytoy_buffer` provides the buffer facade and the backend-independent buffer
behavior used by the rest of the application.

## Terminology

`BufferID`, `BufferSource`, and `URI` represent distinct concepts.

- `BufferID`: identifies a buffer instance.
- `BufferSource`: identifies the source associated with a buffer.
- `URI`: identifies the resource represented by a buffer.

These concepts must not be unified merely because a backend may represent
them using similar values.

## Design

The buffer facade delegates editor-specific behavior to a selected backend
implementation. Buffer users should not need to know whether the active
backend is Vim, Neovim, VSCode, or Dummy.

The buffer contract includes content access and mutation, range operations,
lifecycle state, events, and the relationship between a buffer and the
windows that display it. The contract is shared with the UI package because
Buffer and Window are peer UI concepts.

The Dummy backend is also the backend used by public facade tests when the
application is running outside an editor. Those tests should exercise the
normal product backend-selection path rather than manually selecting the
Dummy implementation.

## Rules

- Preserve the distinction between `BufferID`, `BufferSource`, and `URI`.
- Keep backend-specific behavior behind the buffer facade.
- Keep buffer mutation and range operations consistent with the observable
  `content` and `lines` state.
- Treat the backend-independent buffer behavior as a contract shared by all
  supported backends.
