import vim
from textwrap import dedent
from typing import Callable
import re

_VIM_FUNC_NAME_RE = re.compile(r"[^0-9A-Za-z_]")

type VimFunctionName = str



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

    FUNCTION_MAPS : dict[VimFunctionName, Callable] = dict()
    RETURN_VARIABLE_MAP: dict[VimFunctionName, str] = dict()

    #Vim script / Vim function execution is single-threaded.
    #Python callbacks are executed on Vim’s main event loop.
    #However, Vim functions may be re-entrant.
    #Therefore, global variables used for bridging must be uniquely named per call.


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

        if name is None:
            raw_name = getattr(func, "__name__", func.__class__.__name__)
            if raw_name == "<lambda>":
                raw_name = "lambda"
        else:
            raw_name = name

        safe_name = _VIM_FUNC_NAME_RE.sub("_", raw_name)

        return f"{prefix}_{safe_name}_{id(func)}"

    @classmethod
    def register(cls, func, *, prefix: str | None =None, name: str | None = None) -> str:
        """Register python `func` with `name` identifier.

        Args:
            func(function): python

        Return:
            The function name of Vim. This is also regarded as `key` of `FUNCTION_MAPS`.

        """
        vim_funcname = cls.to_vimfuncname(func, prefix=prefix, name=name)
        ret_var_name = f"{vim_funcname}_pytoy_return"
        if vim_funcname in cls.FUNCTION_MAPS:
            return vim_funcname

        procedures = dedent(f"""
        python3 << EOF
        args = vim.eval("a:000")
        ret = {__name__}.PytoyVimFunctions.FUNCTION_MAPS['{vim_funcname}'](*args)
        vim.vars['{ret_var_name}'] = ret
        EOF
        """).strip()

        vim.command(dedent(
            f"""
            function! {vim_funcname}(...)
            {procedures}
            return g:{ret_var_name}
            endfunction
            """).strip()
        )

        cls.FUNCTION_MAPS[vim_funcname] = func
        cls.RETURN_VARIABLE_MAP[vim_funcname] = ret_var_name

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

        if vim_funcname in cls.RETURN_VARIABLE_MAP:
            ret_var = cls.RETURN_VARIABLE_MAP.pop(vim_funcname)
            vim.command(f"execute 'unlet! g:{ret_var}'")

