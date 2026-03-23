from dataclasses import dataclass
from typing import Callable, Protocol, Literal, Any, Self, ParamSpec, TypeVar, Any
import re
from textwrap import dedent


type FunctionName = str

class StrCallable(Protocol):
    def __call__(self, *args: str) -> str: ...
    
@dataclass(frozen=True)
class RegisteredFunction:
    name: str
    inner: Callable[..., Any]

    @property
    def impl_name(self):
        # The name which is used for the implementation. E.g., in vim, it is the name of the vim function.
        return self.name

    def __call__(self, *args) -> Any:
        return self.inner(*args)


class FunctionRegistryProtocol(Protocol):
    """Register the function which should be called from the backend event UI."""

    def register(self, function: Callable, name: str) -> RegisteredFunction: ...

    def is_registered(self, name: str) -> bool: ...

    def deregister(self, name: FunctionName | RegisteredFunction) -> None: ...


class FunctionRegistryFake(FunctionRegistryProtocol):
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
