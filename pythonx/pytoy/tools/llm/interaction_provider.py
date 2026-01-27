"""
Operator: Do something synchronously with `FairKernel`.
InteractionRequester : Do something with LLM using `FairyKernel`.
"""

import uuid
from pydantic import BaseModel
from dataclasses import dataclass
from pytoy.infra.core.models import EventEmitter


from typing import Any, Callable, Protocol

from pytoy.infra.timertask.thread_executor import ThreadExecutionRequest, ThreadExecutor
from pytoy.tools.llm.models import HooksForInteraction, LLMInteraction
from pytoy.tools.llm.kernel import FairyKernel
from pytoy_llm import completion
from pytoy_llm.models import InputMessage, SyncOutputFormat
from pytoy_llm.models import SyncOutput, SyncOutputFormatStr


@dataclass
class InteractionRequest:
    kernel: FairyKernel
    inputs: list[InputMessage]
    llm_output_format: SyncOutputFormat | SyncOutputFormatStr | type[BaseModel]
    on_success: Callable[[SyncOutput], None]
    on_failure: Callable[[Exception], None]
    hooks: HooksForInteraction | None = None


class InteractionProvider:
    def __init__(self) -> None:
        pass

    def create(self, request: InteractionRequest) -> LLMInteraction:
        """
        kernelとrequesterからLLMInteractionを作り、kernelに登録する。
        PytoyFairyなどから呼び出すことを想定。
        """
        interaction_end_emitter = EventEmitter[Any]()

        def _on_finish(sync_output: SyncOutput):
            try:
                request.on_success(sync_output)
            except Exception as e:
                print("Unhandled exception at `on_success`", e)
            interaction_end_emitter.fire(None)

        def _on_error(exception: Exception):
            try:
                request.on_failure(exception)
            except Exception as e:
                print("Unhandled exception at `on_failure`", e)
            interaction_end_emitter.fire(None)

        # 実際のLLM呼び出し処理
        def _main(_) -> SyncOutput:
            return completion(request.inputs, output_format=request.llm_output_format)

        # スレッド実行リクエスト作成
        execution_request = ThreadExecutionRequest(
            main_func=_main,
            on_finish=_on_finish,
            on_error=_on_error
        )
        execution = ThreadExecutor().execute(execution_request)

        # Interaction生成
        id_ = str(uuid.uuid1())
        interaction = LLMInteraction(
            id=id_,
            task=execution,
            on_exit=interaction_end_emitter.event,
            hooks=request.hooks
        )
        # kernelに登録
        request.kernel.register_interaction(interaction)
        return interaction