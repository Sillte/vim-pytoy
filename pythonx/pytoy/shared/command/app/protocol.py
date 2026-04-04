from typing import Protocol, Literal, Callable
from dataclasses import dataclass


# NOTE: It is unknown whether `InvocationSpec` is necessary or not.
# As of 2026/04, `InvocationSpec` is not used.
@dataclass(frozen=True)
class RangeSpec:
    default: tuple[int, int] | None = None
    type: Literal["Range"] = "Range"


@dataclass(frozen=True)
class CountSpec:
    default: int = 1
    type: Literal["Count"] = "Count"

@dataclass(frozen=True)
class NoneSpec:
    """No additional specification regarding invocation.
    """
    type: Literal["None"] = "None"

type InvocationSpec = RangeSpec | CountSpec | NoneSpec


class CommandApplicationProtocol(Protocol):
    def command(self,
                name: str,
                *,
                invocation_spec: InvocationSpec | None = None,
                exists_ok: bool = True) -> Callable: ...

class GroupApplicationProtocol(Protocol):

    @property
    def name(self) -> str: ...

    def command(self,
                sub_command: str,
                *,
                invocation_spec: InvocationSpec | None = None,
                exists_ok: bool = True) -> Callable: ...


