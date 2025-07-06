# """EnvironmentManager.
# This class handles the properties regaled to the `env` parameters of `subprocess`.
# As of 2025/05, this class handles `uv` and `virtualenv`.
# """

import os
from pathlib import Path
from typing import Callable
import subprocess
from enum import Enum
import vim
from pytoy.ui import lightline_utils


class UvMode(str, Enum):
    UNDEFINED = "undefined"
    ON = "on"
    OFF = "off"


class EnvironmentManager:
    # Singleton.(Thread unsafe.)
    __cache = None

    def __new__(cls):
        if cls.__cache is None:
            self = object.__new__(cls)
            cls.__cache = self
            self._init()
        else:
            self = cls.__cache
        return self

    def _init(self):
        self._uv_mode = UvMode.UNDEFINED
        self._prev_venv_path = None

    def get_uv_venv(self, path: str | Path | None = None) -> Path | None:
        """Return the environment `uv run` uses if it has virtual envrinment. 

        # [TODO] handling of `--package`.
        """
        if path is None:
            path = Path.cwd()

        ret = subprocess.run(
            'uv run python -c "import sys; print(sys.executable)"',
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=os.environ,
            text=True,
            shell=True,
        )
        try:
            python_path = Path(ret.stdout.strip())
        except Exception as e: 
            print(e)
            return None
        if all(
            (python_path.parent / name).exists()
            for name in ["activate", "activate.bat"]
        ):
            # It should be virual environment.
            return python_path.parent.parent
        else:
            # Not virtual environment.
            return None

    def get_command_wrapper(self, force_uv: bool | None = False) -> Callable[[str], str]:
        # [NOTE]: In the future, parameter may become desirable.
        # Consider `--package option`

        if force_uv is True or self.get_uv_mode() == UvMode.ON:
            return lambda cmd: f"uv run {cmd}"
        else:
            return lambda cmd: cmd

    def on_uv_mode_on(self):
        """Hook function when `uv_mode` becomes on.
        Handling the global state of VIM.
        """

        uv_mode = "uv-mode"
        if not lightline_utils.is_registered(uv_mode):
            lightline_utils.register(uv_mode)
        # Change the environment of `JEDI`.
        venv_path = self.get_uv_venv()
        prev_path = vim.vars.get("g:jedi#environment_path")
        if prev_path:
            self._prev_venv_path = prev_path
        if venv_path: 
            vim.vars["g:jedi#environment_path"] = venv_path.as_posix()

    def on_uv_mode_off(self):
        """Hook function when `uv_mode` becomes off.
        Handling the global state of VIM.
        """
        
        uv_mode = "uv-mode"
        if lightline_utils.is_registered(uv_mode):
            lightline_utils.deregister(uv_mode)

        # Change the environment of `JEDI`.
        if self._prev_venv_path:
            vim.vars["g:jedi#environment_path"] = self._prev_venv_path
        else:
            vim.vars["g:jedi#environment_path"] = "auto"

    def set_uv_mode(self, uv_mode: UvMode):
        prev_mode = self._uv_mode
        self._uv_mode = uv_mode
        if prev_mode != uv_mode and self._uv_mode == UvMode.ON:
            self.on_uv_mode_on()
        elif prev_mode != uv_mode and self._uv_mode == UvMode.OFF:
            self.on_uv_mode_off()
        return self._uv_mode


    def get_uv_mode(self):
        if self._uv_mode == UvMode.UNDEFINED:
            if self.get_uv_venv():
                self.set_uv_mode(UvMode.ON)
            else:
                self.set_uv_mode(UvMode.OFF)
        return self._uv_mode

    def toggle_uv_mode(self):
        if self._uv_mode == UvMode.UNDEFINED:
            return self.get_uv_mode()
        if self._uv_mode == UvMode.ON:
            return self.set_uv_mode(UvMode.OFF)
        else:
            return self.set_uv_mode(UvMode.ON)


if __name__ == "__main__":
    manager = EnvironmentManager()
    print(manager.get_command_wrapper()("cmd"))
