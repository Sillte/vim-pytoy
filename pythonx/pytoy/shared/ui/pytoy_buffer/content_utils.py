def normalize_buffer_content(content: str) -> str:
    return content.replace("\r\n", "\n").replace("\r", "\n")


def split_buffer_content(content: str) -> list[str]:
    return normalize_buffer_content(content).split("\n")


def prepare_append_lines(last_line: str, content: str, *, is_empty: bool) -> tuple[bool, list[str]] | None:
    """Normalize and split appended text, returning whether to replace the last line.

    Returns ``None`` for empty input. Otherwise returns
    ``(replace_last_line, lines)``; the first line replaces the existing last
    line when the buffer is empty or that line is blank.
    """
    content = normalize_buffer_content(content)
    if not content:
        return None
    lines = content.split("\n")
    replace_last_line = is_empty or not normalize_buffer_content(last_line)
    return replace_last_line, lines
