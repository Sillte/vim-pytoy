import inspect
import vim
import json
from typing import Callable
import textwrap 


def _signature(target) -> inspect.Signature:
    if isinstance(target, (staticmethod, classmethod)):
        func = target.__func__
    else:
        func = target
    return inspect.signature(func)


class _CustomListManager:
    """This class handles python complete function with custom-list settings."""

    @classmethod
    def get_class_uri(cls) -> str:
        try:
            _prefix = f"{__name__}."
        except:
            _prefix = ""
        return f"{_prefix}_CustomListManager"

    FUNCTION_MAP = dict()
    VIMFUNC_TABLE = dict()
    V_CUSTOMLIST_VARIABLE = "g:customlist_manager_result"

    @classmethod
    def register(cls, name: str, target: Callable | staticmethod) -> str:
        """Return `vimfunc_name` which is used for `completion`."""
        if name in cls.FUNCTION_MAP:
            cls.deregister(name)

        vimfunc_name = cls.to_vimfunc_name(name)
        sig = _signature(target)

        if len(sig.parameters) < 3:
            raise ValueError(f"{target} must take at least 3 parameters.")

        cls.VIMFUNC_TABLE[name] = vimfunc_name
        cls.FUNCTION_MAP[name] = target

        class_uri = cls.get_class_uri()


        vim.command(cls.WRAP_INVOKE_CUSTOMLIST_TEMPLATE.format(vimfunc_name=vimfunc_name,
                                        class_uri=class_uri,
                                        name=name,
                                        result_var=cls.V_CUSTOMLIST_VARIABLE))
        return vimfunc_name
    
    WRAP_INVOKE_CUSTOMLIST_TEMPLATE = textwrap.dedent(r"""
        function! {vimfunc_name}(ArgLead, CmdLine, CursorPos)
        python3 << EOF
        import vim
        arg_lead = vim.eval("a:ArgLead")
        cmd_line = vim.eval("a:CmdLine")
        cursor_pos = int(vim.eval("a:CursorPos"))
        {class_uri}._invoke_customlist("{name}", arg_lead, cmd_line, cursor_pos)
        EOF
        return {result_var}
        endfunction
        """)

    @classmethod
    def _invoke_customlist(cls, name: str, arg_lead: str, cmd_line: str, cursor_pos: int) -> None:
        # Internally, this function is called.
        import vim

        target = cls.FUNCTION_MAP[name]
        try:
            result = target(arg_lead, cmd_line, cursor_pos)
        except Exception as e:
            result = [f"{name} _invoke_customlist_error: {e}"]
        result = json.dumps(result)
        vim.command(f"let {cls.V_CUSTOMLIST_VARIABLE}={result}")

    @classmethod
    def to_vimfunc_name(cls, name: str) -> str:
        vimfunc_name = f"CustomList_Manager__PYTOY__{name}"
        return vimfunc_name

    @classmethod
    def deregister(cls, name: str) -> None:
        if name not in cls.VIMFUNC_TABLE:
            return
        vimfunc_name = cls.VIMFUNC_TABLE[name]
        vim.command(f"delfunction {vimfunc_name}")
        del cls.VIMFUNC_TABLE[name]
        del cls.FUNCTION_MAP[name]
