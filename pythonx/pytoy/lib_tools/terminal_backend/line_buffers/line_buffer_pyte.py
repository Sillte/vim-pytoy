from pytoy.lib_tools.terminal_backend.protocol import (
    LineBufferProtocol,
    DEFAULT_LINES,
    DEFAULT_COLUMNS,
)


class LineBufferPyte(LineBufferProtocol):
    def __init__(self, columns: int = DEFAULT_COLUMNS, lines: int = DEFAULT_LINES):
        import pyte

        self._screen = pyte.Screen(columns, lines)
        self._stream = pyte.Stream(self._screen)

    def feed(self, chunk: str) -> list[str]:
        self.stream.feed(chunk)

        cy = self.screen.cursor.y
        # print("dirty", self.screen.dirty, cy)

        start = min(self.screen.dirty, default=self.lines)
        lines = []
        for s in range(start, cy):
            line = self.screen.display[s]
            lines.append(line.rstrip())
        # print("lines", lines, self.screen.dirty, cy)
        self.screen.dirty.clear()

        if cy == self.lines - 1:  # End of cursor.
            self.screen.reset()
            self.screen.dirty.clear()
        return lines

    def flush(self) -> list[str]:
        cy = self.screen.cursor.y
        line = self.screen.display[cy]
        self.reset()
        return [line]

    def reset(self):
        self.screen.reset()
        self.screen.dirty.clear()

    @property
    def screen(self) -> "pyte.Screen":
        return self._screen

    @property
    def stream(self) -> "pyte.Stream":
        return self._stream

    @property
    def lines(self):
        return self.screen.lines

    @property
    def columns(self):
        return self.screen.columns
