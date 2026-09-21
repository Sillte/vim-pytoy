from typing import Annotated

from pytoy.shared.command import App, Option
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
        raise ValueError("No LLMSessions started.")
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


@app.command("IdeaLLMChatExperiment")
def idea_llm_chat():
    from pytoy.tool_execution.execution_environment import EnvironmentManager
    from pytoy.tools.llm.idea_chat import IdeaChatHandler

    manager = EnvironmentManager()
    workspace = manager.find_workspace(__file__)
    if workspace is None:
        raise ValueError("Apt folder is not found")
    folder = workspace / "mybag" / "IdeaLLMDialog"
    IdeaChatHandler.from_any(folder)
    llm_dialog()
    # buffer = handler.provide_buffer()
    # buffer.show()

    # current_window = PytoyWindow.get_current()
    # line_range = current_window.selected_line_range
    # lines = current_window.buffer.get_current().get_lines(line_range)
    # user_prompt = "\n".join(lines)
    # handler.make_progress(user_prompt)
