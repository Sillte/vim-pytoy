from pytoy.lib_tools.terminal_backend.protocol import (
    LineBufferProtocol,
    DEFAULT_LINES,
    DEFAULT_COLUMNS,
)
import re


# Comprehensive regex to remove ANSI escape codes and other common control characters.
# This regex is designed to work with Python strings (Unicode).
# It covers:
# 1. CSI (Control Sequence Introducer) sequences: \x1b[...m, \x1b[...J, \x1b[...H, etc.
#    - \x1b\[ : Matches the ESC [ literal.
#    - [0-9;?]* : Matches zero or more parameter bytes (digits, semicolons, question marks).
#    - [ -/]* : Matches zero or more intermediate bytes (ASCII space to forward slash).
#    - [@-~] : Matches the final byte that identifies the sequence type.
# 2. OSC (Operating System Command) sequences: \x1b]...BEL or \x1b]...ESC\
#    - \x1b\] : Matches the ESC ] literal.
#    - .*? : Matches any characters non-greedily (the content of the OSC).
#    - (?: \x07 | \x1b\\ ) : Non-capturing group for the terminator, which can be BEL (\x07) or ST (ESC \).
# 3. Character Set Switching: \x1b(A, \x1b)B etc.
#    - \x1b[\(\)][A-Za-z] : Matches ESC ( or ESC ) followed by a letter.
# 4. Standalone Control Characters: Common non-printable ASCII characters.
#    - [\x00-\x08\x0b\x0c\x0e-\x1f\x7f] : Matches NUL, SOH, STX, ETX, EOT, ENQ, ACK, BEL, BS, VT, FF, SO, SI, DLE, DC1-DC4, NAK, SYN, ETB, CAN, EM, SUB, ESC, FS, GS, RS, US, DEL.
#    - Note: \x0a (LF - newline) and \x0d (CR - carriage return) are intentionally excluded from this last part,
#      as they are typically desired as actual line breaks in the output.
#      If you want to remove ALL non-printable characters including newlines/tabs, you would adjust this part.
CONTROL_CODE_RE = re.compile(
    r"""
    \x1b\[             # CSI escape sequence (starts with ESC[)
    [0-9;?]* # Parameter bytes (digits, semicolons, question marks)
    [ -/]* # Intermediate bytes (space to slash)
    [@-~]              # Final byte (e.g., 'm' for SGR, 'J' for erase, 'H' for cursor home)
    |
    \x1b\]             # OSC (Operating System Command) escape sequence (starts with ESC])
    .*?                # Any characters (non-greedy)
    (?:                # Non-capturing group for termination
        \x07           # BEL (ASCII 7)
        |
        \x1b\\         # ST (String Terminator - ESC \)
    )
    |
    \x1b[\(\)][A-Za-z] # Character set switching (e.g., ESC(B)
    |
    [\x00-\x08\x0b\x0c\x0e-\x1f\x7f] # Other common non-printable ASCII control characters (excluding LF, CR, TAB)
    """,
    re.VERBOSE | re.DOTALL,  # re.DOTALL allows '.' to match newlines for OSC sequences
)


class LineBufferNaive(LineBufferProtocol):
    """Return the `lines` based on given information."""

    def __init__(self, columns: int = DEFAULT_COLUMNS, lines: int = DEFAULT_LINES):
        self._chunk_buffer = ""
        self._last_row = 1  # First.
        self._cursor_move_pattern = re.compile(r"\x1b\[(\d+);(\d+)H")
        self._columns = columns
        self._lines = lines
        self._empty_succession: int = 0
        self._prev_non_empty_line: str | None = None

    @property
    def columns(self) -> int:
        return self._columns

    @property
    def lines(self) -> int:
        return self._lines

    def reset(self):
        """Please invoke this function when you restarted this buffer, if necessary."""
        self._chunk_buffer = ""

    def flush(self) -> list[str]:
        line = CONTROL_CODE_RE.sub("", self._chunk_buffer)
        self._chunk_buffer = ""
        return [line]

    @property
    def chunk(self) -> str:
        return self._chunk_buffer

    def feed(self, chunk: str) -> list[str]:
        """Append a chunk of text and return any complete lines (with control codes removed).
        If a chunk does not contain a newline or carriage return, the data is buffered.
        Multiple lines in one chunk are handled gracefully.
        """
        chunk = self._detect_cursor_move_and_maybe_break(chunk)

        lines: list[str] = []

        self._chunk_buffer += chunk
        # Process lines when a newline or carriage return is found
        # Use a loop to handle multiple newlines in a single chunk
        while "\n" in self._chunk_buffer or "\r" in self._chunk_buffer:
            # Find the first newline or carriage return
            newline_idx = -1
            # Prefer \r\n as a single unit if present
            crnl_idx = self._chunk_buffer.find("\r\n")
            if crnl_idx != -1:
                newline_idx = crnl_idx + 1  # Point to the 'n' in '\r\n'
            else:
                nl_idx = self._chunk_buffer.find("\n")
                cr_idx = self._chunk_buffer.find("\r")

                if nl_idx != -1 and (cr_idx == -1 or nl_idx < cr_idx):
                    newline_idx = nl_idx
                elif cr_idx != -1:
                    newline_idx = cr_idx

            if newline_idx != -1:
                # Extract the line including the newline/CR character(s)
                line_to_process = self._chunk_buffer[: newline_idx + 1]
                self._chunk_buffer = self._chunk_buffer[newline_idx + 1 :]

                if line_to_process.strip("\r\n") == "\x1b[K":
                    # print("line_to_process", line_to_process)
                    continue

                # Strip control codes and ANSI escape sequences
                cleaned_line = CONTROL_CODE_RE.sub("", line_to_process)
                # `append` line should not contain `\n`.
                cleaned_line = cleaned_line.replace("\r\n", "\n").strip("\n")
                cleaned_line = cleaned_line.replace("\r", "")

                # May be carridge return and data is repeated.
                if self._prev_non_empty_line == cleaned_line:
                    continue
                if cleaned_line:
                    self._prev_non_empty_line = cleaned_line

                lines.append(cleaned_line)
            else:
                break
        return lines

    def _detect_cursor_move_and_maybe_break(self, text: str) -> str:
        # ANSI cursor move pattern: \x1b[{row};{col}H
        pattern = self._cursor_move_pattern
        output = ""
        last_end = 0
        for match in pattern.finditer(text):
            row = int(match.group(1))
            _ = int(match.group(2))  # col
            if row > self._last_row:
                output += text[last_end : match.start()] + "\r\n"
            else:
                output += text[last_end : match.start()]
            self._last_row = row
            last_end = match.end()
        output += text[last_end:]
        return output
