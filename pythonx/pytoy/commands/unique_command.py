from pytoy.shared.ui.pytoy_window import PytoyWindow

from typing import Annotated, Literal, assert_never
from pytoy.shared.command import App, Argument, Option
app = App()

@app.command("Unique")
def unique_command(arg: Annotated[Literal["buffer", "editor", "window", "tab"] | None, Argument()] = None):
    match arg: 
        case "buffer":
            within_tabs = True
            within_windows = True
        case "editor":
            within_tabs = False
            within_windows = True
        case "window":
            within_tabs = False
            within_windows = True
        case "tab":
            within_tabs = True
            within_windows = False
        case None:
            if 2 <= len(PytoyWindow.get_windows()):
                within_tabs = False
                within_windows = True
            else:
                within_tabs = True
                within_windows = False
        case _:
            assert_never(arg)

    current = PytoyWindow.get_current()
    current.unique(within_tabs=within_tabs, within_windows=within_windows)
