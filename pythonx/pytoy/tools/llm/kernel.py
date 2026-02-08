import threading
import logging
from typing import Final, Callable, Any
from pytoy.contexts.pytoy import GlobalPytoyContext
from pytoy.infra.pytoy_configuration import PytoyConfiguration
from pytoy.tools.llm.models import LLMInteraction
from pytoy.tools.llm.references import ReferenceHandler
from pathlib import Path


class PytoyLLMContext:
    LLM_ROOT_KEY: Final[str] =  "vim_pytoy_llm"
    REFERENCE_FOLDER_KEY: Final[str] = "references"
    def __init__(self, workspace: Path | str, *, ctx: GlobalPytoyContext | None = None):
        if ctx is None:
            ctx = GlobalPytoyContext.get()
        workspace = Path(workspace).absolute()
        self._workspace = workspace
        self._configuration = PytoyConfiguration(workspace)
        self._lock = threading.Lock()
        self.ctx = ctx

        
    @property
    def workspace(self) -> Path:
        return self._workspace

    @property
    def root_folder(self) -> Path:
        """Return the root folder for data related to `PytoyLLM`.
        """
        return self._configuration.get_folder(self.LLM_ROOT_KEY, location="local")
    
    @property
    def logger(self) -> logging.Logger:
        logger = self._configuration.get_logger(location="global")
        if logger.level == logging.NOTSET:
            logger.setLevel(logging.INFO)
        return logger

    @property
    def reference_folder(self) -> Path:
        return self.root_folder / self.REFERENCE_FOLDER_KEY

    @property
    def reference_handler(self) -> ReferenceHandler:
        return ReferenceHandler(self.reference_folder)

    def dispose(self):
        pass


class FairyKernel:
    """Kernel は LLMContext を生成し、workspace 内で閉じた Interaction 管理を行う"""

    def __init__(self, workspace: Path | str):
        # workspace 固定で LLMContext を生成
        self._llm_context = PytoyLLMContext(workspace)
        self.interactions: dict[str, LLMInteraction] = {}
        self.disposables = []
        
    @property
    def llm_context(self) -> PytoyLLMContext:
        return self._llm_context
        
    @property
    def workspace(self) -> Path:
        return self.llm_context.workspace

    def register_interaction(self, interaction: LLMInteraction) -> None:
        id_ = interaction.id
        self.interactions[id_] = interaction
        interaction.on_exit.subscribe(lambda _: self.interactions.pop(id_, None))
        
    def add_disposable(self, disposable: Callable[[], Any]) -> None:
        self.disposables.append(disposable)

    def dispose(self):
        self._llm_context.dispose()
        self.interactions.clear()
        for item in self.disposables:
            item.dispose()

class FairyKernelManager:
    def __init__(self):
        # workspace_path -> Kernel
        self._kernels: dict[Path, FairyKernel] = {}
        self._lock = threading.Lock()

    def summon(self, workspace: Path) -> FairyKernel:
        workspace = workspace.absolute()

        with self._lock:
            # 親ディレクトリを辿って既存 Kernel を探す
            current = workspace
            while True:
                kernel = self._kernels.get(current)
                if kernel is not None:
                    return kernel

                if current.parent == current:
                    break
                current = current.parent

            # 見つからなければ新規作成
            kernel = FairyKernel(workspace)

            def wrapped_dispose():
                with self._lock:
                    self._kernels.pop(workspace, None)

            kernel.add_disposable(wrapped_dispose)
            self._kernels[workspace] = kernel
            return kernel

    def dispose_all(self):
        with self._lock:
            for kernel in list(self._kernels.values()):
                kernel.dispose()
            self._kernels.clear()