from collections import defaultdict
from pytoy.shared.lib.function import RegisteredFunction, FunctionName, FunctionRegistry
from pytoy.shared.ui.status_line.models import StatusLineItemFunction


from typing import Mapping


class RegistryView:
    def __init__(self,
                 expr_to_function: Mapping[str, StatusLineItemFunction],
                 function_to_expr: Mapping[StatusLineItemFunction, str],
                 expr_to_registered: Mapping[str, RegisteredFunction],
                 prefix: str):
        self._expr_to_function = expr_to_function
        self._function_to_expr = function_to_expr
        self._expr_to_registered = expr_to_registered
        self.prefix = prefix

    def from_function_to_expr(self, function: StatusLineItemFunction) -> str | None:
        if not (expr:= self._function_to_expr.get(function)):
            raise RuntimeError("`Expr` is not registered.", expr, function, self._function_to_expr, "rere", self._expr_to_function)
        return expr

    def to_expr(self, funcname: FunctionName | RegisteredFunction) -> str:
        if isinstance(funcname, RegisteredFunction):
            funcname = funcname.impl_name
        expr = f"{funcname}()"
        return expr

    @property
    def expr_to_function(self) -> Mapping[str, StatusLineItemFunction]:
        return self._expr_to_function


class VimExprRegistry:
    """Manage the registration of `VimkFunction`.

    If without operations given by others, this class handles the lifetime of
    Vim functions.
    """
    def __init__(self, winid: int) -> None:  #noqa
        import vim
        self._winid = winid
        # NOTE: `prefix` is crucial for assuring the uniqueness among different windows. 
        self.prefix = f"W{self._winid}_PytoyFunction"
        self._expr_to_item: dict[str, StatusLineItemFunction] = {}
        self._function_to_expr: dict[StatusLineItemFunction, str] = {}
        self._expr_to_registered: dict[str, RegisteredFunction] = {}
        self._expr_to_count: dict[str, int] = defaultdict(int)

    @property
    def view(self) -> RegistryView:
        return RegistryView(self._expr_to_item, self._function_to_expr, self._expr_to_registered, self.prefix)


    def register(self, function: StatusLineItemFunction) -> str:
        """Return `VimExpr.value`.
        """
        registered_func = FunctionRegistry.register(function, prefix=self.prefix)

        expr = self.view.to_expr(registered_func)
        self._expr_to_item[expr] = function
        self._function_to_expr[function] = expr
        self._expr_to_registered[expr] = registered_func
        self._expr_to_count[expr] += 1
        return expr

    def deregister(self, function: StatusLineItemFunction) -> None:
        expr = self.view.from_function_to_expr(function)

        if expr not in self._expr_to_item:
            return
        self._expr_to_count[expr] -= 1
        if self._expr_to_count[expr] <= 0:
            registered = self._expr_to_registered[expr]
            FunctionRegistry.deregister(registered)
            del self._expr_to_count[expr]
            del self._expr_to_registered[expr]
            del self._expr_to_item[expr]
            del self._function_to_expr[function]