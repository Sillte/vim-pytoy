from pytoy.commands.browser_commands import browser_command, browser_source_command
from pytoy.shared.command.core.models import CommandModel
from pytoy.shared.command.core.tokenizer import InterpretedInput, ResolvedInput, tokenize
from pytoy.tools.browser.browser_handler import _format_page_source


def test_simplify_removes_script_style_and_inline_styles() -> None:
    html = (
        "<html><head><style>.x { color: red; }</style><script>run()</script></head>"
        '<body><div class="x" style="color: red">keep</div></body></html>'
    )

    simplified = _format_page_source("Example", html, simplify=True)

    assert simplified.startswith("<--- Example --->\n")
    assert "keep" in simplified
    assert "<script" not in simplified
    assert "<style" not in simplified
    assert "style=" not in simplified


def test_source_is_preserved_without_simplify() -> None:
    html = "<html><script>run()</script></html>"

    source = _format_page_source("Example", html, simplify=False)

    assert source == f"<--- Example --->\n{html}"


def test_browser_command_parses_simplify_boolean_option() -> None:
    model = CommandModel.from_callable(browser_command)

    parsed = InterpretedInput.from_tokens(tokenize("source --simplify"), model)
    resolved = ResolvedInput.from_interpreted_input(model, parsed)

    assert resolved.kwargs["simplify"] is True


def test_browser_command_simplify_defaults_to_false() -> None:
    model = CommandModel.from_callable(browser_command)

    parsed = InterpretedInput.from_tokens(tokenize("source"), model)
    resolved = ResolvedInput.from_interpreted_input(model, parsed)

    assert resolved.kwargs["simplify"] is False


def test_transform_runs_after_simplification_and_keeps_title_header() -> None:
    html = '<script>run()</script><div style="color: red">foo</div>'
    transform_inputs: list[str] = []

    def transform(content: str) -> str:
        transform_inputs.append(content)
        return content.replace("foo", "bar")

    source = _format_page_source("Example", html, simplify=True, transform=transform)

    assert transform_inputs
    assert "<script" not in transform_inputs[0]
    assert "style=" not in transform_inputs[0]
    assert source.startswith("<--- Example --->\n")
    assert "bar" in source


def test_browser_source_command_parses_transform_option() -> None:
    model = CommandModel.from_callable(browser_source_command)

    parsed = InterpretedInput.from_tokens(tokenize("--transform=uppercase --simplify"), model)
    resolved = ResolvedInput.from_interpreted_input(model, parsed)

    assert resolved.kwargs["transform"] == "uppercase"
    assert resolved.kwargs["simplify"] is True
