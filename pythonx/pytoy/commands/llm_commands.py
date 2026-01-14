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
    def _open_config(self):
        from pytoy_llm import get_configuration_path
        path = get_configuration_path()
        param = WindowCreationParam.for_split("vertical", try_reuse=True)
        PytoyWindow.open(path, param=param)

    def __call__(self, opts: OptsArgument):
        from pytoy.tools.llm import PytoyFairy, FairyKernelManager, EditDocumentRequester
        # Currently, `ctx` cannot be accepted as the argument of __call__.
        # Since this is a bug of `CommandManager`, 
        # I have to consider this later. 
        ctx: GlobalPytoyContext | None = None
        if opts.fargs and opts.fargs[0].strip() == "config":
            return self._open_config()
        if ctx is None:
            ctx = GlobalPytoyContext.get()

        current_window = PytoyWindow.get_current()
        current_buffer = current_window.buffer
        llm_fairy: PytoyFairy = PytoyFairy(buffer=current_buffer)


        # Edit operation.
        requester = EditDocumentRequester()
        llm_fairy.make_interaction(requester)
    
