
python3 << EOF
# Makeshift tests for CommandManager.register / exist / deregister.
import vim 
from pytoy.command import CommandManager
c_name = "HOGEHOGECOMMAND"
VVV = 0

CommandManager.deregister(c_name, no_exist_ok=True)

@CommandManager.register(name=c_name)
def func():
    pass

assert CommandManager.is_exist(c_name)

@CommandManager.register(name=c_name, exist_ok=True)
def func2(): 
    global VVV
    VVV = 100
    pass

vim.command(f"{c_name}")
assert VVV == 100
EOF
