"""PyTestCommand
"""
from pytoy.command_utils import CommandManager
from pytoy.ui_utils import create_window


@CommandManager.register(name="Pytest")
class PyTestCommand:
    name = "Pytest"
    def __call__(self, *args):
        if not args:
            command_type = "func"
        else:
            command_type = args[0]

        import vim
        from pytoy.pytools_executors import PytestExecutor
        from pytoy import TERM_STDOUT

        executor = PytestExecutor()
        stdout_window = create_window(TERM_STDOUT, "vertical")
        if command_type == "func":
            path = vim.current.buffer.name
            line = vim.Function("line")(".")
            executor.runfunc(path, line, stdout_window.buffer)
        elif command_type == "file":
            path = vim.current.buffer.name
            executor.runfile(path, stdout_window.buffer)
        elif command_type == "all":
            executor.runall(stdout_window.buffer)
        else:
            raise ValueError(f"Specified `command_type` is not valid.")

    def customlist(self, arg_lead:str, cmd_line: str, cursor_pos:int):
        candidates = ["func", "file", "all"]
        valid_candidates = [elem for elem in candidates if elem.startswith(arg_lead)]
        if valid_candidates:
            return valid_candidates
        return candidates
        

@CommandManager.register(name="Mypy")
class MypyCommand:
    def __call__(self, *args):
        from pytoy.pytools_executors import MypyExecutor
        from pytoy import TERM_STDOUT
        import vim

        from pytoy.ui_utils import create_window
        path = vim.current.buffer.name
        executor = MypyExecutor()
        stdout_window = create_window(TERM_STDOUT, "vertical")
        executor.runfile(path, stdout_window.buffer)


