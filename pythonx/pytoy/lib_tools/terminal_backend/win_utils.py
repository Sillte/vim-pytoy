import time
import subprocess

def send_ctrl_c(pid: int):
    from pathlib import Path
    _this_folder = Path(__file__).absolute().parent
    path = _this_folder / "ctrl_c_isolated.py"
    ret = subprocess.run(["python", str(path), str(pid)]) 
    return ret.returncode == 0


def find_children(parent_pid: int) -> list[int]:
    """Return the list of children process.
    """
    import psutil
    try:
        parent = psutil.Process(parent_pid)
        return [elem.pid for elem in parent.children(recursive=True)]
    except psutil.NoSuchProcess:
        return []


def force_kill(pid: int):
    try:
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except subprocess.CalledProcessError:
        print(f"⚠️ Failed to kill PID {pid}")
