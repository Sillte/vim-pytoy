import logging
import traceback
from collections.abc import Callable
from functools import wraps
from typing import Any, ParamSpec, TypeVar

from fairybrowser import sync_browser, sync_page

from pytoy import TERM_STDOUT
from pytoy.shared.lib.outcome import is_error
from pytoy.shared.timertask.thread_execution import ThreadExecutionExit, ThreadExecutionHandler, ThreadExecutionRequest
from pytoy.shared.ui import BufferSource
from pytoy.shared.ui.pytoy_window import PytoyWindowProvider

P = ParamSpec("P")
T = TypeVar("T")


def _capture_traceback(func: Callable[P, T]) -> Callable[P, T | str]:
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T | str:
        try:
            return func(*args, **kwargs)
        except Exception:
            return traceback.format_exc()

    return wrapper


def _get_page_target_id(page: Any) -> str:
    session = page.context.new_cdp_session(page)
    try:
        return session.send("Target.getTargetInfo")["targetInfo"]["targetId"]
    finally:
        session.detach()


class BrowserHandler:
    def __init__(self, browser_name: str | None = None, *, logger: logging.Logger | None = None) -> None:
        self._browser_name = browser_name
        self._logger = logger

    def open(self) -> None:
        @_capture_traceback
        def on_main() -> None:
            with sync_page(browser_info=self._browser_name):
                pass

        request = ThreadExecutionRequest.from_any(on_main)
        handler = ThreadExecutionHandler.create(request)
        handler.on_exit(self._display_output)
        handler.start()

    def _display_output(self, exit: ThreadExecutionExit[str | None]) -> None:
        buffer_source = BufferSource.from_str(TERM_STDOUT, "nofile")
        if is_error(exit.outcome):
            content = "".join(traceback.format_exception(exit.outcome.exception))
        else:
            content = exit.outcome.value
            if content is None:
                return
        window = PytoyWindowProvider().open_window(buffer_source, param="vertical")
        window.buffer.init_buffer(content)

    def dump_source(self) -> None:
        @_capture_traceback
        def on_main() -> str:
            with sync_page(browser_info=self._browser_name) as page:
                header = f"<--- {page.title()} --->\n"
                return header + page.content()

        request = ThreadExecutionRequest.from_any(on_main)
        handler = ThreadExecutionHandler.create(request)
        handler.on_exit(self._display_output)
        handler.start()

    def list_pages(self) -> None:
        @_capture_traceback
        def on_main() -> str:
            with sync_page(browser_info=self._browser_name) as current_page:
                current_page_id = _get_page_target_id(current_page)

            with sync_browser(info=self._browser_name) as browser:
                pages = [
                    (page.title(), page.url, _get_page_target_id(page) == current_page_id)
                    for context in browser.contexts
                    for page in context.pages
                ]

            if not pages:
                return "No open pages."

            return "\n\n".join(
                f"[{index}] {'[current] ' if is_current else ''}{title or '(untitled)'}\n{url}"
                for index, (title, url, is_current) in enumerate(pages, start=1)
            )

        request = ThreadExecutionRequest.from_any(on_main)
        handler = ThreadExecutionHandler.create(request)
        handler.on_exit(self._display_output)
        handler.start()
