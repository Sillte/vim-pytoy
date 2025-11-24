from pathlib import Path
from typing import Mapping
from pytoy.ui import PytoyBuffer
from pytoy.ui.pytoy_buffer.queue_updater import QueueUpdater
from pytoy.ui.pytoy_buffer import make_buffer
from pytoy.lib_tools.terminal_backend import TerminalBackend, TerminalBackendProvider
from pytoy.lib_tools.terminal_backend.application import (
    AppClassManagerClass,
    AppManager,
)

from pytoy.lib_tools.utils import get_current_directory


class TerminalExecutor:
    def __init__(self, buffer: PytoyBuffer, terminal_backend: TerminalBackend):
        self._buffer = buffer
        self._backend = terminal_backend
        self._updater: None | QueueUpdater = None

    @property
    def buffer(self) -> PytoyBuffer:
        return self._buffer

    @property
    def backend(self) -> TerminalBackend:
        return self._backend

    @property
    def updater(self) -> QueueUpdater | None:
        return self._updater

    def start(
        self,
        cwd: str | Path | None = None, 
        env: Mapping[str, str] | None = None,
    ):
        if cwd is None:
            cwd = get_current_directory()
        if self.alive:
            print("Already running")
            return
        queue = self.backend.queue
        self.backend.start(cwd=cwd, env=env)
        self._updater = QueueUpdater(self.buffer, queue)
        self._updater.register()

    def send(self, cmd: str):
        self.backend.send(cmd)

    @property
    def alive(self) -> bool:
        return self.backend.alive and self.buffer.valid

    @property
    def busy(self) -> bool | None:
        """Whether the somework is performed or not."""
        return self.backend.busy

    def interrupt(self) -> None:
        """Stop the child process."""
        self.backend.interrupt()

    def terminate(self) -> None:
        """Kill the terminal."""
        if not self.alive:
            print("Already terminated.")
            return

        self.backend.terminate()
        assert self.updater
        self.updater.deregister()


class TerminalExecutorManagerClass:
    def __init__(
        self,
        app_manager: AppClassManagerClass,
    ):
        self._cache: dict[tuple[str, str], TerminalExecutor] = dict()
        self._app_manager = app_manager
        self._current_executor = None
        self._current_key: tuple[str, str] | None = None

    @property
    def app_manager(self):
        return self._app_manager

    def get_executor(
        self, app_name: str, buffer_name: str | None = None, **app_init_kwargs
    ) -> TerminalExecutor:
        """Get the executor and change the current_exector.
        When the specified executor is not existent, the new exector is created.
        """

        if buffer_name is None:
            buffer_name = "__CMD__"
        key = (app_name, buffer_name)

        if key in self._cache:
            executor = self._cache[key]
            if executor.alive:
                self._current_key = key
                return executor
            else:
                executor.terminate()
                # Delete the unattainable buffer and construct the new one.

        executor = self._make_executor(app_name, buffer_name, **app_init_kwargs)
        self._cache[key] = executor
        self._current_key = key

        if not executor.alive:
            executor.start()
        return executor

    @property
    def current_executor(self) -> None | TerminalExecutor:
        if not self._current_key:
            return None
        app_name, buffer_name = self._current_key
        return self.get_executor(app_name, buffer_name)

    def reset(self):
        self._current_executor = None
        for _, executor in self._cache.items():
            executor.terminate()
        self._cache = dict()

    def _make_executor(
        self, app_name: str, buffer_name: str = "__CMD__", **app_init_kwargs
    ) -> TerminalExecutor:
        buffer = make_buffer(buffer_name)
        app = self._app_manager.create(app_name, **app_init_kwargs)
        terminal_backend = TerminalBackendProvider().make_terminal(app)
        executor = TerminalExecutor(buffer, terminal_backend)
        return executor


TerminalExecutorManager = TerminalExecutorManagerClass(AppManager)
