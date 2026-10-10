# Specification

This document defines the public contract of `Event`.
It is intended for both users and developers of this package.

## `EventEmitter.fire(value: T)`

- The listeners invoked are the listeners subscribed when `fire(value)` is called. Changes to subscriptions made by a listener take effect on later emissions.
- Listeners are invoked synchronously.
- The order in which listeners are invoked is not guaranteed.
- Thread safety is not guaranteed.

### Exceptions

- If a listener raises an exception during emission, the exception propagates to the caller of `fire()`, and subsequent listeners in that emission are not invoked.
- Exceptions raised by event transformations or predicates, such as those used by `map()` and `filter()`, follow the same rules.

## `EventEmitter.dispose()`

- Calling `dispose()` multiple times has the same effect as calling it once.
- Disposing the emitter removes its current listeners; it does not prevent later subscriptions or emissions.

## `once()`

- `once()` returns an event that invokes each subscriber at most once, including when a callback re-enters the source event or raises an exception.