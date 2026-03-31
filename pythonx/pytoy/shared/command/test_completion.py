import pytest
from typing import Literal
from pytoy.shared.command.models import CommandModel

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


def test_case1():
    def func(arg: str, input: str = "DDD"): ...
    model = CommandModel.from_callable(func)
    result = run_case("--i", 2, model)
    assert set(result["candidates"]) == {CompletionCandidate(start=0, end=3, value="--input")}
    

# --- functions ---
def arg_and_input(arg: str, input: str = "DDD"): ...
def arg_and_input_literal_dd(arg: str, input: Literal["DDD", "DDQ"] = "DDD"): ...
def arg_and_input_literal_kk(arg: str, input: Literal["DDD", "KKK"] = "KKK"): ...
def arg_literal(arg: Literal["apple", "banana"]): ...
def arg_literal_with_option(arg: Literal["foo", "bar"], input: str = "hogehoge"): ...
def only_option(input: str = "hogehoge"): ...

@pytest.mark.parametrize(
    "cmd_line,cursor,func,expected",
    [
        # case1,2
        (
            "--i",
            2,
            arg_and_input,
            {CompletionCandidate(start=0, end=3, value="--input")},
        ),
        (
            "--in",
            4,
            arg_and_input,
            {CompletionCandidate(start=0, end=4, value="--input")},
        ),

        # case3
        (
            "--input ",
            8,
            arg_and_input_literal_dd,
            {
                CompletionCandidate(start=8, end=8, value="DDD"),
                CompletionCandidate(start=8, end=8, value="DDQ"),
            },
        ),

        # case4
        (
            "--input K",
            8,
            arg_and_input_literal_kk,
            {CompletionCandidate(start=8, end=9, value="KKK")},
        ),

        # case5
        (
            "--input=K",
            8,
            arg_and_input_literal_kk,
            {CompletionCandidate(start=0, end=9, value="--input=KKK")},
        ),

        # case6
        (
            "a",
            1,
            arg_literal,
            {CompletionCandidate(start=0, end=1, value="apple")},
        ),

        # case7
        (
            "",
            0,
            arg_literal_with_option,
            {
                CompletionCandidate(start=0, end=0, value="foo"),
                CompletionCandidate(start=0, end=0, value="bar"),
            },
        ),

        # case8
        (
            "-",
            0,
            arg_literal_with_option,
            {
                CompletionCandidate(start=0, end=1, value="--input"),
            },
        ),

        # case9
        (
            "--unknown",
            9,
            only_option,
            set(),
        ),
    ],
)
def test_completion(cmd_line, cursor, func, expected):
    model = CommandModel.from_callable(func)
    result = run_case(cmd_line, cursor, model)
    assert set(result["candidates"]) == expected

if __name__ == "__main__":
    pytest.main([__file__, "--capture=no"])