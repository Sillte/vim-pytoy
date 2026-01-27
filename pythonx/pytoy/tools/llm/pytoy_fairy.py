from pytoy.contexts.pytoy import GlobalPytoyContext
from pytoy.tools.llm.kernel import FairyKernel
from pytoy.ui.pytoy_buffer import PytoyBuffer
from pytoy.ui.pytoy_window import CharacterRange, PytoyWindow


from pathlib import Path


class PytoyFairy:
    def __init__(self, buffer: PytoyBuffer, workspace: str | Path | None = None,
                  ctx: GlobalPytoyContext | None = None):
        if not buffer.is_file:
            raise ValueError("Only file is accepted.")
        if ctx is None:
            ctx = GlobalPytoyContext.get()
        kernel_manager = ctx.fairy_kernel_manager
        if workspace is None:
            workspace = buffer.path.parent
        else:
            workspace = Path(workspace)
        self._kernel = kernel_manager.summon(workspace)
        self._buffer = buffer

    @property
    def kernel(self) -> FairyKernel:
        return self._kernel

    @property
    def buffer(self) -> PytoyBuffer:
        return self._buffer

    @property
    def window(self) -> PytoyWindow | None:
        return self.buffer.window

    @property
    def selection(self) -> CharacterRange:
        if not self.window:
            raise ValueError(" No window for buffer, but `selection` is called.")
        return self.window.selection

    @property
    def llm_context(self):
        return self._kernel.llm_context