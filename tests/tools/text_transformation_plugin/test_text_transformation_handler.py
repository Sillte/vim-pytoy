from pathlib import Path

import pytest

from pytoy.tools.text_transformation_plugin import (
    InvalidTextTransformationPluginError,
    InvalidTextTransformationResultError,
    TextTransformationHandler,
    TextTransformationNotFoundError,
)


def _write_plugin(path: Path, source: str) -> None:
    path.write_text(source, encoding="utf-8")


def test_runs_named_transformation_and_lists_names(tmp_path: Path) -> None:
    _write_plugin(
        tmp_path / "transformations.py",
        """
from pytoy.tools.text_transformation_plugin import register_text_transformation

@register_text_transformation(name="uppercase")
def uppercase(content: str) -> str:
    return content.upper()
""",
    )

    handler = TextTransformationHandler(tmp_path)

    assert handler.names == ("uppercase",)
    assert handler.transform("uppercase", "hello") == "HELLO"


def test_rejects_duplicate_transformation_names(tmp_path: Path) -> None:
    source = """
from pytoy.tools.text_transformation_plugin import register_text_transformation

@register_text_transformation(name="duplicate")
def transform(content: str) -> str:
    return content
"""
    _write_plugin(tmp_path / "first.py", source)
    _write_plugin(tmp_path / "second.py", source)

    with pytest.raises(InvalidTextTransformationPluginError, match="Duplicate text transformation name"):
        TextTransformationHandler(tmp_path).transform("duplicate", "content")


def test_rejects_unknown_transformation(tmp_path: Path) -> None:
    with pytest.raises(TextTransformationNotFoundError, match="not found"):
        TextTransformationHandler(tmp_path).transform("missing", "content")


def test_rejects_non_string_result(tmp_path: Path) -> None:
    _write_plugin(
        tmp_path / "bad.py",
        """
from pytoy.tools.text_transformation_plugin import register_text_transformation

@register_text_transformation(name="bad")
def bad(content: str) -> str:
    return 42
""",
    )

    with pytest.raises(InvalidTextTransformationResultError, match="expected str"):
        TextTransformationHandler(tmp_path).transform("bad", "content")


def test_rejects_invalid_transformation_name() -> None:
    from pytoy.tools.text_transformation_plugin import register_text_transformation

    with pytest.raises(ValueError, match="Invalid text transformation name"):
        register_text_transformation(name="../escape")


def test_discovers_names_without_importing_plugin_code(tmp_path: Path) -> None:
    side_effect = tmp_path / "imported.txt"
    _write_plugin(
        tmp_path / "plugin.py",
        f"""
from pathlib import Path
from pytoy.tools.text_transformation_plugin import register_text_transformation as register

Path({str(side_effect)!r}).write_text("imported", encoding="utf-8")

@register(name="uppercase")
def uppercase(content: str) -> str:
    return content.upper()
""",
    )
    handler = TextTransformationHandler(tmp_path)

    assert handler.names == ("uppercase",)
    assert not side_effect.exists()
    assert handler.transform("uppercase", "hello") == "HELLO"
    assert side_effect.read_text(encoding="utf-8") == "imported"


def test_dumps_loadable_examples_without_overwriting_existing_files(tmp_path: Path) -> None:
    handler = TextTransformationHandler(tmp_path)

    assert handler.dump_default_examples()
    assert handler.names == ("replace_foo", "uppercase")
    assert handler.transform("uppercase", "text") == "TEXT"
    assert handler.transform("replace_foo", "foo food") == "bar bard"

    example_path = tmp_path / "example.py"
    example_path.write_text("# user content", encoding="utf-8")
    assert not handler.dump_default_examples()
    assert example_path.read_text(encoding="utf-8") == "# user content"
