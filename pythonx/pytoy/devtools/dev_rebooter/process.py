import os
import subprocess
import sys


def start_vim_detached(command: list[str]) -> None:
    if sys.platform.startswith("win"):
        detached_process = 0x00000008
        subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=detached_process,
            shell=True,
        )
    else:
        subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            preexec_fn=os.setpgrp,
            shell=False,
        )
