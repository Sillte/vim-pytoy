from __future__ import annotations

from typing import Annotated

from pytoy.shared.command import App, Option
from pytoy.shared.ui import PytoyBuffer
from pytoy.shared.ui.pytoy_window import PytoyWindow, PytoyWindowProvider, WindowCreationParam

app = App()


@app.command("LLMConfig")
def llm_config():
    from pytoy_llm import get_configuration_path

    path = get_configuration_path()
    param = WindowCreationParam.for_split("vertical", try_reuse=True)
    PytoyWindow.open(path, param=param)


@app.command("LLMScope")
def llm_scope():
    from pytoy.tools.llm.scoped_edit import DefaultScopedEditTaskMaker, ScopedEditAction

    current_window = PytoyWindow.get_current()
    current_buffer = current_window.buffer

    # Edit operation.
    task_maker = DefaultScopedEditTaskMaker.from_buffer(current_buffer)
    action = ScopedEditAction(task_maker, current_buffer)
    action.execute()


@app.command("LLMSend")
def llm_send(user_prompt: Annotated[str | None, Option()] = None):
    from pytoy.tool_session.llm import LLMSessionHandler, LLMSessionQuery

    handlers = LLMSessionHandler.query(query=LLMSessionQuery())
    if not handlers:
        raise ValueError("No LLMSessions started.")
    handler = handlers[0]

    if user_prompt is None:
        window = PytoyWindow.get_current()
        line_range = window.selected_line_range
        lines = window.buffer.get_lines(line_range)
        user_prompt = "\n".join(lines)
        window.buffer.range_operator.replace_lines(line_range, [])

    handler.make_progress(user_prompt)


@app.command("LLMDialog")
def llm_dialog():
    from pytoy.tool_session.llm import LLMSessionHandler, LLMSessionQuery

    handlers = LLMSessionHandler.query(query=LLMSessionQuery())
    if not handlers:
        handler = _construct_idea_chat()
    else:
        handler = handlers[0]
    current_window = PytoyWindow.get_current()
    buffer_source = handler.buffer_provider.buffer_source
    is_left = current_window.is_left()
    if is_left:
        param = WindowCreationParam.for_split(split_direction="vertical", try_reuse=True, anchor=current_window.impl)
    else:
        param = WindowCreationParam.for_in_place(try_reuse=True, anchor=current_window.impl)
    window = PytoyWindowProvider().open_window(buffer_source, param)
    window.focus()


@app.command("IdeaLLMChat")
def idea_llm_chat():
    _construct_idea_chat()
    llm_dialog()


def _construct_idea_chat():
    from pytoy.shared.storage import WorkspaceStorage
    from pytoy.tools.llm.idea_chat import IdeaChatHandler

    buffer = PytoyBuffer.get_current()
    if not buffer.path:
        raise ValueError("The current buffer is not file.")
    storage = WorkspaceStorage.from_path(buffer.path)
    path = storage.resolve_path("./idea-spaces/default")
    idea_chat_handler = IdeaChatHandler.from_any(path, workspace=storage.workspace)
    return idea_chat_handler.session_handler
