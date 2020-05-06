import vim
import functools
import inspect

def with_return(func):
    """
    Set the `return` value to `vim` funciton.
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
    """
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        ret = func(*args, **kwargs)
        vim.command(f"let l:ret='{repr(ret)}'")

        # May require modification... 
        #if isinstance(ret, str) or (ret is None):
        #   vim.command(f"let l:ret='{ret}'")
        #else:
        #   vim.command(f"let l:ret={ret}")
        return ret
    return wrapped


_PYTOY_VIM_FUNCTION_MAPS = dict()
class PytoyVimFunctions: 
    """Wrappers of `python` functions for `vim` functions.

    Usecase
    ------------------------------
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

        name = func.__name__
        vim_funcname = f"{prefix}_{name}_{id(name)}"
        vim.command(f"""function! {vim_funcname}(...) 
        python3 {__name__}.PytoyVimFunctions.FUNCTION_MAPS['{vim_funcname}']()
        if exists("l:ret")
            return l:ret
        endif
        endfunction
        """)
        cls.FUNCTION_MAPS[vim_funcname] = func
        return vim_funcname 

    @classmethod
    def deregister(cls, key):
        if key in cls.FUNCTION_MAPS:
            del cls.FUNCTION_MAPS[key]
        vim.command(f"delfunction! {key}")
