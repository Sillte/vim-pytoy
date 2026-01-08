from pathlib import Path
from typing import Callable, Mapping, Any

from pytoy.lib_tools.buffer_executor.protocol import BufferJobProtocol
from pytoy.ui.ui_enum import get_ui_enum, UIEnum
from pytoy.ui import PytoyBuffer


class BufferJob:
    """Façade class for creating and managing buffer jobs across different UIs."""
    
    def __init__(
        self,
        impl: BufferJobProtocol | None = None,
        *,
        name: str | None = None,
        stdout: PytoyBuffer | None = None,
        stderr: PytoyBuffer | None = None,
    ):
        if impl is None:
            if name is None:
                raise ValueError("Either impl or name must be provided")
            impl = _make_buffer_job_impl(name, stdout, stderr)
        self._impl = impl

    @property
    def impl(self) -> BufferJobProtocol:
        return self._impl

    @property
    def name(self) -> str:
        return self._impl.name

    @property
    def cwd(self) -> Path | str | None:
        return self._impl.cwd

    @property
    def stdout(self) -> PytoyBuffer | None:
        return self._impl.stdout

    @property
    def stderr(self) -> PytoyBuffer | None:
        return self._impl.stderr

    @property
    def is_running(self) -> bool:
        return self._impl.is_running

    def job_start(
        self,
        command: str,
        on_start_callable: Callable[[], Mapping] | None = None,
        on_closed_callable: Callable[[BufferJobProtocol], Any] | None = None,
        cwd: Path | str | None = None,
        env: Mapping[str, str] | None = None,
    ) -> None:
        """Start a job with the given command."""
        if on_start_callable is None:
            on_start_callable = lambda: {}
        if on_closed_callable is None:
            on_closed_callable = lambda _: None
        
        self._impl.job_start(command, on_start_callable, on_closed_callable, cwd, env)

    def stop(self) -> None:
        """Stop the running job."""
        self._impl.stop()


def _make_buffer_job_impl(
    name: str,
    stdout: PytoyBuffer | None = None,
    stderr: PytoyBuffer | None = None,
) -> BufferJobProtocol:
    """Factory function to create a BufferJobProtocol implementation based on UIEnum."""
    ui_enum = get_ui_enum()
    if ui_enum == UIEnum.VIM:
        from pytoy.lib_tools.buffer_executor.impls.vim import VimBufferJob
        return VimBufferJob(name, stdout, stderr)
    elif ui_enum in {UIEnum.NVIM, UIEnum.VSCODE}:
        from pytoy.lib_tools.buffer_executor.impls.nvim import NVimBufferJob
        return NVimBufferJob(name, stdout, stderr)
    else:
        raise RuntimeError(f"Unsupported UI: {ui_enum}")


# Backward compatibility: keep the make_buffer_job function
def make_buffer_job(
    name: str,
    stdout: PytoyBuffer | None = None,
    stderr: PytoyBuffer | None = None,
) -> BufferJobProtocol:
    """
    Factory function to create a BufferJobProtocol implementation based on UIEnum.
    
    Deprecated: Use BufferJob class instead.
    """
    return _make_buffer_job_impl(name, stdout, stderr)


if __name__ == "__main__":
    pass
