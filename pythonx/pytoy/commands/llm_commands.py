from typing import Sequence
from pytoy.command import CommandManager
from pytoy.tools.llm.edit_document import EditDocumentRequester
from pytoy.tools.llm.pytoy_fairy import PytoyFairy
from pytoy.ui.pytoy_window import PytoyWindow, WindowCreationParam
from pytoy.infra.command.models import OptsArgument
from pytoy.contexts.pytoy import GlobalPytoyContext

from textwrap import dedent

@CommandManager.register("PytoyLLM", range="")
class PytoyLLMCommand:

    def customlist(self, arg_lead: str, cmd_line: str, cursor_pos: int):
        """This is defined by `Command`."""
        candidates = ["config", "create-dataset", "review"]
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
        from pytoy.tools.llm.pytoy_fairy import PytoyFairy
        # Currently, `ctx` cannot be accepted as the argument of __call__.
        # Since this is a bug of `CommandManager`, 
        # I have to consider this later. 
        #ctx: GlobalPytoyContext | None = None
        #if ctx is None:
        #    ctx = GlobalPytoyContext.get()

        if opts.fargs and opts.fargs[0].strip() == "config":
            return self._open_config()

        if opts.fargs and opts.fargs[0].strip() == "create-dataset":
            return self._make_reference_dataset()

        if opts.fargs and opts.fargs[0].strip() == "review":
            return self._make_review()

        current_window = PytoyWindow.get_current()
        current_buffer = current_window.buffer
        llm_fairy: PytoyFairy = PytoyFairy(buffer=current_buffer)

        # Edit operation.
        requester = EditDocumentRequester(llm_fairy)
        requester.make_interaction()
        
    def _make_reference_dataset(self):
        from pytoy.tools.llm import ReferenceDatasetConstructor
        current_window = PytoyWindow.get_current()
        fairy = PytoyFairy(current_window.buffer)
        ReferenceDatasetConstructor(fairy).make_dataset()


    def _make_review(self):
        from pytoy.tools.llm.review_document  import ReviewDocument
        current_window = PytoyWindow.get_current()
        fairy = PytoyFairy(current_window.buffer)
        review_doc = ReviewDocument(fairy)
        review_doc.make_interaction()
        
