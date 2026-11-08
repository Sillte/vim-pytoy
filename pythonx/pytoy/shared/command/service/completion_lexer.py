import shlex
from dataclasses import dataclass

from pytoy.shared.command.core.models import Token
from pytoy.shared.command.core.tokenizer import tokenize


@dataclass(frozen=True)
class CompletionToken:
    value: str  # Decoded value of the token.
    start: int  # Start of the source range replaced by completion.
    end: int  # Exclusive end of the source range replaced by completion.
    index: int  # Token's zero-based position in the command line.
    leading: str  # Decoded token prefix before the cursor.
    quote: str | None = None  # Quote style associated with the cursor's token context.
    quote_value_start: int | None = None  # Decoded offset where the quoted section starts.
    quote_start: int | None = None  # Source index of the opening quote.
    quote_end: int | None = None  # Source index of the closing quote, or None if unclosed.


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


def _find_quote_end(cmd_line: str, quote_start: int, quote: str, token_end: int) -> int | None:
    escaped = False
    for index in range(quote_start + 1, token_end):
        char = cmd_line[index]
        if escaped:
            escaped = False
        elif char == "\\" and quote != "'":
            escaped = True
        elif char == quote:
            return index
    return None


def _raw_token_range(cmd_line: str, token: Token) -> tuple[int, int]:
    start, end = token.start, token.end
    if start > 0 and end < len(cmd_line):
        quote = cmd_line[start - 1]
        if quote in "'\"" and cmd_line[end] == quote:
            return start - 1, end + 1
    return start, end


def _quote_context(
    cmd_line: str, token_start: int, token_end: int, cursor_pos: int
) -> tuple[str, int, int | None] | None:
    _, quote, quote_start, _ = _unfinished_state(cmd_line[token_start:cursor_pos])
    if quote is not None and quote_start is not None:
        absolute_quote_start = token_start + quote_start
        quote_end = _find_quote_end(cmd_line, absolute_quote_start, quote, token_end)
        return quote, absolute_quote_start, quote_end

    if cursor_pos > token_start and cmd_line[cursor_pos - 1] in "'\"":
        closing_quote = cmd_line[cursor_pos - 1]
        _, prior_quote, prior_quote_start, _ = _unfinished_state(cmd_line[token_start : cursor_pos - 1])
        if prior_quote == closing_quote and prior_quote_start is not None:
            return closing_quote, token_start + prior_quote_start, cursor_pos - 1
    return None


def _completion_token(
    cmd_line: str,
    token: Token,
    token_start: int,
    token_end: int,
    cursor_pos: int,
    quote_context: tuple[str, int, int | None],
) -> CompletionToken:
    quote, quote_start, quote_end = quote_context
    leading = _decode_partial_token(cmd_line[token_start:cursor_pos])
    quote_value_start = len(_decode_partial_token(cmd_line[token_start:quote_start]))
    return CompletionToken(
        value=token.value,
        start=token_start,
        end=token_end,
        index=token.index,
        leading=leading,
        quote=quote,
        quote_value_start=quote_value_start,
        quote_start=quote_start,
        quote_end=quote_end,
    )


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

    quote_value_start = None
    if quote is not None and quote_start is not None:
        quote_start_in_token = quote_start - token_start
        quote_value_start = len(_decode_partial_token(raw_token[:quote_start_in_token]))

    tokens.append(
        CompletionToken(
            value=value,
            start=token_start,
            end=len(cmd_line),
            index=len(tokens),
            leading=leading,
            quote=quote,
            quote_value_start=quote_value_start,
            quote_start=quote_start,
        )
    )
    return tokens


def tokenize_for_completion(cmd_line: str, cursor_pos: int) -> list[CompletionInputToken]:
    """Tokenize input and preserve quote context for the token being completed."""
    try:
        tokens = tokenize(cmd_line)
    except ValueError:
        return _tokenize_unfinished(cmd_line, cursor_pos)

    completion_tokens: list[CompletionInputToken] = []
    for token in tokens:
        token_start, token_end = _raw_token_range(cmd_line, token)
        if token_start <= cursor_pos <= token_end:
            quote_context = _quote_context(cmd_line, token_start, token_end, cursor_pos)
            if quote_context is not None:
                completion_tokens.append(
                    _completion_token(cmd_line, token, token_start, token_end, cursor_pos, quote_context)
                )
                continue
        completion_tokens.append(token)
    return completion_tokens
