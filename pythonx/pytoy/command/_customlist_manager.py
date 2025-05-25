import inspect
import vim
import json
from typing import Callable 

class _CustomListManager:
    """This class handles python complete function with custom-list settings. 
    """
    @classmethod
    def get_class_uri(cls):
        try:
            _prefix = f"{__name__}."
        except:
            _prefix = ""
        return f"{_prefix}_CustomListManager"

    FUNCTION_MAP = dict()
    VIMFUNC_TABLE = dict()
    V_CUSTOMLIST_VARIABLE = "g:customlist_manager_result"

    @classmethod
    def register(cls, name: str, target: Callable) -> str:
        """Return `vimfunc_name` which is used for `completion`.
        """
        if name in cls.FUNCTION_MAP:
            raise ValueError(f"Already `{name=}`  is registered.")
        vimfunc_name = f"CustomList_Manager__PYTOY__{name}"
        sig = inspect.signature(target)
        if len(sig.parameters) != 3:
            raise ValueError(f"{target} must take 3 parameters.")

        cls.VIMFUNC_TABLE[name] = vimfunc_name
        cls.FUNCTION_MAP[name] = target

        class_uri = cls.get_class_uri()

        vim.command(f"""function! {vimfunc_name}(ArgLead, CmdLine, CursorPos) 
python3 << EOF
import vim
arg_lead = vim.eval("a:ArgLead")
cmd_line = vim.eval("a:CmdLine")
cursor_pos = int(vim.eval("a:CursorPos"))
{class_uri}._invoke_customlist("{name}", arg_lead, cmd_line, cursor_pos)
EOF
return {cls.V_CUSTOMLIST_VARIABLE}
endfunction
""".strip())
        return vimfunc_name

    @classmethod
    def _invoke_customlist(cls, name, arg_lead, cmd_line, cursor_pos):
        # Internally, this function is called. 
        import vim
        target = cls.FUNCTION_MAP[name]
        result = target(arg_lead, cmd_line, cursor_pos)
        result = json.dumps(result)
        vim.command(f"let {cls.V_CUSTOMLIST_VARIABLE}={result}")

