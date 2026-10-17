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

## ValuableDemands

Each ValuableDemand is recorded in a Markdown file named
after its unique ID under `demands/`.

Each record contains the following sections:

- `Valuable Demand`: 

- `Decision Rationale`: a concise explanation of why the
  ValuableDemand was selected, including relevant hypotheses,
  background, assumptions, or other contingencies where applicable.

- `Relevant User Input`: the user inputs relevant to the
  selected ValuableDemand and their relationship to it.


`Relevant User Input` should cover only inputs relevant to
the selected ValuableDemand. It must distinguish explicit user
statements from interpretations and must not imply that all
user inputs have been reflected. If no user inputs were provided
or considered in the decision, this should be stated explicitly.

## Fulfillment of ValuableDemand

The primary outputs are completed artifacts stored in `published/`.
Supporting work may include research, validation, evaluation,
organization, and clarification of missing user input when needed
to produce or improve valuable artifacts.

Supporting artifacts may be created when they materially
contribute to producing, evaluating, or connecting valuable artifacts.

Do not create files merely to demonstrate activity.
Prefer the simplest structure that adequately supports the work.

## Audits

`audits/` stores concise IdeaNotes recording the evaluation
of ValuableDemand selection, fulfillment, and the value created.

Each completed work cycle must produce an Audit record.

An Audit should distinguish:
- the appropriateness of the selected ValuableDemand;
- the adequacy of its fulfillment;
- the value actually created, including unresolved uncertainty;
- actionable insights for subsequent activities, when applicable.

Each Audit must link to the IdeaNote recording the ValuableDemand and to the artifact, if one exists.

An Audit does not replace the completed artifact.
It records the evaluation of the work and its outcomes.

Keep Audit records concise. Include only the evidence,
findings, and insights needed to understand the evaluation.


## Dashboard

`dashboard.md` represents the current operational state of the
IdeaSpace.

Maintain a concise view of:

- the current ValuableDemand;
- the current work and its status;

The dashboard is a navigation and state representation. It is not
the primary source of truth for published artifact contents.

Do not use the dashboard as a diary of internal reasoning.
Update it when a meaningful state transition occurs.

Create it when needed. An initially empty IdeaSpace does not need
to contain a pre-generated dashboard.

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
