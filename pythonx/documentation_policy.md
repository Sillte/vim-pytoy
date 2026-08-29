# Documentation Policy

## Principle

Document only information that cannot be reliably inferred from the code.

The code is the single source of truth for implementation details, APIs,
types, and behavior that can be expressed directly in code.

Documentation should preserve design knowledge, constraints, and context
that would otherwise be lost.

Documentation should be maintained according to a minimalism policy, that is,
items which can be inferred from general best practice, code, tests, 
or other single source of truth must not be created or maintained. 


## Separation of Responsibilities

- **Code**
  - Implementation details
  - Types and interfaces
  - Public API
  - Behavior that can be expressed and verified by code

- **DocString**
  - Information needed by users of a class, function, or module
  - Usage and behavioral descriptions of individual APIs

- **Design Policy**
  - Design decisions that cannot be inferred from code
  - Boundaries and responsibilities between components
  - Package-specific constraints
  - Context or rationale that would otherwise be lost

- **Discussions**
  - Unresolved design questions
  - Alternatives and trade-offs under consideration
  - Decisions that have not yet been finalized

## Avoid Overdocumentation

Do not document information merely because it is useful or obvious.

In particular, do not duplicate:

- Class or function responsibilities already clear from the code
- Public API definitions already represented by `__init__.py` or `__all__`
- General programming best practices
- Implementation details that can be understood by reading the code

When information can be expressed clearly and reliably in code,
prefer the code over documentation.

## Design Policy Template

```markdown
# Design Policy

## Purpose

## Terminology

## Design

## Rules

## Notes

## Discussions
```

Sections may be omitted when they contain no package-specific information.

An empty section does not need to be filled merely to complete the template.

## Evolution

Start with the minimum documentation necessary.

Add new documentation rules or sections only when actual development
experience shows that the existing structure is insufficient.

Prefer evolving the documentation policy from concrete problems
rather than anticipating every possible need. 

## AI Authoring Policy

When generating or updating documentation, prefer omission over inference.
Do not summarize, explain, or restate the code.

Assume that implementation details, APIs, types, tests, and observable
behavior are already available to the reader.

Assume that the reader can inspect the code, tests, type hints,
imports, `__init__.py`, `__all__`, and other existing documentation.

Assume that the reader has perfect knowledge of the external packages
and programming languages involved. Information that can be obtained
from external packages or programming languages is unnecessary.

For every proposed item, ask:

> "If someone understood the code perfectly, would this information
> still be missing?"

If the answer is no, omit or remove it.
If the answer is uncertain when deciding whether to delete it,
move it to Discussions.

Document only information that cannot be recovered from those sources,
such as intentional design constraints, non-obvious rationale,
project-specific terminology, or historical/contextual knowledge.

If the purpose or rationale cannot be established with sufficient
confidence, do not promote it to Design or Rules. Put it in
Discussions or omit it.

A document that is too short is preferable to a document that merely
duplicates the code.

Lack of items is preferable to excessive items of mediocre value.

When updating existing documentation, remove existing items that no longer
satisfy this policy.
For example, if an existing item can be reliably inferred from the code, tests, types,
public API, or another single source of truth, remove it.

Do not preserve an item merely because it already exists.

The goal is to maintain the minimum set of information that cannot be
reliably recovered from those sources.
