import re
from collections.abc import Callable

TextTransformation = Callable[[str], str]

_TEXT_TRANSFORMATION_NAME = "__pytoy_text_transformation_name__"
_TEXT_TRANSFORMATION_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


def _is_valid_name(name: object) -> bool:
    return isinstance(name, str) and _TEXT_TRANSFORMATION_NAME_PATTERN.fullmatch(name) is not None


def register_text_transformation(name: str) -> Callable[[TextTransformation], TextTransformation]:
    """Register a named function as a text transformation plugin."""
    if not _is_valid_name(name):
        raise ValueError(f"Invalid text transformation name: {name!r}")

    def decorator(function: TextTransformation) -> TextTransformation:
        setattr(function, _TEXT_TRANSFORMATION_NAME, name)
        return function

    return decorator
