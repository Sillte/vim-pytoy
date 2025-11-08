import vim

import inspect


class TimerTask:
    """Using `timer_start` function, it enables asyncronous process
    executed in VIM main loop.
    Especially, it is expected to use updating UI of VIM.

    """

    FUNCTION_MAP = dict()  # name -> function
    TIMER_MAP = dict()  # name -> timer-id
    VIMFUNCNAME_MAP = dict()  # name -> vim_funcname

    counter = 0

    @classmethod
    def register(cls, func, interval: int = 100, name: str | None = None) -> str:
        """Register the function without the argument."""
        interval = int(interval)
        sig = inspect.signature(func)
        if len(sig.parameters) != 0:
            raise ValueError("Callback must be without parameters.")

        if name is None:
            name = f"AUTONAME{cls.counter}"

        vim_funcname = f"LoopTask_{name}_{id(func)}"
        if __name__ != "__main__":
            prefix = f"{__name__}."
            import_prefix = f"from {__name__} import TimerTask; "
        else:
            prefix = ""
            import_prefix = " "

        procedures = (
            f"python3 {import_prefix} {prefix}TimerTask.FUNCTION_MAP['{name}']()"
        )

        vim.command(f"""function! {vim_funcname}(timer) 
            {procedures}
            endfunction
            """)
        timer_id = int(
            vim.eval(f"timer_start({interval}, '{vim_funcname}', {{'repeat': -1}})")
        )

        cls.FUNCTION_MAP[name] = func
        cls.VIMFUNCNAME_MAP[name] = vim_funcname
        cls.TIMER_MAP[name] = timer_id
        cls.counter += 1
        return name

    @classmethod
    def deregister(cls, name: str):
        if name not in cls.FUNCTION_MAP:
            raise ValueError("No `{name=}` exist for deregistration")

        timer_id = cls.TIMER_MAP[name]
        vim.eval(f"timer_stop({timer_id})")
        vim_funcname = cls.VIMFUNCNAME_MAP[name]
        vim.command(f"delfunction! {vim_funcname}")

        del cls.TIMER_MAP[name]
        del cls.VIMFUNCNAME_MAP[name]
        del cls.FUNCTION_MAP[name]

    @classmethod
    def is_registered(cls, name: str):
        return name in cls.TIMER_MAP

    @classmethod
    def execute_oneshot(cls, func, interval: int = 100, name: str | None = None):
        """Execute the function only one time"""
        interval = int(interval)
        sig = inspect.signature(func)
        if len(sig.parameters) != 0:
            raise ValueError("Callback must be without parameters.")

        if name is None:
            name = f"ONESHOT_AUTONAME{cls.counter}"
        cls.counter += 1

        vim_funcname = f"OneShotTask_{name}_{id(func)}"

        procedures = f"""
python3 << EOF
from {__name__} import TimerTask
TimerTask.FUNCTION_MAP['{name}']()
del TimerTask.FUNCTION_MAP['{name}']
del TimerTask.VIMFUNCNAME_MAP['{name}']
EOF
    """.strip()

        vim.command(f"""function! {vim_funcname}(timer) 
            {procedures}
            call timer_start(10, {{ -> execute('delfunction! {vim_funcname}') }})
            endfunction
            """)

        cls.FUNCTION_MAP[name] = func
        cls.VIMFUNCNAME_MAP[name] = vim_funcname
        timer_id = int(
            vim.eval(f"timer_start({interval}, '{vim_funcname}', {{'repeat': 1}})")
        )
        return timer_id


if __name__ == "__main__":

    def hello():
        print("H")

    TimerTask.register(hello)
