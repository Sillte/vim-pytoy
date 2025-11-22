from pytoy.lib_tools.buffer_executor.protocol import BufferJobProtocol
from pytoy.ui.ui_enum import get_ui_enum, UIEnum
from pytoy.ui import PytoyBuffer


def make_buffer_job(
    name: str,
    stdout: PytoyBuffer | None = None,
    stderr: PytoyBuffer | None = None,
) -> BufferJobProtocol:
    """
    Factory function to create a BufferJobProtocol implementation based on UIEnum.

    Args:
        name (str): The name of the buffer job.
        stdout (PytoyBuffer | None): Buffer for stdout.
        stderr (PytoyBuffer | None): Buffer for stderr.
        env: Environment variables.
        cwd: Working directory.
    Returns:
        BufferJobProtocol: An instance of the appropriate buffer job class.
    """
    ui_enum = get_ui_enum()
    if ui_enum == UIEnum.VIM:
        from pytoy.lib_tools.buffer_executor.impl_vim import VimBufferJob

        return VimBufferJob(name, stdout, stderr)
    elif ui_enum in {UIEnum.NVIM, UIEnum.VSCODE}:
        from pytoy.lib_tools.buffer_executor.impl_nvim import NVimBufferJob

        return NVimBufferJob(name, stdout, stderr)
    else:
        assert False, "Implementation Error"


if __name__ == "__main__":
    pass
