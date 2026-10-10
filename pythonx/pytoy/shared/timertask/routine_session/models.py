import logging
import uuid
from dataclasses import dataclass
from threading import RLock
from typing import Self

from pytoy.shared.lib.event import Disposable, Event, EventEmitter
from pytoy.shared.loggers import setup_logger
from pytoy.shared.timertask.routine_session.unit.handler import RoutineUnitHandler
from pytoy.shared.timertask.routine_session.unit.models import (
    RoutineUnit,
    RoutineUnitHooks,
    RoutineUnitName,
    RoutineUnitRequest,
)
from pytoy.shared.timertask.routine_session.unit.runner import RoutineUnitRunner

type RoutineSessionKind = str
type RoutineSessionID = str


@dataclass(frozen=True)
class RoutineSessionRequest:
    kind: RoutineSessionKind = "$default"
    logger: logging.Logger | None = None

    @classmethod
    def from_any(
        cls,
        kind: RoutineSessionKind | None = None,
        logger: logging.Logger | None = None,
    ) -> Self:
        kind = kind or "$default"
        return cls(kind=kind, logger=logger)


@dataclass(frozen=True)
class RoutineSessionExit:
    id: RoutineSessionID


@dataclass(frozen=True)
class RoutineSessionQuery:
    id: RoutineSessionID | None = None
    kind: RoutineSessionKind | None = None

    @classmethod
    def from_any(
        cls,
        id: RoutineSessionID | None = None,
        kind: RoutineSessionKind | None = None,
    ) -> Self:

        return cls(id=id, kind=kind)


class RoutineSession:
    def __init__(self, kind: RoutineSessionKind, logger: logging.Logger | None = None) -> None:
        self._id = str(uuid.uuid4())
        self._kind = kind
        self._unit_runners: dict[str, RoutineUnitRunner] = dict()
        self._exit_emitter = EventEmitter()
        self._lock = RLock()
        self._terminated = False
        self._logger = logger or setup_logger()

    @property
    def id(self) -> RoutineSessionID:
        return self._id

    @property
    def kind(self) -> RoutineSessionKind:
        return self._kind

    @classmethod
    def from_request(cls, request: RoutineSessionRequest) -> Self:
        return cls(kind=request.kind, logger=request.logger)

    def create_unit(
        self, unit_request: RoutineUnitRequest, hooks: RoutineUnitHooks | None = None
    ) -> RoutineUnitHandler:
        hooks = hooks or RoutineUnitHooks.from_any()
        with self._lock:
            if self._terminated:
                raise RuntimeError("Already RuntimeSession is terminated.")
            if unit_request.max_iteration is not None and unit_request.max_iteration <= 0:
                raise ValueError("Max iteration must be positive.")
            if unit_request.name in self._unit_runners:
                raise ValueError(f"Already {unit_request.name=} is registered.")

            def dispose():
                with self._lock:
                    self._unit_runners.pop(unit_request.name, None)

            unit_runner = RoutineUnitRunner(
                routine_unit=RoutineUnit(
                    name=unit_request.name,
                    worker=unit_request.worker,
                    delay=unit_request.delay,
                    max_iteration=unit_request.max_iteration,
                ),
                hooks=hooks,
                lock=self._lock,
                disposable=Disposable(dispose),
            )
            self._unit_runners[unit_request.name] = unit_runner
        return RoutineUnitHandler(runner=unit_runner)

    def get_unit(self, name: RoutineUnitName) -> RoutineUnitHandler | None:
        with self._lock:
            runner = self._unit_runners.get(name)
        return RoutineUnitHandler(runner=runner) if runner else None

    @property
    def on_exit(self) -> Event[RoutineSessionExit]:
        return self._exit_emitter.event

    def terminate(self) -> None:
        with self._lock:
            if self._terminated:
                return
            self._terminated = True
            runners = tuple(self._unit_runners.values())

        for runner in runners:
            runner.terminate()

        try:
            self._exit_emitter.fire(RoutineSessionExit(id=self._id))
        finally:
            with self._lock:
                self._exit_emitter.dispose()
