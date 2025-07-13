import vim
import os
from pathlib import Path
from pytoy.lib_tools.environment_manager import EnvironmentManager
from pytoy.ui import make_buffer
from pytoy.command import CommandManager, OptsArgument 

from pytoy.lib_tools.terminal_executor import TerminalExecutor
from pytoy.lib_tools.terminal_backend import  TerminalBackendProvider

class CommandTerminal:
    name = "__CMD__"

    executor = None

    @staticmethod
    def get_executor():
        if CommandTerminal.executor:
            return CommandTerminal.executor
        buffer = make_buffer(CommandTerminal.name)
        backend = TerminalBackendProvider().make_terminal(command="cmd.exe")
        executor = TerminalExecutor(buffer, backend)
        CommandTerminal.executor = executor
        return executor


    @CommandManager.register(name="CMD", range=True)
    @staticmethod
    def send(opts: OptsArgument):
        executor = CommandTerminal.get_executor()
        if not executor.alive:
            executor.start()

        # [NOTE]: this specification should be discussed.
        cmd = opts.args
        if not cmd.strip():
            executor.interrupt()

        line1, _ = opts.line1, opts.line2
        if not cmd.strip():
            cmd = vim.eval(f"getline({line1})")
        executor.send(cmd)


