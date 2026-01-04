from dataclasses import dataclass, replace, field
from typing import Self, Mapping, Sequence, Literal, Any, Callable, assert_never, cast


StatusLineItemFunction = Callable[[], str]


@dataclass(frozen=True)
class BaseStatusLineItem:
    """As a ValueObject, value and highlight are regarded as values. 
    """
    value: Any
    highlight: str | None = None
    group: int | Literal["left", "right"]  = field(default="left", compare=False) 
    priority: int | None = field(default=None, compare=False) 

@dataclass(frozen=True)
class TextStatusLineItem(BaseStatusLineItem):
    value: str

@dataclass(frozen=True)
class FunctionStatusLineItem(BaseStatusLineItem):
    value: StatusLineItemFunction

@dataclass(frozen=True)
class UnknownStatusLineItem(BaseStatusLineItem):
    value: Any

StatusLineItem = TextStatusLineItem | FunctionStatusLineItem | UnknownStatusLineItem
