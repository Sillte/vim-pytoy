from dataclasses import dataclass, field
from typing import Any, Callable, Literal

StatusLineItemFunction = Callable[[], str]


@dataclass(frozen=True)
class BaseStatusLineItem:
    value: Any
    highlight: str | None = None
    group: int | Literal["left", "right"] = field(default="left", compare=False)
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
