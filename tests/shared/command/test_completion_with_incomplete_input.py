from typing import Annotated, Literal

import pytest

from pytoy.shared.command.core.models import Argument, CommandModel, Option
from pytoy.shared.command.core.tokenizer import tokenize
from pytoy.shared.command.service.completion import CompletionCandidate, CompletionParam, CompletionService


def func_with_input(input: Annotated[str, Option(..., completer=lambda: ["input", "inside"])] = "input"): ...


def func_with_arg(arg: Annotated[Literal["first"], Argument(completer=lambda: ["first", "five"])]): ...


def func_with_special_values(
    value: Annotated[
        str,
        Option(..., completer=lambda: ["hello world", 'say "hi"', "back\\slash", "semi;colon", "single'quote"]),
    ] = "",
): ...


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


def test_completion_encodes_special_values_without_an_open_quote():
    candidates = complete("--value=", func_with_special_values)

    assert {tokenize(candidate.value)[0].value for candidate in candidates} == {
        "--value=hello world",
        '--value=say "hi"',
        "--value=back\\slash",
        "--value=semi;colon",
        "--value=single'quote",
    }
    assert all(candidate.value.startswith("--value=") for candidate in candidates)


@pytest.mark.parametrize("quote", ['"', "'"])
def test_completion_encodes_special_values_inside_an_open_quote(quote: str):
    candidates = complete(f"--value={quote}", func_with_special_values)

    assert {tokenize(candidate.value + quote)[0].value for candidate in candidates} == {
        "--value=hello world",
        '--value=say "hi"',
        "--value=back\\slash",
        "--value=semi;colon",
        "--value=single'quote",
    }
    assert all(candidate.value.startswith(f"--value={quote}") for candidate in candidates)


@pytest.mark.parametrize("cursor_offset", [-1, 0])
def test_completion_preserves_closed_quote_for_argument(cursor_offset: int):
    cmd_line = '"fi"'

    assert complete(cmd_line, func_with_arg, cursor_pos=len(cmd_line) + cursor_offset) == {
        CompletionCandidate(start=0, end=4, value='"first"'),
        CompletionCandidate(start=0, end=4, value='"five"'),
    }


def test_completion_uses_prefix_inside_closed_quote():
    cmd_line = '--input="in"'

    assert complete(cmd_line, func_with_input, cursor_pos=len(cmd_line) - 1) == {
        CompletionCandidate(start=0, end=len(cmd_line), value='--input="input"'),
        CompletionCandidate(start=0, end=len(cmd_line), value='--input="inside"'),
    }


@pytest.mark.parametrize("quote", ['"', "'"])
@pytest.mark.parametrize("cursor_offset", [-1, 0])
def test_completion_encodes_special_values_inside_a_closed_quote(quote: str, cursor_offset: int):
    cmd_line = f"--value={quote}{quote}"
    candidates = complete(cmd_line, func_with_special_values, cursor_pos=len(cmd_line) + cursor_offset)

    assert {tokenize(candidate.value)[0].value for candidate in candidates} == {
        "--value=hello world",
        '--value=say "hi"',
        "--value=back\\slash",
        "--value=semi;colon",
        "--value=single'quote",
    }
    assert all(candidate.start == 0 and candidate.end == len(cmd_line) for candidate in candidates)
    assert all(
        candidate.value.startswith(f"--value={quote}") and candidate.value.endswith(quote) for candidate in candidates
    )
