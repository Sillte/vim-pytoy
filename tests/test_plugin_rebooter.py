import json
import sys
from pathlib import Path

from pytoy.devtools import PluginRebooter
from pytoy.devtools.dev_rebooter import rebooter
from pytoy.devtools.dev_rebooter.impls import nvim
from pytoy.shared.lib.backend import BackendEnum
from pytoy.tool_execution.execution_environment.uv_environment import UVEnvironmentSolver


def test_restart_writes_contract_cache_files_before_launching(tmp_path, monkeypatch):
    plugin_root = tmp_path / "plugin-root"
    plugin_root.mkdir()
    cache_folder = tmp_path / "cache"
    debug_venv_path = tmp_path / "debug-venv"
    vim_commands = []
    launched_commands = []

    class Vim:
        @staticmethod
        def eval(expression):
            assert expression == "stdpath('cache')"
            return str(cache_folder)

        @staticmethod
        def command(command):
            vim_commands.append(command)
            if command.startswith("mksession! "):
                Path(command.removeprefix("mksession! ")).write_text("session")

    def launch(commands):
        launched_commands.append(commands)
        assert (cache_folder / "pytoy_reboot.json").is_file()
        assert (cache_folder / "pytoy_reboot.vim").is_file()

    monkeypatch.setitem(sys.modules, "vim", Vim)
    monkeypatch.setattr(rebooter, "get_backend_enum", lambda: BackendEnum.NVIM)
    monkeypatch.setattr(UVEnvironmentSolver, "find_workspace", lambda self, path: plugin_root)
    monkeypatch.setattr(UVEnvironmentSolver, "find_venv_path", lambda self, path: debug_venv_path)
    monkeypatch.setattr(nvim, "start_vim_detached", launch)

    PluginRebooter(plugin_root).restart()

    reboot_info = json.loads((cache_folder / "pytoy_reboot.json").read_text())
    assert reboot_info["plugin_folder"] == plugin_root.as_posix()
    assert reboot_info["debug_venv_path"] == debug_venv_path.as_posix()
    assert isinstance(reboot_info["time"], float)
    assert (cache_folder / "pytoy_reboot.vim").read_text() == "session"
    assert vim_commands == [
        f"let &runtimepath='{plugin_root.as_posix()},' . &runtimepath",
        f"mksession! {(cache_folder / 'pytoy_reboot.vim').as_posix()}",
        "qall!",
    ]

    commands = launched_commands[0]
    nvim_index = commands.index("nvim")
    assert commands[nvim_index:] == [
        "nvim",
        "--cmd",
        f"let g:pytoy_debug_venv='{debug_venv_path.as_posix()}'",
        "--cmd",
        f"let g:pytoy_reboot='{plugin_root.as_posix()}'",
        "--cmd",
        f"let &runtimepath='{plugin_root.as_posix()},' . &runtimepath",
        "-S",
        (cache_folder / "pytoy_reboot.vim").as_posix(),
    ]


def test_vim_reboot_command_delegates_to_public_package(monkeypatch):
    from pytoy.commands import devtools_commands

    calls = []

    class Package:
        def restart(self):
            calls.append("restart")

    monkeypatch.setattr(devtools_commands, "PluginRebooter", Package)

    devtools_commands.vim_reboot()

    assert calls == ["restart"]
