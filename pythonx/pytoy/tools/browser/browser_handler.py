import logging
import traceback
from collections.abc import Callable
from functools import wraps
from typing import Any, ParamSpec, Sequence, TypeVar

from fairybrowser import sync_browser, sync_page
from fairybrowser.html_analysis import simplify_html_for_playwright
from fairybrowser.plugins.invocation import InvocationPluginRegistry
from fairybrowser.plugins.readers import PageReaderPluginRegistry

from pytoy import TERM_STDOUT
from pytoy.shared.lib.outcome import is_error
from pytoy.shared.timertask.thread_execution import ThreadExecutionExit, ThreadExecutionHandler, ThreadExecutionRequest
from pytoy.shared.ui import BufferSource
from pytoy.shared.ui.pytoy_window import PytoyWindow, PytoyWindowProvider, WindowCreationParam

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


def _format_page_source(
    title: str,
    html: str,
    *,
    simplify: bool,
    transform: Callable[[str], str] | None = None,
) -> str:
    if simplify:
        html = simplify_html_for_playwright(html)
    if transform is not None:
        html = transform(html)
    return f"<--- {title} --->\n{html}"


class BrowserHandler:
    def __init__(self, browser_name: str | None = None, *, logger: logging.Logger | None = None) -> None:
        self._browser_name = browser_name
        self._logger = logger
        self._plugin_directory = None
        self._buffer_source = BufferSource.from_str(TERM_STDOUT, "nofile")

    def open_browser(self) -> None:
        @_capture_traceback
        def on_main() -> None:
            with sync_page(browser_info=self._browser_name):
                pass

        request = ThreadExecutionRequest.from_any(on_main)
        handler = ThreadExecutionHandler.create(request)
        handler.on_exit(self._display_output)
        handler.start()

    @property
    def read_plugin_names(self) -> Sequence[str]:
        return PageReaderPluginRegistry(self._plugin_directory).list_plugins()

    def read(self, plugin_name: str) -> None:
        @_capture_traceback
        def on_main() -> str:
            result = PageReaderPluginRegistry(self._plugin_directory).read(plugin_name, browser_info=self._browser_name)
            if result is None:
                return "No reading target page exists."
            return result

        self._notify_start()
        request = ThreadExecutionRequest.from_any(on_main)
        handler = ThreadExecutionHandler.create(request)
        handler.on_exit(self._display_output)
        handler.start()

    @property
    def invocation_plugin_names(self) -> Sequence[str]:
        return InvocationPluginRegistry(self._plugin_directory).list_plugins()

    def invoke(self, plugin_name: str, input: str) -> None:

        @_capture_traceback
        def on_main() -> str:
            result = InvocationPluginRegistry(self._plugin_directory).invoke(plugin_name, input)
            if result is None:
                return "No invocation result."
            return str(result)

        self._notify_start()
        request = ThreadExecutionRequest.from_any(on_main)
        handler = ThreadExecutionHandler.create(request)
        handler.on_exit(self._display_output)
        handler.start()

    def _notify_start(
        self,
    ) -> None:
        window = self._open_output_window()
        window.buffer.init_buffer("Browser...")

    def _display_output(self, exit: ThreadExecutionExit[str | None]) -> None:
        if is_error(exit.outcome):
            content = "".join(traceback.format_exception(exit.outcome.exception))
        else:
            content = exit.outcome.value
            if content is None:
                return
        window = self._open_output_window()
        window.buffer.init_buffer(content)

    def _open_output_window(self) -> PytoyWindow:
        param = WindowCreationParam.for_split("vertical", try_reuse=True)
        return PytoyWindowProvider().open_window(self._buffer_source, param=param)

    def dump_source(self, *, simplify: bool = False, transform: str | None = None) -> None:
        @_capture_traceback
        def on_main() -> str:
            with sync_page(browser_info=self._browser_name) as page:
                title = page.title()
                html = page.content()

            text_transformer: Callable[[str], str] | None = None
            if transform is not None:
                from pytoy.tools.text_transformation_plugin import TextTransformationHandler

                handler = TextTransformationHandler.from_global_folder()
                transform_name = transform

                def apply_transform(content: str) -> str:
                    return handler.transform(transform_name, content)

                text_transformer = apply_transform
            return _format_page_source(title, html, simplify=simplify, transform=text_transformer)

        self._notify_start()
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

        self._notify_start()
        request = ThreadExecutionRequest.from_any(on_main)
        handler = ThreadExecutionHandler.create(request)
        handler.on_exit(self._display_output)
        handler.start()
