"""PyTestCommand
"""

from pytoy.command_utils import CommandManager

@CommandManager.register(name="Pytest")
class PyTestCommand:
    name = "Pytest"
    def __call__(self, *args):
        if not args:
            command_type = "func"
        else:
            command_type = args[0]
        from pytoy import pytest_runall, pytest_runfile, pytest_runfunc
        if command_type == "func":
            pytest_runfunc()
        elif command_type == "file":
            pytest_runfile()
        elif command_type == "all":
            pytest_runall()
        else:
            raise ValueError(f"Specified `command_type` is not valid.")

    def customlist(self, arg_lead:str, cmd_line: str, cursor_pos:int):
        candidates = ["func", "file", "all"]
        valid_candidates = [elem for elem in candidates if elem.startswith(arg_lead)]
        if valid_candidates:
            return valid_candidates
        return candidates
        
        # For debug.
        print("arg_lead", arg_lead)
        print("cmd_line", cmd_line)
        print("cursor_pos", cursor_pos)
        return ["func", "file", "all"]
