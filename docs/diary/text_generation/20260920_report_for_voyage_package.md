# Voyage System Experiment

## Status

The `Voyage` system is retired.

This document records the design and experiments behind the system,
rather than preserving its implementation.

The purpose of this document is to preserve what was learned from
the experiment:

- how an LLM can be guided by an explicit document objective;
- how the maturity of that objective can affect generation;
- how a document can be evaluated against its objective;
- how evaluation and generation can form an iterative loop;
- how much state should be maintained around an LLM task.

No replacement implementation is defined here.

---

## Overview

`Voyage` was an experiment in iterative document evolution.

The basic idea was to treat document creation not simply as:

    prompt → generated document

but as a process with an explicit state.

The system introduced three major concepts:

- `Compass`
- `Bearing`
- `EvolvePolicy`

These concepts were combined into a `VoyageState`.

The intended process was approximately:

    Compass
       ↓
    Evolve
       ↓
    Manuscript
       ↓
    Reflect
       ↓
    Bearing + updated Compass
       ↓
    Evolve again

The document was therefore treated as something that could
repeatedly be evaluated and evolved according to an explicit
objective.

---

# Concepts

## Compass

`Compass` represents the objective of the document and the maturity
of that objective.

It contains:

```python
class Compass(BaseModel, frozen=True):
    progress: CompassProgress
    objective: str
````

The progress state was:

```text
emerging
shaping
committed
```

The intended meaning was:

### emerging

The objective is not yet fixed.

The system may explore different directions and refine the objective.

### shaping

The objective is becoming clearer.

Generation should consolidate and clarify the emerging direction.

### committed

The objective is sufficiently fixed.

Generation should prioritize the objective strictly and avoid
unnecessary deviation.

The important observation is that the objective itself was treated
as having a state of maturity.

This allowed the same generation operation to behave differently
depending on how firmly the objective had been established.

---

## Bearing

`Bearing` represents the current assessment of the manuscript
relative to the `Compass`.

It contains:

```python
class Bearing(BaseModel, frozen=True):
    alignment: CompassAlignment
    assessment: str
```

`CompassAlignment` used the following states:

```text
undefined
inadequate
acceptable
excellent
masterpiece
```

The intention was to give the system an explicit representation
of how well the current manuscript aligned with its objective.

The LLM was expected to provide both:

* an alignment state;
* an explanation of that assessment.

`Bearing` therefore represented the current position of the document
relative to its intended direction.

---

## EvolvePolicy

`EvolvePolicy` controlled how strongly the manuscript should be
changed.

The available levels were:

```text
auto
low
medium
high
extreme
```

The intended behavior was approximately:

* `auto`: determine revision pressure from the Compass state;
* `low`: gentle refinement;
* `medium`: stronger structural and expressive refinement;
* `high`: bold reinterpretation and restructuring;
* `extreme`: deliberately break creative stagnation through radical
  changes.

The important idea was to separate:

```
what the document should become
```

from:

```
how aggressively the document should change.
```

`Compass` described direction.

`EvolvePolicy` described revision pressure.

---

# VoyageState

These concepts were combined into:

```python
class VoyageState(BaseModel, frozen=True):
    compass: Compass
    evolve_policy: EvolvePolicy
    bearing: Bearing
```

The state represented the current condition of the document voyage.

Conceptually:

```text
                 Compass
              "Where are we going?"
                    │
                    ▼
                Manuscript
                    │
                    ▼
                 Bearing
              "Where are we?"
                    │
                    ▼
             Compass update
                    │
                    ▼
                 Evolve
```

The system therefore attempted to create a feedback loop between
objective, evaluation, and generation.

---

# LLM Interaction

The system had two primary operations.

## Reflect

`Reflect` evaluated the manuscript against the current Compass.

Its responsibilities were:

1. Decide whether the Compass should be updated.
2. Complete the Compass if necessary.
3. Evaluate the manuscript against the updated Compass.
4. Produce a Bearing.

Conceptually:

```text
Manuscript + Compass
        ↓
      Reflect
        ↓
Compass + Bearing
```

---

## Evolve

`Evolve` generated or revised the manuscript using the current
Compass and EvolvePolicy.

Conceptually:

```text
Manuscript
    +
Compass
    +
EvolvePolicy
    ↓
  Evolve
    ↓
New Manuscript
```

The two operations formed the main feedback loop:

```text
        ┌───────────────┐
        │    Compass    │
        └───────┬───────┘
                │
                ▼
           ┌─────────┐
           │ Evolve  │
           └────┬────┘
                │
                ▼
           Manuscript
                │
                ▼
           ┌─────────┐
           │ Reflect │
           └────┬────┘
                │
                ▼
       Bearing / Compass
                │
                └──────────→ Evolve
```

---

# Original System Prompts

The following prompts are included as historical material.

They document how the concepts above were communicated to the LLM
during the experiment.

They should not be considered a recommended prompt for future use.

---

## Evolve Prompt

```text
# Task: Manuscript Evolution

You are operating in a structured writing system.

The system consists of:
- Compass (objective definition and maturity)
- EvolvePolicy (Instruction of modification)
- Manuscript (document content)

Your job:
1. Generate or revise the manuscript based on the updated states.

## Manuscript Update Instructions

