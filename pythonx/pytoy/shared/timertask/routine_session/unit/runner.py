from threading import RLock

from pytoy.shared.lib.event import Disposable, Event, EventEmitter
from pytoy.shared.timertask.thread_execution import (
    CancelToken,
    ThreadExecutionHandler,
    ThreadExecutionHooks,
    ThreadExecutionRequest,
)
from pytoy.shared.timertask.timertask import TimerTask

from .models import (
    RoutineContext,
    RoutineUnit,
    RoutineUnitHooks,
    RoutineUnitIterationExit,
    RoutineUnitName,
)


class RoutineUnitRunner:
    def __init__(
        self,
        routine_unit: RoutineUnit,
        hooks: RoutineUnitHooks,
        lock: RLock,
        disposable: Disposable,
    ) -> None:
        self._routine_unit = routine_unit
        self._hooks = hooks
        self._lock = lock
        self._is_started: bool = False
        self._is_terminated: bool = False
        self._called: int = 0
        self._execution_handler: ThreadExecutionHandler | None = None
        self._disposable = disposable
        self._execution_start_emitter = EventEmitter[ThreadExecutionHandler]()
        self._iteration_exit_emitter = EventEmitter[RoutineUnitIterationExit]()

    @property
    def name(self) -> RoutineUnitName:
        return self._routine_unit.name

    def start(self) -> None:
        with self._lock:
            if self._is_terminated:
                raise RuntimeError("Already `terminated`.")
            if self._is_started:
                return
            self._is_started = True
        self._make_next_work()

    def terminate(self) -> None:
        with self._lock:
            if self._is_terminated:
                return
            self._is_terminated = True
        if self._execution_handler:
            self._execution_handler.cancel()
        self._disposable.dispose()

    @property
    def alive(self) -> bool:
        with self._lock:
            return self._is_started and (not self._is_terminated)

    def _on_iteration_exit(self, exit: RoutineUnitIterationExit):
        self._hooks.on_exit(exit)
        self._iteration_exit_emitter.fire(exit)
        with self._lock:
            self._execution_handler = None
            self._called += 1
            if self._routine_unit.max_iteration is None:
                is_continued = True
            elif self._called < self._routine_unit.max_iteration:
                is_continued = True
            else:
                is_continued = False
            should_continue = is_continued and (not self._is_terminated)
        if should_continue:
            TimerTask.execute_oneshot(self._make_next_work, interval=self._routine_unit.delay)
        else:
            self.terminate()

    def _make_next_work(self):
        with self._lock:
            if self._is_terminated:
                return

            def _inner(cancel_token: CancelToken):
                context = RoutineContext(cancel_token=cancel_token, unit_name=self.name)
                return self._routine_unit.worker(context)

            request = ThreadExecutionRequest.from_any(_inner)
            handler = ThreadExecutionHandler.create(request)
            event = handler.on_exit.map(
                lambda thread_exit: RoutineUnitIterationExit(name=self.name, outcome=thread_exit.outcome)
            ).once()
            event.subscribe(self._on_iteration_exit)
            self._execution_handler = handler

        self._execution_start_emitter.fire(handler)
        handler.start(
            hooks=ThreadExecutionHooks.from_any(on_result=self._hooks.on_result, on_exception=self._hooks.on_exception)
        )

    @property
    def on_execution_start(self) -> Event[ThreadExecutionHandler]:
        return self._execution_start_emitter.event

    @property
    def on_iteration_exit(self) -> Event[RoutineUnitIterationExit]:
        return self._iteration_exit_emitter.event
