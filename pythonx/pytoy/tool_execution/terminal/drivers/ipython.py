from typing import Sequence

from pytoy.tool_execution.terminal.contract.models import (
    InputOperation,
    InterruptionCode,
    RawStr,
    Snapshot,
    TerminalDriverProtocol,
    WaitOperation,
    WaitUntilOperation,
)


class IPythonDriver(TerminalDriverProtocol):
    def __init__(self, command: str = "ipython --colors=NoColor", kind: str = "ipython"):
        self._command = command
        self._kind = kind
        import re

        self._in_pattern = re.compile(r"In \[(\d+)\]:")

        self._is_first = True

    @property
    def kind(self) -> str:
        return self._kind

    @property
    def command(self) -> str:
        return self._command

    @property
    def eol(self) -> str | None:
        return None

    def is_busy(self, children_pids: list[int], snapshot: Snapshot) -> bool:
        # 最終行付近にプロンプト In [x]: がなければ busy とみなす
        lines = [line.strip() for line in snapshot.content.split("\n") if line.strip()]
        if not lines:
            return True
        last_line = lines[-1]
        is_ready = bool(self._in_pattern.match(last_line))
        return not is_ready

    def make_operations(self, input_str: str) -> Sequence[InputOperation]:
        result: list[InputOperation] = []

        def _is_prepared(snapshot: Snapshot) -> bool:
            content = snapshot.content
            lines = [line.strip("\r ") for line in content.split("\n") if line]
            lines = [line for line in lines if line]
            if not lines:
                return False
            last_line = lines[-1]
            return bool(self._in_pattern.match(last_line))

        if self._is_first:
            # [Weak guess]: It seems a little bit wait is required after the dislay.
            result += [WaitUntilOperation(_is_prepared, timeout=3.0), WaitOperation(0.5)]
            self._is_first = False

        # Empty CRLF is uncecessary....
        body = input_str.replace("\r\n", "\n").replace("\n", "\r").strip("\r")

        result += [
            RawStr(
                "%cpaste -q\n"
            ),  # LineStr("%cpaste -q") # This is not good, since `\r` seems to be recognized as the other meaning.
            WaitOperation(0.5),
            RawStr(body),
            WaitOperation(0.5),
            RawStr("\r--\r"),
        ]
        return result

    def interrupt(self, pid: int, children_pids: list[int]) -> InterruptionCode | None:
        return InterruptionCode(preference="sigint")
