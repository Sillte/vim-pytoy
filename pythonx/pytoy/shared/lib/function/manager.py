from typing import Callable

from pytoy.shared.lib.backend import can_use_vim

from .domain import FunctionName, FunctionRegistryProtocol, RegisteredFunction


def make_function_name(function: Callable, *, prefix: str | None = None) -> FunctionName:
    name = getattr(function, "__name__", function.__class__.__name__)
    if name == "<lambda>":
        name = "lambda"
    name = f"{name}_{id(function)}"
    if prefix is not None:
        name = f"{prefix}_{name}"
    return name


def create_default_impl() -> FunctionRegistryProtocol:
    if can_use_vim():
        from .impls.vim import FunctionRegistryVim

        return FunctionRegistryVim()

    from .impls.dummy import FunctionRegistryDummy

    return FunctionRegistryDummy()


class FunctionManager:
    def __init__(self, impl: FunctionRegistryProtocol | None = None) -> None:
        self._impl = impl or create_default_impl()

    def register(
        self, function: Callable, *, name: FunctionName | None = None, prefix: str | None = None
    ) -> RegisteredFunction:
        if name is None:
            name = make_function_name(function, prefix=prefix)
        elif prefix is not None:
            name = f"{prefix}_{name}"
        return self._impl.register(function, name=name)

    def is_registered(self, name: FunctionName) -> bool:
        return self._impl.is_registered(name)

    def deregister(self, name: FunctionName | RegisteredFunction) -> None:
        self._impl.deregister(name)
