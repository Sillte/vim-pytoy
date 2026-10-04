import types
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    Literal,
    Sequence,
    TypeAliasType,
    Union,
    get_args,
    get_origin,
)

if TYPE_CHECKING:
    pass


type TypeLike = Any
type FlattenType = Any
type LiteralType = Any


def unwrap_type_alias(tp: TypeLike) -> TypeLike:
    seen: set[int] = set()
    while isinstance(tp, TypeAliasType):
        identity = id(tp)
        if identity in seen:
            return tp
        seen.add(identity)
        tp = tp.__value__
    return tp


def is_union(tp: TypeLike):
    tp = unwrap_type_alias(tp)
    return isinstance(tp, types.UnionType) or get_origin(tp) is Union


def is_literal(tp: TypeLike):
    tp = unwrap_type_alias(tp)
    return get_origin(tp) is Literal


def literal_values(tp: LiteralType) -> set[Any]:
    tp = unwrap_type_alias(tp)
    if get_origin(tp) is not Literal:
        raise TypeError(f"`{tp}` is not Literal.")
    return set(get_args(tp))


def unwrap_annotated(tp: TypeLike) -> tuple[type, Sequence[Any]]:
    tp = unwrap_type_alias(tp)
    if get_origin(tp) is Annotated:
        base, *metadata = get_args(tp)
        return unwrap_type_alias(base), metadata
    return tp, []


def flatten_union(tp: TypeLike) -> set[FlattenType]:
    tp = unwrap_type_alias(tp)
    if not is_union(tp):
        return {tp}

    def _inner(tp: TypeLike) -> set[FlattenType]:
        tp = unwrap_type_alias(tp)
        result = set()
        for arg in get_args(tp):
            if is_union(arg):
                result |= _inner(arg)
            else:
                result.add(arg)
        return result

    return _inner(tp)
