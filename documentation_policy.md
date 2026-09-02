# Documentation Policy

## Principle

Document information that cannot be reliably recovered from the code,
tests, or other single sources of truth.

Documentation should preserve design knowledge, constraints, rationale,
terminology, and context that would otherwise be lost.

Prefer minimal documentation. Do not duplicate information that can be
reliably inferred from the code, tests, types, public APIs, or general
knowledge.

## Separation of Responsibilities

- **Code**
  - Implementation
  - Types and interfaces
  - Public APIs
  - Observable behavior

- **DocString**
  - Information needed by users of an individual API
  - API-specific usage and behavioral descriptions

- **Design Policy**
  - Design decisions and constraints
  - Boundaries and responsibilities
  - Project- or package-specific rationale and terminology

- **Discussions**
  - Unresolved questions
  - Alternatives and trade-offs
  - Decisions that have not been finalized

## Avoid Duplication

Do not document:

- Implementation details already clear from the code
- API definitions already represented by the code
- General programming or framework knowledge
- Behavior that can be reliably verified from tests

When information can be expressed clearly and reliably in code,
prefer the code over documentation.

## Design Policy Documents

A `design_policy.md` describes design principles and decisions within
its scope.

A policy should contain only information that cannot be reliably
recovered from the code or other sources of truth.

Use sections only when they contain meaningful information.

Typical sections include:

- Purpose
- Terminology
- Design
- Rules
- Notes
- Discussions

The template is a guideline, not a requirement.

## Evolution

Start with the minimum documentation necessary.

Add documentation when concrete development experience reveals
information that would otherwise be lost.

Remove documentation when its information becomes reliably
recoverable from another source of truth.
