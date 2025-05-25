""" The role of `_OptsConverter` is the 2 below two. 
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
from inspect import _empty as empty
from inspect import Signature
from typing import Type
from pytoy.command.range_count_option import RangeCountOption


class _OptsConverter:
    __converter_providers = []

    @classmethod
    def register(cls, reg_cls: Type["_ConverterProvider"]):
        cls.__converter_providers.append(reg_cls)
        return reg_cls

    def __init__(
        self,
        target,
        nargs: str | int | None,
        range_count_option: RangeCountOption,
    ):
        self.target = target
        self.range_count_option = range_count_option
        providers = [cls() for cls in self.__converter_providers]
        self._converter = self._decide_converter(
            target, nargs, self.range_count_option, providers
        )

    @property
    def nargs(self) -> str | int:
        return self._nargs

    def _decide_converter(self, target, nargs, rc_opt, providers):
        """
        * Decide how to convert `opts` to the parameters of python.
            - Selection of `nargs` are mandatory.
        * If the options of `Command` is not given, infer them.
            - If contradiction exists, raise Exception.
        """
        sig = inspect.signature(target)
        for provider in providers:
            flag, nargs, rc_opt = provider.condition(sig, nargs, rc_opt)
            if flag:
                self._nargs = nargs
                self.range_count_option = rc_opt
                return provider
        raise NotImplementedError(
            "Currently, cannnot handle the signature provided in Python."
        )

    def __call__(self, opts: dict) -> tuple[tuple, dict]:
        """Interpret `opts` and"""
        return self._converter(opts)


class _ConverterProvider:
    """The class which clarifies the siganture of `_ConverterProvider`."""

    def __init__(self):
        self._nargs = None

    def condition(
        self,
        signature: Signature,
        nargs: str | int | None,
        range_count_option: RangeCountOption,
    ) -> tuple[bool, str | int, RangeCountOption]:
        """
        1. Return true if the `__call__` is appropriate for the conversion of `opt` to the signature of `target`.
        2. Set `self._nargs`.
        """
        if nargs is None:
            nargs = "*"
        return False, nargs, range_count_option

    def __call__(self, opts: dict) -> tuple[tuple, dict]:
        """`opts` includes parameters of `Command` in vim-world in a very similar way
        to `lua` lanaguage of `neovim`.
        This function must return (*args, **kwags), which are appropriate for the target.

        """
        return tuple(), dict()


@_OptsConverter.register
class NoArgumentConverter(_ConverterProvider):
    def condition(
        self,
        signature: Signature,
        nargs: str | int | None,
        range_count_option: RangeCountOption,
    ) -> tuple[bool, str | int, RangeCountOption]:
        parameters = signature.parameters
        if len(parameters) == 0:
            assert nargs == 0 or nargs is None, "Consistency"
            nargs = 0
            return True, nargs, range_count_option
        return False, "*", range_count_option

    def __call__(self, opts: dict) -> tuple[tuple, dict]:
        return tuple(), dict()


@_OptsConverter.register
class OptArgumentConverter(_ConverterProvider):
    """Basically, give the opt naively."""

    def condition(
        self,
        signature: Signature,
        nargs: str | int | None,
        range_count_option: RangeCountOption,
    ) -> tuple[bool, str | int, RangeCountOption]:
        parameters = signature.parameters
        if len(parameters) != 1:
            return False, "*", range_count_option
        first_parameter = list(parameters.values())[0]
        if issubclass(first_parameter.annotation, dict):
            if nargs is None:
                nargs = "*"
            return True, nargs, range_count_option
        return False, "*", range_count_option

    def __call__(self, opts: dict) -> tuple[tuple, dict]:
        return (opts,), {}


@_OptsConverter.register
class OneStringArgumentConverter(_ConverterProvider):
    def condition(
        self,
        signature: Signature,
        nargs: str | int | None,
        range_count_option: RangeCountOption,
    ) -> tuple[bool, str | int, RangeCountOption]:
        parameters = signature.parameters
        if len(parameters) != 1:
            return False, "*", range_count_option
        first_parameter = list(parameters.values())[0]
        if not issubclass(first_parameter.annotation, str):
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


if __name__ == "__main__":
    pass
