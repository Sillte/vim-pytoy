import uuid
import time
from textwrap import dedent
from dataclasses import dataclass, field
from pytoy.infra.core.models import Event, EventEmitter
from pytoy.ui.pytoy_buffer import PytoyBuffer, BufferID, BufferEvents
from pytoy.ui.pytoy_window import PytoyWindow, CharacterRange
from typing import Any, Callable, Protocol, Sequence, Callable
from pydantic import BaseModel 
from pytoy_llm.models import SyncOutput, SyncOutputFormatStr, SyncOutputFormat
from pytoy.contexts.pytoy import GlobalPytoyContext

from pytoy.infra.timertask import ThreadWorker

from pytoy_llm import completion
from pytoy_llm.models import InputMessage
from pytoy.ui.notifications import EphemeralNotification

    

type PreSaveHook = Callable[[PytoyBuffer], None]

@dataclass
class HooksForInteraction:
    pre_save: PreSaveHook | None = None


class PytoyLLMContext(BaseModel):
    def __init__(self, buffer: PytoyBuffer, *, ctx: GlobalPytoyContext):
        ...
    
    def dispose(self):
        pass

    
@dataclass
class InteractionRequest:
    inputs: list[InputMessage]
    llm_output_format: SyncOutputFormat | SyncOutputFormatStr | type[BaseModel]
    on_success: Callable[[SyncOutput], None]
    on_failure: Callable[[Exception], None]
    

@dataclass
class LLMInteraction:
    task: Any 
    on_exit: Event[Any]
    id: str = field(default_factory=lambda: str(uuid.uuid1()))
    timestamp: float = field(default_factory=lambda: time.time())
    hooks: HooksForInteraction | None = None
    
                 
class FairyKernel:
    """States of `Fairy`.  
    """

    def __init__(self, buffer: PytoyBuffer, llm_context: PytoyLLMContext):
        self.buffer = buffer
        self.llm_context = llm_context
        self.interactions: dict[str, LLMInteraction] = {}
        
        self.buffer.on_wiped.subscribe(lambda _: self.dispose)
        disposables = []
        disposables.append(self.buffer.events.on_pre_buf.subscribe(lambda _: self.pre_save))
        self.disposables = []
                 
    @property
    def on_end(self) -> Event[BufferID]:
        return self.buffer.on_wiped

    @property
    def events(self) -> BufferEvents:
        return self.buffer.events

    @property
    def window(self) -> PytoyWindow:
        if (window := self.buffer.window):
            return window
        else:
            self.buffer.show()
        window =  self.buffer.window
        assert window is not None
        return window

    @property
    def selection(self) -> CharacterRange:
        return self.window.selection
    

    def register_interaction(self, interaction: LLMInteraction, hooks: HooksForInteraction | None = None):
        # [TODO]: (2026/01/15) Deal with the procesing of `hooks`.
        id_ = interaction.id
        self.interactions[id_] = interaction
        interaction.on_exit.subscribe(lambda _: self.interactions.pop(id_))
    
    def dispose(self, buffer_id: BufferID):
        # Release the resource, acquired by this class.
        # TODO : invoke llm_context.dispose()
        for item in self.disposables:
            item.dispose()
    
    def pre_save(self) -> None:
        # BufPre
        ...
        lines = self.buffer.lines
        import re 
        # TODO: Implement the hooks and perform filter process.
        ...
        content = "\n".join(lines)  
        entire_cr = self.buffer.range_operator.entire_character_range
        self.buffer.range_operator.replace_text(entire_cr, content)


class FairyKernelManager:
    def __init__(self,):
        self._kernels: dict[BufferID, FairyKernel] = dict()
        
    def summon(self, buffer: PytoyBuffer,  *, ctx:GlobalPytoyContext | None = None) -> FairyKernel:
        if ctx is None:
            ctx = GlobalPytoyContext.get()
        # Currently, only 1 Fairy kernel allowes.
        if self._kernels:
            if (kernel := self._kernels.get(buffer.buffer_id)):
                return kernel
            else:
                raise ValueError("Differnt buffer occupies the differnt unique fairy kernel.") 
        else: 
            llm_context = PytoyLLMContext(buffer, ctx=ctx)
            kernel = FairyKernel(buffer, llm_context)
            # Required events for `FairyKernel`.
            self._kernels[buffer.buffer_id] = kernel
            def deregister(_):
                self._kernels.pop(buffer.buffer_id)
            kernel.on_end.subscribe(deregister)
            return kernel
    
    def bye_bye_fairies(self) -> None:
        for buffer_id, fairy in self._kernels.items():
            fairy.dispose(buffer_id)
                
                
class InteractionRequesterProtocol(Protocol):
    def __call__(self, kernel: FairyKernel) -> InteractionRequest:
        ...
    


