# Specification

This document defines the observable command definition, execution, and completion behavior provided by `shared/command`.

## Command definitions

- `Argument` defines a positional command-line value; `Option` defines a named option.
- Options must have a default value or default factory. Arguments without a default are required; arguments with a default are optional.
- Positional values are assigned to required arguments first, then to defaulted arguments, preserving declaration order within each group. Omitted defaulted arguments use their defaults.
- Values are converted according to the parameter's annotated types when possible. Invalid values and unknown options cause execution to fail.
- Boolean options may be specified as `--name` and negated as `--no-name`.
- Named options accept `--name=value` and `--name value` forms.
- `list[...]` and `Sequence[...]` options accept repeated occurrences; their values are accumulated in occurrence order.

## Completion

`CompletionService` receives a `CompletionParam` containing the command-line fragment, cursor position, and offset.

- `cursor_pos` is a zero-based Python `str` insertion index relative to `cmd_line`, in the range `[0, len(cmd_line)]`.
- Candidate `start` and `end` are zero-based Python `str` indices into the caller's original command line. They identify a half-open replacement range `[start, end)`; `end` is exclusive.
- `offset` shifts candidate ranges from the `cmd_line` fragment back to the caller's command-line coordinates. For example, if `Demo --opti` is reduced to ` --opti` with `offset=4`, a local range `[1, 7)` is returned as `[5, 11)`.
- Candidate `value` is always a string. Literal values and values returned by a completer are converted to strings for completion; this does not change execution-time value conversion.
- A list- or sequence-valued option remains available for completion after it has been used, so another occurrence can be entered. A scalar option is omitted from option-name candidates after use.
- An incomplete final single- or double-quoted token can still be completed. The opening quote is retained in the inserted candidate. A trailing escape must not make completion fail.
- `CompletionCandidate.kind` is optional classification metadata. It currently does not affect filtering, insertion, or other completion behavior.

## Exceptions and errors

- Execution parsing uses the command tokenizer and reports malformed input or value-conversion failures to the caller.
- Completion is best-effort for an unfinished final quote or escape; this tolerance does not change execution parsing.
