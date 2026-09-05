from typing import Callable

from pytoy.shared.lib.function.domain import FunctionName, FunctionRegistryProtocol, RegisteredFunction


class FunctionRegistryDummy(FunctionRegistryProtocol):
    def __init__(self):
        self.functions: dict[FunctionName, RegisteredFunction] = dict()

    def register(self, function: Callable, name: str) -> RegisteredFunction:
        if self.is_registered(name):
            raise ValueError(f"Function with name {name} is already registered.")
        registered_function = RegisteredFunction(name=name, inner=function)
        self.functions[name] = registered_function
        return registered_function

    def is_registered(self, name: str) -> bool:
        return name in self.functions

    def deregister(self, name: FunctionName | RegisteredFunction) -> None:
        if isinstance(name, RegisteredFunction):
            name = name.name
        self.functions.pop(name, None)
