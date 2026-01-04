from typing import Callable
from typing import Protocol, Self

type Listener[T] = Callable[[T], None]
type Dispose = Callable[[], None]
type Subscribe[T] = Callable[[Listener[T]], Disposable]

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

    @classmethod
    def once(cls, event: "Event") -> "Event":
        from pytoy.infra.events import event_utils
        return event_utils.once(event)


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


class EventSourceProtocol[T](Protocol):
    @property
    def event(self) -> Event[T]:
        ...

class EmittableEventSourceProtocol[T](Protocol):
    """EventSource for intentional fires are necessary. 
    """
    @property
    def event(self) -> Event[T]:
        ...

    @property
    def emitter(self) -> EventEmitter[T]:
        ...


    

