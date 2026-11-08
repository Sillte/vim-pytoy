from typing import Annotated, Literal

import pytest

from pytoy.shared.command.core.models import Argument, CommandModel, Option
from pytoy.shared.command.service.completion import CompletionCandidate, CompletionParam, CompletionService


def func_with_input(input: Annotated[str, Option(..., completer=lambda: ["input", "inside"])] = "input"): ...


def func_with_arg(arg: Annotated[Literal["first"], Argument(completer=lambda: ["first", "five"])]): ...


def complete(cmd_line: str, func, cursor_pos: int | None = None) -> set[CompletionCandidate]:
    model = CommandModel.from_callable(func)
    result = CompletionService().make_completions(
        model,
        CompletionParam(
            cmd_line=cmd_line,
            cursor_pos=len(cmd_line) if cursor_pos is None else cursor_pos,
            offset=0,
        ),
    )
    return set(result.candidates)


@pytest.mark.parametrize(
    "quote",
    ['"', "'"],
)
def test_completion_preserves_unclosed_quote_for_argument(quote: str):
    cmd_line = f"{quote}fi"

    assert complete(cmd_line, func_with_arg) == {
        CompletionCandidate(start=0, end=len(cmd_line), value=f"{quote}first"),
        CompletionCandidate(start=0, end=len(cmd_line), value=f"{quote}five"),
    }


def test_completion_uses_cursor_prefix_inside_unclosed_quote():
    cmd_line = '"fiX'

    assert complete(cmd_line, func_with_arg, cursor_pos=3) == {
        CompletionCandidate(start=0, end=len(cmd_line), value='"first'),
        CompletionCandidate(start=0, end=len(cmd_line), value='"five'),
    }


def test_completion_preserves_unclosed_quote_for_option_value():
    cmd_line = '--input="in'

    assert complete(cmd_line, func_with_input) == {
        CompletionCandidate(start=0, end=len(cmd_line), value='--input="input'),
        CompletionCandidate(start=0, end=len(cmd_line), value='--input="inside'),
    }


def test_completion_preserves_unclosed_quote_for_separate_option_value():
    cmd_line = '--input "in'

    assert complete(cmd_line, func_with_input) == {
        CompletionCandidate(start=8, end=len(cmd_line), value='"input'),
        CompletionCandidate(start=8, end=len(cmd_line), value='"inside'),
    }


def test_completion_tolerates_trailing_escape():
    assert complete("f\\", func_with_arg) == set()
