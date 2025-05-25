"""PyTestCommand
"""
import vim
from pytoy.command_utils import CommandManager
from pytoy.ui_utils import create_window
from pytoy import ui_utils


@CommandManager.register(name="Pytest")
class PyTestCommand:
    name = "Pytest"
    def __call__(self, command_type: str="func"):
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
    def __call__(self):
        from pytoy.pytools_executors import MypyExecutor
        from pytoy import TERM_STDOUT
        import vim

        from pytoy.ui_utils import create_window
        path = vim.current.buffer.name
        executor = MypyExecutor()
        stdout_window = create_window(TERM_STDOUT, "vertical")
        executor.runfile(path, stdout_window.buffer)


@CommandManager.register(name="GotoDefinition")
class GotoDefinitionCommand:
    def __call__(self, arg: str="try_both"):

        if arg.lower() == "jedi":
            self._go_to_by_jedi()
        elif arg.lower() == "coc":
            self._go_to_by_coc()
        else:
            try:
                self._go_to_by_jedi()
                return
            except Exception as e:
                print(e)
            try:
                self._go_to_by_coc()
            except Exception as e:
                print(e)

    def customlist(self, arg_lead:str, cmd_line: str, cursor_pos:int):
        candidates = ["jedi", "coc"]
        valid_candidates = [elem for elem in candidates if elem.startswith(arg_lead)]
        if valid_candidates:
            return valid_candidates
        return candidates

    def _go_to_by_coc(self):
        ui_utils.sweep_windows(exclude=[vim.current.window])

        if ui_utils.is_leftwindow():
            vim.command("rightbelow vsplit | wincmd l")
            vim.command("call CocAction('jumpDefinition')")
        else:
            vim.command("call CocAction('jumpDefinition')")

    def _go_to_by_jedi(self):
        """
        Utility function to handle `jedi-vim`.
        * https://github.com/davidhalter/jedi-vim
        """
        ui_utils.sweep_windows(exclude=[vim.current.window])
        v = vim.eval("g:jedi#use_splits_not_buffers")
        if ui_utils.is_leftwindow():
            vim.command(f"let g:jedi#use_splits_not_buffers='right'")
        else:
            vim.command(f"let g:jedi#use_splits_not_buffers=''")

        vim.command(f"call g:jedi#goto()")
        vim.command(f"let g:jedi#use_splits_not_buffers='{v}'")

