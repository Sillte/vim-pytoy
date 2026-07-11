"""Python related commands."""

from typing import Literal, Annotated
from pytoy.shared.command import App, Argument


app = App()


@app.command("Pytest")
def pytest_command(scope: Annotated[Literal["func", "file", "folder", "workspace"], Argument()] = "func"):
    from pytoy.tools.python.pytest_runner import PytestRunner

    PytestRunner().run(scope=scope, cwd=None)


@app.command(name="Mypy")
def mypy_command(target: Annotated[Literal["workspace", "current", "rerun"] | str | None, Argument()] = None):
    from pytoy.tools.python.mypy_checker import MypyChecker

    checker = MypyChecker()
    match target:
        case "rerun":
            checker.rerun()
        case _:
            checker.check(target)


@app.command(name="CSpell")
def cspell_command():
    from pytoy.tools.python.cspell_runner import CSpellRunner

    CSpellRunner().run()


@app.command(name="RuffCheck")
def ruff_check(
    target: Annotated[Literal["workspace", "current", "rerun"] | None | str, Argument()] = None,
    fix: bool = True,
    format: bool = False,
    unsafe: bool = False,
):
    from pytoy.tools.python.ruff_checker import RuffChecker

    checker = RuffChecker()
    match target:
        case "rerun":
            checker.rerun()
        case _:
            checker.check(target, fix, format, unsafe)


if __name__ == "__main__":
    pass
