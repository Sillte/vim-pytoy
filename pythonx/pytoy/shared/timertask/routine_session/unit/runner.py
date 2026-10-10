from threading import RLock
from typing import Literal

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

type RoutineUnitStatus = Literal["created", "starting", "executing", "waiting", "exited"]


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
        self._status: RoutineUnitStatus = "created"
        self._called: int = 0
        self._execution_handler: ThreadExecutionHandler | None = None
        self._disposable = disposable
        self._execution_preparing_emitter = EventEmitter[ThreadExecutionHandler]()
        self._iteration_exit_emitter = EventEmitter[RoutineUnitIterationExit]()

    @property
    def name(self) -> RoutineUnitName:
        return self._routine_unit.name

    def start(self) -> None:
        with self._lock:
            if self._status == "exited":
                raise RuntimeError("Already `terminated`.")
            if self._status != "created":
                return
            self._status = "starting"
        try:
            TimerTask.execute_oneshot(self._make_next_work, interval=0)
        except BaseException:
            with self._lock:
                if self._status == "starting":
                    self._status = "created"
            raise

    def terminate(self) -> None:
        with self._lock:
            if self._status == "exited":
                return
            if self._execution_handler is not None:
                try:
                    self._execution_handler.cancel()
                except ValueError:
                    pass
            self._disposable.dispose()
            self._status = "exited"

    @property
    def alive(self) -> bool:
        with self._lock:
            return self._status in ("executing", "waiting")

    def _on_iteration_exit(self, exit: RoutineUnitIterationExit) -> None:
        with self._lock:
            self._execution_handler = None

        errors: list[Exception] = []
        try:
            self._hooks.on_exit(exit)
        except Exception as error:
            errors.append(error)
        try:
            self._iteration_exit_emitter.fire(exit)
        except Exception as error:
            errors.append(error)

        with self._lock:
            self._called += 1
            if self._status == "exited":
                should_continue = False
            else:
                max_iteration = self._routine_unit.max_iteration
                should_continue = max_iteration is None or self._called < max_iteration
                if should_continue:
                    self._status = "waiting"
        try:
            if should_continue:
                TimerTask.execute_oneshot(self._make_next_work, interval=self._routine_unit.delay)
            else:
                self.terminate()
        except Exception as error:
            errors.append(error)
            self.terminate()

        if len(errors) == 1:
            raise errors[0]
        if errors:
            raise ExceptionGroup("Routine unit exit processing failed.", errors)

    def _make_next_work(self) -> None:
        try:
            with self._lock:
                if self._status == "exited":
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
        except BaseException:
            with self._lock:
                is_initial = self._status == "starting"
                if is_initial:
                    self._status = "created"
            if not is_initial:
                self.terminate()
            raise

        try:
            self._execution_preparing_emitter.fire(handler)
        except BaseException:
            handler.discard()
            with self._lock:
                if self._execution_handler is handler:
                    self._execution_handler = None
                is_initial = self._status == "starting"
                if is_initial:
                    self._status = "created"
            if not is_initial:
                self.terminate()
            raise

        start_error: BaseException | None = None
        with self._lock:
            if self._status == "exited":
                should_discard = True
            else:
                should_discard = False
                try:
                    handler.start(
                        hooks=ThreadExecutionHooks.from_any(
                            on_result=self._hooks.on_result, on_exception=self._hooks.on_exception
                        )
                    )
                except BaseException as error:
                    start_error = error
                    self._execution_handler = None
                    if self._status == "starting":
                        self._status = "created"
                else:
                    self._status = "executing"
        if should_discard:
            handler.discard()
        elif start_error is not None:
            self.terminate()
            raise start_error

    @property
    def on_execution_preparing(self) -> Event[ThreadExecutionHandler]:
        return self._execution_preparing_emitter.event

    @property
    def on_iteration_exit(self) -> Event[RoutineUnitIterationExit]:
        return self._iteration_exit_emitter.event
