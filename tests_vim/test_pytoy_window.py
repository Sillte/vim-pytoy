from pytoy.ui.pytoy_window import PytoyWindowProvider
from pytoy.ui.pytoy_window import PytoyWindow
from pytoy.infra.core.models import CursorPosition
from pytoy.ui.pytoy_window.models import ViewportMoveMode


def test_function():
    target = "test_window"
    window = PytoyWindowProvider().create_window(target)
    assert window.buffer.path.name == target
    paths = [window.buffer.path for window in PytoyWindow.get_windows()]
    assert any(path.name == target for path in paths)

def test_unique():
    current = PytoyWindow.get_current()
    current.unique(within_tabs=True, within_windows=False)


def test_cursor():
    target = "test_window"
    window = PytoyWindowProvider().create_window(target)
    window.buffer.append("Hello1")
    window.buffer.append("Hello2")
    window.buffer.append("Hello3")
    window.buffer.append("Hello4")
    target = CursorPosition(line=2, col=5)
    window.move_cursor(cursor=target, viewport_mode=ViewportMoveMode.TOP)
    assert window.cursor == target

from pytoy.ui.pytoy_window import PytoyWindow
test_function()
test_unique()
test_cursor()
#print("OK")