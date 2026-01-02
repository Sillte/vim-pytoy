from typing import Sequence
from pytoy.command import CommandManager
from pytoy.ui import make_buffer
from pytoy.ui.pytoy_window import PytoyWindow, WindowCreationParam
from pytoy.infra.command.models import OptsArgument
from pytoy.ui.pytoy_window import PytoyWindow, CharacterRange
from pytoy.ui.notifications import EphemeralNotification

from pytoy.infra.timertask import ThreadWorker
from textwrap import dedent


@CommandManager.register("PytoyLLM", range="")
class PytoyLLMCommand:

    def _open_config(self):
        from pytoy_llm import get_configuration_path
        path = get_configuration_path()
        param = WindowCreationParam.for_split("vertical", try_reuse=True)
        PytoyWindow.open(path, param=param)


    def __call__(self, opts: OptsArgument):
        if opts.fargs and opts.fargs[0].strip() == "config":
            return self._open_config()

        current_window = PytoyWindow.get_current()
        current_buffer = current_window.buffer
        BUFFER_NAME = "MOCK_LLM" 
        from pytoy_llm import completion
        from pytoy_llm.models import InputMessage
        from pathlib import Path

        if Path(current_buffer.path).name != BUFFER_NAME:
            param = WindowCreationParam.for_split("vertical", try_reuse=True)
            target_window = PytoyWindow.open(BUFFER_NAME, param=param)
        else:
            target_window = current_window
        class RewritePrompt:
            def __init__(self, query_start: str, query_end: str, document: str):
                self.query_start = query_start
                self.query_end = query_end
                self.document = document

            def render(self) -> str:
                return dedent(f"""
                You are an assistant integrated into a code/text editor.

                Your task:
                - Rewrite the text strictly between the markers:
                  `{self.query_start}` and `{self.query_end}`

                Rules:
                - Output ONLY the rewritten text.
                - Do NOT include the markers themselves.
                - Do NOT add explanations or commentary.
                - Keep the original intent and tone.
                - You may rephrase, reorganize, or clarify the content.
                - Prefer similar length to the original unless clarity or correctness requires otherwise.
                - Select the appropriate language from the documents and query, either English or Japanese.
                - Complete any incomplete sentences or bullet points.
                - If the user provides hints like "???", "..." or placeholders, replace them with the most plausible information.
                - If you need plceholders or ellipsis to balance correctness and conciseness, you "..." in bullet points.

                Context:
                The following is the entire document for reference:

                <document>
                {self.document}
                </document>
                """).strip()

        class OneAction:
            def __init__(self, window: PytoyWindow):
                self.window = window
                self.buffer = window.buffer
                self.selection = window.selection
                self._id = self._gen_id()

            @property
            def id(self):
                return self._id

            @property
            def query_start(self) -> str: 
                return f"[pytoy-llm][{self.id}]>$>"

            @property
            def query_end(self) -> str: 
                return f">$>[pytoy-llm][{self.id}]"

            def construct_input(self, window: PytoyWindow, selection: CharacterRange) -> list[InputMessage]:
                document = self.window.buffer.content
                content = RewritePrompt(self.query_start, self.query_end, document).render()
                mes1 = InputMessage(role="system",
                                   content=content)
                return [mes1]

            def start(self):
                text = self.buffer.get_text(self.selection)
                operator = self.buffer.range_operator
                new_text = self.query_start + "\n" + text + "\n" + self.query_end
                target_selection = operator.replace_text(self.selection, new_text)
                inputs = self.construct_input(self.window, target_selection)
                ThreadWorker.run(lambda : self._task_func(inputs), self.on_finish, self.on_error)
                
            def _task_func(self, inputs: Sequence[InputMessage]) -> str:
                return str(completion(list(inputs), output_format="str"))  # This is time consuming

            def on_finish(self, output: str) -> None:
                start_range = self.buffer.range_operator.find_first(self.query_start, reverse=True)
                end_range = self.buffer.range_operator.find_first(self.query_end, reverse=True)
                if start_range is None or end_range is None:
                    print("Request is gone...")
                    return 
                cr = CharacterRange(start_range.start, end_range.end)
                self.buffer.range_operator.replace_text(cr, output)

            def on_error(self, exception: Exception) -> None:
                ThreadWorker.add_message(str(exception))
                EphemeralNotification().notify("LLM Error. See `:messages`.")

            def _gen_id(self) -> str:
                import random
                return str(random.randint(0, 10000))

        action = OneAction(target_window)
        action.start()