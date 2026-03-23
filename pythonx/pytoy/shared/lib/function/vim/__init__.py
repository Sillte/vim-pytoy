from typing import Callable, Self
import re
from textwrap import dedent
from pytoy.shared.lib.function.domain import FunctionRegistryProtocol, FunctionName, RegisteredFunction, StrCallable


_VIM_FUNC_NAME_RE = re.compile(r"[^0-9A-Za-z_]")


def wrap_str_callable(func: Callable) -> StrCallable:
    def wrapper(*args: str) -> str:
        return str(func(*args))
    wrapper.__name__ = f"wrapped_{getattr(func, '__name__', 'func')}"
    return wrapper


class FunctionRegistryVim(FunctionRegistryProtocol):
    instances: dict[int, Self] = dict()  # type: dict[str, Self]

    @classmethod
    def get_instance(cls, id: int) -> Self:
        return cls.instances[id]

    def __init__(self):
        FunctionRegistryVim.instances[id(self)] = self
        self.id = id(self)
        self.functions: dict[FunctionName, RegisteredFunction] = dict()
        self.return_map: dict[FunctionName, str] = dict()
        import vim

        self.vim = vim

    def _get_function(self, name: FunctionName) -> RegisteredFunction:
        return self.functions[name]
    
    def _normalize_name(self, name: str) -> FunctionName:
        name = _VIM_FUNC_NAME_RE.sub("_", name)
        return name.capitalize()

    def register(self, function: Callable, name: str) -> RegisteredFunction:
        if not name:
            name = getattr(function, "__name__", function.__class__.__name__)
            if name == "<lambda>":
                name = "lambda"
            name = f"{name}_{id(function)}"

        name = self._normalize_name(name)
        ret_var_name = f"{name}_pytoy_return_{self.id}"

        if self.is_registered(name):
            raise ValueError(f"Function with name {name} is already registered.")

        if __name__ != "__main__":
            import_prefix = f"from {__name__} import FunctionRegistryVim"
        else:
            import_prefix = " "

        procedures = dedent(f"""
        python3 << EOF
        {import_prefix}
        args = vim.eval("a:000")
        ret = FunctionRegistryVim.get_instance({self.id})._get_function('{name}')(*args)
        vim.vars['{ret_var_name}'] = ret
        EOF
        """).strip()

        self.vim.command(
            dedent(
                f"""
            function! {name}(...)
            {procedures}
            return g:{ret_var_name}
            endfunction
            """
            ).strip()
        )

        self.functions[name] = RegisteredFunction(name=name, inner=function)
        self.return_map[name] = ret_var_name
        return self.functions[name]

    def is_registered(self, name: str) -> bool:
        name = self._normalize_name(name)
        return bool(name in self.functions or int(self.vim.eval(f"exists('{name}')")))

    def deregister(self, name: FunctionName | RegisteredFunction) -> None:
        if isinstance(name, RegisteredFunction):
            name = name.name
        self.functions.pop(name, None)
        self.vim.command(f"delfunction! {name}")

        ret_var = self.return_map.pop(name, None)
        if ret_var:
            self.vim.command(f"execute 'unlet! g:{ret_var}'")
