from typing import Any, Protocol
from pytoy.shared.lib.backend import can_use_vim


class VimCommandUserProtocol(Protocol):
    def command(self, cmd: str) -> None: ...

    def eval(self, expr: str) -> Any: ...


class VimCommandUserDummy(VimCommandUserProtocol):
    def command(self, name: str) -> Any: ...

    def eval(self, name: str) -> Any: ...


def get_vim_impl() -> VimCommandUserProtocol:
    if can_use_vim():
        import vim

        return vim
    else:
        return VimCommandUserDummy()
