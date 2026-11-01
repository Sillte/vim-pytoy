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
    name: Annotated[str | None, Option()] = None,
    simplify: Annotated[bool, Option(default=False)] = False,
    transform: Annotated[str | None, Option(completer=_complete_text_transformation_names)] = None,
):
    from pytoy.tools.browser.browser_handler import BrowserHandler

    handler = BrowserHandler(browser_name=name)
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
    name: Annotated[str | None, Option()] = None,
    simplify: Annotated[bool, Option(default=False)] = False,
    transform: Annotated[str | None, Option(completer=_complete_text_transformation_names)] = None,
) -> None:
    from pytoy.tools.browser.browser_handler import BrowserHandler

    BrowserHandler(browser_name=name).dump_source(simplify=simplify, transform=transform)
