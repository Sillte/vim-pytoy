import threading
from textwrap import dedent
from typing import Self

import vim
from pytoy.shared.lib.backend import BackendEnum, get_backend_enum
from pytoy.shared.lib.event import Event, EventEmitter
from pytoy.shared.lib.outcome import Error, Success
from pytoy.shared.timertask.domain import (
    FunctionName,
    OnTaskCallback,
    RegisteredTask,
    TaskExit,
    TaskName,
    TaskStatus,
    TimerStopException,
    TimerTaskImplProtocol,
)


class TimerTaskImplVim(TimerTaskImplProtocol):
    instance: Self | None = None

    def __init__(
        self,
    ) -> None:
        self._counter = 0
        self.tasks: dict[TaskName, RegisteredTask] = dict()
        self.statuses: dict[TaskName, TaskStatus] = dict()
        self._timer_map: dict[TaskName, int] = dict()
        if TimerTaskImplVim.instance is not None:
            raise RuntimeError("TimerTaskImplVim already instantiated")
        TimerTaskImplVim.instance = self
        self._lock = threading.RLock()
        self._registered_emitter = EventEmitter[TaskName]()
        self._deregistered_emitter = EventEmitter[TaskName]()
        self._exit_emitter = EventEmitter[TaskExit]()

    @property
    def on_exit(self) -> Event[TaskExit]:
        return self._exit_emitter.event

    @property
    def on_registered(self) -> Event[TaskName]:
        return self._registered_emitter.event

    @property
    def on_deregistered(self) -> Event[TaskName]:
        return self._deregistered_emitter.event

    def register(
        self,
        func: OnTaskCallback,
        interval: int = 100,
        name: TaskName | None = None,
        repeat: int = -1,
    ) -> TaskName:
        self._counter += 1

        taskname = name or f"AUTONAME{self._counter}"
        vim_funcname = f"LoopTask_{taskname}_{id(func)}_{self._counter}"

        task = RegisteredTask(
            name=taskname,
            function=func,
            impl_function_name=vim_funcname,
            initial_repeat=repeat,
        )

        # Vimコードの生成と実行
        vim_code = self._create_vim_code(taskname, vim_funcname)

        def _impl_function():
            with self._lock:
                if taskname in self.tasks:
                    raise ValueError(f"Task {taskname!r} is already registered.")
                vim.command(vim_code)
                # Vim側の repeat オプションは常に -1 (無限) に設定し、管理は Python 側で行う
                vim_repeat_opt = -1
                timer_id = int(vim.eval(f"timer_start({interval}, '{vim_funcname}', {{'repeat': {vim_repeat_opt}}})"))
                self.tasks[taskname] = task
                self.statuses[taskname] = TaskStatus(repeat=repeat)
                self._timer_map[taskname] = timer_id
                self._registered_emitter.fire(taskname)

        if get_backend_enum() == BackendEnum.VIM:
            _impl_function()
        else:
            vim.session.threadsafe_call(lambda *args: _impl_function())

        return taskname

    def _execute_task(self, name: TaskName):
        with self._lock:
            task = self.tasks.get(name)
            status = self.statuses.get(name)
        if task is None or status is None:
            return

        func = task.function

        try:
            func()
        except TimerStopException:
            self._schedule_deregister(name)
            self._exit_emitter.fire(TaskExit(name, Success("stopped")))
            return
        except Exception as exception:
            self._schedule_deregister(name)
            self._exit_emitter.fire(TaskExit(name, Error(exception)))
            return

        is_finished = False
        with self._lock:
            if status.repeat >= 0:
                status.repeat -= 1
                if status.repeat <= 0:
                    is_finished = True

        if is_finished:
            self._schedule_deregister(name)
            self._exit_emitter.fire(TaskExit(name, Success("finished")))

    def _create_vim_code(self, taskname: TaskName, impl_function_name: FunctionName) -> str:
        """Helper to generate the complex VimL function block with error/repeat logic."""

        if __name__ != "__main__":
            prefix = f"{__name__}."
            import_prefix = f"from {__name__} import TimerTaskImplVim, TimerStopException"
        else:
            prefix = ""
            import_prefix = " "

        python_procedures = dedent(
            f"""
            python3 << EOF
            {import_prefix}
            name = '{taskname}'
            instance = {prefix}TimerTaskImplVim.instance
            if instance is not None:
                instance._execute_task(name)
            EOF
        """
        ).strip()

        vim_code = dedent(f"""
            function! {impl_function_name}(timer)
                {python_procedures}
            endfunction

            function! VimPytoyTimerTaskDeleteFunction_private(name, timer_id)
                call timer_stop(a:timer_id)
                execute 'delfunction!' . a:name
            endfunction
        """)

        return vim_code.strip()

    def _schedule_deregister(self, name: TaskName):
        """Deregisters the task from the timer thread asynchronously."""

        with self._lock:
            timer_id = self._timer_map.get(name)
            task = self.tasks.get(name)
        if timer_id is None or task is None:
            return
        vim_funcname = task.impl_function_name

        def _impl_function():
            with self._lock:
                vim.command(
                    dedent(f"""
                    call timer_start(1, {{ -> VimPytoyTimerTaskDeleteFunction_private('{vim_funcname}', {timer_id}) }} )
                """).strip()
                )
                self.tasks.pop(name)
                self.statuses.pop(name)
                self._timer_map.pop(name)
                self._deregistered_emitter.fire(name)

        if get_backend_enum() == BackendEnum.VIM:
            _impl_function()
        else:
            vim.session.threadsafe_call(lambda *args: _impl_function())

    def deregister(self, name: TaskName, *, strict: bool = False):
        if strict:
            if not self.is_registered(name):
                raise KeyError(f"No timer task registered with name: '{name}'")
        self._schedule_deregister(name)

    def is_registered(self, name: str):
        with self._lock:
            return name in self._timer_map
