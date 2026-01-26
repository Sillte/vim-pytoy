import uuid
import time
import threading
from pathlib import Path
from textwrap import dedent
from dataclasses import dataclass, field
from pytoy.infra.core.models import Event, EventEmitter
from pytoy.tools.llm.models import HooksForInteraction
from pytoy.ui.pytoy_buffer import PytoyBuffer, BufferID, BufferEvents
from pytoy.ui.pytoy_window import PytoyWindow, CharacterRange
from typing import Any, Callable, Protocol, Sequence, Callable, Final
from pydantic import BaseModel 
from pytoy_llm.models import SyncOutput, SyncOutputFormatStr, SyncOutputFormat
from pytoy.contexts.pytoy import GlobalPytoyContext
from pytoy.infra.timertask import ThreadWorker
from pytoy.infra.timertask.thread_executor import ThreadExecutor, ThreadExecutionRequest
from pytoy.lib_tools.pytoy_configuration import PytoyConfiguration

from pytoy_llm import completion
from pytoy_llm.models import InputMessage
from pytoy.ui.notifications import EphemeralNotification

from pytoy.tools.llm.references import ReferenceHandler, ReferenceSectionWriter, ReferenceCollector

from pytoy_llm.materials.composers.models import LLMTask
from pytoy_llm.materials.composers import TaskPromptComposer



class PytoyLLMContext:
    LLM_ROOT_KEY: Final[str] =  "vim_pytoy_llm"
    REFERENCE_FOLDER_KEY: Final[str] = "references"
    def __init__(self, buffer: PytoyBuffer, *, ctx: GlobalPytoyContext):
        self._configuration =  PytoyConfiguration(buffer.path.parent)
        self._lock = threading.Lock
        
    @property
    def root_folder(self) -> Path:
        """Return the root folder for data related to `PytoyLLM`.
        """
        return self._configuration.get_folder(self.LLM_ROOT_KEY, location="local")

    @property
    def reference_folder(self) -> Path: 
        return self.root_folder / self.REFERENCE_FOLDER_KEY
    
    @property
    def reference_handler(self) -> ReferenceHandler:
        return ReferenceHandler(self.reference_folder)
    
    def dispose(self):
        pass

    
@dataclass
class InteractionRequest:
    inputs: list[InputMessage]
    llm_output_format: SyncOutputFormat | SyncOutputFormatStr | type[BaseModel]
    on_success: Callable[[SyncOutput], None]
    on_failure: Callable[[Exception], None]
    hooks: HooksForInteraction | None = None
    

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
        
        self.buffer.on_wiped.subscribe(self.dispose)
        disposables = []
        disposables.append(self.buffer.events.on_pre_buf.subscribe(self.pre_save))
        self.disposables = disposables

                 
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
    

    def register_interaction(self, interaction: LLMInteraction):
        id_ = interaction.id
        self.interactions[id_] = interaction
        interaction.on_exit.subscribe(lambda _: self.interactions.pop(id_))
    
    def dispose(self, buffer_id: BufferID):
        # Release the resource, acquired by this class.
        # TODO : invoke llm_context.dispose()
        for item in self.disposables:
            item.dispose()
    
    def pre_save(self, _: BufferID) -> None:
        # BufPre in the domain of VIM. 
        # This is justified, since the simulutaneous interactions a few at most. 
        for interaction in self.interactions.values():
            hooks = interaction.hooks
            if hooks and hooks.pre_save:
                hooks.pre_save(self.buffer)

class FairyKernelManager:
    def __init__(self,):
        self._kernels: dict[BufferID, FairyKernel] = dict()
        
    def summon(self, buffer: PytoyBuffer,  *, ctx:GlobalPytoyContext | None = None) -> FairyKernel:
        if ctx is None:
            ctx = GlobalPytoyContext.get()
        # Currently, only 1 Fairy kernel allowed.
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
        
