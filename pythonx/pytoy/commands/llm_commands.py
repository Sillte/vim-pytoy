from typing import Sequence, cast, Annotated, Literal, assert_never, ClassVar, TYPE_CHECKING
from pytoy.shared.ui.pytoy_window import PytoyWindow, WindowCreationParam
from pytoy.shared.ui.pytoy_buffer import PytoyBuffer
from pytoy.shared.command import App, Argument

if TYPE_CHECKING:
    from pytoy.tools.llm.document.voyages.presentation import DocumentVoyageUI


app = App()


@app.command("PytoyLLM")
def pytoy_llm(kind: Annotated[Literal["config", "create-dataset", "review", "edit"] | None, Argument()] = None):
    from pytoy.tools.llm.pytoy_fairy import PytoyFairy
    from pytoy.tools.llm import ReferenceDatasetConstructor
    from pytoy_llm import get_configuration_path
    from pytoy.tools.llm.document.reviewers.naive_reviewers  import NaiveReviewDocumentRequester
    from pytoy.tools.llm.document.editors.scoped_editors import ScopedEditDocumentRequester

    # If you would like to use ...
    #if ctx is None:
    #    ctx = GlobalPytoyContext.get()
    
    def _open_config():
        path = get_configuration_path()
        param = WindowCreationParam.for_split("vertical", try_reuse=True)
        PytoyWindow.open(path, param=param)

    def _make_reference_dataset():
        current_window = PytoyWindow.get_current()
        fairy = PytoyFairy(current_window.buffer)
        ReferenceDatasetConstructor(fairy).make_dataset()

    def _make_review():
        current_window = PytoyWindow.get_current()
        fairy = PytoyFairy(current_window.buffer)
        review_doc = NaiveReviewDocumentRequester(fairy)
        review_doc.make_interaction()
        
    def _edit_scope():
        current_window = PytoyWindow.get_current()
        current_buffer = current_window.buffer
        llm_fairy: PytoyFairy = PytoyFairy(buffer=current_buffer)

        # Edit operation.
        requester = ScopedEditDocumentRequester(llm_fairy)
        requester.make_interaction()

    match kind:
        case "config":
            _open_config()
        case "create-dataset":
            _make_reference_dataset()
        case "review":
            _make_review()
        case "edit":
            _edit_scope()
        case None:
            _edit_scope()
        case _:
            assert_never(kind)


class PytoyVoyageDocument:
    _voyage_ui: ClassVar["None | DocumentVoyageUI"]  = None  # noqa

    @classmethod
    def has_ui(cls) -> bool:
        return cls._voyage_ui is not None

    @classmethod
    def _ensure_ui(cls) -> "DocumentVoyageUI":
        if not cls._voyage_ui:
            cls.reset()
        if cls._voyage_ui is None:
            raise ValueError("DocumentVoyageUI cannot be obtained.")
        return cls._voyage_ui

    @classmethod
    def open_config(cls):
        from pytoy_llm import get_configuration_path
        path = get_configuration_path()
        param = WindowCreationParam.for_split("vertical", try_reuse=True)
        PytoyWindow.open(path, param=param)
        
    @classmethod
    def get_manuscript_buffer(cls) -> "PytoyBuffer | None":
        if not cls._voyage_ui:
            return None
        return cls._voyage_ui.pytoy_fairy.buffer
        
    @classmethod
    def reset(cls):
        from pytoy.shared.ui.pytoy_buffer import PytoyBuffer
        from pytoy.tools.llm.document.voyages.presentation import DocumentVoyageUI
        from pytoy.tools.llm.pytoy_fairy import PytoyFairy
        buffer = PytoyBuffer.get_current()
        if not buffer.is_file:
            raise ValueError("`manuscript buffer must be `FILE`.`")
        fairy = PytoyFairy(buffer)
        cls._voyage_ui = DocumentVoyageUI(fairy)
        return cls._voyage_ui
        
    @classmethod
    def evolve(cls):
        voyage_ui = cls._ensure_ui()
        from pytoy.tools.llm.document.voyages.presentation import DocumentVoyageUI
        voyage_ui.evolve()

    @classmethod
    def reflect(cls):
        voyage_ui = cls._ensure_ui()
        voyage_ui.reflect()

    @classmethod
    def check_state(cls):
        if not cls._voyage_ui:    
            raise ValueError("No `VoyageUI` yet.")
        from pytoy.tools.llm.document.voyages.presentation import DocumentVoyageUI
        voyage_ui = cls._ensure_ui()
        voyage_ui.check_state()


@app.command("PytoyVoyage")
def pytoy_voyage(kind: Annotated[Literal["config", "evolve", "reflect", "reset", "check-state"] | None, Argument()] = None):
    match kind:
        case "config":
            PytoyVoyageDocument.open_config()
        case "evolve":
            PytoyVoyageDocument.evolve()
        case "reflect":
            PytoyVoyageDocument.reflect()
        case "reset":
            PytoyVoyageDocument.reset()
        case "check-state":
            PytoyVoyageDocument.check_state()
        case None:
            if not PytoyVoyageDocument.has_ui():
                if PytoyBuffer.get_current().is_file:
                    return PytoyVoyageDocument.evolve()
            else:
                return PytoyVoyageDocument.reflect()
        case _:
            assert_never(kind)
