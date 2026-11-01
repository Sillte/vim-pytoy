from pathlib import Path
from typing import Protocol, assert_never

from pytoy.devtools.dev_rebooter.models import RebootInfo
from pytoy.shared.lib.backend import BackendEnum, get_backend_enum


class RebooterWithInfoProtocol(Protocol):
    def prepare(self) -> RebootInfo: ...

    def reboot(self, reboot_info: RebootInfo) -> None: ...


def create_rebooter_for_current_backend(root_folder: Path, *, minimal: bool = False) -> RebooterWithInfoProtocol:
    from pytoy.devtools.dev_rebooter.impls.dummy import DummyRebooter
    from pytoy.devtools.dev_rebooter.impls.nvim import NVimRebooter
    from pytoy.devtools.dev_rebooter.impls.vim import VimRebooter
    from pytoy.devtools.dev_rebooter.impls.vscode import VSCodeRebooter

    backend = get_backend_enum()
    match backend:
        case BackendEnum.VIM:
            return VimRebooter(root_folder, minimal=minimal)
        case BackendEnum.NVIM:
            return NVimRebooter(root_folder, minimal=minimal)
        case BackendEnum.VSCODE:
            return VSCodeRebooter(root_folder, minimal=minimal)
        case BackendEnum.DUMMY:
            return DummyRebooter(root_folder, minimal=minimal)
        case _:
            assert_never(backend)
