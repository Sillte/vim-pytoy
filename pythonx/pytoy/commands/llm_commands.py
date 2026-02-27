from typing import Sequence, cast
from pytoy.command import CommandManager
from pytoy.ui.pytoy_window import PytoyWindow, WindowCreationParam
from pytoy.ui.pytoy_buffer import PytoyBuffer
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
        from pytoy.tools.llm.document.editors.scoped_editors import ScopedEditDocumentRequester
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
        requester = ScopedEditDocumentRequester(llm_fairy)
        requester.make_interaction()
        
    def _make_reference_dataset(self):
        from pytoy.tools.llm import ReferenceDatasetConstructor
        from pytoy.tools.llm.pytoy_fairy import PytoyFairy
        current_window = PytoyWindow.get_current()
        fairy = PytoyFairy(current_window.buffer)
        ReferenceDatasetConstructor(fairy).make_dataset()


    def _make_review(self):
        from pytoy.tools.llm.document.reviewers.naive_reviewers  import NaiveReviewDocumentRequester
        from pytoy.tools.llm.pytoy_fairy import PytoyFairy
        current_window = PytoyWindow.get_current()
        fairy = PytoyFairy(current_window.buffer)
        review_doc = NaiveReviewDocumentRequester(fairy)
        review_doc.make_interaction()
        


@CommandManager.register("PytoyVoyage", range="")
class PytoyVoyageDocument:
    voyage_ui: "None | DocumentVoyageUI"  = None  # noqa type:ignore

    def customlist(self, arg_lead: str, cmd_line: str, cursor_pos: int):
        """This is defined by `Command`."""
        candidates = ["reflect", "evolve", "reset", "config"]
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
        if opts.fargs and opts.fargs[0].strip() == "config":
            return self._open_config()
        if opts.fargs and opts.fargs[0].strip() == "evolve":
            return self._evolve()
        if opts.fargs and opts.fargs[0].strip() == "reflect":
            return self._reflect()
        if opts.fargs and opts.fargs[0].strip() == "reset":
            return self._initialize_voyage_ui()
        
        if not opts.fargs:
            if self.voyage_ui is None:
                if PytoyBuffer.get_current().is_file:
                    return self._evolve()
            else:
                return self._reflect()
        raise ValueError(f"Invalid OptsArgument, {opts.fargs=}")
        
    @property
    def manuscript_buffer(self) -> "PytoyBuffer | None":
        if not self.voyage_ui:
            return None
        return self.voyage_ui.pytoy_fairy.buffer
        
    def _initialize_voyage_ui(self):
        from pytoy.ui.pytoy_buffer import PytoyBuffer
        from pytoy.tools.llm.document.voyages.presentation import DocumentVoyageUI
        from pytoy.tools.llm.pytoy_fairy import PytoyFairy
        buffer = PytoyBuffer.get_current()
        if not buffer.is_file:
            raise ValueError("`manuscript buffer must be `FILE`.`")
        self.buffer = buffer
        fairy = PytoyFairy(self.buffer)
        self.voyage_ui = DocumentVoyageUI(fairy)
        return self.voyage_ui
        
    def _evolve(self):
        if not self.voyage_ui:
            self._initialize_voyage_ui()
        if not self.voyage_ui:
            raise RuntimeError("Implmenetation Error.")
        from pytoy.tools.llm.document.voyages.presentation import DocumentVoyageUI
        self.voyage_ui.evolve()

    def _reflect(self):
        if not self.voyage_ui:
            self._initialize_voyage_ui()
        if not self.voyage_ui:
            raise RuntimeError("Implmenetation Error.")
        self.voyage_ui.reflect()

