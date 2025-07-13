"""Since this sending key codes may interrupt
the global state of process.
So, 

**multiprocessing** is not yet tried, 
but it seems work when this is called via `subprocess`. 
"""
import sys
import ctypes
import time

pid = int(sys.argv[1])
kernel32 = ctypes.windll.kernel32
kernel32.FreeConsole()
kernel32.AttachConsole(pid)
kernel32.SetConsoleCtrlHandler(None, True)
kernel32.GenerateConsoleCtrlEvent(0, 0)
time.sleep(0.05)
kernel32.SetConsoleCtrlHandler(None, False)
kernel32.FreeConsole()
