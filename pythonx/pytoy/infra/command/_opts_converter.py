"""The role of `_OptsConverter` is the below two points.
1. convert the return of `opts` (Lua-like return of the command in neovim)
so that the given `callable` can accept them as the argument.

2. Infer the options of `VimFunction` (such as nargs/count/range) or verify the values of them.
   When there is no specification regarding the options, this converter infers the appropriate one.
   When there is specified in the `Command`, this converter verifies the compatibility of python functions
   and the option of commands.
   If invalid, it raises Exception.

To resolve the correspondence of `signature` of python functions and command options.
`_ConverterProvider` is defined this function. If any `_ConverterProvider` can state
that it is able to map the signature of functions and `opts`.

Note that the Role 1 is carried out at the execution time of the function,
whle the Role 2 is is carried out at the definition time of the Command.
"""

import inspect
from inspect import Signature
from typing import Any, Sequence, Mapping
from pytoy.infra.command.protocol import ConverterProviderProtocol, CommandFunction
from pytoy.infra.command.models import OptsArgument, RangeCountOption, NARGS
from pytoy.infra.command._opts_arguments_converters import (
    NoArgumentConverter,
    OptArgumentConverter,
    OneStringArgumentConverter,
    OpsDataclassArgumentConverter,  # NOQA
)


def _signature(target: CommandFunction) -> Signature:
    if isinstance(target, staticmethod):
        func = target.__func__
    else:
        func = target
    return inspect.signature(func)


class _OptsConverter:
    _provider_classes: list[type[ConverterProviderProtocol]] = [
        NoArgumentConverter,
        OptArgumentConverter,
        OneStringArgumentConverter,
        OpsDataclassArgumentConverter,
    ]

    def __init__(
        self,
        target: CommandFunction,
        nargs: NARGS | None,
        range_count_option: RangeCountOption,
    ):
        self.target = target
        self._range_count_option = range_count_option
        self._converter = self._decide_converter(target, nargs, self.range_count_option)

    @property
    def nargs(self) -> NARGS:
        if self._nargs is None:
            raise ValueError("nargs is not decided yet.")
        return self._nargs

    @property
    def range_count_option(self) -> RangeCountOption:
        return self._range_count_option

    def _decide_converter(
        self, target: CommandFunction, nargs: NARGS | None, rc_opt: RangeCountOption
    ):
        """
        * Decide how to convert `opts` to the parameters of python.
            - Selection of `nargs` are mandatory.
        * If the options of `Command` is not given, infer them.
            - If contradiction exists, raise Exception.
        """
        for provider_cls in self._provider_classes:
            provider = provider_cls()
            flag, nargs, rc_opt = provider.condition(target, nargs, rc_opt)
            if flag:
                self._nargs = nargs
                self._range_count_option = rc_opt
                return provider

        sig = _signature(target)
        raise NotImplementedError(
            f"Currently, cannnot handle the signature provided in {sig.parameters=}, {target=}, {nargs=}"
        )

    def __call__(self, opts: dict[str, Any]) -> tuple[Sequence[Any], Mapping[str, Any]]:
        """Interpret `opts` and"""
        return self._converter(opts)
