from typing import Literal
import pytest

from pytoy.shared.command.tokenizer import (
    tokenize,
    InterpretedInput,
    ResolvedInput,
    BooleanOptionTakesNoValue
)
from pytoy.shared.command.models import CommandModel


def test_literal_basic():
    def func(mode: Literal["fast", "slow"]): ...

    model = CommandModel.from_callable(func)
    cmd_line = "fast"

    tokens = tokenize(cmd_line)
    interp = InterpretedInput.from_tokens(tokens, model)

    assert interp.arguments == ["fast"]
    assert interp.options == {}

    resolved = ResolvedInput.from_interpreted_input(model, interp)
    assert resolved.arg_kwargs["mode"] == "fast"
    assert resolved.kwargs == {}


def test_tokenize_preserves_token_boundaries():
    cmd_line = 'cmd "hello world" --flag'
    tokens = tokenize(cmd_line)

    assert [t.value for t in tokens] == ["cmd", "hello world", "--flag"]
    assert tokens[1].start == cmd_line.index("hello world")
    assert cmd_line[tokens[1].start : tokens[1].end] == "hello world"
    assert tokens[2].is_current_token(tokens[2].start)
    assert not tokens[2].is_current_token(tokens[2].end)


def test_interpret_tokens_boolean_options():
    def func(verbose: bool = False, level: int = 1): ...

    model = CommandModel.from_callable(func)

    tokens = tokenize("--verbose")
    interp = InterpretedInput.from_tokens(tokens, model)
    assert interp.arguments == []
    assert interp.options["verbose"] == [True]

    tokens = tokenize("--no-verbose")
    interp = InterpretedInput.from_tokens(tokens, model)
    assert interp.options["verbose"] == [False]

    tokens = tokenize("--verbose true")
    interp = InterpretedInput.from_tokens(tokens, model)
    assert any(isinstance(elem, BooleanOptionTakesNoValue) for elem in  interp.exceptions)


def test_interpret_tokens_option_value_assignment():
    from pathlib import Path

    def func(path: str, output: Path = Path("out.txt")): ...

    model = CommandModel.from_callable(func)

    tokens = tokenize("input.txt --output=result.txt")
    interp = InterpretedInput.from_tokens(tokens, model)
    assert interp.arguments == ["input.txt"]
    assert interp.options["output"] == ["result.txt"]
    r_input = ResolvedInput.from_interpreted_input(model, interp)
    assert r_input.kwargs["output"] == Path("result.txt")


def test_resolved_input_converts_types_and_uses_defaults():
    def func(count: int, debug: bool = False, tags: list[str] = []): ...

    model = CommandModel.from_callable(func)

    tokens = tokenize("42 --debug --tags=hello --tags=world")
    interp = InterpretedInput.from_tokens(tokens, model)
    resolved = ResolvedInput.from_interpreted_input(model, interp)

    assert resolved.arg_kwargs["count"] == 42
    assert resolved.kwargs["debug"] is True
    assert resolved.kwargs["tags"] == ["hello", "world"]


def test_resolved_input_rejects_unknown_option():
    def func(name: str): ...

    model = CommandModel.from_callable(func)
    interp = InterpretedInput(arguments=["foo"], options={"bad": ["value"]})

    with pytest.raises(ValueError, match="Unknown option: bad"):
        ResolvedInput.from_interpreted_input(model, interp)


def test_resolved_input_rejects_too_many_arguments():
    def func(name: str): ...

    model = CommandModel.from_callable(func)
    interp = InterpretedInput(arguments=["foo", "bar"], options={})

    with pytest.raises(ValueError, match="Too many arguments"):
        ResolvedInput.from_interpreted_input(model, interp)


def test_resolved_input_rejects_unconvertible_argument():
    def func(value: int): ...

    model = CommandModel.from_callable(func)
    interp = InterpretedInput(arguments=["not-a-number"], options={})

    with pytest.raises(TypeError, match="Cannot convert argument 'value' value 'not-a-number' to any allowed type"):
        ResolvedInput.from_interpreted_input(model, interp)

if __name__ == "__main__":
    pytest.main([__file__, "--capture=no"])