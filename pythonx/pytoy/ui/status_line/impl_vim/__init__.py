from pytoy.ui.status_line.impl_vim.expr_registry import VimExprRegistry
from pytoy.ui.status_line.impl_vim.models import StatusNode, Conditional, Align
from pytoy.ui.status_line.impl_vim.models import parse_statusline, to_statusline
from pytoy.ui.status_line.impl_vim.node_converters import VimStatusNodeConverter
from pytoy.ui.status_line.impl_vim.node_converters import UnknownNodeConverter
from pytoy.ui.status_line.impl_vim.node_converters import VimExprNodeConverter
from pytoy.ui.status_line.impl_vim.node_converters import VimTextNodeConverter
from pytoy.ui.status_line.models import StatusLineItem, UnknownStatusLineItem, TextStatusLineItem, FunctionStatusLineItem
from pytoy.ui.status_line.protocol import StatusLineManagerProtocol
from typing import Mapping, Sequence, cast
import vim


class StatusLineManagerVim(StatusLineManagerProtocol):

    def __init__(self, vim_window: "vim.Window") -> None:
        # NOTE: UnknownNodeConverter is a fallback, hence the order is important.
        self.vim_window = vim_window 
        self.expr_registry = VimExprRegistry(self.vim_window)
        self.reverters: Mapping[type[StatusLineItem], VimStatusNodeConverter] = {FunctionStatusLineItem:VimExprNodeConverter(self.expr_registry.view),
                                                                                 TextStatusLineItem: VimTextNodeConverter(),
                                                                                 UnknownStatusLineItem: UnknownNodeConverter() }
        self.converters: Sequence[VimStatusNodeConverter] = list(self.reverters.values())
        assert isinstance(self.converters[-1], UnknownNodeConverter), "Important"
                                                               
    def _resolve_priority(self, priority: int | None) -> int:
        return priority if priority else 0

    def register(self, item: StatusLineItem) -> StatusLineItem: 
        """
        Note: 
        As a specification, the identity of `StatusLine` is regarded as the set of `node`, 
        not the sequence of `node`. 
        This restriction is unavoidable since the values of `StatusLineItem` is (value, and highlight). 
        So, when users perform `register` -> `unregister` sequentially, the position of status line may change. 
        Nevertheless, the contents of `status` line is assured to be same.  
        """
        # Update the states
        if isinstance(item, FunctionStatusLineItem):
            self.expr_registry.register(item.value)
        
        current_items = self.nodes_to_items(self.current_nodes)
        # Update the states


        items = current_items + [item]
        # 現在は挿入位置を考えない.

        # The large proprity correspond to the edge.
        #left_items = sorted([item for item in current_items if item.side == "left"], key=lambda item: self._resolve_priority(item.priority), 
        #                    reverse=True)

        #right_items = sorted([item for item in current_items if item.side == "right"], key=lambda item: self._resolve_priority(item.priority), 
        #                    reverse=False)
        #def _to_key(priority: int | None) -> float:
        #    return self._resolve_priority(priority)

        #if item.side == "left":
        #    priority = self._resolve_priority(item.priority)
        #    if (not left_items) or priority >= _to_key(left_items[0].priority):
        #        left_items = [item, *left_items]
        #    for i in range(1, len(left_items)):
        #        if priority >= _to_key(left_items[i].priority):
        #            left_items = [*left_items[:i - 1], item, *left_items[i:]]
        #            break
        #    else:
        #        left_items = [*left_items, item]
        #else:
        #    # TODO left.side == "right" の時の処理もどうように..
        #    # 今は雑な実装をしておく
        #    right_items = [item, *right_items]

        #new_nodes = self.items_to_nodes(left_items + right_items)
        new_nodes = self.items_to_nodes(items)
        self.set_statusline(new_nodes)

        return item

    @property
    def current_nodes(self) -> Sequence[StatusNode]:
        status_line = self.vim_window.options['statusline']
        if isinstance(status_line, bytes):
            status_line = status_line.decode('utf-8', errors='replace')
        return parse_statusline(status_line)

    def set_statusline(self, nodes: Sequence[StatusNode]):
        status_line = to_statusline(nodes)
        self.vim_window.options['statusline'] = status_line

    def deregister(self, item: StatusLineItem, strict_error=False) -> bool:

        nodes = self._item_to_nodes(item)

        if isinstance(item, FunctionStatusLineItem):
            self.expr_registry.deregister(item.value)

        target_index = None
        current_nodes = self.current_nodes
        for i, start_node in enumerate(current_nodes):
            if start_node == nodes[0]:
                if current_nodes[i:i + len(nodes)] == nodes:
                    target_index = i
                    break
        if target_index is None:
            print("Deletion of `deregister fails...`")
            return False
        new_nodes = [*current_nodes[:target_index], *current_nodes[target_index + len(nodes):]]
        self.set_statusline(new_nodes)
        return True


    @property
    def items(self) -> Sequence[StatusLineItem]:
        nodes = self.current_nodes
        return self.nodes_to_items(nodes)


    def nodes_to_items(self, nodes: Sequence[StatusNode]) -> list[StatusLineItem]:
        items = []
        while nodes:
            for converter in self.converters:
                ret = converter.to_item(nodes)
                if ret is not None:
                    item, nodes = ret
                    items.append(item)
                    break
        return items

    def _item_to_nodes(self, item: StatusLineItem) -> list[StatusNode]:
        return self.reverters[type(item)].from_item(item)

    def items_to_nodes(self, items: Sequence[StatusLineItem]) -> list[StatusNode]:
        return sum((self._item_to_nodes(item) for item in items), [])

def test_func():
    from pytoy.ui.status_line.models import FunctionStatusLineItem
    item = FunctionStatusLineItem(value = lambda : "AHA")
#item = TextStatusLineItem(value="TEXTTEXT", side="right")
    import vim
    manager = StatusLineManagerVim(vim.current.window)
    nodes = manager.current_nodes
    assert nodes == manager.current_nodes
    manager.register(item)
    assert nodes != manager.current_nodes
    manager.deregister(item)

    assert nodes == manager.current_nodes, (nodes, manager.current_nodes)
