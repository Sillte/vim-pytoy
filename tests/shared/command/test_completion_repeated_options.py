from typing import Annotated

from pytoy.shared.command.core.models import CommandModel, Option
from pytoy.shared.command.core.tokenizer import InterpretedInput, ResolvedInput, tokenize
from pytoy.shared.command.service.completion import CompletionCandidate, CompletionParam, CompletionService


def list_option(tags: Annotated[list[str], Option(..., completer=lambda: ["one", "two"])] = []): ...


def scalar_option(tag: Annotated[str, Option(..., completer=lambda: ["one", "two"])] = ""): ...


def complete(func, cmd_line: str) -> set[CompletionCandidate]:
    model = CommandModel.from_callable(func)
    result = CompletionService().make_completions(
        model,
        CompletionParam(cmd_line=cmd_line, cursor_pos=len(cmd_line), offset=0),
    )
    return set(result.candidates)


def test_list_option_remains_available_after_use():
    cmd_line = "--tags=one --"

    assert complete(list_option, cmd_line) == {CompletionCandidate(start=11, end=len(cmd_line), value="--tags")}


def test_list_option_values_can_be_completed_again():
    cmd_line = "--tags=one --tags=t"
    model = CommandModel.from_callable(list_option)
    interpreted = InterpretedInput.from_tokens(tokenize("--tags=one --tags=two"), model)
    assert ResolvedInput.from_interpreted_input(model, interpreted).kwargs == {"tags": ["one", "two"]}

    assert complete(list_option, cmd_line) == {CompletionCandidate(start=11, end=len(cmd_line), value="--tags=two")}


def test_scalar_option_remains_unavailable_after_use():
    assert complete(scalar_option, "--tag=one --") == set()
