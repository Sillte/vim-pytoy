import types
from typing import (
    Sequence,
    Any,
    Callable,
    Mapping,
    get_origin,
    get_args,
    Union,
    TYPE_CHECKING,
    Annotated,
    Self,
    Literal,
)
from dataclasses import dataclass, field
from pytoy.shared.lib.text import LineRange


if TYPE_CHECKING:
    from inspect import Parameter


type TypeLike = Any
type FlattenType = Any
type LiteralType = Any


def is_union(tp: TypeLike):
    return isinstance(tp, types.UnionType) or get_origin(tp) is Union


def is_literal(tp: TypeLike):
    return get_origin(tp) is Literal

def literal_values(tp: LiteralType) -> set[Any]:
    if get_origin(tp) is not Literal:
        raise TypeError(f"`{tp}` is not Literal.")
    return set(get_args(tp))

def unwrap_annotated(tp: TypeLike) -> tuple[type, Sequence[Any]]:
    if get_origin(tp) is Annotated:
        base, *metadata = get_args(tp)
        return base, metadata
    return tp, []


def flatten_union(tp: TypeLike) -> set[FlattenType]:
    if not is_union(tp):
        return {tp}

    def _inner(tp: TypeLike) -> set[FlattenType]:
        result = set()
        for arg in get_args(tp):
            if is_union(arg):
                result |= _inner(arg)
            else:
                result.add(arg)
        return result

    return _inner(tp)

