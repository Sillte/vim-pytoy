# Design Policy

## Purpose

`shared/lib/events` defines editor-independent event concepts exposed to UI
and application code. It assembles events from concrete mechanisms, but does
not own those mechanisms.

## Boundaries

- `domain/` owns the semantic contracts for events consumed by the rest of
  the application: buffer lifecycle events, window lifecycle events, and key
  actions.
- `buffer_events.py` and `window_events.py` adapt Vim autocmds into those
  semantic events. They may depend on `autocmd/` and context objects.
- `action_events.py` adapts keymaps into semantic action events. It may depend
  on `keymap/`.
- `autocmd/` owns Vim autocmd registration, dispatch, payload extraction, and
  Vim-specific event specifications.
- `keymap/` owns key sequence registration, Vim mapping commands, and the
  implementation details needed to emit key action events.

```text
events/domain  <- events providers <- autocmd / keymap
```

The domain contracts must not depend on Vim, autocmd managers, keymap managers,
contexts, or UI implementations.

## Rules

- Add a new event to `events/domain` when it describes a stable semantic event
  that consumers can use without knowing how the event is produced.
- Keep source-specific details in the source package. A new Vim autocmd belongs
  in `autocmd/`; a new key mapping belongs in `keymap/`.
- Event payloads in `domain` must represent the semantic identity exposed to
  consumers, such as a buffer number or window ID, rather than raw Vim
  callback arguments.
- Providers may implement domain protocols structurally; inheritance is not
  required merely to satisfy the contract.
- `events/__init__.py` and `events/domain/__init__.py` are the intentional
  public exports. Do not expose implementation modules as a convenience.

## Adding Events

When adding an event, first decide its semantic owner, payload, and provider.
Add the domain contract before adding a concrete source adapter. This keeps
future event additions consistent and prevents `events/` from becoming a
collection of unrelated Vim callbacks.
