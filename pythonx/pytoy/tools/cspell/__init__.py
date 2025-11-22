from pathlib import Path
from tokenize import tokenize, STRING, COMMENT
import uuid
import re
import ast
import subprocess

from dataclasses import dataclass


class CSpellOneFileChecker:
    """Mainly, motivation of this class is two-fold.

    1. It seems that `job_start` of `vim` cannot handle well
    the output of `CSpell` in windows environment.

    So, this class implements the sync version of CSpell

    2. (Only Python): In default, CSpell Checker is applied
    to all the documents, including library names.
    It may distract the user, so only the `STRING` and `COMMENT`
    are checked when the option is clarified.
    """

    def __init__(self, only_python_string=None):
        self.only_python_string = only_python_string

    def __call__(self, in_path: str | Path) -> str:
        in_path = Path(in_path)

        if not self.only_python_string:
            # [NOTE]: It seems that specification of current folder is important.
            ret = subprocess.run(
                ["cspell", in_path.as_posix()],
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=in_path.parent,
            )
            if ret.returncode != 0:
                raise ValueError("`cpell` may not be installed?")
            return ret.stdout
        else:
            return self._apply_on_python_string(in_path)

    def _apply_on_python_string(self, in_path: Path) -> str:
        if in_path.suffix != ".py":
            raise ValueError("This option can only handle `python` file.")

        def _embedded(in_path: Path | str) -> str:
            """Embedding the token information to another text.
            * UUID is used for clarifying the start of token information
            """
            in_path = Path(in_path)
            with open(in_path, "rb") as f:
                tokens = list(tokenize(f.readline))
            id_ = uuid.uuid1()
            first_line = f"UUID={id_}:{in_path.as_posix()}"
            doc = [first_line]
            for token in tokens:
                if token.type in {STRING, COMMENT}:
                    header = f"{id_}:{token.start}"  # token.start: (line, col)
                    text = token.string.replace("\r\n", "\n")
                    doc += [header, text]
            text = "\n".join(doc)
            return text

        @dataclass
        class _Order:
            """Handle the correspondence toward the original file.
            line is the one in the embedded file.
            orig_tuple are the ones in the original file. (token.start)
            """

            line: int
            orig_tuple: tuple[int, int]  # original (line, col)

            def __post_init__(self):
                self.line = int(self.line)
                self.orig_tuple = tuple([int(elem) for elem in self.orig_tuple])

        @dataclass
        class _Info:
            """Unknown word.
            (line, col) are the ones in embedded files.
            """

            line: int
            col: int
            word: str

            def __post_init__(self):
                self.line = int(self.line)
                self.col = int(self.col)

        def _analyze(text: str) -> str:
            lines = text.split("\n")
            UUID, orig_path = lines[0].split(":", 1)
            UUID = UUID.strip("UUID=")

            offset = 1  # This is because the start of index is 0.
            orders = []
            for line_no in range(1, len(lines)):
                line = lines[line_no]
                if line.startswith(UUID):
                    _, orig_tuple = line.split(":")
                    orig_tuple = ast.literal_eval(orig_tuple)
                    orders.append(
                        _Order(line=int(line_no) + offset, orig_tuple=orig_tuple)
                    )

            ret = subprocess.run(
                "cspell stdin://dummy.py",
                shell=True,
                stdout=subprocess.PIPE,
                input=text,
                text=True,
            )
            if ret.returncode != 0:
                raise ValueError("`cpell` may not be installed?")
            pattern = re.compile(r"(.*):(?P<line>\d+):(?P<col>\d+).*\((?P<word>(.+))\)")
            infos = []
            for line in ret.stdout.split("\n"):
                if m := pattern.match(line):
                    data = m.groupdict()
                    line_no = int(data["line"])
                    if line_no == 1:
                        continue  # This means `orig_path` includes the unknown word.
                    else:
                        infos.append(
                            _Info(
                                line=line_no,
                                col=int(data["col"]),
                                word=data["word"],
                            )
                        )

            commands = sorted(infos + orders, key=lambda elem: elem.line)
            result = []
            assert isinstance(commands[0], _Order)
            e_line = commands[0].line
            offset_l, offset_c = commands[0].orig_tuple
            for command in commands[1:]:
                if isinstance(command, _Order):
                    e_line = command.line
                    offset_l, offset_c = command.orig_tuple
                elif isinstance(command, _Info):
                    word = command.word
                    line = command.line - e_line - 1 + offset_l
                    col = command.col + offset_c
                    out = f"{orig_path}:{line}:{col} - Unknown word ({word})"
                    result.append(out)
            result = "\n".join(result)
            return result

        embedded_text = _embedded(in_path)
        return _analyze(embedded_text)


if __name__ == "__main__":
    checker = CSpellOneFileChecker(only_python_string=True)
    output = checker(__file__)
    print(output)
