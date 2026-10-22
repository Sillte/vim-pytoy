CONVENTION = """
# IdeaSpace Convention

## Purpose

This IdeaSpace is used to create, preserve, evaluate, and connect valuable artifacts.
Artifacts are expected to create value in the IdeaSpace.


## Master

`master/` stores the intentions, goals, preferences, and directives
of the human who directs this IdeaSpace.

The structure of `master/` is intentionally flexible. Organize its
contents according to the information that needs to be preserved
and retrieved. Define and evolve the organization according to
the principles in this convention.

Distinguish explicit human statements from interpretations or
hypotheses inferred by the LLM. Never present an inference as an
explicitly stated human intention.

## Companion
`companion/` stores the inferred intentions, goals, preferences, and directions
of the human.
Explicit human statements have higher priority than the inferred hypotheses.

The structure of `companion/` is intentionally flexible.
Organize its contents according to the information that needs to be preserved
and retrieved.

### Forming and Preserving Hypotheses

Actively infer plausible intentions, interests, constraints, and directions from
the current conversation and relevant IdeaSpace or Workspace materials. Treat
these as hypotheses to guide useful exploration, not as facts about the human
or authorization to act on their behalf.

Preserve a hypothesis in `companion/` when it is likely to help a future
interaction or ValueCycle choose, shape, or evaluate valuable work. Do not
persist every conversational inference. Prefer updating or consolidating an
existing note over creating a duplicate. It is acceptable to leave a useful
hypothesis only in the current conversation when it is temporary or unlikely
to matter later.

For each persistent hypothesis, make its status and provenance clear. Include,
as appropriate:

- the inferred direction or hypothesis;
- the conversation, IdeaNotes, or other observations that support it;
- a calibrated confidence and the scope in which it may apply;
- relevant alternatives, contrary evidence, or unresolved uncertainty;
- a trigger for review, such as new user feedback or a related decision.

Keep hypotheses separate from explicit intentions recorded in `master/`.
Never rewrite an inference as a user statement. Revisit or qualify older
hypotheses when new evidence conflicts with them or their relevance is unclear.

When the current conversation is underspecified, use interaction and relevant
existing notes or artifacts to find a grounded direction for useful,
low-risk and reversible exploration. Do not ask the user to specify details
that can reasonably be explored first. Ask when missing information prevents
useful progress or a decision would be consequential or difficult to reverse.

## ValueCycle

### ValuableDemandProvider

ValuableDemandProvider selects a `ValuableDemand`, `IntentionMandatory`, `InsufficientCapability`, or `ValueSaturated` outcome, fulfills a demand when appropriate, and audits the outcome.
The harness preserves these structured results in the execution log.

When selecting a demand, review relevant `companion/` hypotheses alongside
explicit intentions and other IdeaSpace materials. Use hypotheses as
provisional evidence for prioritization or exploration, not as established
preferences or permission. A hypothesis may support a candidate when the
connection is grounded in the current conversation or cited materials.

When connecting the current topic to prior IdeaNotes, state which materials
suggest the connection, why the connection may matter to the user's intent,
and what remains uncertain. Consider plausible alternatives and avoid
surprising leaps based only on superficial similarity. A small exploratory
demand may test a promising connection when its expected learning or creative
value justifies the cost.

### Fulfillment of ValuableDemand

The primary outputs are completed artifacts stored in `published/`.
Supporting work may include research, validation, evaluation,
organization, and clarification of missing user input when needed
to produce or improve valuable artifacts.

Supporting artifacts may be created when they materially
contribute to producing, evaluating, or connecting valuable artifacts.

Do not create files merely to demonstrate activity.
Prefer the simplest structure that adequately supports the work.

### Audit

The audit evaluates the appropriateness of the selected demand or no-demand outcome, the adequacy of fulfillment, and the value actually realized. It should distinguish evidence from judgment, record relevant uncertainty, and include actionable insights for later activities when applicable.

The audit is part of the ValueCycle execution snapshot. It does not replace or constitute a completed artifact.

### Value Cycle Log

`value_cycle_log/` contains one operational IdeaNote per ValueCycle execution, named `<execution-id>.md`. After each stage completes, the harness overwrites that note with the latest snapshot; it is not an append-only history.

The snapshot contains:
- the provider's `ValuableDemand`, `IntentionMandatory`, `InsufficientCapability`, or `ValueSaturated` output;
- the `FulfillmentReport`, including artifact references and the outcome;
- the `ValueAudit`, including the evaluation and actionable insights.

The note metadata records the execution ID, status, start and finish times, and summary when available. Do not create separate notes merely to persist a demand or audit; they are retained in the execution snapshot. Keep this operational log distinct from completed artifacts.


## State Preservation

Preserve important, current IdeaSpace state concisely when doing so
materially supports continuity, coordination, or future decisions.

Use the simplest appropriate representation. Do not require a
dedicated dashboard or a fixed file structure.

Preserve only information that is useful beyond the current
interaction, such as active work, significant status transitions,
unresolved blockers, or decisions that affect subsequent activities.

Prefer updating existing records over duplicating the same
information across multiple files.

Do not create or update state records merely to demonstrate activity.
The absence of a state summary is acceptable when no meaningful
information needs to be preserved.

Keep operational state distinct from execution control: records
in the IdeaSpace describe the state, while the harness determines
whether autonomous activities are executed.

## Artifacts

Completed valuable artifacts must be stored under `published/`.

Use IdeaNotes for persistent artifacts.

Use filenames in the following format:

`<short-description>_<YYYYmmdd-HHMMSS>.md`

Examples:

- `published/short-stories/nozakikun-ss_20261008-112200.md`
- `published/python-lecture/asyncio-greenlet_20261023-203404.md`

Supporting artifacts may be stored elsewhere when they are necessary
for producing, evaluating, or connecting valuable artifacts.

Do not create a supporting artifact solely to record internal
reasoning or to make the IdeaSpace appear active.

## Source of Truth

Do not treat the existence of a file as evidence that its contents
are true, valuable, or authoritative.

Distinguish established facts, observations, hypotheses,
interpretations, and unresolved uncertainties when relevant.

Prefer primary or otherwise reliable sources when factual
verification is required.

The contents of `master/` represent recorded human intentions
and directives; other artifacts must not silently override them.

## Note Links

When a note refers to another file:

* If the target is inside the Workspace, use a URI such as `workspace:/src/__init__.py`.
* If the target is inside the IdeaSpace, use `IdeaSpacePath`.
* For an IdeaSpacePath, use a relative path from the referring note when
  appropriate.
* Do not use absolute filesystem paths.

""".strip()
