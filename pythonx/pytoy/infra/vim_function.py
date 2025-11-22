import vim
from textwrap import dedent
from typing import Callable

type VimFunctionName = str


_PYTOY_VIM_FUNCTION_MAPS: dict[VimFunctionName, Callable]  = dict()


class PytoyVimFunctions:
    """Wrappers of `python` functions for `vim` functions.

    Usecase
    -------------------------------------------------------
    As a callback function, `vim` functions may be required.

    Usage
    ------------------------------
    * You have to import this class so that `:python3 PytoyVimFunctions` is valid.
    * The wrapped python function signature must be `def func(*args).`
    """

    FUNCTION_MAPS = _PYTOY_VIM_FUNCTION_MAPS

    @classmethod
    def to_vimfuncname(cls, func: Callable, *, prefix:str | None = None, name: str | None = None) -> str:
        """This function returns the same `vimfuncname`,
        when we call `register`.
        Sometimes, we have to know the name for deregister in prior to register.
        In these cases, we use them.
        """
        # You should consider this with auto-deregister mechanism.
        # if name in cls.FUNCTION_MAPS:
        #    raise ValueError(f"`{name}` is already used at `PytoyVimFunctions`. ")
        if prefix is None:
            prefix = "Pytoy_VIMFUNC"

        # For `__name__`'s reference ` pytoy.func_utils` access must be passed.
        if name is None:
            try:
                name = func.__name__
            except AttributeError:
                name = func.__class__.__name__  # For callable of classes.

        vim_funcname = f"{prefix}_{name}_{id(func)}"
        return vim_funcname

    @classmethod
    def register(cls, func, *, prefix: str | None =None, name: str | None = None) -> str:
        """Register python `func` with `name` identifier.

        Args:
            func(function): python

        Return:
            The function name of Vim. This is also regarded as `key` of `FUNCTION_MAPS`.

        """
        vim_funcname = cls.to_vimfuncname(func, prefix=prefix, name=name)

        procedures = dedent(f"""
        python3 << EOF
        args = vim.eval("a:000")
        {__name__}.PytoyVimFunctions.FUNCTION_MAPS['{vim_funcname}'](*args)
        EOF
        """).strip()

        vim.command(dedent(
            f"""
            function! {vim_funcname}(...)
            {procedures}
            endfunction
            """).strip()
        )
        cls.FUNCTION_MAPS[vim_funcname] = func

        return vim_funcname

    @classmethod
    def is_registered(cls, vim_funcname: VimFunctionName) -> bool:
        return bool(
            vim_funcname in cls.FUNCTION_MAPS
            or int(vim.eval(f"exists('{vim_funcname}')"))
        )

    @classmethod
    def deregister(cls, vim_funcname: VimFunctionName) -> None:
        if vim_funcname in cls.FUNCTION_MAPS:
            del cls.FUNCTION_MAPS[vim_funcname]
        vim.command(f"delfunction! {vim_funcname}")
