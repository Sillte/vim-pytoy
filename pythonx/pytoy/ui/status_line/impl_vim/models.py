from dataclasses import dataclass, replace
from typing import Self, Mapping, Sequence, Literal, Any, Callable, assert_never, cast

@dataclass
class BaseStatusNode:

    def to_str(self) -> str:
        ...


@dataclass
class ControlStatusNode(BaseStatusNode):

    @classmethod
    def get_prefix(cls) -> str:
        ...

    @classmethod
    def construct(cls, line: str) -> tuple[Self, str]:
        ...


@dataclass
class Highlight(ControlStatusNode):
    name: str
    def to_str(self):
        return f"%#{self.name}#"

    @classmethod
    def get_prefix(cls) -> str:
        return "%#"

    @classmethod
    def construct(cls, line: str) -> tuple[Self, str]:
        prefix = cls.get_prefix()
        assert line[:len(prefix)] == prefix

        index = line.find("#", len(prefix))
        assert index != -1
        name = line[len(prefix):index]
        return cls(name=name), line[index + 1:]

@dataclass
class VimExpr(ControlStatusNode):
    expr: str   # "lightline#mode()" / "&paste ? '|' : ''"

    def to_str(self):
        return f"%{{{self.expr}}}"

    @classmethod
    def get_prefix(cls) -> str:
        return "%{"

    @classmethod
    def construct(cls, line: str) -> tuple[Self, str]:
        prefix = cls.get_prefix()
        assert line[:len(prefix)] == prefix
        start = len(prefix)
        end = line.find("}", start)
        expr = line[start:end]
        return cls(expr=expr), line[end + 1:]


@dataclass
class Conditional(ControlStatusNode):
    children: list["StatusNode"]

    def to_str(self):
        inner = "".join(child.to_str() for child in self.children)
        return f"%({inner}%)"


    @classmethod
    def get_prefix(cls) -> str:
        return "%("

    @classmethod
    def construct(cls, line: str) -> tuple[Self, str]:
        depth = 1
        i = 2  # "%(" の直後
        
        inner = None
        rest = None
        while i < len(line):
            if line.startswith("%(", i):
                depth += 1
                i += 2
            elif line.startswith("%)", i):
                depth -= 1
                if depth == 0:
                    inner = line[2:i]
                    rest = line[i+2:]
                    break
                i += 2
            else:
                i += 1
        assert inner is not None
        assert rest is not None
        children = parse_statusline(inner)
        return cls(children=children), rest


@dataclass
class Align(ControlStatusNode):

    def to_str(self):
        return f"%="

    @classmethod
    def get_prefix(cls) -> str:
        return "%="

    @classmethod
    def construct(cls, line: str) -> tuple[Self, str]:
        assert line[:2] == "%="
        return (cls(), line[2:])


@dataclass
class Text(BaseStatusNode):
    value: str

    def to_str(self) -> str:
        return self.value

    @classmethod
    def construct_by_consume_text(cls, line: str, prefixes: list[str]) -> tuple[Self, str]:
        for i in range(1, len(line)):
            for p in prefixes:
                if line.startswith(p, i):
                    return cls(value=line[:i]), line[i:]
        return cls(value=line), ""

StatusNode = Highlight | VimExpr | Conditional | Align | Text


CONTROL_NODE_TYPES: list[type[ControlStatusNode]] = [Highlight, VimExpr, Conditional, Align]


def parse_statusline(status_line: str) -> list[StatusNode]:
    line = status_line
    types = sorted(CONTROL_NODE_TYPES, key=lambda c: len(c.get_prefix()), reverse=True)
    prefix_to_cls = {cls.get_prefix(): cls for cls in types}
    prefixes = list(prefix_to_cls.keys()) 
    nodes = []
    while line:
        for key in prefix_to_cls:
            if line.startswith(key):
                cls = prefix_to_cls[key]
                node, line = cls.construct(line)
                nodes.append(node)
                break
        else:
            node, line = Text.construct_by_consume_text(line, prefixes)
            nodes.append(node)
    return nodes

def to_statusline(nodes: Sequence[StatusNode]) -> str:
    return "".join(n.to_str() for n in nodes)