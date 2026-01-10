from pytoy.tty_executor.impls.process_utils import force_kill
from pytoy.tty_executor.models import ConsoleSnapshot, WaitOperation, InputOperation
from pytoy.tty_executor.protocol import TTYApplicationProtocol


from typing import Sequence


class ShellApplication(TTYApplicationProtocol):
    WIN_DEFAULT_SHELL_COMMAND = "cmd.exe"
    LINUX_DEFAULT_SHELL_COMMAND = "bash"

    def __init__(self, command: str | None = None):
        self._command = "cmd.exe"

    @property
    def command(self) -> str:
        return self._command

    def is_busy(self, children_pids: list[int], snapshot: ConsoleSnapshot) -> bool:
        return bool(children_pids)

    def make_lines(self, input_str: str) -> Sequence[InputOperation]:
        """Modify the command before sending to `terminal`"""
        raw_lines = [line.rstrip("\r") for line in input_str.split("\n")]
        joined_lines: list[str] = []
        buffer = ""
        continuation_chars = {"\\", "^", "`"}
        for line in raw_lines:
            stripped = line.rstrip()
            if stripped and stripped[-1] in continuation_chars:
                # 継続文字を削除して空白を追加
                buffer += stripped[:-1] + " "
            else:
                buffer += stripped
                joined_lines.append(buffer)
                buffer = ""

        if buffer:
            joined_lines.append(buffer)

        return joined_lines

    def interrupt(self, pid: int, children_pids: list[int]):
        _ = children_pids
        """Interrupt the process.
        """
        _ = pid
        for child in children_pids:
            force_kill(child)


class IPythonApplication(TTYApplicationProtocol):
    def __init__(self, command: str = "ipython"):
        self._command = command
        self._in_pattern = re.compile(r"In \[(\d+)\]:")
        self._is_prepared = False

    @property
    def command(self) -> str:
        return self._command

    def is_busy(self, children_pids: list[int], snapshot: ConsoleSnapshot) -> bool:
        # 最終行付近にプロンプト In [x]: がなければ busy とみなす
        lines = [line.strip() for line in snapshot.content.split("\n") if line.strip()]
        if not lines:
            return True
        last_line = lines[-1]
        is_ready = bool(self._in_pattern.match(last_line))
        if is_ready:
            self._is_prepared = True
        return not is_ready

    def make_lines(self, input_str: str) -> Sequence[InputOperation]:
        result: list[InputOperation] = []

        # 1. cpaste モード開始
        result.append("%cpaste -q")
        result.append(WaitOperation(0.2))

        # 2. コード本体 (内部の改行を PTY 向けに \r に)
        body = input_str.replace("\r\n", "\n").replace("\n", "\r")
        result.append(body)
        result.append(WaitOperation(0.1))

        # 3. 終了合図
        result.append("--")
        result.append(WaitOperation(0.1))

        return result

    def interrupt(self, pid: int, children_pids: list[int]):
        # ここは OS や環境に応じた Ctrl-C 送信が必要
        # CTRL + Cを後で実装する。これにはちょっと工夫が必要
        raise RuntimeError("Not yet implemented.")
        ...