import subprocess

def send_ctrl_c(pid: int):
    from pathlib import Path
    _this_folder = Path(__file__).absolute().parent
    path = _this_folder / "ctrl_c_isolated.py"
    ret = subprocess.run(["python", str(path), str(pid)]) 
    return ret.returncode == 0


def focus_gvim():
    """Bring current GVim window to front.
    Works only in GVim. No external dependencies.
    """
    import ctypes
    import ctypes.wintypes
    import os

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    SW_SHOW = 5

    SetForegroundWindow = user32.SetForegroundWindow
    ShowWindow = user32.ShowWindow
    EnumWindows = user32.EnumWindows
    GetWindowThreadProcessId = user32.GetWindowThreadProcessId
    IsWindowVisible = user32.IsWindowVisible
    IsWindowEnabled = user32.IsWindowEnabled
    #AttachThreadInput = user32.AttachThreadInput
    #GetCurrentThreadId = kernel32.GetCurrentThreadId

    my_pid = os.getpid()
    hwnds = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.c_void_p)
    def enum_proc(hwnd, lParam):
        _ = lParam
        pid = ctypes.wintypes.DWORD()
        GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        visible = IsWindowVisible(hwnd)
        enabled = IsWindowEnabled(hwnd)
        if pid.value == my_pid and visible and enabled:
            hwnds.append(hwnd)
        return True

    EnumWindows(enum_proc, None)

    if hwnds:
        hwnd = hwnds[0]
        ShowWindow(hwnd, SW_SHOW)
        SetForegroundWindow(hwnd)
