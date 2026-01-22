
from pytoy.infra.timertask.stdout_rescuer import StdoutProxy
import vim
from pytoy.infra.timertask.timer import TimerTask, TimerStopException
from pytoy.contexts.pytoy import GlobalPytoyContext 

import threading
from queue import Queue
from typing import Callable, Any, Literal, assert_never

from dataclasses import dataclass
import os


@dataclass
class _WorkState:
    done: bool = False
    error: Exception | None = None
    main_return: Any | None = None


class ThreadWorker:
    """Execute a heady load task in the other thread.
    Note that callback functions are executed in the context of main thread,
    but the main_function is executed in non-main thread.
    Hence, you have to perform the necessary ui-modification in callback class.
    
    """

    @classmethod
    def run(
        cls,
        main_func: Callable[[], Any],
        on_finish: Callable[[Any], None] | None = None,
        on_error: Callable[[Exception], None] | None = None,
        polling_interval: int = 50,
    ):
        """Execute"""
        work_state = _WorkState()

        def _target():
            try:
                work_state.main_return = main_func()
            except Exception as e:
                work_state.error = e
            finally:
                work_state.done = True

        StdoutProxy.ensure_activate()
        thread = threading.Thread(target=_target, daemon=True)
        thread.start()

        def _check_status():
            if work_state.done:
                try:
                    if work_state.error:
                        if on_error:
                            on_error(work_state.error)
                        else:
                            err_type = type(work_state.error).__name__
                            msg = f"{err_type}: {work_state.error}"
                            vim.command(
                                f"echohl ErrorMsg | echom '[ThreadWorker Error] {msg.replace(chr(39), chr(39) * 2)}' | echohl None"
                            )
                    else:
                        if on_finish:
                            on_finish(work_state.main_return)
                except Exception as e:
                    raise TimerStopException() from e
                # To prevent the infinite loop, if the problem occurs,
                # Stop the timer and raise the exception.
                raise TimerStopException()

        TimerTask.register(
            _check_status,
            interval=polling_interval,
            name=f"TimerTaskThreadWorker_{thread.ident}",
        )

    @classmethod
    def add_message(cls, message: str) -> None:
        """ This MUST be called in the main thread.
        The message is added to `:messages`. 
        The expected usecase is when you would like to store 
        the information of exception `on_error`.   
        However, if you use `print` or `echo`, 
        it disturbs user-experience.   
        So, only when you would like to store the excpetion details, 
        you call this function and notify the user to refer `:messages`.

        """
        message = message.replace("'", "''")
        vim.command(f"echom '{message}'")