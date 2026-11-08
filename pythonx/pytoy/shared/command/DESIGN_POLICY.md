# Design Policy

## Purpose

`shared/command` defines command models, parses command input, resolves values, executes commands, and provides editor command adapters and completion.

## Package boundaries

- `core/` owns command definition metadata, argument and option models, tokenization for execution, and conversion of parsed values. It is independent of editor backends and service orchestration.
- `service/` owns backend-independent execution and completion workflows. It may depend on `core/`, but must not depend on editor APIs or concrete command adapters.
- `app/` owns the user-facing command and group facades, the implementation-facing protocols, and backend adapters. Backend adapters may depend on `service/` and `core/`.
- `service/completion_lexer.py` owns tolerant tokenization details needed only for completion. Do not weaken or change execution tokenization to accommodate incomplete editor input.

```text
Consumers -> app facade -> backend adapters -> service -> core
                            implements app protocols
```

## Public API and contracts

- `shared.command.__init__` is the user-facing entry point for command and group registration, decorators, and injected range/count values. Preserve its intentional exports.
- `shared.command.service.__init__` exposes the completion and execution service API, including the completion parameter and result types. Preserve those exports.
- `app/protocol.py` defines the contract implemented by command backends. Keep backend implementation details behind that contract and the app facade.
- Core models, tokenizers, completion lexer tokens, and backend implementation classes are implementation details unless deliberately exported through the owning package's `__init__.py`.
- Do not make `CompletionToken` or its union with `Token` part of the package's public API.

## Dependency and behavior rules

- Keep core independent of service and app layers. Keep services independent of concrete editor backends.
- Perform backend-specific coordinate conversion at the adapter boundary. Completion internals use Python `str` insertion indices and half-open replacement ranges.
- Keep execution parsing and completion parsing distinct where their input guarantees differ. Completion may tolerate unfinished quotes or escapes; execution must retain its established parsing behavior.
- Keep positional argument ordering consistent between completion and execution by using the ordering defined by `CommandModel`.
- Keep repeated-value option semantics aligned between completion and execution. The model determines whether an option accepts multiple values; avoid duplicating type-origin checks in consumers.
- Normalize candidate values to strings for completion without changing the types used for execution.
- Add abstractions such as a completion parse-state model only when they clarify a real responsibility or remove meaningful duplication. Do not introduce layers solely to match a generic architecture pattern.

## Change guidance

Before changing command behavior, identify its consumers and whether it belongs to command metadata, execution, completion, or a backend adapter. Preserve the package's public exports and validate behavior with focused execution and completion tests.
