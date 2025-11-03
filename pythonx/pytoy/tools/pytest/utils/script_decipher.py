from dataclasses import dataclass
from pathlib import Path


@dataclass
class _TestTarget:
    path: Path
    start_line: int
    end_line: int
    funcname: str
    classname: str = None

    @property
    def command(self):
        """Return the test specification comment"""
        if not self.classname:
            return f'pytest "{self.path}::{self.funcname}"'
        return f'pytest "{self.path}::{self.classname}::{self.funcname}"'


class ScriptDecipher:
    def __init__(self, path, targets):
        self.path = path
        self.targets = targets

    def pick(self, line_number: int):
        """Return the most appropriate `TestTarget`."""
        range_to_target = dict()
        for target in self.targets:
            if target.start_line <= line_number <= target.end_line:
                return target
        return None

    @classmethod
    def from_path(cls, path: Path):
        # [NOTE]: import of parso takes some time,
        # so, we do now want to import it at initialization.
        import parso

        path = Path(path)
        text = path.read_text(encoding="utf8")
        module = parso.parse(text)
        targets = []
        targets += cls._gather_test_funcs(module, path)
        targets += cls._gather_test_class_methods(module, path)
        return cls(path, targets)

    @classmethod
    def _gather_test_funcs(cls, module, path):
        def _to_target(node):
            name = node.name.value
            start_line = node.start_pos[0]
            end_line = node.end_pos[0]
            target = _TestTarget(
                path=path, start_line=start_line, end_line=end_line, funcname=name
            )
            return target

        targets = []
        children = getattr(module, "children", [])
        for node in children:
            if node.type == "funcdef":
                target = _to_target(node)
                targets.append(target)
            if node.type == "decorated":
                cands = getattr(node, "children", [])
                for cand in cands:
                    if cand.type == "funcdef":
                        target = _to_target(cand)
                        targets.append(target)
        return targets

    @classmethod
    def _gather_test_class_methods(cls, module, path):
        def _search_method_nodes(class_node):
            def _inner(node):
                if node.type == "funcdef":
                    return [node]
                children = getattr(node, "children", [])
                return sum((_inner(child) for child in children), [])

            return _inner(class_node)

        targets = []
        children = getattr(module, "children", [])
        for node in children:
            if node.type == "classdef":
                classname = node.name.value
                method_nodes = _search_method_nodes(node)
                for method_node in method_nodes:
                    funcname = method_node.name.value
                    start_line = method_node.start_pos[0]
                    end_line = method_node.end_pos[0]
                    target = _TestTarget(
                        path=path,
                        start_line=start_line,
                        end_line=end_line,
                        funcname=funcname,
                        classname=classname,
                    )
                    targets.append(target)
        return targets


if __name__ == "__main__":
    import parso
    from pathlib import Path

    module = parso.parse(Path(__file__).read_text())
    print(module)
    interpreter = ScriptDecipher.from_path(__file__)
    print(len(interpreter.targets))
    p = interpreter.pick(12)
