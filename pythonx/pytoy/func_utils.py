import vim
import functools
import inspect

def with_return(func):
    """
    Set the `return` value to `vim` function.
    Specifically, to `l:ret`,  `value` is `set`.
 
    Note
    ----

    ```python
    @with_return
    def func():
        result = "hogehoge"
        return result
    ```
    ```vim
    function! Func() 
        py3 func()
        return l:ret
    endfunction
    ```

    * Maybe this decorator is used in module functions and 
    called not locally, but globally.
    In these cases, `l:` cannot be used, so `g:pytoy_return` is used

    (2022/02/24) I wonder the mutual exclusion is all right? 
    (2025/04/29) Hence, in this case, `Lock` mechanism must be required, 
    to prevent the contamination of multi-threads. 
    However, this seems daunting, so this utility function is used 
    under the assumption that this mechanism is used in the single thread. 
    """
    def _escape(s):
        """Escape the single quotation for vim 
        """
        s = str(s)
        return s.replace("'", "''")


    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        ret = func(*args, **kwargs)
        if isinstance(ret, str):
            vim.command(f"let g:pytoy_return='{_escape(ret)}'")
        else:
            vim.command(f"let g:pytoy_return=eval('{_escape(repr(ret))}')")

        return ret
    return wrapped


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
            procedures = f"python3 {__name__}.PytoyVimFunctions.FUNCTION_MAPS['{vim_funcname}']()"
        else:
            procedures = f"""
python3 << EOF
args = vim.eval("a:000")
{__name__}.PytoyVimFunctions.FUNCTION_MAPS['{vim_funcname}'](*args)
EOF
    """.strip()

        vim.command(f"""function! {vim_funcname}(...) 
            {procedures}
            if exists("g:pytoy_return")
                return g:pytoy_return
            endif
            endfunction
            """)
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
