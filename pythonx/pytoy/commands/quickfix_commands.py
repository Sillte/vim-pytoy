from typing import Literal, Annotated
from pytoy.shared.command import App, Argument
from pathlib import Path


app = App()

@app.command("Quickfix")
def quickfix_command(kind: Annotated[Literal["open", "next", "prev"] | None,  Argument()] = None):
    from pytoy.shared.ui.pytoy_quickfix import PytoyQuickfix
    from pytoy.shared.ui.pytoy_quickfix.presenter import QuickfixPresenter
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
    
