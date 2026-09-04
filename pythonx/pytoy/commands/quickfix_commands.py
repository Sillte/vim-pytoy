from typing import Annotated, Literal

from pytoy.shared.command import App, Argument

app = App()


@app.command("Quickfix")
def quickfix_command(kind: Annotated[Literal["open", "next", "prev"] | None, Argument()] = None):
    from pytoy.shared.ui.pytoy_quickfix import PytoyQuickfix, QuickfixPresenter

    quickfix = PytoyQuickfix()
    if not quickfix.records:
        raise ValueError("No quickfix records.")

    match kind:
        case "open":
            viewer = QuickfixPresenter(quickfix)
            viewer.show()
        case "next":
            quickfix.next()
        case "prev":
            quickfix.prev()
