
---
name: documentation
description: >
  Decide what information belongs in docstrings, SPECIFICATION.md,
  DESIGN_POLICY.md, or other documentation. Use when creating, reviewing,
  updating, or removing documentation or docstrings.
user-invocable: true
---

# Documentation

Use this skill when creating, reviewing, updating, or removing
documentation or docstrings.

## Principles

- Document knowledge that would otherwise be lost.
- Do not duplicate information reliably available from code,
  types, APIs, tests, or other authoritative sources.
- Prefer the smallest useful document.
- Remove information that is obsolete, duplicated, or reliably
  recoverable elsewhere.
- Assume readers understand the programming language and external
  packages. Explain them only when necessary to clarify
  project-specific behavior, constraints, or design decisions.

## Documentation Ownership

- **Docstring**: information needed by users of an individual API,
  including API-specific usage and behavior.
- **SPECIFICATION.md**: public contracts and observable behavior
  that package users may rely on.
- **DESIGN_POLICY.md**: design principles and decisions for package
  developers, including purpose, terminology, responsibilities,
  boundaries, constraints, and rationale.
- **Other documentation**: information appropriate to the document's
  purpose and intended readers.

## Procedure

1. Identify the information to document and its intended readers.
2. Determine the appropriate documentation owner.
3. Check authoritative sources and existing documentation.
4. Add only information that would otherwise be lost.
5. Remove obsolete, duplicated, or unnecessary information.

## Completion Check

Before finishing, confirm that:

- Every statement has an intentional documentation owner.
- No information is unnecessarily duplicated.
- The document is concise and contains no empty sections.

## When Working with DESIGN_POLICY.md

Before modifying a DESIGN_POLICY.md, read all applicable policies.

A DESIGN_POLICY.md applies to its directory and descendants.
A more specific policy refines a broader policy.

Include only information that cannot be reliably recovered
from code or other sources of truth.

Use only sections that contain meaningful information.

Common sections include:

- Purpose
- Terminology
- Design
- Rules
- Notes
- Discussions

### Completion Check

When finishing a DESIGN_POLICY.md change, confirm that:

- The scope and applicable policies are clear.
- Final decisions are separated from unresolved discussions.


## When Working with SPECIFICATION.md

Before modifying a SPECIFICATION.md, read all other applicable
SPECIFICATION.md files.

A SPECIFICATION.md applies to its directory and descendants.
A more specific specification refines a broader specification.

Include only public contracts that package users may rely on.

### Completion Check

When finishing a SPECIFICATION.md change, confirm that:

- The specification is concise and contains no unnecessary explanations.
- Unresolved discussions are not presented as established contracts.
- Unresolved issues are documented separately only when relevant to users.