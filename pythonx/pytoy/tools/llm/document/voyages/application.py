from textwrap import dedent
from typing import Annotated, Callable

from pydantic import BaseModel, Field
from pytoy_llm import completion
from pytoy_llm.models import LLMMessage, LLMParam
from pytoy_llm.task.models import (
    InvocationSpecMeta,
    LLMInvocationSpec,
    TaskSpec,
)

from pytoy.tool_execution.llm_execution import LLMExecutionHandler, LLMExecutionHooks, LLMExecutionRequest, LLMExecutor
from pytoy.tools.llm.document.voyages.domain import Bearing, Compass, EvolvePolicy


class EvolveRequest(BaseModel, frozen=True):
    compass: Annotated[Compass, Field(description="The direction at which the document should pursue.")]
    manuscript: Annotated[str, Field(description="The current manuscript.")]
    evolve_policy: Annotated[EvolvePolicy, Field(description="The policy for editing of the document.")] = EvolvePolicy(
        degree="auto"
    )


class EvolveResponse(BaseModel, frozen=True):
    manuscript: Annotated[
        str,
        Field(
            description=(
                "The fully rewritten manuscript.\n"
                "It is the entire document from beginning to end.\n"
                "Note that output must be self-contained.\n"
                "A reader must be able to read the `manuscript` field alone \n"
            )
        ),
    ]
    reason: Annotated[
        str, Field(description="The reason and policy regarding the generation or revision of the manuscript.")
    ]
    compass: Annotated[Compass, Field(description="The direction at which the document should pursue.")]


def _evolve_create_message(evolve_request: EvolveRequest) -> LLMMessage:
    compass = evolve_request.compass
    compass_fragment = dedent(
        f"""
    ```json
    {Compass.model_json_schema()}
    ```
    ```json
    {compass.model_dump_json()}
    ```
    """.strip()
    )

    evolve_policy = evolve_request.evolve_policy
    evolve_policy_fragment = dedent(f"""
    ```json
    {EvolvePolicy.model_json_schema()}
    ```
    ```json
    {evolve_policy.model_dump_json()}
    ```

    - EvolvePolicy overrides conservative behavior.
      When degree is high or extreme, avoid minimal edits.
    """)

    system_prompt = dedent(
        f"""
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
        
    {compass_fragment}

    ### Generation policy from the `EvolvePolicy`

    {evolve_policy_fragment}

    When the `degree` is `auto`, refer to the generation policy from `Compass`.
    Otherwise, the policy from `EvolvePolicy` overrides the policy from `Compass`.
    ---

    Return a valid `EvolveResponse` JSON object.
    Do not output anything else.

    """.strip()
    )
    return LLMMessage.from_prompt(user=evolve_request.manuscript, system=system_prompt)


def evolve(evolve_request: EvolveRequest) -> EvolveResponse:
    """Update the manuscript based on  `EvolveRequest`."""
    message = _evolve_create_message(evolve_request)
    return completion(message, output_type=EvolveResponse)


def build_evolve_task_spec(
    llm_param: LLMParam | None = None,
    connection_name: str | None = None,
) -> TaskSpec:
    meta = InvocationSpecMeta(name="EvolveInvocation", intent="Evolve the manuscript")
    invocation_spec = LLMInvocationSpec(
        meta=meta,
        output_type=EvolveResponse,
        create_messages=_evolve_create_message,
        connection=connection_name,
        llm_param=llm_param,
    )
    task_spec = TaskSpec.from_single_spec(meta="VoyageEvolveTask", invocation_spec=invocation_spec)
    return task_spec


class ReflectRequest(BaseModel, frozen=True):
    manuscript: Annotated[str, Field(description="The current manuscript.")]
    compass: Annotated[Compass, Field(description="The current compass")]


class ReflectResponse(BaseModel, frozen=True):
    bearing: Annotated[
        Bearing,
        Field(description="The current bearing of the manuscript."),
    ]
    compass: Annotated[Compass, Field(description="The updated compass")]


def _reflect_create_messages(reflect_request: ReflectRequest) -> LLMMessage:
    compass_json = reflect_request.compass.model_dump_json()

    system_prompt = dedent(
        f"""
    # Task: Reflect and Update State

    You are evaluating a manuscript within a structured writing system.
    The manuscript is given as the input of the user. 

    Responsibilities:
    1. Decide whether `Compass` should be updated.
    2. If and only if the `Compass` is not sufficient to generate `Bearing`, complete attributes of `Compass`. 
    3. Evaluate the manuscript against the updated `Compass` and produce a valid `Bearing`.

    Current Compass:
    ```json
    {compass_json}
    ```

    Return a valid `ReflectResponse` JSON object.
    Do not output anything else.
    """.strip()
    )

    return LLMMessage.from_prompt(user=reflect_request.manuscript, system=system_prompt)


def reflect(reflect_request: ReflectRequest) -> ReflectResponse:
    """For testing or direct usage."""
    messages = _reflect_create_messages(reflect_request)
    return completion(messages, output_type=ReflectResponse)


def build_reflect_task_spec(
    llm_param: LLMParam | None = None,
    connection_name: str | None = None,
) -> TaskSpec:
    """Construct an TaskRequest for the Reflect task."""
    meta = InvocationSpecMeta(name="ReflectInvocation", intent="Reflect on the manuscript")
    invocation_spec = LLMInvocationSpec(
        meta=meta,
        output_type=ReflectResponse,
        create_messages=_reflect_create_messages,
        llm_param=llm_param,
        connection=connection_name,
    )
    return TaskSpec.from_single_spec(meta="VoyageReflectTask", invocation_spec=invocation_spec)


class VoyageInteractionCreator:
    """Create the interaction."""

    def __init__(self):
        pass

    def create_evolve_interaction(
        self,
        evolve_request: EvolveRequest,
        handle_output: Callable[[EvolveResponse], None],
        on_failure: Callable[[Exception], None],
        llm_param: LLMParam | None = None,
        connection_name: str | None = None,
    ) -> LLMExecutionHandler:
        """Create `evolve` interaction (asynchronous procedure call of `evolve`)"""
        task_spec = build_evolve_task_spec(
            llm_param=llm_param,
            connection_name=connection_name,
        )
        execution_request = LLMExecutionRequest(task_spec=task_spec, input=evolve_request)
        executor = LLMExecutor()
        return executor.execute(
            execution_request, hooks=LLMExecutionHooks.from_any(handle_output=handle_output, on_exception=on_failure)
        )

    def create_reflect_interaction(
        self,
        reflect_request: ReflectRequest,
        handle_output: Callable[[ReflectResponse], None],
        on_failure: Callable[[Exception], None],
        llm_param: LLMParam | None = None,
        connection_name: str | None = None,
    ) -> LLMExecutionHandler:
        """Create `evolve` interaction (asynchronous procedure call of `evolve`)"""
        task_spec = build_reflect_task_spec(
            llm_param=llm_param,
            connection_name=connection_name,
        )
        execution_request = LLMExecutionRequest(task_spec=task_spec, input=reflect_request)
        executor = LLMExecutor()
        return executor.execute(
            execution_request, hooks=LLMExecutionHooks.from_any(handle_output=handle_output, on_exception=on_failure)
        )
