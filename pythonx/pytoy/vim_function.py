import vim
import inspect


_PYTOY_VIM_FUNCTION_MAPS = dict()


class PytoyVimFunctions:
    """Wrappers of `python` functions for `vim` functions.

    Usecase
    -------------------------------------------------------
    As a callback function, `vim` functions may be required.

    Usage
    ------------------------------
    * You have to import this class so that `:python3 PytoyVimFunctions` is valid.
    * The wrapped python function signature must be `def func().`
    """

    FUNCTION_MAPS = _PYTOY_VIM_FUNCTION_MAPS

    @classmethod
    def register(cls, func, prefix=None):
        """Register python `func` with `name` identifier.

        Args:
            func(function): python

        Return:
            The function name of Vim. This is also regarded as `key` of `FUNCTION_MAPS`.

        """
        # You should consider this with auto-deregister mechanism.
        # if name in cls.FUNCTION_MAPS:
        #    raise ValueError(f"`{name}` is already used at `PytoyVimFunctions`. ")
        if prefix is None:
            prefix = "Pytoy_VIMFUNC"

        # For `__name__`'s reference ` pytoy.func_utils` access must be passed.
        try:
            name = func.__name__
        except AttributeError:
            name = func.__class__.__name__  # For callable of classes.

        vim_funcname = f"{prefix}_{name}_{id(name)}"

        # Depending of the number of parameters, change the
        # definition and calling of functions.
        # Currently(2022/02/26), only `*args` and  `<f-args>` are dealt with.
        # Notice that `python3  << EOF` starts without `spaces`.
        sig = inspect.signature(func)
        if len(sig.parameters) == 0:
            procedures = f"python3 {__name__}.PytoyVimFunctions.FUNCTION_MAPS['{vim_funcname}']()"  #NOQA
        else:
            procedures = f"""
python3 << EOF
args = vim.eval("a:000")
{__name__}.PytoyVimFunctions.FUNCTION_MAPS['{vim_funcname}'](*args)
EOF
    """.strip()

        vim.command(
            f"""function! {vim_funcname}(...)
            {procedures}
            endfunction
            """
        )
        cls.FUNCTION_MAPS[vim_funcname] = func

        return vim_funcname

    @classmethod
    def is_registered(cls, key):
        return bool(key in cls.FUNCTION_MAPS or int(vim.eval(f"exists('{key}')")))

    @classmethod
    def deregister(cls, key):
        if key in cls.FUNCTION_MAPS:
            del cls.FUNCTION_MAPS[key]
        vim.command(f"delfunction! {key}")
