from typing import Annotated, Literal, assert_never

from pytoy.shared.command import App, Argument, Option

app = App()
type BrowserOperations = Literal["open", "source", "pages"]


@app.command("Browser")
def browser_command(
    operation: Annotated[BrowserOperations | None, Argument()] = None, name: Annotated[str | None, Option()] = None
):
    from pytoy.tools.browser.browser_handler import BrowserHandler

    handler = BrowserHandler(browser_name=name)
    match operation:
        case "open" | None:
            handler.open()
        case "source":
            handler.dump_source()
        case "pages":
            handler.list_pages()
        case _:
            assert_never(operation)
