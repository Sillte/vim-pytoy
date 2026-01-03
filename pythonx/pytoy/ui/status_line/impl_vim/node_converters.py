from typing import Sequence

from pytoy.ui.status_line.impl_vim.expr_registry import RegistryView
from pytoy.ui.status_line.impl_vim.models import Highlight, Text, VimExpr, StatusNode
from pytoy.ui.status_line.models import FunctionStatusLineItem, TextStatusLineItem, UnknownStatusLineItem, StatusLineItem


class VimStatusNodeConverter[T: StatusLineItem]:
    """
    Note that `StatusLineItem` 1 <-> 1 or2 `StatusNode`.
    """

    def to_item(self, nodes: Sequence[StatusNode]) -> None | tuple[T, Sequence[StatusNode]]:
        """Return `None` if the start of nodes cannot be converted, 
        if conversion is possible, tuple of Item and remaining StatusNode` is returned.
        """
        ...

    def from_item(self, item:T) -> list[StatusNode]:
        ...


class UnknownNodeConverter(VimStatusNodeConverter):
    """Fallback Converter.
    """

    def to_item(self, nodes: Sequence[StatusNode]) -> tuple[UnknownStatusLineItem, Sequence[StatusNode]]:
        item = UnknownStatusLineItem(value=nodes[0])
        return item, nodes[1:]

    def from_item(self, item: UnknownStatusLineItem) -> list[StatusNode]:
        return [item.value]


class VimExprNodeConverter(VimStatusNodeConverter):

    def __init__(self, expr_reader: RegistryView):
        self.expr_reader = expr_reader

    def to_item(self, nodes: Sequence[StatusNode]) -> None | tuple[FunctionStatusLineItem | UnknownStatusLineItem, Sequence[StatusNode]]:
        if isinstance(nodes[0], Highlight) and 2 <= len(nodes) and isinstance(nodes[1], VimExpr):
            h_node, v_node = nodes[0], nodes[1]
            consume = 2
        elif isinstance(nodes[0], VimExpr):
            h_node, v_node = None, nodes[0]
            consume = 1
        else:
            return None
        if v_node.expr in self.expr_reader.expr_to_function:
            value = self.expr_reader.expr_to_function[v_node.expr]
            highlight= h_node.name if h_node else None
            item = FunctionStatusLineItem(value=value, highlight=highlight)
            return item, nodes[consume:]
        else:
            return None

    def from_item(self, item: FunctionStatusLineItem) -> list[StatusNode]:
        expr = self.expr_reader.from_function_to_expr(item.value)
        if expr is None:
            raise RuntimeError("Implementation Error.", expr)
        if item.highlight:
            return [Highlight(item.highlight), VimExpr(expr=expr)]
        else:
            return [VimExpr(expr=expr)]


class VimTextNodeConverter(VimStatusNodeConverter):

    def to_item(self, nodes: Sequence[StatusNode]) ->  None | tuple[TextStatusLineItem, Sequence[StatusNode]]:
        if isinstance(nodes[0], Highlight) and 2 <= len(nodes) and isinstance(nodes[1], Text):
            h_node, t_node = nodes[0], nodes[1]
            consume = 2
        elif isinstance(nodes[0], Text):
            h_node, t_node = None, nodes[0]
            consume = 1
        else:
            return None
        highlight= h_node.name if h_node else None
        item = TextStatusLineItem(value=t_node.value, highlight=highlight)
        return item, nodes[consume:]

    def from_item(self, item: TextStatusLineItem) -> list[StatusNode]:
        if item.highlight:
            return [Highlight(item.highlight),  Text(value=item.value)]
        else:
            return [Text(value=item.value)]