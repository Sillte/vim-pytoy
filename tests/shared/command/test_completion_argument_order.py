from typing import Annotated

from pytoy.shared.command.core.models import Argument, CommandModel
from pytoy.shared.command.core.tokenizer import InterpretedInput, ResolvedInput, tokenize
from pytoy.shared.command.service.completion import CompletionCandidate, CompletionParam, CompletionService


def command(
    first: Annotated[str, Argument()],
    optional: Annotated[str, Argument(completer=lambda: ["optional-candidate"])] = "default",
    *,
    later: Annotated[str, Argument(completer=lambda: ["later-candidate"])],
): ...


def complete(model: CommandModel, cmd_line: str) -> set[CompletionCandidate]:
    result = CompletionService().make_completions(
        model,
        CompletionParam(cmd_line=cmd_line, cursor_pos=len(cmd_line), offset=0),
    )
    return set(result.candidates)


def test_completion_uses_runtime_positional_argument_order():
    model = CommandModel.from_callable(command)

    interpreted = InterpretedInput.from_tokens(tokenize("first later-value"), model)
    resolved = ResolvedInput.from_interpreted_input(model, interpreted)
    assert resolved.arg_kwargs == {"first": "first", "later": "later-value", "optional": "default"}

    assert complete(model, "first ") == {CompletionCandidate(start=6, end=6, value="later-candidate")}
    assert complete(model, "first later-value ") == {CompletionCandidate(start=18, end=18, value="optional-candidate")}
