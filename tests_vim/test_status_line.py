from pytoy.shared.ui.status_line.models import FunctionStatusLineItem
from pytoy.shared.ui.status_line import StatusLineManager
from pytoy.shared.ui.pytoy_window.protocol import WindowEvents
from pytoy.shared.ui.pytoy_window import PytoyWindowProvider

window = PytoyWindowProvider().get_current()
winid = window.winid

events = WindowEvents.from_winid(winid)
item = FunctionStatusLineItem(value=lambda: "AHA")
manager = StatusLineManager(events)
manager.register(item)
manager.deregister(item)
manager.register(item)
