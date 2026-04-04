from typing import Callable
from pytoy.shared.lib.backend import BackendEnum, get_backend_enum

from pytoy.shared.command.app.protocol import CommandApplicationProtocol, GroupApplicationProtocol
from pytoy.shared.command.app.protocol import InvocationSpec


def get_application_impl() -> CommandApplicationProtocol:
    backend_enum = get_backend_enum()
    if backend_enum in {BackendEnum.VIM, BackendEnum.NVIM, BackendEnum.VSCODE}:
        from pytoy.shared.command.app.impls.vim import CommandApplicationVim

        return CommandApplicationVim()
    else:
        from pytoy.shared.command.app.impls.dummy import CommandApplicationDummy

        return CommandApplicationDummy()


def get_group_impl(name: str) -> GroupApplicationProtocol:
    backend_enum = get_backend_enum()
    if backend_enum in {BackendEnum.VIM, BackendEnum.NVIM, BackendEnum.VSCODE}:
        from pytoy.shared.command.app.impls.vim import GroupApplicationVim

        return GroupApplicationVim(name)
    else:
        from pytoy.shared.command.app.impls.dummy import CommandGroupDummy

        return CommandGroupDummy(name)


class CommandApplication:
    def __init__(self, impl: CommandApplicationProtocol | None = None) -> None:
        impl = impl or get_application_impl()
        self._impl = impl

    @property
    def impl(self) -> CommandApplicationProtocol:
        return self._impl

    def command(self, name: str, *, invocation_spec: InvocationSpec | None = None, exists_ok: bool = True) -> Callable:
        return self.impl.command(name, invocation_spec=invocation_spec, exists_ok=exists_ok)


class CommandGroup:
    def __init__(self, name: str, impl: GroupApplicationProtocol | None = None) -> None:
        self._name = name
        self._impl = impl or get_group_impl(name)

    @property
    def impl(self) -> GroupApplicationProtocol:
        return self._impl

    @property
    def name(self) -> str:
        return self._name

    def command(self, sub_command: str, *, invocation_spec: InvocationSpec | None = None, exists_ok: bool = True) -> Callable:
        return self.impl.command(sub_command, invocation_spec=invocation_spec, exists_ok=exists_ok)