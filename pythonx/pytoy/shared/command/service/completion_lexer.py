import shlex
from dataclasses import dataclass

from pytoy.shared.command.core.models import Token
from pytoy.shared.command.core.tokenizer import tokenize


@dataclass(frozen=True)
class CompletionToken:
    value: str
    start: int
    end: int
    index: int
    leading: str
    open_quote: str | None = None
    open_quote_value_start: int | None = None


type CompletionInputToken = Token | CompletionToken


def _configure_lexer(text: str) -> shlex.shlex:
    lexer = shlex.shlex(text, posix=True)
    lexer.whitespace_split = True
    lexer.commenters = ""
    return lexer


def _unfinished_state(text: str) -> tuple[int | None, str | None, int | None, bool]:
    token_start = None
    quote = None
    quote_start = None
    escaped = False

    for index, char in enumerate(text):
        if token_start is None:
            if char.isspace():
                continue
            token_start = index

        if escaped:
            escaped = False
        elif char == "\\" and quote != "'":
            escaped = True
        elif quote is not None:
            if char == quote:
                quote = None
                quote_start = None
        elif char in "'\"":
            quote = char
            quote_start = index
        elif char.isspace():
            token_start = None

    return token_start, quote, quote_start, escaped


def _decode_partial_token(text: str) -> str:
    quote, _, trailing_escape = _unfinished_state(text)[1:]
    # Complete syntax only in the temporary parse input, never in the source text.
    suffix = "\\" if trailing_escape else ""
    if quote is not None:
        suffix += quote

    lexer = _configure_lexer(text + suffix)
    token = lexer.get_token()
    return token or ""


def _tokenize_unfinished(cmd_line: str, cursor_pos: int) -> list[CompletionInputToken]:
    token_start, quote, quote_start, trailing_escape = _unfinished_state(cmd_line)
    if token_start is None or (quote is None and not trailing_escape):
        raise ValueError("Input is not an unfinished quoted or escaped token")

    tokens: list[CompletionInputToken] = list(tokenize(cmd_line[:token_start]))
    if cursor_pos < token_start:
        return tokens

    raw_token = cmd_line[token_start:]
    leading_raw = raw_token[: cursor_pos - token_start]
    value = _decode_partial_token(raw_token)
    leading = _decode_partial_token(leading_raw)

    open_quote = None
    quote_value_start = None
    if quote is not None and quote_start is not None:
        quote_start_in_token = quote_start - token_start
        open_quote = quote
        quote_value_start = len(_decode_partial_token(raw_token[:quote_start_in_token]))

    tokens.append(
        CompletionToken(
            value=value,
            start=token_start,
            end=len(cmd_line),
            index=len(tokens),
            leading=leading,
            open_quote=open_quote,
            open_quote_value_start=quote_value_start,
        )
    )
    return tokens


def tokenize_for_completion(cmd_line: str, cursor_pos: int) -> list[CompletionInputToken]:
    """Tokenize normally, accepting an unfinished final quote or escape for completion."""
    try:
        tokens: list[CompletionInputToken] = []
        tokens.extend(tokenize(cmd_line))
        return tokens
    except ValueError:
        return _tokenize_unfinished(cmd_line, cursor_pos)