class OperatorProtocol(Protocol):
    """Do something synchronously. 
    """
    def __call__(self,  kernel: FairyKernel) -> None:
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
    
    def make_operation(self, operator: OperatorProtocol) -> Any:
        """One time operation, synchronously.
        """
        return operator(self.kernel)


    def make_interaction(self, requester: InteractionRequesterProtocol)-> LLMInteraction:
        request = requester(self.kernel)
        
        interaction_end_emitter = EventEmitter[Any]()
        def _revised_on_finish(sync_output: SyncOutput):
            try:
                request.on_success(sync_output)
            except Exception as e:
                print("Unhandled exception at `on_success`", e)
            interaction_end_emitter.fire(None)

        def _revised_on_error(exception: Exception):
            try:
                request.on_failure(exception)
            except Exception as e:
                print("Unhandled exception at `on_failure`", e)
            interaction_end_emitter.fire(None)
            
        def _main(_) -> SyncOutput:
            return completion(request.inputs, output_format=request.llm_output_format)
        
        execution_request = ThreadExecutionRequest(main_func=_main, on_finish=_revised_on_finish, on_error=_revised_on_error)
        execution = ThreadExecutor().execute(execution_request)
        id_ = str(uuid.uuid1())

        interaction = LLMInteraction(id=id_, task=execution, on_exit=interaction_end_emitter.event, hooks=request.hooks)
        self.kernel.register_interaction(interaction)
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
        range_operator.replace_text(selection, new_text)
        document = buffer.content
        inputs = self._make_inputs(document, kernel)

        
        def _revert_ranges(buffer: PytoyBuffer):
            start_range = buffer.range_operator.find_first(self.query_start, reverse=False)
            if start_range:
                buffer.range_operator.replace_text(start_range, "")
            end_range = buffer.range_operator.find_first(self.query_end, reverse=False)
            if end_range:
                buffer.range_operator.replace_text(end_range, "")

        def on_success(output: SyncOutput) -> None:
            output = str(output)
            buffer = kernel.buffer
            start_range = buffer.range_operator.find_first(self.query_start, reverse=False)
            end_range = buffer.range_operator.find_first(self.query_end, reverse=False)
            if start_range is None or end_range is None:
                EphemeralNotification().notify("Request is gone, so no operations.")
                return 
            cr = CharacterRange(start_range.start, end_range.end)
            buffer.range_operator.replace_text(cr, output)

        def on_error(exception: Exception) -> None:
            _revert_ranges(kernel.buffer)
            ThreadWorker.add_message(str(exception))
            EphemeralNotification().notify("LLM Error. See `:messages`.")
            
        hooks = HooksForInteraction(pre_save=_revert_ranges) 

        llm_output_format = "str"
        return InteractionRequest(inputs=inputs, 
                                  llm_output_format=llm_output_format, 
                                  on_success=on_success,
                                  on_failure=on_error,
                                  hooks=hooks) 

       
    def _make_inputs(self, document: str, kernel: FairyKernel) -> list[InputMessage]:
        intent = (
            " Revise the text strictly between the markers:\n"
            f"`{self.query_start}` and `{self.query_end}`.\n"
            "as a part of <document>.\n"
            "All content outside the markers must be treated as read-only context.\n"
            "============================================================\n"
            "LOCAL INSTRUCTION OVERRIDE\n"
            "============================================================\n"
            "Immediately adjacent to the markers, there MAY be additional\n"
            "instructions written by the user.\n\n"
            "- These instructions, if present, are located:\n"
              f"- Immediately AFTER `{self.query_start}`, or\n"
              f"- Immediately BEFORE `{self.query_end}`.\n"
            "If such instructions exist:\n"
            "- You MUST follow them.\n"
            "- They take PRIORITY over all other instructions,\n"
              "except for the absolute output constraints.\n"
            "============================================================\n"
            "LANGUAGE SELECTION (MANDATORY)\n"
            "============================================================\n"

            "Before rewriting, you MUST do the following internally:\n"
            "1. Determine the dominant language of the document\n"
               "(Japanese, English, or Python).\n"
            "2. Choose ONLY ONE instruction set below that matches the dominant language.\n"
            "3. COMPLETELY IGNORE the instruction set of the other languages.\n"
            "Do NOT output this decision or any analysis.\n"
            "============================================================\n"
            "ENGLISH INSTRUCTIONS\n"
            "============================================================\n"
            "Use these instructions ONLY if the dominant language is English.\n"
            "Style and consistency:\n"
            "- Strictly match the tone, formality, and writing style of the surrounding document.\n"
            "- Match sentence length, paragraph structure, and level of explicitness.\n"
            "- Do NOT introduce new metaphors, idioms, or stylistic flair.\n"
            "- Do NOT make the text sound more “helpful” or “polite” than the rest of the document.\n"
            "Editorial rules:\n"
            "- You may rephrase, reorganize, or clarify for readability.\n"
            "- Complete incomplete sentences or bullet points when necessary.\n"
            "- Replace placeholders such as `...`, `???`, or unfinished items\n"
              "with the most plausible content.\n"
            "- Maintain technical accuracy and domain-appropriate vocabulary.\n"
            "- Maintain styles such as itemization or quotes.\n"

            "============================================================\n"
            "JAPANESE INSTRUCTIONS\n"
            "============================================================\n"

            "Use these instructions ONLY if the dominant language is Japanese.\n"

            "文体・語調の厳守（最重要）:\n"
            "- 文書全体で使われている文体を**厳密に模倣**せよ。\n"
            "- 文末表現（だ／である／です・ます調）を**完全に統一**せよ。\n"
            "- 語彙の硬さ（技術文・説明文・口語）を文書全体に合わせよ。\n"
            "- 編集箇所以外と連続して読んだときに違和感が一切ないことを最優先とせよ。\n"
            "- 箇条書き、引用などのスタイルを保持せよ\n"

            "編集ルール:\n"
            "- 内容の意図を変更してはならない。\n"
            "- 必要な場合のみ、表現の整理・簡潔化・明確化を行ってよい。\n"
            "- 不完全な文や箇条書きは、文脈から自然に補完せよ。\n"
            "- `...` や `???` などのプレースホルダは、最も自然な内容で置き換えよ。\n"
            "- 新しい語調・比喩・言い回しを**新規に導入してはならない**。\n"
            "============================================================\n"
            "PYTHON INSTRUCTIONS\n"
            "============================================================\n"
            "Use these instructions ONLY if the dominant language is Python.\n"

            "Style and consistency (CRITICAL):\n"
            "- Strictly preserve the coding style of the surrounding code.\n"
            "- Match indentation, line breaks, naming conventions, and formatting.\n"
            "- Follow the existing paradigm (procedural, functional, OOP) exactly.\n"
            "- Do NOT introduce new abstractions, patterns, or helper functions\n"
            "  unless they are clearly implied by the surrounding code.\n"

            "Code editing rules:\n"
            "- Do NOT change the external behavior or public interface.\n"
            "- Maintain semantic equivalence unless the context clearly requires correction.\n"
            "- Complete incomplete code fragments if necessary, using the most plausible intent.\n"
            "- Replace placeholders such as `...`, `pass`, or unfinished blocks\n"
            "  with contextually appropriate implementations.\n"
            "- Preserve comments unless they are incorrect; match their tone and verbosity.\n"

            "Technical constraints:\n"
            "- Ensure the code remains valid Python.\n"
            "- Do NOT optimize, refactor, or modernize unless explicitly instructed.\n"
            "- If refactoring or modernization is required to resolve an issue, do NOT modify the code directly.\n"
            "  Instead, leave a comment at the relevant location describing the concern. \n"
            "- If the logic appears incorrect or ambiguous, preserve the original code and annotate the issue using comments only. \n"
            "- Avoid adding defensive checks, logging, or documentation beyond what exists.\n"
            )

        output_description = ("You are revising the document or code. \n"
                              "Output the most appropriate part of senetences\n"
                              "as the completed document.\n"
                              )

        output_spec = (f"The text between `{self.query_start}` and `{self.query_end}`.")
        
        llm_task = LLMTask(name="Your sole goal is to produce the final rewritten content that can be pasted back verbatim into the original document.",
                       intent=intent,
                       rules= [
                           "Rewrite ONLY the content between the markers.",
                            "Output ONLY the rewritten text.",
                            "Do NOT include the markers themselves.",
                            "Do NOT add explanations, commentary, or meta text.",
                            "Do NOT output tags such as <document>.",
                            "Preserve the original intent and meaning. ",
                            "Prefer similar length unless clarity or correctness requires change.",
                            "The rewritten text must read naturally when placed back into the document.",
                       ],
                       role="You are a professional editor who revise the technical documents.",
                       output_description=output_description,
                       output_spec=output_spec,
                       )

        reference_handler = kernel.llm_context.reference_handler
        if reference_handler.exist_reference:
            ref_section_writer = reference_handler.section_writer
            section_data = ref_section_writer.make_section_data()
            section_usage = ref_section_writer.make_section_usage()
            composer = TaskPromptComposer(llm_task, [section_usage], [section_data])
        else:
            composer = TaskPromptComposer(llm_task, [], [])
        messages = composer.compose_messages(user_prompt=self._make_user_prompt(document))
        return list(messages)

    
    def _make_user_prompt(self, document: str) -> str:
        return ("Here is the document:\n"
                "<document>\n"
                f"{document}\n"
                "</document>\n"
        )
            

class ReferenceDatasetConstructor(OperatorProtocol):
    def __call__(self, fairy_kernel: FairyKernel) -> Any:
        # First, construct the entire dataset.
        collector = fairy_kernel.llm_context.reference_handler.collector
        # [TODO]: In a remote context, we should ensure the `root_folder` is valid.
        # It is better to introduce `filepath` for `PytoyBuffer`.
        root_folder = fairy_kernel.buffer.path.parent
        if not root_folder:
            print("No root folder found for the buffer. Cannot collect references.")
            return
        print(f"{root_folder=} in `ReferenceDatasetConstructor`.")
        collector.collect_all(root_folder)
        
