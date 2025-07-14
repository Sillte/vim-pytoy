import subprocess

def send_ctrl_c(pid: int):
    from pathlib import Path
    _this_folder = Path(__file__).absolute().parent
    path = _this_folder / "ctrl_c_isolated.py"
    ret = subprocess.run(["python", str(path), str(pid)]) 
    return ret.returncode == 0

