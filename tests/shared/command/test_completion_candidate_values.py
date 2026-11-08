from pathlib import Path
from typing import Annotated, Any, Literal, cast

from pytoy.shared.command.core.models import Argument, CommandModel, Option
from pytoy.shared.command.service.completion import CompletionCandidate, CompletionParam, CompletionService


def numeric_literal(value: Literal[1, 2]): ...


def path_argument(
    value: Annotated[str, Argument(completer=cast(Any, lambda: [Path("alpha.txt"), Path("beta.txt")]))],
): ...


def path_option(
    value: Annotated[str, Option(..., completer=cast(Any, lambda: [Path("alpha.txt"), Path("beta.txt")]))] = "",
): ...


def complete(func, cmd_line: str) -> set[CompletionCandidate]:
    model = CommandModel.from_callable(func)
    result = CompletionService().make_completions(
        model,
        CompletionParam(cmd_line=cmd_line, cursor_pos=len(cmd_line), offset=0),
    )
    return set(result.candidates)


def test_numeric_literal_values_are_string_completion_candidates():
    assert complete(numeric_literal, "") == {
        CompletionCandidate(start=0, end=0, value="1"),
        CompletionCandidate(start=0, end=0, value="2"),
    }


def test_argument_completer_values_are_string_completion_candidates():
    assert complete(path_argument, "") == {
        CompletionCandidate(start=0, end=0, value="alpha.txt"),
        CompletionCandidate(start=0, end=0, value="beta.txt"),
    }


def test_option_completer_values_are_string_completion_candidates():
    assert complete(path_option, "--value=") == {
        CompletionCandidate(start=0, end=8, value="--value=alpha.txt"),
        CompletionCandidate(start=0, end=8, value="--value=beta.txt"),
    }
