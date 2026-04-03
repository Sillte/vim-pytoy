import types
from typing import (
    Sequence,
    Any,
    Callable,
    Mapping,
    TYPE_CHECKING,
    Self,
    Literal,
)
from dataclasses import dataclass, field
from pytoy.shared.lib.text import LineRange
from pytoy.shared.command.utils import flatten_union, is_union, unwrap_annotated, is_literal, literal_values

# 0-based, exclusive range [start, end)
RangeParam = LineRange
if TYPE_CHECKING:
    from inspect import Parameter

MISSING_DEFAULT = object()


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
type Completer = Callable[[], Sequence[str]]


@dataclass(frozen=True)
class Field:
    default: Any = MISSING_DEFAULT
    default_factory: Callable | None = None
    completer: Completer | None = None


class Argument:
    def __init__(
        self,
        default: Any = MISSING_DEFAULT,
        *,
        default_factory: Any = None,
        help: str | None = "",
        completer: Completer | None = None,
    ):
        self._default = default
        self._help = help
        self._default_factory = default_factory
        self._completer = completer

    def __repr__(self):
        return f"Argument(default={self._default!r})"

    @property
    def required(self) -> bool:
        return self.default is MISSING_DEFAULT and self.default_factory is None

    @property
    def default(self) -> Any:
        return self._default

    @property
    def default_factory(self) -> Any:
        return self._default_factory

    @property
    def help(self) -> str | None:
        return self._help

    @property
    def completer(self) -> Completer | None:
        return self._completer


class Option:
    def __init__(
        self,
        default: Any = MISSING_DEFAULT,
        *,
        default_factory: Any = None,
        help: str | None = None,
        completer: Completer | None = None,
    ):
        self._default = default
        self._default_factory = default_factory
        self._help = help
        self._completer = completer

    @property
    def default(self) -> Any:
        return self._default

    @property
    def default_factory(self) -> Any:
        return self._default_factory

    @property
    def help(self) -> str | None:
        return self._help

    @property
    def completer(self) -> Completer | None:
        return self._completer


@dataclass(frozen=True)
class DefaultGetter:
    default: Any = MISSING_DEFAULT
    default_factory: Callable | None = None

    @classmethod
    def from_field(cls, field: Field) -> Self:
        return cls(default=field.default, default_factory=field.default_factory)

    @classmethod
    def from_option(cls, option: Option) -> Self:
        return cls(default=option.default, default_factory=option.default_factory)

    @classmethod
    def from_argument(cls, argument: Argument) -> Self:
        return cls(default=argument.default, default_factory=argument.default_factory)

    def __bool__(self):
        return (self.default is not MISSING_DEFAULT) or (self.default_factory is not None)

    def get_default(self):
        if self.default is not MISSING_DEFAULT:
            return self.default
        if self.default_factory is not None:
            return self.default_factory()
        return MISSING_DEFAULT
    

type CompletionFunction = Callable[[], Sequence[str]]

@dataclass(frozen=True)
class CompleterModel:
    impl: CompletionFunction

    @classmethod
    def from_any(cls, arg: Any) -> Self:
        if callable(arg):
            return cls(impl=arg)  #type: ignore
        elif isinstance(arg, Sequence):
            return cls(impl=lambda: arg)
        raise TypeError(f"Cannot convert `{arg}` to `CompleterModel`")
        
    
    def __call__(self) -> Sequence[str]:
        return self.impl()


@dataclass(frozen=True)
class ArgumentModel:
    name: str
    types: set[type]
    literal_values: Sequence[Any] | None = None
    only_literal: bool = False
    default_getter: DefaultGetter | None = None
    completer: CompleterModel | None = None

    @property
    def required(self) -> bool:
        return self.default_getter is None

    @property
    def default(self) -> Any:
        if self.default_getter is None:
            return MISSING_DEFAULT
        return self.default_getter.get_default()
    
    def get_candidate_values(self) -> Sequence[str]:
        result = []
        if self.literal_values:
            result += self.literal_values
        if self.completer:
            result += self.completer()
        return result


