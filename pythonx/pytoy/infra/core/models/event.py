

from typing import Any, Callable, Any

type Listener[T] = Callable[[T], Any]
type Dispose = Callable[[], None]


class Disposable:
    def __init__(self, dispose: Dispose):
        self._dispose = dispose

    def dispose(self) -> None:
        self._dispose()
type Subscribe[T] = Callable[[Listener[T]], "Disposable"]


class EventProtocol[T]:
    def subscribe(self, listener: Listener[T]) -> Disposable:
        ...

    def map(self, transform: Callable[[T], Any]) -> "EventProtocol":
        ...

    def filter(self, predicate: Callable[[T], bool]) -> "EventProtocol":
        ...



class Event[T](EventProtocol):
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
            # For idempotency, 
            try:
                self._listeners.remove(listener)
            except (ValueError, RuntimeError):
                pass

        return Disposable(dispose)

    def fire(self, value: T) -> None:
        for listener in list(self._listeners):
            listener(value)

    def dispose(self) -> None:
        self._listeners.clear()