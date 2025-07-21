from pytoy.tools.terminal_applications.ipyton_application import IPythonApplication  # noqa
from pytoy.ui.pytoy_buffer import PytoyBuffer
from pytoy.lib_tools.terminal_backend.application import AppManager
from pytoy.lib_tools.terminal_backend.application import DEFAULT_SHELL_APPLICATION_NAME


def get_default_app_name(buffer: PytoyBuffer | None=None) -> str:
    if buffer is None:
        buffer = PytoyBuffer.get_current()
    path = buffer.path
    if path and path.suffix == ".py":
        if AppManager.is_registered("ipython"):
            return "ipython"
    return DEFAULT_SHELL_APPLICATION_NAME
