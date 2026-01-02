import vim
from typing import Callable, Any, Literal
from textwrap import dedent
from dataclasses import dataclass


type TaskName = str
type VimFuncName = str

type NormalStopReason = Literal[
    "finished", "stopped"
]  # `repeat` is comsued or exeception is raised.

type OnTaskCallback = Callable[[], None]
type OnFinishCallback = Callable[[NormalStopReason], None] | Callable[[], None]
type OnErrorCallback = Callable[[Exception], None] | Callable[[], None]


class TimerStopException(Exception):
    """Exception raised inside the timer callback to stop the registered loop.
    Note that when this exception is raised, `on_finish` callback is invoked with 'stopped' reason.
    """

    pass


def _wrap_to_one_argument_func(
    func: Callable[[], Any] | Callable[[Any], Any],
) -> Callable[[Any], Any]:
    """Wrap the function to one accepting one argument."""
    import inspect  # inspcet requires a little bit long

    sig = inspect.signature(func)
    if len(sig.parameters) == 0:

        def wrapper(_: Any) -> Any:
            return func()

        return wrapper
    elif len(sig.parameters) == 1:
        return func  # type: ignore[return-value]
    else:
        raise ValueError("Function must accept either zero or one argument.")


@dataclass(frozen=True)
class _TaskConfig:
    """Static configuration for a TimerTask, which does not change after registration."""

    on_finish: Callable[[NormalStopReason], None] | None = None
    on_error: OnErrorCallback | None = None
    initial_repeat: int = -1


@dataclass
class _TaskStatus:
    """Status of a TimerTask, which may change during execution."""

    repeat: int


class TimerTask:
    """Using `timer_start` function, it enables asynchronous process
    executed in VIM main loop, with repetition and error handling capabilities.
    """

    FUNCTION_MAP: dict[TaskName, Callable[[], None]] = dict()  # name -> function
    TIMER_MAP: dict[TaskName, int] = dict()
    VIMFUNCNAME_MAP: dict[TaskName, VimFuncName] = dict()

    # Given configuration.
    CONFIG_MAP: dict[TaskName, _TaskConfig] = dict()
    # NEW: Dynamic status of the `TASK`.
    STATUS_MAP: dict[TaskName, _TaskStatus] = dict()

    counter: int = 0

    @classmethod
    def _create_vim_code(cls, name: TaskName, vim_funcname: VimFuncName) -> str:
        """Helper to generate the complex VimL function block with error/repeat logic."""

        if __name__ != "__main__":
            prefix = f"{__name__}."
            import_prefix = f"from {__name__} import TimerTask, TimerStopException"
        else:
            prefix = ""
            import_prefix = " "

        python_procedures = dedent(
            f"""
            python3 << EOF
            {import_prefix}

            def work():
                name = '{name}'
                config = {prefix}TimerTask.CONFIG_MAP.get(name)
                status = {prefix}TimerTask.STATUS_MAP.get(name)
                func = {prefix}TimerTask.FUNCTION_MAP.get(name)

                if func is None or config is None or status is None:
                    return
                try:
                    func()
                except {prefix}TimerStopException as tse:
                    {prefix}TimerTask._schedule_deregister(name)
                    cause = tse.__cause__
                    if config.on_finish and (not cause):
                        config.on_finish('stopped')
                    elif config.on_error and cause:
                        config.on_error(cause)
                    elif cause:
                        raise cause
                    return
                except Exception as e:
                    {prefix}TimerTask._schedule_deregister(name)
                    if config.on_error:
                        config.on_error(e)
                    raise e

                repeat = status.repeat
                if repeat > 0:
                    status.repeat = status.repeat - 1 
                    if status.repeat == 0:
                        {prefix}TimerTask._schedule_deregister(name)
                        if config.on_finish:
                            config.on_finish("finished")
                        return
            work()
            EOF
        """).strip()

        vim_code = dedent(f"""
            function! {vim_funcname}(timer)
                {python_procedures}
            endfunction
        """)

        return vim_code.strip()

    # Vim Function, which is used as an ending function for the task.
    vim.command(
        dedent("""
    function! VimPytoyTimerTaskDeleteFunction_private(name, timer_id)
        call timer_stop(a:timer_id)
        execute 'delfunction!' . a:name
    endfunction
    """).strip()
    )

    @classmethod
    def _schedule_deregister(cls, name: TaskName):
        """Deregisters the task from the timer thread asynchronously."""

        timer_id = cls.TIMER_MAP.get(name)
        vim_funcname = cls.VIMFUNCNAME_MAP.get(name)
        if not timer_id or not vim_funcname:
            return
        vim.command(
            dedent(f"""
            call timer_start(1, {{ -> VimPytoyTimerTaskDeleteFunction_private('{vim_funcname}', {timer_id}) }} )
        """).strip()
        )

        cls.TIMER_MAP.pop(name, None)
        cls.VIMFUNCNAME_MAP.pop(name, None)
        cls.FUNCTION_MAP.pop(name, None)
        cls.CONFIG_MAP.pop(name, None)
        cls.STATUS_MAP.pop(name, None)

    @classmethod
    def register(
        cls,
        func: OnTaskCallback,
        interval: int = 100,
        name: TaskName | None = None,
        repeat: int = -1,
        on_finish: OnFinishCallback | None = None,
        on_error: OnErrorCallback | None = None,
    ) -> str:
        """Register the function with optional repeat count and callbacks."""
        import inspect  # inspect requires a little bit long.

        interval = int(interval)
        if on_finish:
            on_finish = _wrap_to_one_argument_func(on_finish)
        if on_error:
            on_error = _wrap_to_one_argument_func(on_error)

        if len(inspect.signature(func).parameters) != 0:
            raise ValueError("Task Callback must be without parameters.")

        if name is None:
            name = f"AUTONAME{cls.counter}"

        config = _TaskConfig(
            on_finish=on_finish, on_error=on_error, initial_repeat=repeat
        )
        cls.CONFIG_MAP[name] = config
        cls.STATUS_MAP[name] = _TaskStatus(repeat=repeat)

        vim_funcname = f"LoopTask_{name}_{id(func)}_{cls.counter}"

        # VimLコードの生成と実行
        vim_code = cls._create_vim_code(name, vim_funcname)
        vim.command(vim_code)

        # Vim側の repeat オプションは常に -1 (無限) に設定し、管理は Python 側で行う
        vim_repeat_opt = -1
        timer_id = int(
            vim.eval(
                f"timer_start({interval}, '{vim_funcname}', {{'repeat': {vim_repeat_opt}}})"
            )
        )

        cls.FUNCTION_MAP[name] = func
        cls.VIMFUNCNAME_MAP[name] = vim_funcname
        cls.TIMER_MAP[name] = timer_id
        cls.counter += 1
        return name

    @classmethod
    def deregister(cls, name: TaskName, *, strict: bool = False):
        if name not in cls.FUNCTION_MAP:
            if strict:
                raise ValueError(f"No timer task registered with name: '{name}'")
        cls._schedule_deregister(name)

    @classmethod
    def is_registered(cls, name: str):
        return name in cls.TIMER_MAP

    @classmethod
    def execute_oneshot(cls, func, interval: int = 100, name: str | None = None):
        """Execute the function only one time"""
        return cls.register(func, interval=interval, name=name, repeat=1)


if __name__ == "__main__":
    def hello():
        print("H")
    TimerTask.register(hello)
