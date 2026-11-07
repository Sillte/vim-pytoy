from typing import Annotated, Literal, assert_never

from pytoy.shared.command import App, Argument, Option

app = App()
type BrowserOperations = Literal["open", "source", "pages"]


def _complete_text_transformation_names() -> tuple[str, ...]:
    from pytoy.tools.text_transformation_plugin import TextTransformationHandler

    return TextTransformationHandler.from_global_folder().names


@app.command("Browser")
def browser_command(
    operation: Annotated[BrowserOperations | None, Argument()] = None,
    browser_name: Annotated[str | None, Option()] = None,
    simplify: Annotated[bool, Option(default=False)] = False,
    transform: Annotated[str | None, Option(completer=_complete_text_transformation_names)] = None,
):
    from pytoy.tools.browser.browser_handler import BrowserHandler

    handler = BrowserHandler(browser_name=browser_name)
    match operation:
        case "open" | None:
            handler.open()
        case "source":
            handler.dump_source(simplify=simplify, transform=transform)
        case "pages":
            handler.list_pages()
        case _:
            assert_never(operation)


@app.command("BrowserSource")
def browser_source_command(
    browser_name: Annotated[str | None, Option()] = None,
    simplify: Annotated[bool, Option(default=False)] = False,
    transform: Annotated[str | None, Option(completer=_complete_text_transformation_names)] = None,
) -> None:
    from pytoy.tools.browser.browser_handler import BrowserHandler

    BrowserHandler(browser_name=browser_name).dump_source(simplify=simplify, transform=transform)


def _complete_browser_read_names():
    from pytoy.tools.browser.browser_handler import BrowserHandler

    return BrowserHandler().read_plugin_names


@app.command("BrowserRead")
def browser_read_command(
    plugin_name: Annotated[str, Argument(completer=_complete_browser_read_names)],
    browser_name: Annotated[str | None, Option()] = None,
) -> None:
    from pytoy.tools.browser.browser_handler import BrowserHandler

    BrowserHandler(browser_name=browser_name).read(plugin_name)


def _complete_browser_invocation_names():
    from pytoy.tools.browser.browser_handler import BrowserHandler

    return BrowserHandler().invocation_plugin_names


@app.command("BrowserInvoke")
def browser_invoke_command(
    plugin_name: Annotated[str, Argument(completer=_complete_browser_invocation_names)],
    browser_name: Annotated[str | None, Option()] = None,
) -> None:
    from pytoy.shared.ui import PytoyWindow
    from pytoy.tools.browser.browser_handler import BrowserHandler

    current_window = PytoyWindow.get_current()
    selection = current_window.selection
    text = current_window.buffer.get_text(selection)

    if not text:
        raise ValueError("Text is empty.")
    current_window.buffer.replace_text(selection, "")

    BrowserHandler(browser_name=browser_name).invoke(plugin_name, input=text)


# playwright と selenium を比較してー Version2 .
#
#
