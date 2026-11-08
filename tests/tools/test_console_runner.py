from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

from pytoy.shared.ui.pytoy_window import WindowCreationParam
from pytoy.tools import console as console_module
from pytoy.tools.console import ConsoleRunner


class FakeHandler:
    def __init__(self, status: str):
        self.status = status
        self.start_count = 0

    def start(self):
        self.start_count += 1


class FakeController:
    def __init__(self, handler: FakeHandler):
        self.handler = handler
        self.created = None
        self.sent = None

    def get_or_create_handler(self, driver, buffer, *, cwd):
        self.created = (driver, buffer, cwd)
        return self.handler

    def send(self, driver, buffer, content, *, cwd):
        self.sent = (driver, buffer, content, cwd)


class FakeSelector:
    def get_preferrable_driver(self, current_window):
        assert current_window is not None
        return "shell"

    def get_preferrable_buffer(self, current_window):
        assert current_window is not None
        return "__SHELL__"


class FakeWindow:
    def __init__(self):
        self.focus_count = 0

    def focus(self):
        self.focus_count += 1


class FakeWindowProvider:
    def __init__(self, window: FakeWindow):
        self.window = window
        self.opened = None

    def open_window(self, buffer, param):
        self.opened = (buffer, param)
        return self.window


def make_runner(monkeypatch, *, handler_status: str = "created"):
    current_window = SimpleNamespace(buffer=SimpleNamespace(file_path=Path("C:/project/main.py")))
    monkeypatch.setattr(console_module.PytoyWindow, "get_current", lambda: current_window)

    handler = FakeHandler(handler_status)
    controller = FakeController(handler)
    window = FakeWindow()
    provider = FakeWindowProvider(window)
    monkeypatch.setattr(console_module, "PytoyWindowProvider", lambda: provider)

    runner = ConsoleRunner.__new__(ConsoleRunner)
    cast(Any, runner)._controller = controller
    cast(Any, runner)._selector = FakeSelector()
    return runner, controller, handler, window, provider


def test_open_starts_and_shows_console(monkeypatch):
    runner, controller, handler, window, provider = make_runner(monkeypatch)

    runner.open(buffer=None, cwd="C:/project")

    assert controller.created == ("shell", "__SHELL__", Path("C:/project"))
    assert handler.start_count == 1
    assert provider.opened is not None
    assert provider.opened[0] == "__SHELL__"
    assert isinstance(provider.opened[1], WindowCreationParam)
    assert window.focus_count == 1


def test_open_reuses_running_console_without_starting_it(monkeypatch):
    runner, _, handler, _, _ = make_runner(monkeypatch, handler_status="running")

    runner.open(buffer="__TERMINAL__", cwd="C:/project")

    assert handler.start_count == 0


def test_run_uses_controller_send_to_start_and_send_command(monkeypatch):
    runner, controller, _, _, _ = make_runner(monkeypatch)

    runner.run("echo hello", buffer="__TERMINAL__", driver="shell", cwd="C:/project")

    assert controller.sent == ("shell", "__TERMINAL__", "echo hello", Path("C:/project"))
