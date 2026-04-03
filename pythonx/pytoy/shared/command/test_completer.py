import pytest
from typing import Literal, Annotated
from pytoy.shared.command.models import CommandModel, Completer, Option, Argument

from pytoy.shared.command.completion import CandiateFactory, CmdlineStatus, NextTokenResolver, CompletionCandidate
from pytoy.shared.command.tokenizer import tokenize


def run_case(cmd_line: str, cursor_pos: int, model: CommandModel, debug: bool = False) -> dict:
    tokens = tokenize(cmd_line)
    status = CmdlineStatus(
        cmd_line=cmd_line,
        cursor_pos=cursor_pos,
        tokens=tokens,
        command_model=model,
    )

    current_position = status.current_position
    resolver = NextTokenResolver()

    if current_position.current_token:
        prev_tokens = [
            t for t in tokens
            if t.end < current_position.cursor_pos
        ]
    else:
        prev_tokens = tokens
    appeals = resolver.resolve_appeals(prev_tokens, model)

    factory = CandiateFactory()
    candidates = factory.create(current_position, appeals, model)

    if debug:
        print("----")
        print(f"INPUT : '{cmd_line}' (cursor={cursor_pos})")
        print("TOKENS:", [t.value for t in tokens])
        print("POS   :", status.current_position)
        print("APPEAL:", [a for a in appeals])
        print("CANDS :", [c for c in candidates])
        print("----", flush=True)

    result = dict()
    result["candidates"] = candidates
    result["appeals"] = appeals
    return result


# --- functions ---
def func_with_input(input: Annotated[str, Option(..., completer=lambda: ["input", "output"])] = "input"): ...
def func_with_input_and_literal(input: Annotated[Literal["input"] | str, Option(..., completer=lambda: ["in1", "out1"])] = "input"): ...
def func_arg_completer(arg: Annotated[Literal["five"], Argument(completer=lambda: ["first", "second", "five"])]):...


@pytest.mark.parametrize(
    "cmd_line,cursor,func,expected",
    [
        (
            "--i",
            2,
            func_with_input,
            {CompletionCandidate(start=0, end=3, value="--input")},
        ),
        (
            "--input=i",
            8,
            func_with_input_and_literal,
            {CompletionCandidate(start=0, end=9, value="--input=in1"), CompletionCandidate(start=0, end=9, value="--input=input")},
        ),
        (
            "f",
            0,
            func_arg_completer,
            {CompletionCandidate(start=0, end=1, value="first"), CompletionCandidate(start=0, end=1, value="five")},
        ),
    ],
)
def test_completion(cmd_line, cursor, func, expected):
    model = CommandModel.from_callable(func)
    result = run_case(cmd_line, cursor, model, debug=False)
    assert set(result["candidates"]) == expected

if __name__ == "__main__":
    pytest.main([__file__, "--capture=no"])


    #cmd_line = "--input=i"
    #cursor = 8
    #model = CommandModel.from_callable(func_with_input_and_literal)
    #print(model)
    #result = run_case(cmd_line, cursor, model, debug=True)

    #cmd_line = "f"
    #cursor = 0
    #model = CommandModel.from_callable(func_arg_completer)
    #print(model)
    #result = run_case(cmd_line, cursor, model, debug=True)