@dataclass(frozen=True)
class OptionModel:
    name: str
    types: set[type]
    default_getter: DefaultGetter
    literal_values: Sequence[Any] | None = None
    only_literal: bool = False
    completer: CompleterModel | None = None

    @property
    def default(self) -> Any:
        return self.default_getter.get_default()

    def get_candidate_values(self) -> Sequence[str]:
        result = []
        if self.literal_values:
            result += self.literal_values
        if self.completer:
            result += self.completer()
        return result


def _resolve_type_and_default(param) -> tuple[Literal["Argument", "Option"], DefaultGetter | None]:

    from inspect import Parameter

    # Type-like handling.
    # To be specific, when domain object is given.
    raw_default = param.default
    if isinstance(raw_default, Argument):
        if raw_default.required:
            dg = None
        else:
            dg = DefaultGetter.from_argument(raw_default)
        return "Argument", dg

    if isinstance(raw_default, Option):
        return "Option", DefaultGetter.from_option(raw_default)

    if isinstance(raw_default, DefaultGetter):
        return "Option", raw_default

    # FastAPI-like handling and fallback.
    if raw_default is not Parameter.empty:
        dg = DefaultGetter(default=raw_default)
    else:
        dg = None

    param_type = None
    # Annotated(Field) fallback
    _, metadata = unwrap_annotated(param.annotation)
    for meta in metadata:
        # Fallback for class specification.
        if meta is Argument:
            meta = Argument()
        elif meta is Option:
            meta = Option()

        if isinstance(meta, Field):
            if dg is None and (cand := DefaultGetter.from_field(meta)):
                dg = cand
        elif isinstance(meta, Argument):
            if dg is None and (cand := DefaultGetter.from_argument(meta)):
                dg = cand
            param_type = "Argument"
        elif isinstance(meta, Option):
            if dg is None and (cand := DefaultGetter.from_option(meta)):
                dg = cand
            param_type = "Option"

    if param_type is None:
        if dg is None:
            param_type = "Argument"
        else:
            param_type = "Option"
    return param_type, dg


def _resolve_completer(param) -> Completer | None:
    raw_default = param.default
    if isinstance(raw_default, (Argument, Option)):
        if raw_default.completer:
            return raw_default.completer

    _, metadata = unwrap_annotated(param.annotation)
    for meta in metadata:
        # Fallback for class specification.
        if isinstance(meta, Field):
            if meta.completer:
                return meta.completer
        elif isinstance(meta, (Argument, Option)):
            if meta.completer:
                return meta.completer
    return None


@dataclass(frozen=True)
class CommandModel:
    arguments: Sequence[ArgumentModel]
    options: Sequence[OptionModel]
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
        arguments: list[ArgumentModel] = []
        options: list[OptionModel] = []
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

            literal_values = _get_literal_values(param.annotation)
            is_only_literal = _is_only_literal(param.annotation)
            arg_type, default_getter = _resolve_type_and_default(param)
            completer = _resolve_completer(param)

            if arg_type == "Option" and (not default_getter):
                raise ValueError(f"Option `{param}` requires a default")

            if arg_type == "Argument":
                arguments.append(
                    ArgumentModel(
                        name=param.name,
                        types=annotated_types,
                        literal_values=literal_values,
                        only_literal=is_only_literal,
                        default_getter=default_getter,
                        completer=CompleterModel.from_any(completer) if completer else None,
                    )
                )
            elif arg_type == "Option" and default_getter is not None:
                options.append(
                    OptionModel(
                        name=param.name,
                        types=annotated_types,
                        default_getter=default_getter,
                        literal_values=literal_values,
                        only_literal=is_only_literal,
                        completer=CompleterModel.from_any(completer) if completer else None,
                    )
                )
            else:
                raise RuntimeError("Implementation Error.")
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


if __name__ == "__main__":
    ...
