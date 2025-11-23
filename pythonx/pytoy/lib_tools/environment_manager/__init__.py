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
from pytoy.lib_tools.utils import get_current_directory


class UvMode(str, Enum):
    UNDEFINED = "undefined"
    ON = "on"
    OFF = "off"
    
def _add_uv_path_fallback() -> bool:
    """
    side-effects: updating of `os.envioron['PATH']
    """
    ret = subprocess.run("bash -lic 'which uv'", shell=True, stdout=subprocess.PIPE, text=True)
    if ret.returncode != 0:
        return False
    folder = Path(ret.stdout.strip()).parent.as_posix()
    current_path = os.environ.get('PATH', '')
    new_path = f"{folder}{os.pathsep}{current_path}"
    os.environ['PATH'] = new_path
    vim.command(f'let $PATH="{new_path}"')
    return True


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
            path = get_current_directory()
            
        def _to_python_path() -> Path | None:
            ret = subprocess.run(
                'uv run python -c "import sys; print(sys.executable)"',
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                env=os.environ,
                cwd=path, 
                text=True,
                shell=True,
            )
            if ret.returncode == 0:
                return Path(ret.stdout.strip())
            return None

        if not (python_path := _to_python_path()):
            # Maybe `bash` is not applied here.
            _add_uv_path_fallback()
            python_path = _to_python_path()
        if not python_path:
            return None

        if all(
            (python_path.parent / name).exists()
            for name in ["activate", "activate.bat"]
        ):
            # It should be virtual environment.
            return python_path.parent.parent
        else:
            # Not virtual environment.
            return None

    def get_command_wrapper(
        self, force_uv: bool | None = False
    ) -> Callable[[str], str]:
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
        

def term_start():
    import sys
    from pytoy.ui.utils import to_filepath
    from pytoy.ui.ui_enum import get_ui_enum, UIEnum
    if get_ui_enum() != UIEnum.VIM:
        raise ValueError("This funciton is only for `VIM`.")
    
    venv_folder = EnvironmentManager().get_uv_venv()
    if not venv_folder:
        raise ValueError("Cannot find the `venv_folder`.")
    if sys.platform == "win32":

        activate_path = venv_folder / "Scripts" / "activate"
    else:
        activate_path = venv_folder / "bin" / "activate"

    number = vim.eval(r"term_start(&shell)")

    def _to_slash_path(path):
        path = Path(path)
        result = str(path).replace("\\", "/")
        return result

    path = _to_slash_path(activate_path)
    keys = rf"{_to_slash_path(path)} \<CR>"
    vim.eval(rf'term_sendkeys({number}, "{keys}")')


if __name__ == "__main__":
    manager = EnvironmentManager()

