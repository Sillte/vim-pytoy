import vim


from pytoy.shared.timertask.domain import TaskStatus, FunctionName, OnTaskCallback, RegisteredTask, TaskName, TimerStopException, TimerTaskImplProtocol
from pytoy.shared.timertask.domain import NormalStopReason, OnFinishCallback, OnErrorCallback


from textwrap import dedent
from typing import Callable, Self


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

    def register(
        self,
        func: OnTaskCallback,
        interval: int = 100,
        name: TaskName | None = None,
        repeat: int = -1,
        on_finish: Callable[[NormalStopReason], None] | None = None,
        on_error: Callable[[Exception], None] | None = None,
    ) -> TaskName:
        self._counter += 1

        taskname = name or f"AUTONAME{self._counter}"
        vim_funcname = f"LoopTask_{taskname}_{id(func)}_{self._counter}"

        task = RegisteredTask(
            name=taskname,
            function=func,
            impl_function_name=vim_funcname,
            on_finish=on_finish,
            on_error=on_error,
            initial_repeat=repeat,
        )

        # Vimコードの生成と実行
        vim_code = self._create_vim_code(taskname, vim_funcname)
        vim.command(vim_code)

        # Vim側の repeat オプションは常に -1 (無限) に設定し、管理は Python 側で行う
        vim_repeat_opt = -1
        timer_id = int(vim.eval(f"timer_start({interval}, '{vim_funcname}', {{'repeat': {vim_repeat_opt}}})"))
        self.tasks[taskname] = task
        self.statuses[taskname] = TaskStatus(repeat=repeat)
        self._timer_map[taskname] = timer_id

        return taskname

    def _execute_task(self, name: TaskName):
        task = self.tasks.get(name)
        status = self.statuses.get(name)
        if task is None or status is None:
            return

        func = task.function
        on_finish = task.on_finish
        on_error = task.on_error

        try:
            func()
        except TimerStopException as tse:
            self._schedule_deregister(name)
            cause = tse.__cause__
            if on_finish and (not cause):
                on_finish('stopped')
            elif on_error and cause:
                on_error(cause)  #type: ignore
            elif cause:
                raise cause
            return
        except Exception as e:
            self._schedule_deregister(name)
            if on_error:
                on_error(e)
            raise e

        if status.repeat > 0:
            status.repeat -= 1
            if status.repeat == 0:
                self._schedule_deregister(name)
                if on_finish:
                    on_finish("finished")

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

        timer_id = self._timer_map.get(name)
        task = self.tasks.get(name)
        if timer_id is None or task is None:
            return
        vim_funcname = task.impl_function_name
        vim.command(
            dedent(f"""
            call timer_start(1, {{ -> VimPytoyTimerTaskDeleteFunction_private('{vim_funcname}', {timer_id}) }} )
        """).strip()
        )
        self.tasks.pop(name)
        self.statuses.pop(name)
        self._timer_map.pop(name)

    def deregister(self, name: TaskName, *, strict: bool = False):
        if name not in self.tasks:
            if strict:
                raise ValueError(f"No timer task registered with name: '{name}'")
            return
        self._schedule_deregister(name)

    def is_registered(self, name: str):
        return name in self._timer_map