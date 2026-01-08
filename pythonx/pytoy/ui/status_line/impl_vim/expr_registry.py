# Note: The raw usage of PytoyVimFuncitons is not appropriate.    
# Once the utility class iss implemented, change it. 

from collections import defaultdict
from pytoy.infra.vim_function import PytoyVimFunctions, VimFunctionName
from pytoy.ui.status_line.models import StatusLineItemFunction


from typing import Mapping


class RegistryView:
    def __init__(self,
                 expr_to_function: Mapping[str, StatusLineItemFunction],
                 expr_to_funcname: Mapping[str, VimFunctionName],
                 prefix: str):
        self._expr_to_function = expr_to_function
        self._expr_to_funcname = expr_to_funcname
        self.prefix = prefix

    def from_function_to_expr(self, function: StatusLineItemFunction) -> str | None:
        funcname = PytoyVimFunctions.to_vimfuncname(function, prefix = self.prefix)
        expr = self.to_expr(funcname)
        if expr not in self._expr_to_funcname:
            raise RuntimeError("`Expr` is not registered.", expr, funcname)
        return expr

    def to_expr(self, funcname: VimFunctionName) -> str:
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
        self._expr_to_funcname: dict[str, VimFunctionName] = {}
        self._expr_to_count: dict[str, int] = defaultdict(int)

    @property
    def view(self) -> RegistryView:
        return RegistryView(self._expr_to_item, self._expr_to_funcname, self.prefix)


    def register(self, function: StatusLineItemFunction) -> str:
        """Return `VimExpr.value`.
        """
        funcname = PytoyVimFunctions.register(function, prefix=self.prefix)

        expr = self.view.to_expr(funcname)
        self._expr_to_item[expr] = function
        self._expr_to_funcname[expr] = funcname
        self._expr_to_count[expr] += 1
        return expr

    def deregister(self, function: StatusLineItemFunction) -> None:
        expr = self.view.from_function_to_expr(function)

        if expr not in self._expr_to_item:
            return
        self._expr_to_count[expr] -= 1
        if self._expr_to_count[expr] <= 0:
            funcname = self._expr_to_funcname[expr]
            PytoyVimFunctions.deregister(funcname)
            del self._expr_to_count[expr]
            del self._expr_to_funcname[expr]
            del self._expr_to_item[expr]