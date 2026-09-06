from __future__ import annotations

from typing import Any, Callable, Protocol, overload

from typing_extensions import TypeIs

type Listener[T] = Callable[[T], Any]
type Dispose = Callable[[], None]


class Disposable:
    def __init__(self, dispose: Dispose):
        self._dispose = dispose

    def dispose(self) -> None:
        self._dispose()


type Subscribe[T] = Callable[[Listener[T]], "Disposable"]


def once[T](event: Event[T]) -> Event[T]:
    def subscribe(listener: Listener[T]) -> Disposable:
        alive_disposable: Disposable | None = None

        def wrapper(value: T) -> None:
            nonlocal alive_disposable
            if alive_disposable is None:
                return
            listener(value)
            alive_disposable.dispose()
            alive_disposable = None

        alive_disposable = event.subscribe(wrapper)
        return Disposable(lambda: alive_disposable.dispose() if alive_disposable is not None else None)

    return Event(subscribe)


def map_event[T, U](event: Event[T], transform: Callable[[T], U]) -> Event[U]:
    """If the source of event is disposed, then the returned Event is not fired."""

    def subscribe(listener: Listener[U]) -> Disposable:
        return event.subscribe(lambda value: listener(transform(value)))

    return Event[U](subscribe)


@overload
def filter[T, R](
    event: Event[T],
    predicate: Callable[[T], TypeIs[R]],
) -> Event[R]: ...


@overload
def filter[T](
    event: Event[T],
    predicate: Callable[[T], bool],
) -> Event[T]: ...


def filter[T](event: Event[T], predicate: Callable[[T], bool]) -> Event[Any]:
    def subscribe(listener: Listener[T]) -> Disposable:
        def wrapper(value: T) -> None:
            if predicate(value):
                listener(value)

        disposable = event.subscribe(wrapper)
        return Disposable(disposable.dispose)

    return Event(subscribe)


class EventProtocol[T](Protocol):
    def subscribe(self, listener: Listener[T]) -> Disposable: ...

    def once(self) -> "EventProtocol[T]": ...

    def map[R](self, transform: Callable[[T], R]) -> "EventProtocol[R]": ...

    @overload
    def filter[R](
        self,
        predicate: Callable[[T], TypeIs[R]],
    ) -> "EventProtocol[R]": ...

    @overload
    def filter(
        self,
        predicate: Callable[[T], bool],
    ) -> "EventProtocol[T]": ...

    def filter(self, predicate: Callable[[T], bool]) -> "EventProtocol[Any]": ...


class Event[T]:
    def __init__(self, subscribe: Subscribe[T]):
        self._subscribe = subscribe

    def subscribe(self, listener: Listener[T]) -> Disposable:
        return self._subscribe(listener)

    def __call__(self, listener: Listener[T]) -> Disposable:
        # For decorator.
        return self.subscribe(listener)

    def once(self) -> Event:
        return once(self)

    def map[R](self, transform: Callable[[T], R]) -> Event[R]:
        return map_event(self, transform)

    @overload
    def filter[R](
        self,
        predicate: Callable[[T], TypeIs[R]],
    ) -> Event[R]: ...

    @overload
    def filter(
        self,
        predicate: Callable[[T], bool],
    ) -> Event[T]: ...

    def filter(self, predicate: Callable[[T], bool]) -> Event[Any]:
        return filter(self, predicate)


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
