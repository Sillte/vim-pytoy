"""PyTestCommand
"""

import vim
from pytoy.command import CommandManager
from pytoy.ui_utils import create_window, store_window
from pytoy.ui_pytoy import PytoyBuffer, make_buffer
from pytoy import ui_utils


@CommandManager.register(name="Pytest")
class PyTestCommand:
    name = "Pytest"

    def __call__(self, command_type: str = "func"):
        import vim
        from pytoy.pytools_executors import PytestExecutor
        from pytoy import TERM_STDOUT

        executor = PytestExecutor()
        pytoy_buffer = make_buffer(TERM_STDOUT, "vertical")
        if command_type == "func":
            path = vim.current.buffer.name
            line = int(vim.eval("line('.')"))
            executor.runfunc(path, line, pytoy_buffer)
        elif command_type == "file":
            path = vim.current.buffer.name
            executor.runfile(path, pytoy_buffer)
        elif command_type == "all":
            executor.runall(pytoy_buffer)
        else:
            raise ValueError(f"Specified `command_type` is not valid.")

    def customlist(self, arg_lead: str, cmd_line: str, cursor_pos: int):
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
        path = vim.current.buffer.name
        executor = MypyExecutor()
        pytoy_buffer = make_buffer(TERM_STDOUT, "vertical")
        executor.runfile(path, pytoy_buffer)


@CommandManager.register(name="GotoDefinition")
class GotoDefinitionCommand:
    def __call__(self, arg: str = "try_both"):
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

    def customlist(self, arg_lead: str, cmd_line: str, cursor_pos: int):
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
        import jedi_vim
        ui_utils.sweep_windows(exclude=[vim.current.window])
        v = vim.eval("g:jedi#use_splits_not_buffers")
        if ui_utils.is_leftwindow():
            vim.command(f"let g:jedi#use_splits_not_buffers='right'")
        else:
            vim.command(f"let g:jedi#use_splits_not_buffers=''")

        names = jedi_vim.goto(mode="goto")
        vim.command(f"let g:jedi#use_splits_not_buffers='{v}'")
        if not names:
            raise ValueError("Cannot use `jedi_vim.goto`")


@CommandManager.register(name="RuffCheck")
class RuffChecker:
    def __call__(self):
        from pathlib import Path
        from pytoy import TERM_STDOUT
        from pytoy.pytools_executors import RuffExecutor

        path = vim.current.buffer.name
        pytoy_buffer = make_buffer(TERM_STDOUT, "vertical")
        executor = RuffExecutor()
        executor.check_file(Path(path), pytoy_buffer) 



@CommandManager.register(name="CSpell")
class CSpellCommand:
    def __call__(self):
        import re

        from pathlib import Path
        from pytoy import TERM_STDOUT
        from pytoy.pytools_utils.cspell_utils import CSpellOneFileChecker

        path = vim.current.buffer.name
        if Path(path).suffix == ".py":
            checker = CSpellOneFileChecker(only_python_string=True)
        else:
            checker = CSpellOneFileChecker(only_python_string=False)
        output = checker(path)

        records = []
        pattern = re.compile(
            r"(?P<filename>.+):(?P<lnum>\d+):(?P<col>\d+).*\((?P<text>(.+))\)"
        )
        lines = output.split("\n")
        for line in lines:
            m = pattern.match(line)
            if m:
                record = m.groupdict()
                records.append(record)

        # [TODO]: It cannot be used in nvim.
        setloclist = vim.bindeval('function("setloclist")')

        win_id = vim.eval("win_getid()")
        if records:
            setloclist(win_id, records)
            unknow_words = list(set(str(item["text"]) for item in records))
            with store_window():
                vim.command("lopen")

            buffer = make_buffer(TERM_STDOUT, "vertical")
            buffer.init_buffer()
            buffer.append(f"**UNKNOWN WORDS**")
            buffer.append(f"{unknow_words}")
        else:
            print("No unknown words.")
