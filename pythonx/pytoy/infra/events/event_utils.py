from pytoy.infra.events.models import  Event, EventEmitter


def once[T](event: Event[T]) -> Event[T]:
    emitter = EventEmitter[T]()
    disposed = False

    def listener(value: T) -> None:
        nonlocal disposed
        if disposed:
            return
        disposed = True
        emitter.fire(value)
        disposable.dispose()

    disposable = event.subscribe(listener)
    return emitter.event
