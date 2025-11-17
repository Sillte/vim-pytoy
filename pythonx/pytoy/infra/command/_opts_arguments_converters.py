from collections.abc import Mapping as AbcMapping
from typing import Annotated, Any, get_args, get_origin
from pytoy.infra.command.protocol import ConverterProviderProtocol, CommandFunction  
from pytoy.infra.command.range_count_option import RangeCountOption
from dataclasses import dataclass


import inspect
from inspect import Signature, _empty as empty


def _signature(target: CommandFunction) -> Signature:
    if isinstance(target, staticmethod):
        func = target.__func__
    else:
        func = target
    return inspect.signature(func)



class NoArgumentConverter(ConverterProviderProtocol):
    def condition(
        self,
        target: CommandFunction,
        nargs: str | int | None,
        range_count_option: RangeCountOption,
    ) -> tuple[bool, str | int, RangeCountOption]:
        signature = _signature(target)
        parameters = signature.parameters
        if len(parameters) == 0:
            assert nargs == 0 or nargs is None, "Consistency"
            nargs = 0
            return True, nargs, range_count_option
        return False, "*", range_count_option

    def __call__(self, opts: dict) -> tuple[tuple, dict]:
        return tuple(), dict()


def _unwrapped_annotation_origin_type(annotation: Any) -> type:
    """If the annotation is `Annotated`, return the origin-type of first argument of it.
    Otherwise, return the `origin_type` itself.
    """
    if annotation is empty:
        return empty
    if get_origin(annotation) is Annotated:
         annotation = get_args(annotation)[0]
    origin = get_origin(annotation) or annotation
    return origin


class OptArgumentConverter(ConverterProviderProtocol):
    """Basically, give the opt as dict naively."""

    def condition(
        self,
        target: CommandFunction,
        nargs: str | int | None,
        range_count_option: RangeCountOption,
    ) -> tuple[bool, str | int, RangeCountOption]:
        signature = _signature(target)
        parameters = signature.parameters
        if len(parameters) != 1:
            return False, "*", range_count_option
        first_parameter = list(parameters.values())[0]
        annotation = first_parameter.annotation
        if annotation is empty:
            return False, "*", range_count_option
        if get_origin(annotation) is Annotated:
            annotation = get_args(annotation)[0]
        origin = get_origin(annotation) or annotation
        try:
            if issubclass(origin, (dict, AbcMapping)):
                if nargs is None:
                    nargs = "*"
                return True, nargs, range_count_option
        except TypeError:
            pass
        return False, "*", range_count_option

    def __call__(self, opts: dict) -> tuple[tuple, dict]:
        return (opts,), {}


class OneStringArgumentConverter(ConverterProviderProtocol):
    def condition(
        self,
        target: CommandFunction,
        nargs: str | int | None,
        range_count_option: RangeCountOption,
    ) -> tuple[bool, str | int, RangeCountOption]:
        signature = _signature(target)
        parameters = signature.parameters
        if len(parameters) != 1:
            return False, "*", range_count_option
        first_parameter = list(parameters.values())[0]
        annotation = _unwrapped_annotation_origin_type(first_parameter.annotation)
        if not issubclass(annotation, str):
            return False, "*", range_count_option
        if first_parameter.default is empty:
            if nargs is None:
                nargs = 1
            assert str(nargs) != str(0), "Consistency"
            self._propagate_empty = True
            return True, nargs, range_count_option
        else:
            nargs = "?" if nargs is None else nargs
            self._propagate_empty = False
            return True, nargs, range_count_option

    def __call__(self, opts: dict) -> tuple[tuple, dict]:
        if self._propagate_empty or bool(opts["args"]):
            return (opts["args"],), {}
        else:
            return tuple(), {}


@dataclass
class OptsArgument:
    """This is a naive wrapper of `dict` as `opts`."""

    args: str
    fargs: list
    count: int | None = None
    line1: int | None = None
    line2: int | None = None
    range: tuple[int, int] | int | None = None


class OpsDataclassArgumentConverter(ConverterProviderProtocol):
    def condition(
        self,
        target: CommandFunction,
        nargs: str | int | None,
        range_count_option: RangeCountOption,
    ) -> tuple[bool, str | int, RangeCountOption]:
        signature = _signature(target)
        parameters = signature.parameters
        if len(parameters) != 1:
            return False, "*", range_count_option
        first_parameter = list(parameters.values())[0]
        annotation = _unwrapped_annotation_origin_type(first_parameter.annotation)
        if issubclass(annotation, OptsArgument):
            if nargs is None:
                nargs = "*"
            return True, nargs, range_count_option
        return False, "*", range_count_option

    def __call__(self, opts: dict) -> tuple[tuple, dict]:
        opts_argument = OptsArgument(**opts)
        return (opts_argument,), {}


if __name__ == "__main__":
    pass
