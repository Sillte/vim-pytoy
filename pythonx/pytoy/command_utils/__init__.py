import inspect
import functools

import vim
from pytoy.func_utils import PytoyVimFunctions, with_return


class CommandManager:
    """Handling `Command!` for `vim` with `python`.

    Note
    -------
    Requirements for `command`. 


    Registration of `Command` is performed via `CommandManager.register`. 

    Example
    -------------

    Mandatotry rules
    -------------
    * `Command` must be `callable`. 
        - The parameters are given `*args`.  (deduced from the specification of vim's command.)

    Optional rules
    --------------
    * If `command` has it's name, it is used for defining `vim-function`.
    * If `command` has `customlist`, `-complete=customlist` is used.
    * If `command` has `custom` attribute, its used for `-complete` option.
        - For details, please refer to `:h compand-complete`.
    """
    v_customlist_variable = "g:customlist_variable"
    _COMMANDS = dict()


    @classmethod
    def register(cls, *args, **kwargs):
        """This behaves both of decorators bothof without keywords and with keywords.  
        The implementation is delegated to `_register`. 
        """
        if len(args) == 1:
            # Case: normal calling or decorator without keywords.
            return cls._register(args[0], **kwargs)
        elif len(args) == 0 and bool(kwargs):
            # Case: decorator with keywords. 
            return functools.partial(cls._register, **kwargs)
        else:
            raise ValueError("Parameter formats are invalid at `CommandManager.register`.")

    @classmethod
    def _register(cls, command: "Command", **kwargs):
        # When class is given, it is instantiated without parameters. 
        if inspect.isclass(command):
            command = command()

        if "name" in kwargs:
            name = kwargs["name"]
        else:
            try:
                name = command.name 
            except AttributeError:
                name = command.__name__

        funcname = PytoyVimFunctions.register(command, prefix="__PytoyCommand")

        cls._COMMANDS[name] = command
        customlist = getattr(command, "customlist", kwargs.get("customlist", None))
        if callable(customlist):
            cls._define_customlist_command(name, funcname)
        else:
            complete = getattr(command, "complete", kwargs.get("complete", None))
            cls._define_command(name, funcname, complete)
        pass

    @classmethod
    def _define_customlist_command(cls, name, funcname):
        """Define `customlist` and `command`.
        """
        customlist_funcname = f"__{funcname}_customlist"

        vim.command(f"""function! {customlist_funcname}(ArgLead, CmdLine, CursorPos) 
python3 << EOF
import vim
arg_lead = vim.eval("a:ArgLead")
cmd_line = vim.eval("a:CmdLine")
cursor_pos = vim.eval("a:CursorPos")
from {__name__} import CommandManager  # `__name__ represents `module` such as `pytoy.command_utils`. 
CommandManager._invoke_customlist("{name}", arg_lead, cmd_line, cursor_pos)
EOF
return {cls.v_customlist_variable}
endfunction
""".strip())
        vim.command(f'command! -complete=customlist,{customlist_funcname} -nargs=* {name} call {funcname}(<f-args>)')

    @classmethod
    def _define_command(cls, name, funcname, complete=None):
        #print("name", name, funcname)
        if complete is None:
            vim.command(f'command! -nargs=* {name} call {funcname}(<f-args>)')
        else:
            vim.command(f'command! -complete={complete} -nargs=* {name} call {funcname}(<f-args>)')

    @classmethod
    def _invoke_customlist(cls, name, arg_lead, cmd_line, cursor_pos):
        # Internally, this function is called. 
        command = cls._COMMANDS[name]
        result = command.customlist(arg_lead, cmd_line, cursor_pos)
        vim.command(f"let {cls.v_customlist_variable}={result}")


@CommandManager.register
class DummyCommand():
    name = "Dummy"
    
    def __call__(self, *args):
        print("Dummy Called.")

    def customlist(self, arg_lead:str, cmd_line: str, cursor_pos:int):
        return []



if __name__ == "__main__":
    pass

