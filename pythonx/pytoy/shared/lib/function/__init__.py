from typing import Callable
from pytoy.shared.lib.function.domain import FunctionRegistryProtocol, FunctionName, RegisteredFunction
from pytoy.shared.lib.backend import can_use_vim


def make_function_name(function: Callable, *, prefix: str | None = None) -> FunctionName:
    name = getattr(function, "__name__", function.__class__.__name__)
    if name == "<lambda>":
        name = "lambda"
    name = f"{name}_{id(function)}"
    if prefix is not None:
        name = f"{prefix}_{name}"
    return name


def get_default_impl() -> FunctionRegistryProtocol:
    if can_use_vim():
        from pytoy.shared.lib.function.vim import FunctionRegistryVim

        return FunctionRegistryVim()
    from pytoy.shared.lib.function.domain import FunctionRegistryFake

    return FunctionRegistryFake()


class FunctionRegistry:
    impl: FunctionRegistryProtocol | None = None

    @classmethod
    def set_impl(cls, impl: FunctionRegistryProtocol) -> None:
        cls.impl = impl

    @classmethod
    def get_impl(cls) -> FunctionRegistryProtocol:
        if cls.impl is None:
            cls.impl = get_default_impl()
        return cls.impl

    @classmethod
    def register(
        cls, func: Callable, *, name: FunctionName | None = None, prefix: str | None = None
    ) -> RegisteredFunction:
        if name is None:
            name = make_function_name(func, prefix=prefix)
        else:
            if prefix is not None:
                name = f"{prefix}_{name}"
        return cls.get_impl().register(func, name=name)

    @classmethod
    def is_registered(cls, name: FunctionName) -> bool:
        return cls.get_impl().is_registered(name)

    @classmethod
    def deregister(cls, name: FunctionName | RegisteredFunction) -> None:
        cls.get_impl().deregister(name)
