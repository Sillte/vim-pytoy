from typing import Annotated, Literal, assert_never

from pytoy.shared.command import App, Argument
from pytoy.shared.ui.pytoy_window import PytoyWindow, WindowCreationParam

app = App()


@app.command("PytoyLLM")
def pytoy_llm(kind: Annotated[Literal["config", "edit"] | None, Argument()] = None):
    from pytoy_llm import get_configuration_path

    from pytoy.tools.llm.scoped_edit.action import ScopedEditAction

    def _open_config():
        path = get_configuration_path()
        param = WindowCreationParam.for_split("vertical", try_reuse=True)
        PytoyWindow.open(path, param=param)

    def _edit_scope():
        current_window = PytoyWindow.get_current()
        current_buffer = current_window.buffer

        # Edit operation.
        ScopedEditAction.from_default(current_buffer).execute()

    match kind:
        case "config":
            _open_config()
        case "edit":
            _edit_scope()
        case None:
            _edit_scope()
        case _:
            assert_never(kind)


# Comment
# This package provides Pytoy LLM integration.
# It supports configuration management and scoped document editing.
# The package exposes commands for opening the configuration and editing
# the current document scope.
# ....
# ....
