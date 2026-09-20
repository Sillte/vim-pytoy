# Design Policy

## Purpose

`scoped_edit` provides an LLM-assisted operation for reconstructing a selected
part of a document while preserving the surrounding document.


## Design

`ScopedEditAction` owns the document-side operation.

It is responsible for:

- identifying the edit scope,
- establishing and maintaining the reconstruction boundary,
- invoking LLM execution,
- applying the returned reconstruction to the original buffer,
- recovering from execution failures.

`ScopedReconstructionContract` defines the operational contract used by the
action to establish and enforce the reconstruction boundary.

The LLM does not receive the operational reconstruction contract directly.

`ScopedEditLLMContract` is the intentionally narrower representation of the
contract exposed to TaskSpec construction. It contains only the rules that
must be communicated to the LLM.

Task makers consume `ScopedEditLLMContract` rather than
`ScopedReconstructionContract`.

## Responsibility Boundaries

The action layer owns document mutation and reconstruction safety.

The `task_specs` layer owns LLM task construction, including language,
style, completion, and other editing rules.


Information is passed across the boundary through the smallest representation
required by the receiving layer.

The package public API is exposed from `scoped_edit.__init__`. Consumers use
`ScopedEditAction`, `DefaultScopedEditTaskMaker`, and the scoped-edit contract
types through that package API rather than importing implementation modules.

When execution fails, the action removes only the reconstruction markers.
The selected document content is preserved for user inspection or retry.

LLM output that contains an incomplete, reversed, or nested marker pair is
rejected before it can replace the scoped document content.

## Design Decisions

### Keep the operational contract separate from the LLM contract

`ScopedReconstructionContract` contains both operational behavior and
information that must be communicated to the LLM.

These concerns are intentionally separated by exposing
`ScopedEditLLMContract` to the task-making layer.
