import os
import sys
import subprocess
from pathlib import Path


class VimPluginPackage:
    """Utility class for managing and developing Vim plugins.

    This class helps to detect the root directory of a Vim plugin
    and provides tools to restart Vim with the plugin correctly loaded.
    It supports automatic session saving and reinitialization during development.

    Attributes:
        root_folder (Path): The root directory of the detected Vim plugin package.
    """

    def __init__(self, start_folder: str | Path | None = None):
        """Initialize the package and detect its root directory.

        Args:
            start_folder (str | Path | None):
                The starting directory or file path to locate the Vim plugin root.
                If not specified, the current working directory is used.
        """
        if start_folder is None:
            import vim
            from pytoy.ui import to_filename

            try:
                current = to_filename(vim.eval("expand('%:p:h')"))
                start_folder = Path(current)
            except Exception:
                start_folder = Path.cwd()

        start_folder = Path(start_folder)

        root_folder = self._find_plugin_root(start_folder)
        self._root_folder = root_folder

    @property
    def root_folder(self) -> Path:
        return self._root_folder

    def restart(self, with_vimrc=True, kill_myprocess: bool = True):
        """Save the current session and restart Vim/GVim/nvim with this plugin loaded.

        Args:
            with_vimrc (bool):
                If True, the plugin's root folder is prepended to the 'runtimepath'
                before loading the user's vimrc with `--cmd` options.
                If False, starts Vim with '-u NONE'.
            kill_myprocess (bool):
                If True, terminates the current Vim process after starting the new one.

        Note:
            This is useful when reinitializing plugin state during development,
            especially when changes affect runtime behavior or require a clean environment.
        """
        _VimRebooter(self.root_folder)(
            with_vimrc=with_vimrc, kill_myprocess=kill_myprocess
        )

    def _find_plugin_root(self, start_folder: Path | None = None):
        """Search upward from the given folder to locate the plugin root.

        Args:
            start_folder (Path | None): Directory to start the search from.

        Returns:
            Path: The detected plugin root folder.

        Raises:
            ValueError: If no valid plugin structure is found in the parent hierarchy.
        """
        if start_folder is None:
            start_folder = Path.cwd()

        def _is_inner(folder: Path):
            for ext in ["py", "lua", "vim"]:
                if self._is_non_empty_iter(folder.glob(f"*.{ext}")):
                    return True
            if folder.name.startswith("python"):
                return True
            return False

        def _is_root(folder: Path):
            if any(
                (folder / elem).exists() for elem in ["plugin", "autoload", "syntax"]
            ):
                return True
            return False

        folder = start_folder

        while True:
            if _is_root(folder):
                return folder
            if (not _is_inner(folder)) or folder.parent == folder:
                raise ValueError(f"The given folder is NOT plugin:{start_folder=}")
            folder = folder.parent

    def _is_non_empty_iter(self, iteration):
        """Check whether the given iterable has any elements.

        Args:
            iteration (Iterable): The iterable to check.

        Returns:
            bool: True if the iterable has at least one item, otherwise False.

        Note: If you invoke this function, iteration is consumed (corrupted).
        """
        it = iter(iteration)
        try:
            next(it)
        except StopIteration:
            return False
        return True


class _VimRebooter:
    """Perform rebooting of `vim/nvim/gvim`.

    When the activation is carried out via this function.
    `g:pytoy_reboot = 1` is added for the spawned (n/g) vim.

    [NOTE]: (with_vimrc=True)
        Sometimes, plugin loaders `prepend` their configuration path
        to the first `rtp` / `runtimepath`.
        If the plugin loader uses this kind of mechanism,
        the idea the path is prepended as the initialization of `(n/g)vim` fails.
        To curcumvent this situation please use the defined variable
        `g:pytoy_reboot=1` to notify the plugin manager, and it does not
        override the prepended path.

    * `debug`: Please see `scriptnames` / `echo &runtimepath`.
    """

    def __init__(self, root_folder: Path):
        self.root_folder = Path(root_folder)

    def __call__(self, with_vimrc: bool = True, kill_myprocess: bool = True):
        """
        When `with_vimrc` = True, please refer to the docstring of the class.
        """
        import vim

        cache_folder = Path.home() / ".cache/vim"

        if not cache_folder.exists():
            cache_folder.mkdir(parents=True)
        session_file = cache_folder / "devplugin.vim"
        vim.command(f"mksession! {session_file.as_posix()}")

        if int(vim.eval("&term == 'builtin_gui'")):
            app = "gvim"
            is_gui = True
        else:
            is_gui = False
            if int(vim.eval("has('nvim')")):
                app = "nvim"
            else:
                app = "vim"
        commands = [app, "--cmd", f"let g:pytoy_reboot='{self.root_folder.as_posix()}'"]
        if with_vimrc:
            commands += [
                "--cmd",
                f"let &runtimepath='{self.root_folder.as_posix()},' . &runtimepath",
            ]
        else:
            commands += ["-u", "NONE"]
        commands += ["-S", f"{session_file.as_posix()}"]

        if not is_gui:
            if sys.platform.startswith("win"):
                consoles = ["start", "cmd", "/k"]
            elif sys.platform.startswith("linux"):
                consoles = ["x-terminal-emulator", "-e"]
            else:
                raise RuntimeError("Unrecognized platform")
            commands = consoles + commands

        _start_vim_detached(commands)

        if kill_myprocess:
            vim.command("qall!")


def _start_vim_detached(cmd):
    if sys.platform.startswith("win"):
        DETACHED_PROCESS = 0x00000008
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=DETACHED_PROCESS,
            shell=True,
        )
    else:
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            preexec_fn=os.setpgrp,
            shell=False,
        )


if __name__ == "__main__":
    pass
