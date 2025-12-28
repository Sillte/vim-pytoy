from typing import Sequence
from pytoy.command import CommandManager
from pytoy.ui import make_buffer
from pytoy.infra.command.models import OptsArgument
from pytoy.ui.pytoy_buffer import PytoyBuffer

from pytoy.infra.timertask import TimerTask, ThreadWorker


import threading
from typing import Callable, Any, Optional

from dataclasses import dataclass


@CommandManager.register("PytoyLLM", range="")
class PytoyLLMCommand:
    def __call__(self, opts: OptsArgument):
        ...
        line1 = opts.line1
        line2 = opts.line2

        content = PytoyBuffer.get_current().content
        lines = content.split("\n")
        if line1 is not None and line2 is not None:
            target = "\n".join(lines[line1 - 1 : line2 + 1 - 1])
        else:
            target = content
        from pytoy_llm import completion


        buffer = make_buffer("__pytoy__stdout", mode="vertical")

        def task_func() -> str:
            return str(completion(target, output_format="str"))

        def on_finish(output: str) -> None:
            buffer.append(str(output))

        ThreadWorker.run(task_func, on_finish)

