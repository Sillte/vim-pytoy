from typing import Sequence
from pytoy.command import CommandManager
from pytoy.ui import make_buffer
from pytoy.infra.command.models import OptsArgument
from pytoy.ui.pytoy_buffer import PytoyBuffer

from pytoy.infra.timertask import  ThreadWorker


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
        from pytoy_llm.models import InputMessage


        buffer = make_buffer("__pytoy__stdout", mode="vertical")
        PREFIX = "[pytoy-llm] Thinking..."
        buffer.append(PREFIX)

        def task_func() -> str:
            mes1 = InputMessage(role="system", content="Since this is called by vim and intended to be used by the substituted of the given message, please make it short like 4 lines. ")
            mes2 = InputMessage(role="user", content=f"The following is the given query from the user: {target}")
            return str(completion([mes1, mes2], output_format="str"))

        def on_finish(output: str) -> None:
            c_range = buffer.range_operator.find_first(PREFIX, reverse=True)
            if c_range is None:
                buffer.append(str(output))
            else:
                buffer.replace_text(c_range, output)
        ThreadWorker.run(task_func, on_finish)
