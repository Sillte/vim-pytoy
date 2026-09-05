from collections.abc import Callable

from pytoy.shared.lib.function.domain import (
    FunctionName,
    FunctionRegistryProtocol,
    RegisteredFunction,
)
from pytoy.shared.lib.function.manager import FunctionManager

__all__ = [
    "FunctionName",
    "FunctionManager",
    "FunctionRegistry",
    "FunctionRegistryProtocol",
    "RegisteredFunction",
]


class FunctionRegistry:
    """Convenience facade for the function manager in the global core context."""

    @staticmethod
    def _manager() -> FunctionManager:
        from pytoy.contexts.core import GlobalCoreContext

        return GlobalCoreContext.get().function_manager

    @classmethod
    def register(
        cls, func: Callable, *, name: FunctionName | None = None, prefix: str | None = None
    ) -> RegisteredFunction:
        return cls._manager().register(func, name=name, prefix=prefix)

    @classmethod
    def is_registered(cls, name: FunctionName) -> bool:
        return cls._manager().is_registered(name)

    @classmethod
    def deregister(cls, name: FunctionName | RegisteredFunction) -> None:
        cls._manager().deregister(name)
