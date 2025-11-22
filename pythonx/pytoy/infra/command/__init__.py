import shlex
from typing import Callable
from typing import TypeAlias
import inspect

from pytoy.infra.command.models import RangeCountOption, CommandFunction
import vim

from pytoy.infra.command.models import RangeCountType
from pytoy.infra.command._opts_converter import _OptsConverter
from pytoy.infra.command._customlist_manager import _CustomListManager

from pytoy.infra.command.models import OptsArgument, NARGS, CommandFunction  # NOQA


class CommandManager:
    FUNCTION_MAPS: dict[str, CommandFunction] = dict()
    COMMAND_MAPS: dict[str, str] = dict()
    CONVERTER_MAPS: dict[str, _OptsConverter] = dict()

    @classmethod
    def register(
        cls,
        name: str,
        nargs: NARGS | None = None,
        range: str | int | None = None,
        count: int | None = None,
        complete: CommandFunction | str | None = None,
        addr: None = None,
        *,
        exist_ok: bool = False,
    ):
        """Register the commands"""
        rc_opt = RangeCountOption(range, count)

        def _inner(target):
            nonlocal complete

            def _is_function_target(target: str | CommandFunction | None) -> bool:
                return inspect.isfunction(target) or isinstance(target, staticmethod)

            if isinstance(target, classmethod):
                raise ValueError(
                    f"Classmethod cannot be registered, {target=}, {name=}"
                )

            if _is_function_target(target):
                cls._handle_existent_command(name=name, exist_ok=exist_ok)
                if _is_function_target(complete):
                    assert not isinstance(complete, str) and complete is not None
                    c_vimfunc_name = _CustomListManager.register(name, complete)
                    complete_str = f"customlist,{c_vimfunc_name}"
                elif isinstance(complete, str):
                    complete_str = complete
                else:
                    complete_str = None

                return cls._register_for_func(
                    target,
                    name,
                    nargs,
                    range_count_option=rc_opt,
                    complete=complete_str,
                    addr=addr,
                )
            elif inspect.isclass(target):
                instance = target()
                assert callable(instance), "CommandClass must implement `__call__`"

                # [NOTE]: I am wondering whether we should be whether we should be able
                # to get `name` from `instance property`.
                cls._handle_existent_command(name=name, exist_ok=exist_ok)

                if complete is None and hasattr(instance, "customlist"):
                    c_vimfunc_name = _CustomListManager.register(
                        name, getattr(instance, "customlist")
                    )
                    complete_vimname = f"customlist,{c_vimfunc_name}"
                else:
                    complete_vimname = None
                return cls._register_for_func(
                    instance,
                    name,
                    nargs,
                    range_count_option=rc_opt,
                    complete=complete_vimname,
                    addr=addr,
                )
            else:
                raise ValueError("The object of registration is illegal.")

        return _inner

    @classmethod
    def deregister(cls, name: str, no_exist_ok: bool = True):
        """De-register the `name` commmand."""
        if name not in cls.COMMAND_MAPS:
            if no_exist_ok:
                return
            else:
                raise ValueError(f"The `command` is NOT registered. `{name=}`")
        _CustomListManager.deregister(name)
        cls._deregister_for_func(name)

    @classmethod
    def is_exist(cls, name: str) -> bool:
        """Return whether the given `name` is already registered or not."""
        return name in cls.COMMAND_MAPS

    @classmethod
    def _register_for_func(
        cls,
        func: CommandFunction,
        name: str,
        nargs: NARGS | None = None,
        range_count_option: None | RangeCountOption = None,
        complete: str | None = None,
        addr: None = None,
    ) -> Callable:
        # vim_funcname = f"PytoyFunc_FOR_COMMAND_{name}"
        vim_funcname = cls.to_vimfunc_name(name)
        if name in cls.COMMAND_MAPS:
            raise ValueError(f"The same `command` is already registered. `{name=}`")
        if vim_funcname in cls.FUNCTION_MAPS:
            raise ValueError(
                "Already `FUNCTION` is defined? (Very rare situation.), {vim_funcname}"
            )

        if range_count_option is None:
            range_count_option = RangeCountOption()

        converter = _OptsConverter(func, nargs, range_count_option)
        # Note that `OptsConverter` verifies and infers the options.
        # Hence, at this juncture, the command options is resolved.
        cls.CONVERTER_MAPS[name] = converter
        nargs = converter.nargs
        rc_opt = converter.range_count_option

        class_uri = cls.get_class_uri()
        # `procedure` is inside the function.
        procedure = f"""python3 << EOF
opts = {class_uri}._iterpret_opt_argument(**{rc_opt.to_dict()})
args, kwargs = {class_uri}.CONVERTER_MAPS['{name}'](opts)
{class_uri}.FUNCTION_MAPS['{vim_funcname}'](*args, **kwargs)
EOF""".strip()
        vim.command(
            f"""function! {vim_funcname}({cls._make_vimfunc_params(rc_opt)}) 
            {procedure}
            endfunction
            """
        )

        command = cls._make_command(nargs, name, vim_funcname, rc_opt, complete, addr)
        # print("command", command)
        vim.command(command)
        assert vim_funcname not in cls.FUNCTION_MAPS, "Duplicated Command"
        cls.FUNCTION_MAPS[vim_funcname] = func
        cls.COMMAND_MAPS[name] = command

        return func

    @classmethod
    def _make_vimfunc_params(
        cls,
        range_count_option: RangeCountOption,
    ) -> str:
        """
        Based on `range` and `count` option, determine the parameters
        of the vim-function.
        The candidates are as follows.
        (line1, line2, q_args)
        (count, q_args)
        (q_args)
        """
        type_, _ = range_count_option.pair
        if type_ == RangeCountType.RANGE:
            return ",".join(["line1", "line2", "q_args"])
        elif type_ == RangeCountType.COUNT:
            return ",".join(["count", "q_args"])
        else:
            assert type_ is RangeCountType.NONE
            return ",".join(["q_args"])

    @classmethod
    def _make_command(
        cls,
        nargs: NARGS,
        command_name: str,
        function_name: str,
        range_count_option: RangeCountOption,
        complete: str | None = None,
        addr: str | None = None,
    ) -> str:
        """Note that the"""

        if isinstance(nargs, str):
            assert nargs in {"*", "?", "+"}

        # Current implentation deficiency
        assert addr is None

        result = f"command! -nargs={nargs} "

        type_, value = range_count_option.pair
        if type_ == RangeCountType.RANGE:
            if value and (value is not True):
                result += f" -range={value} "
            else:
                result += " -range"
        elif type_ == RangeCountType.COUNT:
            if value and (value is not True):
                result += f" -count={value} "
            else:
                result += " -count "

        if complete is not None:
            result += f" -complete={complete} "
        # [TODO](Other options...)

        result += f" {command_name} "

        result += f" call {function_name}"

        parameters = []
        if type_ == RangeCountType.RANGE:
            parameters += ["<line1>", "<line2>"]
        elif type_ == RangeCountType.COUNT:
            parameters.append("<count>")

        parameters.append("<q-args>")

        result += f"({','.join(parameters)})"
        return result

    @classmethod
    def _iterpret_opt_argument(cls, count=None, range=None):
        """This function interprets when the original function is as below.
        This function is immediately called from `VimFunctions` to revolve
        the information about arguments.

        def command_func(opts: dict):
            pass

        Note that this interface mimics as `lua`.

        [TODO]: `<mods>`, `<bang>` cannot be handled yet.

        # This function is very closedly connected to `_make_command`.
        # Especially, for the number of arguments of `vim_function` .
        """
        opts = dict()

        opts["args"] = vim.eval("a:q_args")
        # [TODO] This is crude implementation
        # It is desirable to approach to the "true" implementation.
        # For example, this cannot handle the case where `space` is included
        # inside the '"'.
        opts["fargs"] = [elem for elem in shlex.split(opts["args"])]

        if count is not None:
            # Func(count, q_args)
            # (<count>, <q-args>)
            opts["count"] = int(vim.eval("a:count"))
        elif range is not None:
            # Func(line1, line2, q_args)
            # (<count>, <q-args>)
            opts["line1"] = int(vim.eval("a:line1"))
            opts["line2"] = int(vim.eval("a:line2"))
            opts["range"] = opts["line2"] - opts["line1"] + 1
        return opts

    @classmethod
    def get_class_uri(cls):
        try:
            prefix = f"{__name__}."
        except:
            prefix = ""
        return f"{prefix}CommandManager"

    @classmethod
    def to_vimfunc_name(cls, name: str) -> str:
        vim_funcname = f"PytoyFunc_FOR_COMMAND_{name}"
        return vim_funcname

    @classmethod
    def _deregister_for_func(cls, name: str):
        vim_funcname = cls.to_vimfunc_name(name)
        vim.command(f"delfunction {vim_funcname}")
        vim.command(f"delcommand {name}")

        del cls.FUNCTION_MAPS[vim_funcname]
        del cls.COMMAND_MAPS[name]
        del cls.CONVERTER_MAPS[name]

    @classmethod
    def _handle_existent_command(cls, name: str, exist_ok: bool):
        if cls.is_exist(name):
            if exist_ok:
                cls.deregister(name=name, no_exist_ok=False)
            else:
                raise ValueError(f"The same `command` is already registered. `{name=}`")


Command: TypeAlias = CommandManager


if __name__ == "__main__":
    # Below are the test functions.
    pass

    @CommandManager.register(name="MockCommandNoArg")
    def mock_command():
        print("Hellomock")

    @CommandManager.register(name="MockCommandDictArg")
    def mock_command2(opts: dict):
        print("Hellomock", opts)

    def crude(a, b, c):
        return [str(a), str(b), str(c), "curud"]

    @CommandManager.register(
        name="MockCommandStrArg", complete=lambda a, b, c: [str(a), str(b), str(c)]
    )
    def mock_command3(s: str):
        print("HelloStr", s)

    @CommandManager.register(name="MockClass")
    class Mock:
        def __call__(self, s: str = "optional"):
            print("HelloStrACLASS", s)

    @CommandManager.register(name="MockTarget")
    class Target:
        def __call__(self, s: str = "optional"):
            print(s)

        def customlist(self, arg_lead: str, cmd_line: str, cursor_pos: int):
            candidates = ['"DAFA"', "'AAAC'", "'AABC'"]
            valid_candidates = [
                elem for elem in candidates if elem.startswith(arg_lead)
            ]
            if valid_candidates:
                return valid_candidates
            return candidates
