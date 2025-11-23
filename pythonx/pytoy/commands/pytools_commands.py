"""Python related commands."""

from typing import Sequence
import vim
from pytoy.command import CommandManager
from pytoy.ui import make_buffer
from pytoy.ui.ui_enum import get_ui_enum, UIEnum
from pytoy.ui.pytoy_window import PytoyWindow
from pytoy.ui.utils import to_filepath
from pytoy.ui.pytoy_quickfix import QuickFixRecord


@CommandManager.register(name="Pytest")
class PyTestCommand:
    name = "Pytest"

    def __call__(self, command_type: str = "func"):
        import vim
        from pytoy.lib_tools import BufferExecutor
        from pytoy import TERM_STDOUT

        path = to_filepath(vim.current.buffer.name)
        cwd = path.parent
        line = int(vim.eval("line('.')"))

        from pytoy.tools.pytest.utils import to_func_command, PytestDecipher
        pytoy_buffer = make_buffer(TERM_STDOUT, "vertical")

        command_type_to_func = {}
        suffix = "--capture=no --quiet"
        command_type_to_func["func"] = lambda path, line: to_func_command(path, line, suffix)
        command_type_to_func["file"] = lambda path, line: f"pytest '{path}' {suffix}"
        command_type_to_func["all"] = lambda path, line: f"pytest {suffix}"

        def make_qf_records(content: str) -> Sequence[QuickFixRecord]:
            rows = PytestDecipher(content).records
            return [QuickFixRecord.from_dict(row) for row in rows]
        
        command = command_type_to_func[command_type](path, line)
        
        executor = BufferExecutor("PytestCommand", stdout=pytoy_buffer)
        executor.run(command, make_qf_records, cwd=cwd)
        
    def customlist(self, arg_lead: str, cmd_line: str, cursor_pos: int):
        candidates = ["func", "file", "all"]
        valid_candidates = [elem for elem in candidates if elem.startswith(arg_lead)]
        if valid_candidates:
            return valid_candidates
        return candidates


@CommandManager.register(name="Mypy")
class MypyCommand:
    def __call__(self, opts: dict):
        from pytoy.lib_tools import BufferExecutor
        from pytoy import TERM_STDOUT
        from pytoy.lib_tools.environment_manager import EnvironmentManager
        from pytoy.commands.utils import override, workspace_func, fallback_argument
        import vim


        current_path = str(to_filepath(vim.current.buffer.name))
        
        fargs = opts["fargs"]
        fargs = override(fargs, {"workspace": workspace_func})
        fargs = fallback_argument(fargs, current_path)

        pytoy_buffer = make_buffer(TERM_STDOUT, "vertical")
        arg = " ".join(map(str, fargs))
        command = f'mypy --show-traceback --show-column-numbers "{arg}"'
        executor = BufferExecutor("MypyExecutor", pytoy_buffer)

        quickfix_regex = r"(?P<filename>.+):(?P<lnum>\d+):(?P<col>\d+):(?P<_type>(.+)):(?P<text>(.+))"
        executor.run(command, quickfix_regex)


    def customlist(self, arg_lead: str, cmd_line: str, cursor_pos: int):
        candidates = ["workspace"]
        valid_candidates = [elem for elem in candidates if elem.startswith(arg_lead)]
        if valid_candidates:
            return valid_candidates
        return candidates


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



@CommandManager.register(name="CSpell")
class CSpellCommand:
    def __call__(self):

        from pathlib import Path
        from pytoy import TERM_STDOUT
        from pytoy.tools.cspell import CSpellOneFileChecker
        from pytoy.ui import to_filepath
        from pytoy.ui.pytoy_quickfix import PytoyQuickFix, handle_records, to_quickfix_creator

        path = to_filepath(vim.current.buffer.name)

        if Path(path).suffix == ".py":
            checker = CSpellOneFileChecker(only_python_string=True)
        else:
            checker = CSpellOneFileChecker(only_python_string=False)
        output = checker(path)
        regex = r"(?P<filename>.+):(?P<lnum>\d+):(?P<col>\d+).*\((?P<text>(.+))\)"
        maker = to_quickfix_creator(regex)
        records = maker(output)
        handle_records(PytoyQuickFix(cwd=path.parent), records, win_id=None)


@CommandManager.register(name="RuffCheck")
class RuffChecker:
    def __call__(self, opts: dict):
        from pytoy import TERM_STDOUT
        from pytoy.lib_tools.buffer_executor import BufferExecutor
        from pytoy.lib_tools.environment_manager import EnvironmentManager
        from pytoy.commands.utils import override, workspace_func, fallback_argument

        pytoy_buffer = make_buffer(TERM_STDOUT, "vertical")
        executor = BufferExecutor("RuffChecer", pytoy_buffer)

        current_path = str(to_filepath(vim.current.buffer.name))

        fargs = opts["fargs"]
        fargs = override(fargs, {"workspace": workspace_func})
        fargs = fallback_argument(fargs, current_path)
        def _format() -> None:
            executor.sync_run(f"ruff format {fargs[0]}")
        fargs = override(fargs, {"--format": _format})

        command = f"ruff check {' '.join(map(str, fargs))} --output-format=concise"
        regex = r"(?P<filename>.+):(?P<lnum>\d+):(?P<col>\d+):(?P<text>(.+))"
        executor.run(command, quickfix_creator=regex)

    def customlist(self, arg_lead: str, cmd_line: str, cursor_pos: int):
        candidates = ["workspace", "--fix", "--format", "--unsafe-fixes"]
        valid_candidates = [elem for elem in candidates if elem.startswith(arg_lead)]
        if valid_candidates:
            return valid_candidates
        return candidates