import shlex
from dataclasses import dataclass


@dataclass
class Token:
    value: str
    start: int  # Start index on cmd_line
    end: int  # End index on cmd_line. cmd_line[start: end] correspond to the original.
    index: int  # Order of the token.

    def is_current_token(self, current_pos: int):
        # [NOTE]: It may require some
        return self.start <= current_pos <= self.end


# shlex is considering `"` or `'`, so it expands to
QUOATE_CHARS = {'"', "'"}


def tokenize(cmd_line: str) -> list[Token]:
    """Generate the list of tokens from `cmd_line`."""
    lexer = shlex.shlex(cmd_line, posix=True)
    lexer.whitespace_split = True
    lexer.commenters = ""

    tokens = []
    current_pos = 0
    index = 0

    while True:
        token_str = lexer.get_token()
        if token_str == lexer.eof:
            break
        if not token_str:
            break
        if not cmd_line[current_pos:]:
            break

        diff_pos = cmd_line[current_pos:].find(token_str)
        if diff_pos == -1:
            break
        start_pos = current_pos + diff_pos
        end_pos = start_pos + len(token_str) - 1

        while 1 <= start_pos and cmd_line[start_pos - 1] in QUOATE_CHARS:
            start_pos -= 1
        while end_pos + 1 < len(cmd_line) and cmd_line[end_pos + 1] in QUOATE_CHARS:
            end_pos += 1
        end_pos += 1  # arg[start_pos: start_pos + end_pos] is content

        tokens.append(Token(token_str, start_pos, end_pos, index))
        current_pos = end_pos
        index += 1

    return tokens


if __name__ == "__main__":
    cmd = 'mycmd --input=abc --flag --output `somefile.txt` --input "some  file.txt"'
    tokens = tokenize(cmd)
    for t in tokens:
        print(f"[{t.index}] '{t.value}' ({t.start}-{t.end})", cmd[t.start : t.end])
