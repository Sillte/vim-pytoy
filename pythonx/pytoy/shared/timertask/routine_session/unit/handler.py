from pytoy.shared.lib.event import Event
from pytoy.shared.timertask.thread_execution import (
    ThreadExecutionHandler,
)

from .models import (
    RoutineUnitIterationExit,
)
from .runner import RoutineUnitRunner


class RoutineUnitHandler:
    def __init__(self, runner: RoutineUnitRunner) -> None:
        self._runner = runner

    def start(self) -> None:
        self._runner.start()

    def terminate(self) -> None:
        self._runner.terminate()

    @property
    def alive(self) -> bool:
        return self._runner.alive

    @property
    def on_execution_start(self) -> Event[ThreadExecutionHandler]:
        return self._runner.on_execution_start

    @property
    def on_iteration_exit(self) -> Event[RoutineUnitIterationExit]:
        return self._runner.on_iteration_exit
