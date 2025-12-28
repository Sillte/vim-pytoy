
import vim
from pytoy.infra.timertask.timer import TimerTask, TimerStopException

import threading
from typing import Callable, Any

from dataclasses import dataclass


@dataclass
class _WorkState:
    done: bool = False
    error: Exception | None = None
    main_return: Any | None = None


class ThreadWorker:
    """Execute a heady load task in the other thread.
    Note that callback functions are executed in the context of main thread,
    but the main_functinon is executed in non-main thread.
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

        thread = threading.Thread(target=_target, daemon=True)
        thread.start()

        def _check_status():
            if work_state.done:
                # 終了していたらタイマーを止めてCallbackを呼ぶ
                if work_state.error:
                    if on_error:
                        on_error(work_state.error)
                    else:
                        print(f"Error in thread: {work_state.error}")
                        err_type = type(work_state.error).__name__
                        msg = f"{err_type}: {work_state.error}"
                        vim.command(
                            f"echohl ErrorMsg | echom '[ThreadWorker Error] {msg.replace(chr(39), chr(39) * 2)}' | echohl None"
                        )
                else:
                    if on_finish:
                        on_finish(work_state.main_return)
                raise TimerStopException()

        TimerTask.register(
            _check_status,
            interval=polling_interval,
            name=f"TimerTaskThreadWorker_{thread.ident}",
        )