class PytoyFairy:
    def __init__(self, buffer: PytoyBuffer,
                   llm_context: PytoyLLMContext | None = None,
                  *, ctx:GlobalPytoyContext | None = None):
        if not buffer.is_file:
            raise ValueError("Only file is accepted.")
        if ctx is None:
            ctx = GlobalPytoyContext.get()
        kernel_manager = ctx.fairy_kernel_manager
        self._kernel = kernel_manager.summon(buffer)
        
    @property
    def kernel(self) -> FairyKernel:
        return self._kernel
        
    @property
    def on_end(self) -> Event[BufferID]:
        return self._kernel.on_end
        

    @property
    def buffer(self) -> PytoyBuffer:
        return self.kernel.buffer

    @property
    def window(self) -> PytoyWindow:
        return self.kernel.window

    @property
    def selection(self) -> CharacterRange:
        return self.window.selection

    @property
    def llm_context(self):
        return self._kernel.llm_context


    def make_interaction(self, requester: InteractionRequesterProtocol, *, hooks: HooksForInteraction | None = None)-> LLMInteraction:
        request = requester(self.kernel)
        
        emitter = EventEmitter[Any]()
        def _revised_on_finish(sync_output: SyncOutput):
            try:
                request.on_success(sync_output)
            except Exception as e:
                print("Unhandled exception at `on_success`", e)
            emitter.fire(None)

        def _revised_on_error(exception: Exception):
            try:
                request.on_failure(exception)
            except Exception as e:
                print("Unhandled exception at `on_failure`", e)
            emitter.fire(None)
            
        def _main() -> SyncOutput:
            return completion(request.inputs, output_format=request.llm_output_format)
        
        # Maybe , using `ctx`, we are able realize DI.
        # We shoul give `event to `ThreadWorker` so that 
        # the deregister of `task` works.
        id_ = str(uuid.uuid1())
        task = ThreadWorker.run(main_func=_main,
                         on_finish=_revised_on_finish,
                         on_error=_revised_on_error)
        interaction =  LLMInteraction(id=id_, task=task, on_exit=emitter.event)
        self.kernel.register_interaction(interaction, hooks=hooks)
        return interaction

    

class EditDocumentRequester:
    def __init__(self):
        self._id = uuid.uuid4().hex[:8]


    @property
    def query_start(self) -> str: 
        return f"[pytoy-llm][{self._id}]>$>"

    @property
    def query_end(self) -> str: 
        return f">$>[pytoy-llm][{self._id}]"
        
    def __call__(self, kernel: FairyKernel) -> InteractionRequest:
        buffer = kernel.buffer
        selection = kernel.selection
        range_operator = buffer.range_operator

        text = buffer.get_text(selection)
        new_text = self.query_start + "\n" + text + "\n" + self.query_end
        target_selection = range_operator.replace_text(selection, new_text)
        document = buffer.content
        inputs = self._make_inputs(document)
        llm_output_format = "str"

        def on_success(output: SyncOutput) -> None:
            output = str(output)
            buffer = kernel.buffer
            start_range = buffer.range_operator.find_first(self.query_start, reverse=True)
            end_range = buffer.range_operator.find_first(self.query_end, reverse=True)
            if start_range is None or end_range is None:
                print("Request is gone...")
                return 
            cr = CharacterRange(start_range.start, end_range.end)
            buffer.range_operator.replace_text(cr, output)

        def on_error(exception: Exception) -> None:
            ThreadWorker.add_message(str(exception))
            EphemeralNotification().notify("LLM Error. See `:messages`.")


        return InteractionRequest(inputs=inputs, 
                                  llm_output_format=llm_output_format, 
                                  on_success=on_success,
                                  on_failure=on_error) 

        
    def _make_inputs(self, document: str) -> list[InputMessage]:
        prompt = self._make_prompt(document)
        return [InputMessage(role="system", content=prompt)]
    


    def _make_prompt(self, document: str) -> str:
        return dedent(f"""
        You are a professional editor integrated into a document editor.

        Your task:
        - Rewrite the text strictly between the markers:
          `{self.query_start}` and `{self.query_end}`

        Bigger Goal:
        - You and receiver collaboratively ake a nice document likeable for many people to understand. 
          
        Input tags:
        - <document>...</document>: the inside of <document> tag corresponds to the target document.

        Rules:
        - Output ONLY the rewritten text.
        - Do NOT include the markers themselves.
        - Do NOT output Input tags for the output.
        - Do NOT add explanations or commentary.
        - Keep the original intent.
        - You may rephrase, reorganize, or clarify the content.
        - Prefer similar length to the original unless clarity or correctness requires otherwise.
        - Select the appropriate language from the documents and query, either English or Japanese.
            - If Japanese is frequently used inside the document, the output is Japanese.
            - Otherwise, the output is English. 
        - Complete any incomplete sentences or bullet points.
        - If the user provides hints like "???", "..." or placeholders, replace them with the most plausible information.
        - If you need plceholders or ellipsis to balance correctness and conciseness, you "..." in bullet points.
        - Make the tone and politeness of output to over the documnet.
            - 日本語の場合、常態と敬体を文章中で統一せよ。
            - In English, standardize the writing style; do not mix different registers or sentence-ending styles.

        Your task: (Reminder)
        - Rewrite the text strictly between the markers:
          `{self.query_start}` and `{self.query_end}`

        <document>
        {document}
        </document>
        """).strip()
            