from dataclasses import dataclass
from typing import Callable
from typing import Protocol, Self, Any




@dataclass(frozen=True)
class CursorPosition:
    """This represents the position of cursor.
    Here, both of `line` and `col` are 0-based.
    Note that `line` and `col` in vim start from 1, while 
    thoese start from 0 in vscode.
    Hence, you have to take it into account to implement
    the concrete classs for vim/vscode.
    """
    line: int  # 0-based.
    col: int   # 0-based, Unicode codepoint index (Python str index)


@dataclass(frozen=True)
class CharacterRange:
    """
    Represents a half-open text range [start, end).

    - start: inclusive
    - end: exclusive
    """
    start: CursorPosition
    end: CursorPosition

    def __post_init__(self):
        if (self.end.line, self.end.col) < (self.start.line, self.start.col):
            object.__setattr__(self, "start", self.end)
            object.__setattr__(self, "end", self.start)

    @property
    def is_empty(self) -> bool:
        return self.start == self.end
    
    def as_line_range(self, cut_first_line: bool = False, cut_last_line: bool = False) -> "LineRange":
        if cut_first_line and self.start.col != 0:
            start = self.start.line + 1
        else:
            start = self.start.line

        if self.end.col == 0: 
            end = self.end.line
        elif cut_last_line:
            end = self.end.line
        else:
            end = self.end.line + 1
        return LineRange(start, max(start, end))


@dataclass(frozen=True)
class LineRange:
    """0-based, exclusive range [start, end)

    Example:
        LineRange(0, 1) -> Only 0.
        LineRange(0, 0) -> Just before the 0 (Insertion Point)
    """
    start: int
    end: int

    @property
    def count(self) -> int:
        return self.end - self.start


type Listener[T] = Callable[[T], None]
type Dispose = Callable[[], None]
type Subscribe[T] = Callable[[Listener[T]], "Disposable"]


class Disposable:
    def __init__(self, dispose: Dispose):
        self._dispose = dispose

    def dispose(self) -> None:
        self._dispose()


class Event[T]:
    def __init__(self, subscribe: Subscribe[T]):
        self._subscribe = subscribe

    def subscribe(self, listener: Listener[T]) -> Disposable:
        return self._subscribe(listener)

    def __call__(self, listener: Listener[T]) -> Disposable:
        # For decorator. 
        return self.subscribe(listener)

    def once(self) -> "Event":
        from pytoy.infra.core import event_utils
        return event_utils.once(self)

    def map(self, transform: Callable[[T], Any]) -> "Event":
        from pytoy.infra.core import event_utils
        return event_utils.map_event(self, transform)

    def filter(self, predicate: Callable[[T], bool]) -> "Event":
        from pytoy.infra.core import event_utils
        return event_utils.filter(self, predicate)


class EventEmitter[T]:
    def __init__(self) -> None:
        self._listeners: list[Listener[T]] = []
        self.event = Event[T](self._subscribe)

    def _subscribe(self, listener: Listener[T]) -> Disposable:
        self._listeners.append(listener)

        def dispose():
            self._listeners.remove(listener)

        return Disposable(dispose)

    def fire(self, value: T) -> None:
        for listener in list(self._listeners):
            listener(value)

    def dispose(self) -> None:
        self._listeners.clear()