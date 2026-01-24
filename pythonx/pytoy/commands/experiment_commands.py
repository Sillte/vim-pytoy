from pytoy.infra.command.models import OptsArgument
import vim
from pytoy.ui import make_buffer
from pytoy.lib_tools.utils import get_current_directory
from pytoy.command import CommandManager

#from pytoy.lib_tools.terminal_backend.executor import TerminalExecutor
from pytoy.lib_tools.terminal_executor import TerminalExecutor, TerminalExecution, BufferRequest, TerminalExecutor, ExecutionRequest
from pytoy.lib_tools.terminal_runner.drivers import TerminalDriverManager, TerminalDriverProtocol, DEFAULT_SHELL_DRIVER_NAME
from pytoy.contexts.pytoy import GlobalPytoyContext

from pytoy.infra.command import OptsArgument

from pytoy.infra.sub_commands import (
    MainCommandSpec,
    SubCommandSpec,
    OptionSpec,
    SubCommandsHandler,
)

from pathlib import Path 

from pytoy.lib_tools.utils import get_current_directory
from pytoy.infra.command import Command
from pytoy.ui.pytoy_buffer import PytoyBuffer
from pytoy.ui.pytoy_buffer import PytoyBuffer, make_buffer


@CommandManager.register("GatherTextFiles")
class GatherTextFiles:
    def __init__(self) -> None:
        pass

    def __call__(self):
        from pytoy.tools.llm.materials.similar_documents import SimilarDocumentsSurveyer
        from pytoy.lib_tools.environment_manager import EnvironmentManager
        buffer = PytoyBuffer.get_current()
        if not buffer.is_file:
            raise ValueError("Target buffer is not file.")
        path = buffer.path
        workspace = EnvironmentManager().get_workspace(path, preference="system")
        workspace = workspace or path.parent
        result = SimilarDocumentsSurveyer(start_path=path, workspace=workspace).documents.text_result
        buffer = make_buffer("__docs__", "vertical")
        buffer.init_buffer()
        buffer.append(result)
    

