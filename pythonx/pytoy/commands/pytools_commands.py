"""Python related commands."""

import vim
from pytoy.command import CommandManager
from pytoy.ui import make_buffer
from pytoy.ui.ui_enum import get_ui_enum, UIEnum
from pytoy.ui.pytoy_window import PytoyWindow
from pytoy.ui.utils import to_filepath


@CommandManager.register(name="Pytest")
class PyTestCommand:
    name = "Pytest"

    def __call__(self, command_type: str = "func"):
        import vim
        from pytoy.tools import PytestExecutor
        from pytoy import TERM_STDOUT

        executor = PytestExecutor()
        # `make_buffer` may change the current buffer.
        path = vim.current.buffer.name
        path = to_filepath(path)
        line = int(vim.eval("line('.')"))

        pytoy_buffer = make_buffer(TERM_STDOUT, "vertical")
        if command_type == "func":
            executor.runfunc(path, line, pytoy_buffer)
        elif command_type == "file":
            executor.runfile(path, pytoy_buffer)
        elif command_type == "all":
            executor.runall(pytoy_buffer)
        else:
            raise ValueError("Specified `command_type` is not valid.")

    def customlist(self, arg_lead: str, cmd_line: str, cursor_pos: int):
        candidates = ["func", "file", "all"]
        valid_candidates = [elem for elem in candidates if elem.startswith(arg_lead)]
        if valid_candidates:
            return valid_candidates
        return candidates


@CommandManager.register(name="Mypy")
class MypyCommand:
    def __call__(self):
        from pytoy.tools.mypy import MypyExecutor
        from pytoy import TERM_STDOUT
        import vim

        path = vim.current.buffer.name
        path = to_filepath(path)
        executor = MypyExecutor()
        pytoy_buffer = make_buffer(TERM_STDOUT, "vertical")
        executor.runfile(path, pytoy_buffer)


@CommandManager.register(name="GotoDefinition")
class GotoDefinitionCommand:
    def __call__(self, arg: str = "try_both"):
        if get_ui_enum() not in {UIEnum.VIM, UIEnum.NVIM}:
            raise RuntimeError("This command is only available in  VIM and NVIM.")
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
        PytoyWindow.get_current().unique()
        if PytoyWindow.get_current().is_left():
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

        PytoyWindow.get_current().unique()
        v = vim.eval("g:jedi#use_splits_not_buffers")
        if PytoyWindow.get_current().is_left():
            vim.command("let g:jedi#use_splits_not_buffers='right'")
        else:
            vim.command("let g:jedi#use_splits_not_buffers=''")

        names = jedi_vim.goto(mode="goto")
        vim.command(f"let g:jedi#use_splits_not_buffers='{v}'")
        if not names:
            raise ValueError("Cannot use `jedi_vim.goto`")


@CommandManager.register(name="RuffCheck")
class RuffChecker:
    def __call__(self, opts: dict):
        from pytoy import TERM_STDOUT
        from pytoy.tools.ruff import RuffExecutor
        from pytoy.lib_tools.environment_manager import EnvironmentManager

        fargs = opts["fargs"]
        if "workspace" in fargs:
            # This is using the knowledge that
            # `The parent of virtualenv folder is the root of the project`.
            venv_folder = EnvironmentManager().get_uv_venv()
            if not venv_folder:
                raise ValueError("This is not under UV workspace.")
            root_folder = venv_folder.parent
            path = root_folder
            fargs.remove("workspace")
            fargs.append(str(path))

        arguments = [elem for elem in fargs if not elem.startswith("-")]
        if not arguments:
            path = vim.current.buffer.name
            path = to_filepath(path)
            fargs.append(path)

        executor = RuffExecutor()
        pytoy_buffer = make_buffer(TERM_STDOUT, "vertical")
        executor.check(fargs, pytoy_buffer)

    def customlist(self, arg_lead: str, cmd_line: str, cursor_pos: int):
        candidates = ["workspace", "--fix"]
        valid_candidates = [elem for elem in candidates if elem.startswith(arg_lead)]
        if valid_candidates:
            return valid_candidates
        return candidates


@CommandManager.register(name="CSpell")
class CSpellCommand:
    def __call__(self):
        import re

        from pathlib import Path
        from pytoy import TERM_STDOUT
        from pytoy.tools.cspell import CSpellOneFileChecker
        from pytoy.ui import to_filepath

        path = to_filepath(vim.current.buffer.name)
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
            buffer = make_buffer(TERM_STDOUT, "vertical")
            buffer.init_buffer()
            buffer.append("**UNKNOWN WORDS**")
            buffer.append(f"{unknow_words}")
        else:
            print("No unknown words.")
