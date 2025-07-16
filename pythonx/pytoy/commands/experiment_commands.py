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

        from pytoy.lib_tools.terminal_backend.impl_win import TerminalBackendWin
        from pytoy.lib_tools.terminal_backend import TerminalBackend
        from pytoy.lib_tools.terminal_backend.application import InteractiveApplication, ShellApplication

        from pytoy.lib_tools.terminal_backend.line_buffers import LineBufferPyte

        if False:
            app = InteractiveApplication("python")
            impl = TerminalBackendWin(app)
            backend = TerminalBackend(impl)
            #wrapped = f"exec({cmd!r})"
        else:
            app = ShellApplication("cmd.exe")
            impl = TerminalBackendWin(app, LineBufferPyte())
            backend = TerminalBackend(impl)

        buffer = make_buffer(CommandTerminal.name)
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
        #if not cmd.strip():
        #    executor.interrupt()

        line1, line2 = opts.line1, opts.line2
        if not cmd.strip():
            lines = vim.eval(f"getline({line1}, {line2})")
            cmd = "\n".join(lines)

        executor.send(cmd)


