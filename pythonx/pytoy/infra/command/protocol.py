from pytoy.infra.command.models import RangeCountOption, CommandFunction, NARGS


from inspect import Signature
from typing import Any, Protocol, Callable


class ConverterProviderProtocol(Protocol):
    def condition(
        self,
        target: CommandFunction,
        nargs: NARGS | None,
        range_count_option: RangeCountOption,
    ) -> tuple[bool, str | int, RangeCountOption]:
        """
        1. Return true if the `__call__` is appropriate for the conversion of `opt` to the signature of `target`.
        The following has meaning if the first one is True.
        2. Convert `nargs` to the appropriate one if nargs is None.
        3. `range_count_option` maybe modified if necessary.
        """
        ...

    def __call__(self, opts: dict[str, Any]) -> tuple[tuple, dict[str, Any]]:
        """`opts` includes parameters of `Command` in vim-world in a very similar way
        to `lua` lanaguage of `neovim`.
        This function must return (*args, **kwags), which are appropriate for the target to invoke.

        """
        ...
