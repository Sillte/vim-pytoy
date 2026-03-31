import types
from typing import (
    Sequence,
    Any,
    Callable,
    Mapping,
    TYPE_CHECKING,
    Self,
)
from dataclasses import dataclass, field
from pytoy.shared.lib.text import LineRange
from pytoy.shared.command.utils import flatten_union, is_union, unwrap_annotated, is_literal, literal_values

type AcceptableType = str | int | float | bool | None

RangeParam = LineRange
if TYPE_CHECKING:
    from inspect import Parameter


def _get_types(annotation: Any, default_type: type = str) -> set[type]:
    """Return the non-union types."""
    import inspect

    if annotation is inspect.Parameter.empty:
        return {default_type}
    if annotation is None:
        return {type(None)}

    unwrapped, _ = unwrap_annotated(annotation)
    if is_union(unwrapped):
        return flatten_union(unwrapped)
    else:
        return {unwrapped}


MISSING_DEFAULT = object()


def _get_default(param: "Parameter") -> Any:
    from inspect import Parameter

    if param.default is not Parameter.empty:
        return param.default

    _, metadata = unwrap_annotated(param.annotation)
    for meta in metadata:
        if isinstance(meta, Field):
            default_getter = DefaultGetter.from_field(meta)
            if default_getter:
                return default_getter
    return MISSING_DEFAULT


def _get_literal_values(annotation: Any) -> Sequence[Any] | None:
    result = []
    flatten_types = _get_types(annotation)
    for typ in flatten_types:
        if is_literal(typ):
            result += list(literal_values(typ))
    return result if result else None


def _is_only_literal(annotation: Any) -> bool:
    flatten_types = _get_types(annotation)
    return all(is_literal(typ) for typ in flatten_types)


@dataclass(frozen=True)
class CountParam:
    count: int


type InjectedParam = RangeParam | CountParam


@dataclass(frozen=True)
class Argument:
    name: str
    types: set[type]
    literal_values: Sequence[Any] | None = None
    only_literal: bool = False
    # completer: Callable[[], list[Any]] | None = None  # Not yet used.


@dataclass(frozen=True)
class Field:
    default: Any = MISSING_DEFAULT
    default_factory: Callable | None = None


@dataclass(frozen=True)
class DefaultGetter:
    default: Any = MISSING_DEFAULT
    default_factory: Callable | None = None

    @classmethod
    def from_field(cls, field: Field) -> Self:
        return cls(default=field.default, default_factory=field.default_factory)

    def __bool__(self):
        return (self.default is not MISSING_DEFAULT) or (self.default_factory is not None)

    def get_default(self):
        if self.default is not MISSING_DEFAULT:
            return self.default
        if self.default_factory is not None:
            return self.default_factory()
        return MISSING_DEFAULT


@dataclass(frozen=True)
class Option:
    name: str
    types: set[type]
    default_getter: Any | DefaultGetter
    literal_values: Sequence[Any] | None = None
    only_literal: bool = False

    # completer: Callable[[], list[Any]] | None = None  # Not yet used.

    @property
    def default(self) -> Any:
        if isinstance(self.default_getter, DefaultGetter):
            return self.default_getter.get_default()
        return self.default_getter
    
    def get_candidate_values(self) -> Sequence[str]:
        if self.literal_values:
            return self.literal_values
        return []


@dataclass(frozen=True)
class CommandModel:
    arguments: Sequence[Argument]
    options: Sequence[Option]
    impl: Callable 
    injected_params: Mapping[str, type[InjectedParam]] = field(default_factory=dict)
    args_name: str | None = None
    kwargs_name: str | None = None


    @classmethod
    def from_callable(cls, function: Callable) -> Self:
        from inspect import signature, Parameter

        sig = signature(function)
        args_name: str | None = None
        kwargs_name: str | None = None
        injected_params: dict[str, type[InjectedParam]] = {}
        arguments: list[Argument] = []
        options: list[Option] = []
        for param in sig.parameters.values():
            if param.kind == Parameter.VAR_POSITIONAL:
                args_name = param.name
                continue
            elif param.kind == Parameter.VAR_KEYWORD:
                kwargs_name = param.name
                continue

            default_type = type(param.default) if param.default is not Parameter.empty else str
            annotated_types = _get_types(param.annotation, default_type=default_type)

            # def _get_intersection(annotated_types: set[type], required:tuple[type]):
            #    return {cand for cand in annotated_types if any(issubclass(cand, elem) for elem in required)}
            def _get_intersection(annotated_types: set[type], required: Sequence[type]):
                result = set()
                for cand in annotated_types:
                    if cand is type(None):
                        continue
                    for elem in required:
                        if cand is elem or (isinstance(cand, type) and issubclass(cand, elem)):
                            result.add(cand)
                return result

            if targets := _get_intersection(annotated_types, (RangeParam, CountParam)):
                injected_params[param.name] = targets.pop()
                continue

            default = _get_default(param)
            literal_values = _get_literal_values(param.annotation)
            is_only_literal = _is_only_literal(param.annotation)

            if default is MISSING_DEFAULT:
                arguments.append(
                    Argument(
                        name=param.name,
                        types=annotated_types,
                        literal_values=literal_values,
                        only_literal=is_only_literal,
                    )
                )
            else:
                options.append(
                    Option(
                        name=param.name,
                        types=annotated_types,
                        default_getter=default,
                        literal_values=literal_values,
                        only_literal=is_only_literal,
                    )
                )
        return cls(
            arguments=arguments,
            options=options,
            args_name=args_name,
            kwargs_name=kwargs_name,
            injected_params=injected_params,
            impl=function,
        )


@dataclass(frozen=True)
class Token:
    value: str
    start: int  # スライス用 start index
    end: int  # スライス用 end index (cmd_line[start:end])
    index: int  # トークンの順番

    def is_current_token(self, current_pos: int):
        # スライス感覚で統一
        return self.start <= current_pos < self.end


@dataclass(frozen=True)
class BooleanOptions:
    names: Sequence[str]

    @classmethod
    def from_command_model(cls, command_model: CommandModel) -> Self:
        names = [opt.name for opt in command_model.options if bool in opt.types]
        return cls(names=names)



def func(arg: str): ...


if __name__ == "__main__":
    from typing import Callable

    class CommandApplication:
        def __init__(
            self,
        ): ...

        def command(self, name: str) -> Callable: ...
