from typing import Callable
type CommandWrapper = Callable[[str], str]

naive_command_wrapper = lambda cmd: cmd

