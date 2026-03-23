python3 << EOF
# Makeshift tests for CommandManager.register / exist / deregister.
import vim 
from pytoy.shared.lib.function import FunctionRegistry

def add(*args) -> str:
    return "#$#$#".join(args)
    
data = FunctionRegistry.register(add)

result = vim.eval(f"{data.impl_name}('dsrre', 'fafae')")
print("Result from vim:", result)

result = vim.eval(f"{data.impl_name}('dsrre', 'fafae')")

EOF
