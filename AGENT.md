# AGENTS.md

This repository is a personal project for exploring Python-based
editor plugin development and software architecture.

Follow the applicable `design_policy.md` files when modifying the
codebase.

## Documentation

- `README.md`: project overview and user-facing documentation.
- `design_policy.md`: design principles and architectural decisions.
- `documentation_policy.md`: rules for what and how to document.
- `AGENTS.md`: instructions for AI agents working in this repository.

A `design_policy.md` applies to its directory and descendants.
More specific policies refine broader policies.

## Architecture

- Preserve dependency direction and responsibility boundaries.
- Prefer simple designs over unnecessary abstractions.
- Keep implementation details behind public APIs.
- Avoid unnecessary global state and import-time side effects.

## Testing

- Test public behavior, not implementation details.
- Prefer simple, behavior-oriented tests.
- Avoid unnecessary mocks.
- Use `threading.Event` for asynchronous execution instead of `sleep`.
- Inspect the near tests before implementing tests.
- Do not add tests merely to increase coverage.
