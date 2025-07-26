import os
import sys
import subprocess


class VimRebooter:
    def __init__(self):
        pass

    def __call__(self):
        import vim
        from pytoy.ui import get_ui_enum, UIEnum

        if get_ui_enum() == UIEnum.VSCODE:
            from pytoy.ui.vscode.api import Api

            api = Api()
            api.action("vscode-neovim.restart")
            return

        if int(vim.eval("&term == 'builtin_gui'")):
            is_gui = True
            app = "gvim"
        else:
            is_gui = False
            if int(vim.eval("has('nvim')")):
                app = "nvim"
            else:
                app = "vim"
        commands = None
        if sys.platform.startswith("win32"):
            if not is_gui:
                commands = ["start", "cmd", "/k", app]
            else:
                commands = [app]
        elif sys.platform.startswith("linux"):
            if not is_gui:
                commands = None
            elif sys.platform.startswith("linux"):
                commands = ["x-terminal-emulator", "-e", app]
        else:
            raise RuntimeError("Not Implemented")

        if commands:
            _start_vim_detached(commands)

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