The manuscript provided by the user is the current manuscript.
Revise or regenerate it accordingly.

### Generation policy from `Compass`

- Respect the Compass objective according to its progress level.
    - emerging → allow exploration and refinement.
    - shaping → consolidate and clarify direction.
    - committed → strictly prioritize the objective.

### Generation policy from the `EvolvePolicy`

- auto:
    Adjust pressure based on Compass progress and current maturity.
- low:
    Gentle refinement. Preserve structure and voice.
    Stimulate subtle improvement.
- medium:
    Strong refinement. Improve structure, sharpen themes,
    enhance emotional dynamics.
- high:
    Intensive stimulation. Bold reinterpretation and structural
    reshaping are allowed while preserving the Compass objective.
- extreme:
    Break stagnation mode.
    Apply radical restructuring or reinterpretation specifically
    to overcome creative deadlock.

When the `degree` is `auto`, refer to the generation policy from
`Compass`.

Otherwise, the policy from `EvolvePolicy` overrides the policy
from `Compass`.

Return a valid `EvolveResponse` JSON object.
Do not output anything else.
```

---

## Reflect Prompt

```text
# Task: Reflect and Update State

You are evaluating a manuscript within a structured writing system.

The manuscript is given as the input of the user.

Responsibilities:

1. Decide whether `Compass` should be updated.
2. If and only if the `Compass` is not sufficient to generate
   `Bearing`, complete attributes of `Compass`.
3. Evaluate the manuscript against the updated `Compass` and
   produce a valid `Bearing`.

Current Compass:

[Compass JSON]

Return a valid `ReflectResponse` JSON object.
Do not output anything else.
```

These prompts are preserved because they show an important aspect
of the experiment: the system did not merely ask the LLM to "write
better".

It attempted to make the LLM operate within an explicit conceptual
model consisting of direction, maturity, evaluation, and revision
pressure.

---

# What Was Interesting

## 1. Objective can be treated as state

A useful observation from the experiment was that an objective does
not necessarily have to be represented as a fixed instruction.

An objective may itself evolve.

For example:

```text
emerging
    ↓
shaping
    ↓
committed
```

This provides a way to distinguish exploratory generation from
generation that should strictly preserve an established direction.

This idea may be useful in future LLM systems.

---

## 2. Evaluation and generation can form a feedback loop

The separation between `Reflect` and `Evolve` provided an explicit
cycle:

```text
generate
    ↓
evaluate
    ↓
update objective
    ↓
generate again
```

This is different from a single prompt that asks the LLM to
simultaneously create and criticize its own output.

The experiment therefore provided a concrete example of treating
LLM interaction as an iterative process rather than a single
completion.

---

## 3. Revision intensity can be separated from objective

`Compass` and `EvolvePolicy` represented two different dimensions.

```text
Compass
    = What should the document become?

EvolvePolicy
    = How strongly should the document change?
```

This separation was useful conceptually.

It made it possible to imagine a document whose objective is already
clear but which still requires a radical rewrite, as well as a
document whose objective is still emerging and therefore should be
handled more cautiously.

---

## 4. Explicit state can become heavier than the original problem

The experiment also demonstrated an opposite effect.

Once `Compass`, `Bearing`, `EvolvePolicy`, and `VoyageState` existed,
the surrounding system began to require:

* state serialization;
* state validation;
* UI for editing state;
* TOML representation;
* state reconstruction;
* interaction objects;
* asynchronous execution;
* state update rules.

The system gradually became a system for maintaining the Voyage
state, rather than simply a system for helping with document creation.

This is an important warning.

An explicit state model can make an LLM workflow clearer,
but the state model itself can become the dominant complexity.

---

# What Should Not Be Preserved

The following implementation details are not considered part of the
lasting design:

* `VoyageState` as a persistent domain model;
* TOML serialization of the state;
* the original UI structure;
* `VoyageInteractionCreator`;
* the original request/response classes;
* the exact `CompassAlignment` vocabulary;
* the exact prompt wording;
* the original package structure.

These were implementation choices made during the experiment.

They should not constrain a future implementation.

---

# What Should Be Preserved

The following observations are considered worth retaining:

1. An LLM workflow can explicitly represent the maturity of an
   objective.

2. Document evaluation can be represented separately from document
   generation.

3. Revision intensity can be separated from the objective itself.

4. Evaluation and generation can form an iterative feedback loop.

5. Explicit workflow state can improve conceptual clarity, but can
   also introduce substantial application complexity.

6. A useful experiment should not necessarily become a permanent
   domain model.

---

# Relation to Materials


# Decision

The `Voyage` implementation is retired.

No replacement implementation is defined at this time.

The experiment is retained as a design record because the concepts
of:

* objective maturity;
* evaluation against an objective;
* revision pressure;
* iterative reflection and evolution

may be useful in a future LLM writing system.

Any future implementation should be designed from the observed
requirements rather than by directly reviving the original
`Voyage`, `Compass`, `Bearing`, or `EvolvePolicy` classes.

As a side note, the concepts explored by `Voyage` may be useful
when considering a more unified interface for document-oriented
knowledge and writing workflows. The current design of
`IdeaNote` / `IdeaSpace` may provide one possible foundation for
such a workflow, but this has not been evaluated or designed as
a replacement for `Voyage`.