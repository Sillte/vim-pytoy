from pytoy.infra.autocmd.autocmd_manager import VimAutocmd
from pytoy.infra.core.models import Listener
from collections import defaultdict
from pytoy.infra.core.models.event import Disposable, Event, EventProtocol


from typing import Hashable, Self, Sequence, Callable, Any


class EntityEventExceptionGroup(ExceptionGroup):

    @classmethod
    def from_event(cls, event: Event, exceptions: Sequence[Exception]) -> Self:
        message = f"Event[{event}]: EntityEventRouter failed with {len(exceptions)} errors."
        return cls( message, list(exceptions))



class GlobalEvent[T: Hashable](EventProtocol):
    def __init__(self, event: Event[T]) -> None: 
        self._event = event
        self._cached: dict[T, set[Listener[T]]] = defaultdict(set)
        self._disposable = self._event.subscribe(self._select_listener)

    def __del__(self):
        self._disposable.dispose()

    def _select_listener(self, value: T) -> None:
        if value in self._cached:
            exceptions = []
            for listener in list(self._cached[value]):
                try:
                    listener(value)
                except Exception as e:
                    exceptions.append(e)
            if exceptions:
                raise EntityEventExceptionGroup.from_event(self._event, exceptions)

    def subscribe(self, listener: Listener[T]) -> Disposable:
        return self._event.subscribe(listener)


    def at(self, entity_id: T) -> Event[T]:
        def subscribe(listener: Listener[T]) -> Disposable:
            self._cached[entity_id].add(listener)
            def dispose() -> None:
                self._cached[entity_id].remove(listener)
                if not self._cached[entity_id]:
                    del self._cached[entity_id]
            return Disposable(lambda: dispose())
        return Event(subscribe)


    def map(self, transform: Callable[[T], Any]) -> "EventProtocol":
        return self._event.map(transform)

    def filter(self, predicate: Callable[[T], bool]) -> "EventProtocol":
        return self._event.filter(predicate)


class EntityEventRouter[T: Hashable]:
    """Implement the efficient `filter` implementation
    """
    def __init__(self, event: Event[T]):
        self._event: Event[T] = event
        self._cached: dict[T, set[Listener[T]]] = defaultdict(set)
        self._disposable = self._event.subscribe(self._select_listener)

    def __del__(self):
        self._disposable.dispose()

    def _select_listener(self, value: T) -> None:
        if value in self._cached:
            exceptions = []
            for listener in list(self._cached[value]):
                try:
                    listener(value)
                except Exception as e:
                    exceptions.append(e)
            if exceptions:
                raise EntityEventExceptionGroup.from_event(self.source_event, exceptions)

    @property
    def source_event(self) -> Event[T]:
        return self._event

    def at(self, entity_id: T) -> Event[T]:
        def subscribe(listener: Listener[T]) -> Disposable:
            self._cached[entity_id].add(listener)
            def dispose() -> None:
                self._cached[entity_id].remove(listener)
                if not self._cached[entity_id]:
                    del self._cached[entity_id]
            return Disposable(lambda: dispose())
        return Event(subscribe)