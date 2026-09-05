from dataclasses import dataclass
from typing import Any, Callable, Protocol

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
