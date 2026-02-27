import logging
import functools
from textwrap import dedent
from typing import Annotated, cast, Callable
from pydantic import BaseModel, Field
from pytoy.tools.llm.document.voyages.domain import Compass, EvolvePolicy, Bearing

from pytoy_llm.models import InputMessage, LLMConfig

from pytoy_llm.task import (
    InvocationSpecMeta,
    LLMInvocationSpec,
    LLMTaskRequest,
    LLMTaskSpec,
    LLMTaskSpecMeta,
)
from pytoy_llm import completion

from pytoy.tools.llm.kernel import FairyKernel
from pytoy.tools.llm.interaction_provider import InteractionProvider, InteractionRequest, LLMInteraction


class EvolveRequest(BaseModel, frozen=True):
    compass: Annotated[
        Compass, Field(description="The direction at which the document should pursue.")
    ]
    manuscript: Annotated[str, Field(description="The current manuscript.")]
    evolve_policy: Annotated[EvolvePolicy, Field(description="The policy for editing of the document.")] = EvolvePolicy(degree="auto")


class EvolveResponse(BaseModel, frozen=True):
    manuscript: Annotated[str, Field(description=("The fully rewritten manuscript.\n"
                                        "It is the entire document from beginning to end.\n"
                                        "Note that output must be self-contained.\n"
                                        "A reader must be able to read the `manuscript` field alone \n"
                                     ))]
    reason: Annotated[str, Field(description="The reason and policy regarding the generation or revision of the manuscript.")]
    compass: Annotated[
        Compass, Field(description="The direction at which the document should pursue.")
    ]
    

def wrap_logger(function: Callable, logger: logging.Logger) -> Callable:
    @functools.wraps(function)
    def wrapped(*args, **kwargs):
        for arg in args:
            logger.info(f"{type(arg).__name__}:{arg}")
        for k, v in kwargs.items():
            logger.info(f"{k}={type(v).__name__}:{v}")

        try:
            result = function(*args, **kwargs)
        except Exception as e:
            logger.exception(f"Exception in {function.__name__}: {e}")
            raise  # そのまま外に伝える

        logger.info(f"{type(result).__name__}:{result}")
        return result

    return wrapped

def _evolve_create_messages(evolve_request: EvolveRequest) -> list[InputMessage]:
    user_message = InputMessage(role="user", content=evolve_request.manuscript)
    
    compass = evolve_request.compass
    compass_fragment = dedent(f"""
    ```json
    {Compass.model_json_schema()}
    ```
    ```json
    {compass.model_dump_json()}
    ```
    """.strip())

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
    
    system_prompt = dedent(f"""
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

    """.strip())
    system_message = InputMessage(role="system", content=system_prompt)
    return [user_message, system_message]


def evolve(evolve_request: EvolveRequest) -> EvolveResponse:
    """Update the manuscript based on  `EvolveRequest`.
    """
    messages = _evolve_create_messages(evolve_request)
    result = completion(messages, output_format=EvolveResponse)
    return cast(EvolveResponse, result)


def build_evolve_task_request(request: EvolveRequest, llm_config: LLMConfig | None = None, connection_name: str | None = None, logger: logging.Logger | None = None) -> LLMTaskRequest:
    create_messages = wrap_logger(_evolve_create_messages, logger) if logger else _evolve_create_messages
    meta = InvocationSpecMeta(name="EvolveInvocation", intent="Evolve the manuscript")
    invocation_spec = LLMInvocationSpec(meta=meta,
                                        output_spec=EvolveResponse,
                                        create_messages=create_messages,
                                        llm_config=llm_config,
                                        connection_name=connection_name)
    task_spec = LLMTaskSpec.from_single_spec(meta="VoyageEvolveTask", invocation_spec=invocation_spec)
    return LLMTaskRequest(task_spec=task_spec, task_input=request)



class ReflectRequest(BaseModel, frozen=True):
    manuscript: Annotated[str, Field(description="The current manuscript.")]
    compass: Annotated[Compass, Field(description="The current compass")]


class ReflectResponse(BaseModel, frozen=True):
    bearing: Annotated[
        Bearing,
        Field(description="The current bearing of the manuscript."),
    ]
    compass: Annotated[Compass, Field(description="The updated compass")]


def _reflect_create_messages(reflect_request: ReflectRequest) -> list[InputMessage]:
    user_message = InputMessage(
        role="user",
        content=reflect_request.manuscript,
    )

    compass_json = reflect_request.compass.model_dump_json()

    system_prompt = dedent(f"""
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
    """.strip())

    system_message = InputMessage(role="system", content=system_prompt)
    return [user_message, system_message]


def reflect(reflect_request: ReflectRequest) -> ReflectResponse:
    """For testing or direct usage."""
    messages = _reflect_create_messages(reflect_request)
    return cast(ReflectResponse, completion(messages, output_format=ReflectResponse))


def build_reflect_task_request(
    request: ReflectRequest,
    llm_config: LLMConfig | None = None,
    connection_name: str | None = None,
    logger: logging.Logger | None = None,
    
) -> LLMTaskRequest:
    """Construct an LLMTaskRequest for the Reflect task."""
    create_messages = wrap_logger(_reflect_create_messages, logger) if logger else _reflect_create_messages
    meta = InvocationSpecMeta(name="ReflectInvocation", intent="Reflect on the manuscript")
    invocation_spec = LLMInvocationSpec(
        meta=meta,
        output_spec=ReflectResponse,
        create_messages=create_messages,
        llm_config=llm_config,
        connection_name=connection_name,
    )
    task_spec = LLMTaskSpec.from_single_spec(meta="VoyageReflectTask", invocation_spec=invocation_spec)
    return LLMTaskRequest(task_spec=task_spec, task_input=request)


class VoyageInteractionCreator:
    """Create the interaction.
    """
    def __init__(self, kernel: FairyKernel):
        self.kernel = kernel

    def create_evolve_interaction(self,
                                evolve_request: EvolveRequest,
                                on_success: Callable[[EvolveResponse], None],
                                on_failure: Callable[[Exception], None],
                                llm_config: LLMConfig | None = None,
                                connection_name: str | None = None) -> LLMInteraction:
        """Create `evolve` interaction (asynchronous procedure call of `evolve`)
        """
        task_request = build_evolve_task_request(evolve_request, llm_config=llm_config, connection_name=connection_name, logger=self.kernel.llm_context.logger)
        interaction_request = InteractionRequest(self.kernel, task_request=task_request, on_success=on_success, on_failure=on_failure)
        return InteractionProvider().create(interaction_request)

    def create_reflect_interaction(self,
                                   reflect_request: ReflectRequest,
                                on_success: Callable[[ReflectResponse], None],
                                on_failure: Callable[[Exception], None],
                                llm_config: LLMConfig | None = None,
                                connection_name: str | None = None) -> LLMInteraction:
        """Create `evolve` interaction (asynchronous procedure call of `evolve`)
        """
        task_request = build_reflect_task_request(reflect_request, llm_config=llm_config, connection_name=connection_name, logger=self.kernel.llm_context.logger)
        interaction_request = InteractionRequest(self.kernel, task_request=task_request, on_success=on_success, on_failure=on_failure)
        return InteractionProvider().create(interaction_request)