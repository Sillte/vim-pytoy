from typing import Sequence
from pytoy.command import CommandManager
from pytoy.ui import make_buffer
from pytoy.ui.pytoy_window import PytoyWindow, WindowCreationParam
from pytoy.infra.command.models import OptsArgument
from pytoy.ui.pytoy_window import CharacterRange
from pytoy.ui.notifications import EphemeralNotification
from pytoy.contexts.pytoy import GlobalPytoyContext

from pytoy.infra.timertask import ThreadWorker
from textwrap import dedent

@CommandManager.register("PytoyLLM", range="")
class PytoyLLMCommand:

    def customlist(self, arg_lead: str, cmd_line: str, cursor_pos: int):
        """This is defined by `Command`."""
        candidates = ["config", "create-dataset"]
        valid_candidates = [elem for elem in candidates if elem.startswith(arg_lead)]
        if valid_candidates:
            return valid_candidates
        return candidates

    def _open_config(self):
        from pytoy_llm import get_configuration_path
        path = get_configuration_path()
        param = WindowCreationParam.for_split("vertical", try_reuse=True)
        PytoyWindow.open(path, param=param)

    def __call__(self, opts: OptsArgument):
        from pytoy.tools.llm import PytoyFairy, FairyKernelManager, EditDocumentRequester, ReferenceDatasetConstructor
        # Currently, `ctx` cannot be accepted as the argument of __call__.
        # Since this is a bug of `CommandManager`, 
        # I have to consider this later. 
        ctx: GlobalPytoyContext | None = None
        if opts.fargs and opts.fargs[0].strip() == "config":
            return self._open_config()

        if opts.fargs and opts.fargs[0].strip() == "create-dataset":
            return self._make_reference_dataset()

        if ctx is None:
            ctx = GlobalPytoyContext.get()

        current_window = PytoyWindow.get_current()
        current_buffer = current_window.buffer
        llm_fairy: PytoyFairy = PytoyFairy(buffer=current_buffer)

        # Edit operation.
        requester = EditDocumentRequester()
        llm_fairy.make_interaction(requester)
        
    def _make_reference_dataset(self, ):
        from pytoy.tools.llm import PytoyFairy,  ReferenceDatasetConstructor, FairyKernelManager
        operator = ReferenceDatasetConstructor()

        current_window = PytoyWindow.get_current()
        current_buffer = current_window.buffer
        llm_fairy: PytoyFairy = PytoyFairy(buffer=current_buffer)
        llm_fairy.make_operation(operator)
        
