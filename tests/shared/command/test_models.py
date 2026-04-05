from pytoy.shared.command.core.models import RangeParam, CountParam, Field, CommandModel
from typing import Annotated

import pytest


def func_simple(arg: str, opt: int = 42): ...


def func_with_injected(rng: RangeParam, cnt: CountParam, normal: str = "hi"): ...


def func_with_union(arg: int | str, rng: RangeParam | None = None): ...


def func_with_annotated(opt: Annotated[int, Field(default=123)]): ...


def test_simple():
    model = CommandModel.from_callable(func_simple)
    assert len(model.arguments) == 1
    assert model.arguments[0].name == "arg"
    assert len(model.options) == 1
    opt = model.options[0]
    assert opt.name == "opt"
    assert opt.default == 42


def test_injected():
    model = CommandModel.from_callable(func_with_injected)
    assert "cnt" in model.injected_params
    assert "rng" in model.injected_params
    assert len(model.arguments) == 0
    assert len(model.options) == 1
    opt = model.options[0]
    assert opt.name == "normal"
    assert opt.default == "hi"


def test_union():
    model = CommandModel.from_callable(func_with_union)
    arg = model.arguments[0]
    assert arg.name == "arg"
    assert arg.types == {int, str}, arg.types
    assert not model.options


def test_annotated_field_default():
    model = CommandModel.from_callable(func_with_annotated)
    opt = model.options[0]
    assert opt.default == 123
