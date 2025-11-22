from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Any, TypeAlias


# Type alias for command functions (can be callable, classmethod, or staticmethod)
CommandFunction: TypeAlias = Callable[..., Any] | staticmethod
NARGS: TypeAlias = str | int


class RangeCountType(Enum):
    RANGE = "range"
    COUNT = "count"
    NONE = None


@dataclass
class RangeCountOption:
    """In definition of commands, only one of `range` and `count`
    can be set.
    This class handles this relationship.
    """

    _type: RangeCountType = field(init=False, default=RangeCountType.NONE)
    _value: str | int | None = field(init=False, default=None)

    def __init__(self, range: None | str | int = None, count: int | None = None):
        if range is not None and count is not None:
            raise ValueError("Either of `range` or `count` can be set")

        if range is not None:
            self._type = RangeCountType.RANGE
            self._value = range
        if count is not None:
            self._type = RangeCountType.COUNT
            self._value = count

    @property
    def type(self) -> RangeCountType:
        return self._type

    def set_pair(self, type_: RangeCountType, value: str | int):
        """Setter of the instance values."""
        if self._type is not RangeCountType.NONE:
            raise ValueError(
                "`set_pair` can only be called if the type is NONE (unset)."
            )
        self._type = type_
        self._value = value

    @property
    def pair(self) -> tuple[RangeCountType, str | None | int]:
        """Return the option parameter

        In case of `range` (range, (value))
        In case of `count` (count, (value))
        In case of `None` (None, None)
        """
        return (self._type, self._value)

    def to_dict(self) -> dict[str, str]:
        """Provide the info of the instance as dict."""
        result = {}
        if self._type is RangeCountType.RANGE:
            result[RangeCountType.RANGE.value] = self._value
        if self._type is RangeCountType.COUNT:
            result[RangeCountType.COUNT.value] = self._value
        return result


@dataclass
class OptsArgument:
    """This is a naive wrapper of `dict` as `opts`."""

    args: str
    fargs: list
    count: int | None = None
    line1: int | None = None
    line2: int | None = None
    range: tuple[int, int] | int | None = None
