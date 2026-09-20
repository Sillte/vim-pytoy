import logging
import uuid
from typing import Self, Sequence

from pytoy.shared.lib.text import CharacterRange
from pytoy.shared.pytoy_configuration import PytoyConfiguration
from pytoy.shared.timertask.thread_execution import add_log_message
from pytoy.shared.ui.notifications import EphemeralNotification
from pytoy.shared.ui.pytoy_buffer import PytoyBuffer
from pytoy.tool_execution.llm import LLMExecutionHooks, LLMExecutionRequest, LLMExecutor
from pytoy.tools.llm.scoped_edit.contract import ScopedEditLLMContract, ScopedEditTaskMakerProtocol
from pytoy.tools.llm.scoped_edit.task_specs.default_spec import DefaultScopedEditTaskMaker


class ScopedReconstructionContract:
    def __init__(self, query_start: str, query_end: str):
        self._query_start = query_start
        self._query_end = query_end

    @classmethod
    def from_id(cls, id_: str | None = None):
        if id_ is None:
            id_ = uuid.uuid4().hex[:8]
        query_start = f"[pytoy-llm][{id_}]>$>"
        query_end = f">$>[pytoy-llm][{id_}]"
        return cls(query_start, query_end)

    @property
    def rules(self) -> Sequence[str]:
        return [
            f"The model's modification authority is strictly limited to the text between `{self.query_start}` and `{self.query_end}`.",
            "The model MUST NOT modify, summarize, or reproduce any text outside this region.",
            f"The output MUST NOT include the markers `{self.query_start}` or `{self.query_end}`.",
            "The output MUST consist solely of the reconstructed content for the scoped region.",
            "When the markers are removed, the resulting document must read as a coherent whole.",
            "The scoped text may be a fragment of a larger document.",
            "If surrounding context exists, stylistic and structural conventions implied by it must be preserved.",
        ]

    @property
    def override_directive_rules(self) -> Sequence[str]:
        return [
            "**Directive Handling:**",
            "- If the first non-empty line inside the markers starts with one or more `@`, treat that line as a directive and DO NOT include it in the output.",
            "- The number of consecutive `@` characters defines its strength:",
            "    - @: weak directive (lower priority than the other rules.).",
            "    - @@, @@@, @@@@ or more: absolute directive (redefines the reconstruction objective and strategy within the scoped boundary).",
            "- Directives may redefine task intent, tone, or structural goals, but they MUST NOT violate the scoped boundary contract.",
            "- Directives cannot authorize modification of text outside the markers.",
            "- The directive line MUST be completely removed before reconstruction begins.",
        ]

    @property
    def llm_contract(self) -> ScopedEditLLMContract:
        return ScopedEditLLMContract(rules=self.rules, override_rules=self.override_directive_rules)

    def insert_markers(self, buffer: PytoyBuffer, selection: CharacterRange) -> None:
        text = buffer.get_text(selection)
        new_text = f"{self.query_start}\n{text}\n{self.query_end}"
        buffer.range_operator.replace_text(selection, new_text)

    def revert_markers(self, buffer: PytoyBuffer) -> None:
        start_range = buffer.range_operator.find_first(self.query_start)
        if start_range:
            buffer.range_operator.replace_text(start_range, "")
        end_range = buffer.range_operator.find_first(self.query_end)
        if end_range:
            buffer.range_operator.replace_text(end_range, "")

    def override_target(self, buffer: PytoyBuffer, content: str) -> None:
        """Based on the contract with LLM,  `content` should be the text within markers.
        Unfortunately, if content includes `markers`, then the inside of markers becomes the `target`.
        """
        content = self._recover_edit_target(content)
        start_range = buffer.range_operator.find_first(self.query_start)
        end_range = buffer.range_operator.find_first(self.query_end)

        if not start_range or not end_range:
            EphemeralNotification().notify("Request is gone, so no operations from `ScopedEdit`.")
            return
        cr = CharacterRange(start_range.start, end_range.end)
        buffer.range_operator.replace_text(cr, content)

    def _recover_edit_target(self, content: str) -> str:
        lines = content.replace("\r\n", "\n").split("\n")
        s_index, e_index = None, None
        for i, line in enumerate(lines):
            if line.find(self.query_start.strip()) == 0:
                s_index = i
                break
        for i in reversed(range(len(lines))):
            line = lines[i]
            if line.find(self.query_end.strip()) == 0:
                e_index = i
                break
        if s_index is not None and e_index is not None and s_index < e_index:
            output_in_concern = "\n".join(lines[s_index + 1 : e_index])
        else:
            output_in_concern = content
        return output_in_concern

    @property
    def query_start(self) -> str:
        return self._query_start

    @property
    def query_end(self) -> str:
        return self._query_end


class ScopedEditAction:
    def __init__(
        self, buffer: PytoyBuffer, character_range: CharacterRange, task_maker: ScopedEditTaskMakerProtocol
    ) -> None:
        self._buffer = buffer
        self._character_range = character_range
        self._task_maker = task_maker

        self._id = uuid.uuid4().hex[:8]
        self.scoped_edit_contract = ScopedReconstructionContract.from_id(self._id)

    @classmethod
    def from_default(cls, buffer: PytoyBuffer | None = None) -> Self:
        buffer = buffer or PytoyBuffer.get_current()
        if window := buffer.window:
            character_range = window.selection
        else:
            raise ValueError(f"Buffer does not have `Selection`. {buffer=}")
        task_maker = DefaultScopedEditTaskMaker()
        return cls(buffer=buffer, character_range=character_range, task_maker=task_maker)

    def execute(self) -> None:
        buffer = self._buffer
        if buffer.window is None:
            raise ValueError("Cannot execute because Selection cannot be obtained.")
        self.scoped_edit_contract.insert_markers(buffer, self._character_range)

        document = buffer.content
        llm_contract = self.scoped_edit_contract.llm_contract
        task_spec = self._task_maker.make_task(document, contract=llm_contract)

        logger = PytoyConfiguration().get_logger(location="global", level=logging.INFO)
        logger.info("Preparation of `ScopeEdit`.")

        kind = "ScopedEditor"
        llm_request = LLMExecutionRequest(task_spec=task_spec, input=document, logger=logger, kind=kind)
        executor = LLMExecutor()
        if not executor.can_execute(kind=kind):
            raise RuntimeError("Already another request is executing for ScopedEditor.")
        hooks = LLMExecutionHooks.from_any(
            on_output=lambda output: self._apply_output(buffer, output),
            on_exception=lambda exc: self._handle_error(buffer, exc),
        )
        executor.execute(llm_request, hooks=hooks)

    def _apply_output(self, buffer: PytoyBuffer, output: str) -> None:
        output_str = str(output)
        self.scoped_edit_contract.override_target(buffer, output_str)

    def _handle_error(self, buffer: PytoyBuffer, exception: Exception) -> None:
        self.scoped_edit_contract.revert_markers(buffer)
        add_log_message(str(exception))
        EphemeralNotification().notify("LLM Error at `ScopedEdit`. See `:messages`.")
