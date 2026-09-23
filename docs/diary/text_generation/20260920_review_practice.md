# Document Review Experiment

## Status

The previous Document Review implementation is being retired.
Its implementation-specific state models and execution flow are not
preserved as a dedicated document-review subsystem.

The experiment is retained as a source of prompt and workflow practices
for future LLM-based review capabilities.

## Core Insight

Document review should not be treated as an absolute judgment of
whether a document is "good".

A useful review first establishes the context in which the document
should be evaluated:

- intended reader
- document goal
- required qualities
- definition of completion

The review can then evaluate the document against those criteria.

## Review Context

The experiment explored inferring:

- document purpose
- document style
- required editing role
- intended reader
- document goal
- required qualities
- completion definition

The useful insight is that making this context explicit can improve the
consistency and relevance of LLM-generated reviews.

## Review Strategy

The experiment distinguished between:

- structural / strategic editing
- polishing / refinement

The useful insight is that the appropriate review strategy depends on
the current state of the document.

A document with structural or goal-alignment problems may require
diagnosis and redesign, while a document that already satisfies its
fundamental purpose may benefit more from focused refinement.

## Review and Revision

The experiment combined diagnosis, review, rewriting, and progress
assessment in a single LLM interaction.

This revealed that these are conceptually distinct operations:

- Review: identify strengths, weaknesses, and remaining gaps.
- Revision: modify the document according to an intended improvement.
- Re-review: evaluate the revised document.

They may be composed into a workflow, but they do not need to be
implemented as one operation.

## Baseline and Progress

The experiment explored keeping an explicit baseline before revision
and comparing the result after revision.

This is useful when building iterative review workflows.

## Editing Constraints

The experiment identified several useful constraints for LLM-based
polishing:

- preserve the original meaning when polishing
- maintain the document's language
- consider structural and logical consistency
- distinguish improvement from arbitrary rewriting
- explicitly report remaining gaps when they cannot be resolved

These are practices rather than requirements of the Review domain.

## What Is Preserved

The experiment provides reusable knowledge for future LLM capabilities:

1. Evaluate documents relative to purpose and audience.
2. Make the desired outcome explicit before reviewing.
3. Adapt review strategy to the document's current state.
4. Separate evaluation from modification when useful.
5. Preserve a meaningful baseline when comparing revisions.
6. Treat review criteria as contextual guidance rather than permanent
   document state.